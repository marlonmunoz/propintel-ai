"""
Stripe billing — Checkout, Customer Portal, webhooks, status.

Hosted Checkout / Portal only (no card data touches this server).
Requires STRIPE_SECRET_KEY, STRIPE_PRICE_PAID_MONTHLY; optional STRIPE_WEBHOOK_SECRET
until /billing/webhook is wired with Stripe CLI or Dashboard.
"""

from __future__ import annotations

import html
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import stripe
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.auth import (
    UserContext,
    get_current_user,
    get_current_user_with_role,
    is_app_admin,
)
from backend.app.core.limiter import limiter
from backend.app.db.database import get_db
from backend.app.db.models import BillingCustomer, BillingEvent, Profile
from backend.app.services.notifications import send_admin_email

logger = logging.getLogger("propintel")

router = APIRouter(prefix="/billing", tags=["Billing"])

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "").strip()
_STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
_STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_PAID_MONTHLY", "").strip()
_STRIPE_AUTOMATIC_TAX = os.getenv("STRIPE_AUTOMATIC_TAX", "1").strip().lower() in (
    "1",
    "true",
    "yes",
)

# Use `or` so an accidentally empty env var still falls back to the default
# (os.getenv returns "" for an explicitly set-but-empty var, which is falsy).
_DEFAULT_FE = (os.getenv("BILLING_FRONTEND_ORIGIN") or "http://127.0.0.1:5174").rstrip("/")
_BILLING_SUCCESS_URL = (os.getenv("BILLING_SUCCESS_URL") or f"{_DEFAULT_FE}/billing/success").strip()
_BILLING_CANCEL_URL = (os.getenv("BILLING_CANCEL_URL") or f"{_DEFAULT_FE}/billing/canceled").strip()
_BILLING_PORTAL_RETURN_URL = (
    os.getenv("BILLING_PORTAL_RETURN_URL") or f"{_DEFAULT_FE}/profile"
).strip()

if _STRIPE_SECRET_KEY:
    stripe.api_key = _STRIPE_SECRET_KEY


def _require_stripe_configured() -> None:
    if not _STRIPE_SECRET_KEY or not _STRIPE_PRICE_ID:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured (missing STRIPE_SECRET_KEY or STRIPE_PRICE_PAID_MONTHLY).",
        )


async def _require_jwt_user(user: UserContext = Depends(get_current_user)) -> UserContext:
    if user.auth_method != "jwt" or not user.user_id:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Billing requires a signed-in user (Bearer token).",
        )
    return user


def _dt_from_unix(ts: int | float | None) -> datetime | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _subscription_price_id(sub: dict[str, Any]) -> str | None:
    items = sub.get("items") or {}
    data = items.get("data") if isinstance(items, dict) else None
    if not data or not isinstance(data, list) or not data:
        return None
    first = data[0] if isinstance(data[0], dict) else {}
    price = first.get("price")
    if isinstance(price, dict):
        return price.get("id")
    if isinstance(price, str):
        return price
    return None


def _profile_by_user_id(db: Session, user_id: str) -> Profile | None:
    uid = (user_id or "").strip()
    if not uid:
        return None
    return (
        db.query(Profile)
        .filter(func.lower(Profile.id) == uid.lower())
        .first()
    )


def _set_profile_role(db: Session, user_id: str, role: str) -> None:
    """Set profiles.role from Stripe subscription status.

    Never demotes an existing "admin" — Stripe billing state should only
    ever toggle a profile between "user" and "paid". Without this guard, an
    admin who tests checkout and later cancels (or lets a test subscription
    expire) would be silently demoted to "user" and lose admin access.
    """
    profile = _profile_by_user_id(db, user_id)
    if profile is not None and (profile.role or "").strip().lower() != "admin":
        profile.role = role  # type: ignore[assignment]


def _ensure_stripe_customer(db: Session, user: UserContext) -> BillingCustomer:
    """Return billing_customers row, creating Stripe Customer + DB row if needed."""
    row = (
        db.query(BillingCustomer)
        .filter(BillingCustomer.user_id == user.user_id)
        .first()
    )
    if row:
        return row

    _require_stripe_configured()
    customer_params: dict[str, Any] = {
        "metadata": {"supabase_user_id": user.user_id or ""},
    }
    if user.email:
        customer_params["email"] = user.email
    customer = stripe.Customer.create(**customer_params)
    row = BillingCustomer(
        user_id=user.user_id,
        stripe_customer_id=customer.id,
        stripe_subscription_id=None,
        subscription_status=None,
        price_id=None,
        current_period_end=None,
        cancel_at_period_end=False,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        # Two concurrent checkout requests raced; roll back and return the row
        # that the other request committed (unique constraint on stripe_customer_id).
        db.rollback()
        row = (
            db.query(BillingCustomer)
            .filter(BillingCustomer.user_id == user.user_id)
            .first()
        )
        if not row:
            # Extremely unlikely; re-raise if we genuinely can't find the row.
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail="Could not create billing record. Please try again.",
            )
        return row
    db.refresh(row)
    return row


def _resolve_user_id_from_subscription(db: Session, sub: dict[str, Any]) -> str | None:
    meta = sub.get("metadata") or {}
    if isinstance(meta, dict):
        uid = meta.get("supabase_user_id")
        if uid:
            return str(uid).strip() or None

    sub_id = sub.get("id")
    if sub_id:
        row = (
            db.query(BillingCustomer)
            .filter(BillingCustomer.stripe_subscription_id == sub_id)
            .first()
        )
        if row:
            return str(row.user_id)

    cust_id = sub.get("customer")
    if cust_id:
        row = (
            db.query(BillingCustomer)
            .filter(BillingCustomer.stripe_customer_id == cust_id)
            .first()
        )
        if row:
            return str(row.user_id)
    return None


def _sync_subscription_to_db(db: Session, user_id: str, sub: dict[str, Any]) -> None:
    """Upsert billing_customers + profiles.role from a Stripe Subscription object dict."""
    cust_id = sub.get("customer")
    if not cust_id or not user_id:
        return

    status_str = (sub.get("status") or "").strip()
    sub_id = sub.get("id")
    price_id = _subscription_price_id(sub)
    period_end = _dt_from_unix(sub.get("current_period_end"))
    cancel_at_end = bool(sub.get("cancel_at_period_end"))

    row = (
        db.query(BillingCustomer)
        .filter(BillingCustomer.user_id == user_id)
        .first()
    )
    if not row:
        row = BillingCustomer(
            user_id=user_id,
            stripe_customer_id=str(cust_id),
            stripe_subscription_id=str(sub_id) if sub_id else None,
            subscription_status=status_str or None,
            price_id=price_id,
            current_period_end=period_end,
            cancel_at_period_end=cancel_at_end,
        )
        db.add(row)
    else:
        row.stripe_customer_id = str(cust_id)  # type: ignore[assignment]
        if sub_id:
            row.stripe_subscription_id = str(sub_id)  # type: ignore[assignment]
        row.subscription_status = status_str or None  # type: ignore[assignment]
        row.price_id = price_id  # type: ignore[assignment]
        row.current_period_end = period_end  # type: ignore[assignment]
        row.cancel_at_period_end = cancel_at_end  # type: ignore[assignment]

    # Role mapping (PRICING_PLAN.md)
    if status_str in ("active", "trialing", "past_due", "unpaid"):
        _set_profile_role(db, user_id, "paid")
    elif status_str in ("canceled", "incomplete_expired"):
        _set_profile_role(db, user_id, "user")
    # incomplete (unfinished checkout), paused, etc. — do not flip role here


def _record_event(
    db: Session,
    *,
    stripe_event_id: str,
    event_type: str,
    user_id: str | None,
    payload_summary: dict[str, Any],
) -> bool:
    """
    Insert webhook audit row. Returns True if inserted, False if duplicate event id.

    ``payload_summary`` must never contain the raw Stripe payload — it is a
    small, hand-constructed dict of non-sensitive audit fields (event type,
    customer ID, etc.).  Storing the full payload would embed card-brand /
    last-4 and other PCI-adjacent data in our own Postgres table, which is
    outside Stripe's PCI-compliance boundary for connected accounts.
    """
    row = BillingEvent(
        stripe_event_id=stripe_event_id,
        event_type=event_type,
        user_id=user_id,
        payload_summary=payload_summary,
    )
    db.add(row)
    try:
        db.flush()
        return True
    except IntegrityError:
        db.rollback()
        return False


# Stripe events that trigger a founder notification email.
_NOTIFY_EVENTS = frozenset({
    "checkout.session.completed",   # new subscriber
    "customer.subscription.deleted",  # cancellation took effect
    "invoice.payment_failed",       # renewal charge failed
})


def _notification_identity(
    db: Session, user_id: str | None, data_obj: dict[str, Any]
) -> str:
    """Best-effort human identifier (email > user_id > Stripe customer)."""
    if user_id:
        profile = _profile_by_user_id(db, user_id)
        if profile is not None:
            email = (str(profile.email or "")).strip()
            if email:
                return email
    # Stripe payloads sometimes carry an email directly (checkout / invoice).
    direct = (
        data_obj.get("customer_email")
        or (data_obj.get("customer_details") or {}).get("email")
    )
    if direct:
        return str(direct).strip()
    return user_id or str(data_obj.get("customer") or "unknown user")


def _build_billing_notification(
    db: Session,
    *,
    event_type: str,
    user_id: str | None,
    data_obj: dict[str, Any],
) -> tuple[str, str] | None:
    """Return (subject, html_body) for a notable billing event, else None.

    Never raises — a notification must never interfere with webhook processing.
    """
    try:
        if event_type not in _NOTIFY_EVENTS:
            return None
        # Only subscription-mode checkouts represent a new Pro subscriber.
        if event_type == "checkout.session.completed" and data_obj.get("mode") != "subscription":
            return None

        who = html.escape(_notification_identity(db, user_id, data_obj))

        if event_type == "checkout.session.completed":
            headline = "New PropIntel Pro subscriber"
            subject = f"New PropIntel Pro subscriber: {who}"
            detail = f"<strong>{who}</strong> just subscribed to PropIntel AI Pro ($29/mo)."
        elif event_type == "customer.subscription.deleted":
            headline = "Subscription canceled"
            subject = f"PropIntel subscription canceled: {who}"
            detail = f"<strong>{who}</strong>'s subscription has ended — role reverted to free."
        else:  # invoice.payment_failed
            headline = "Renewal payment failed"
            subject = f"PropIntel payment failed: {who}"
            detail = f"A renewal payment failed for <strong>{who}</strong>. Stripe will retry per dunning settings."

        html_body = (
            f'<p style="font-size:16px;font-weight:600;margin:0 0 8px">{headline}</p>'
            f"<p>{detail}</p>"
            f'<hr style="border:none;border-top:1px solid #e5e7eb;margin:16px 0">'
            f'<p style="font-size:12px;color:#6b7280">Stripe event: {html.escape(event_type)} · '
            f"Automated PropIntel AI billing notification</p>"
        )
        return subject, html_body
    except Exception:  # noqa: BLE001 — never break the webhook over a notification
        logger.exception("Failed to build billing notification for %s", event_type)
        return None


# ---------------------------------------------------------------------------
# API responses
# ---------------------------------------------------------------------------


class CheckoutResponse(BaseModel):
    url: str


class PortalResponse(BaseModel):
    url: str


class BillingStatusResponse(BaseModel):
    role: str
    subscription_status: str | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@limiter.limit("10/minute")
@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout_session(
    request: Request,
    user: UserContext = Depends(_require_jwt_user),
    db: Session = Depends(get_db),
) -> CheckoutResponse:
    _require_stripe_configured()
    bc = _ensure_stripe_customer(db, user)

    success_url = _BILLING_SUCCESS_URL
    if "{CHECKOUT_SESSION_ID}" not in success_url:
        sep = "&" if "?" in success_url else "?"
        success_url = f"{success_url}{sep}session_id={{CHECKOUT_SESSION_ID}}"

    uid_str = user.user_id or ""
    checkout_params: dict[str, Any] = {
        "mode": "subscription",
        "customer": str(bc.stripe_customer_id),
        "client_reference_id": uid_str,
        "line_items": [{"price": _STRIPE_PRICE_ID, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": _BILLING_CANCEL_URL,
        "subscription_data": {"metadata": {"supabase_user_id": uid_str}},
        "metadata": {"supabase_user_id": uid_str},
    }
    if _STRIPE_AUTOMATIC_TAX:
        checkout_params["automatic_tax"] = {"enabled": True}
        # Stripe Tax: persist billing address from Checkout onto the Customer for tax calc.
        checkout_params["customer_update"] = {"address": "auto"}
        checkout_params["billing_address_collection"] = "required"
    try:
        session = stripe.checkout.Session.create(**checkout_params)
    except stripe.InvalidRequestError as exc:
        msg = (getattr(exc, "user_message", None) or str(exc) or "").strip()
        logger.warning("Stripe checkout session failed: %s", msg)
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=msg or "Stripe could not create checkout session.",
        ) from exc
    if not session.url:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Stripe did not return a checkout URL.",
        )
    return CheckoutResponse(url=session.url)


@limiter.limit("10/minute")
@router.post("/portal", response_model=PortalResponse)
def create_portal_session(
    request: Request,
    user: UserContext = Depends(_require_jwt_user),
    db: Session = Depends(get_db),
) -> PortalResponse:
    _require_stripe_configured()
    bc = (
        db.query(BillingCustomer)
        .filter(BillingCustomer.user_id == user.user_id)
        .first()
    )
    if not bc or not bc.stripe_customer_id:  # type: ignore[truthy-function]
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="No Stripe customer on file. Subscribe via Checkout first.",
        )
    portal = stripe.billing_portal.Session.create(
        customer=str(bc.stripe_customer_id),
        return_url=_BILLING_PORTAL_RETURN_URL,
    )
    if not portal.url:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail="Stripe did not return a portal URL.",
        )
    return PortalResponse(url=portal.url)


@limiter.limit("60/minute")
@router.get("/status", response_model=BillingStatusResponse)
def billing_status(
    request: Request,
    user: UserContext = Depends(get_current_user_with_role),
    db: Session = Depends(get_db),
) -> BillingStatusResponse:
    if user.auth_method != "jwt" or not user.user_id:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )
    effective = "admin" if is_app_admin(db, user) else user.role
    bc = (
        db.query(BillingCustomer)
        .filter(BillingCustomer.user_id == user.user_id)
        .first()
    )
    if not bc:
        return BillingStatusResponse(role=effective)
    return BillingStatusResponse(
        role=effective,
        subscription_status=bc.subscription_status,  # type: ignore[arg-type]
        current_period_end=bc.current_period_end,  # type: ignore[arg-type]
        cancel_at_period_end=bc.cancel_at_period_end,  # type: ignore[arg-type]
    )


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Response:
    if not _STRIPE_SECRET_KEY:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Stripe is not configured.")

    if not _STRIPE_WEBHOOK_SECRET:
        logger.warning("STRIPE_WEBHOOK_SECRET is empty — refusing webhook (configure Stripe CLI or Dashboard).")
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook endpoint not configured (set STRIPE_WEBHOOK_SECRET).",
        )

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    if not sig_header:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Missing Stripe-Signature header.")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=_STRIPE_WEBHOOK_SECRET,
        )
    except ValueError as exc:
        logger.warning("Invalid webhook payload: %s", exc)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid payload.") from exc
    except stripe.SignatureVerificationError as exc:
        logger.warning("Invalid webhook signature: %s", exc)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Invalid signature.") from exc

    # stripe v11: Event, Session, etc. all subclass dict — .get() always works.
    etype = event.get("type")
    eid = event.get("id")
    data_obj = event.get("data", {}).get("object", {})

    summary: dict[str, Any] = {"type": etype}
    user_hint: str | None = None
    if isinstance(data_obj, dict):
        if etype == "checkout.session.completed" and data_obj.get("mode") == "subscription":
            user_hint = (
                data_obj.get("client_reference_id")
                or (data_obj.get("metadata") or {}).get("supabase_user_id")
            )
            if user_hint:
                user_hint = str(user_hint).strip() or None
        elif etype in ("customer.subscription.updated", "customer.subscription.deleted"):
            user_hint = _resolve_user_id_from_subscription(db, data_obj)
        elif etype == "invoice.payment_failed":
            cust = data_obj.get("customer")
            if cust:
                summary["customer"] = str(cust)
                row = (
                    db.query(BillingCustomer)
                    .filter(BillingCustomer.stripe_customer_id == str(cust))
                    .first()
                )
                if row:
                    user_hint = str(row.user_id)

    inserted = _record_event(
        db,
        stripe_event_id=str(eid),
        event_type=str(etype),
        user_id=user_hint,
        payload_summary=summary,
    )
    if not inserted:
        return Response(status_code=200, content=json.dumps({"received": True, "duplicate": True}))

    try:
        if etype == "checkout.session.completed" and isinstance(data_obj, dict):
            if data_obj.get("mode") == "subscription":
                uid = (
                    data_obj.get("client_reference_id")
                    or (data_obj.get("metadata") or {}).get("supabase_user_id")
                )
                sub_id = data_obj.get("subscription")
                if isinstance(sub_id, dict):
                    sub_id = sub_id.get("id")
                if uid and sub_id:
                    sub = stripe.Subscription.retrieve(str(sub_id))
                    sub_dict = sub.to_dict() if hasattr(sub, "to_dict") else dict(sub)
                    _sync_subscription_to_db(db, str(uid), sub_dict)

        elif etype == "customer.subscription.updated" and isinstance(data_obj, dict):
            uid = _resolve_user_id_from_subscription(db, data_obj)
            if uid:
                _sync_subscription_to_db(db, uid, data_obj)

        elif etype == "customer.subscription.deleted" and isinstance(data_obj, dict):
            uid = _resolve_user_id_from_subscription(db, data_obj)
            if uid:
                merged = {**data_obj, "status": "canceled"}
                _sync_subscription_to_db(db, uid, merged)

        db.commit()
    except Exception:
        logger.exception("Webhook handler failed for event %s", eid)
        db.rollback()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed.",
        ) from None

    # Founder notification — best-effort, scheduled AFTER the DB commit so we
    # never email about a change that didn't persist, and AFTER the 200 is
    # returned to Stripe (BackgroundTasks) so a slow/failed email can't delay
    # or fail the webhook.  The identity lookup runs now while the DB session
    # is still open; only the network send is deferred.
    if isinstance(data_obj, dict):
        notification = _build_billing_notification(
            db, event_type=str(etype), user_id=user_hint, data_obj=data_obj
        )
        if notification is not None:
            subject, html_body = notification
            background_tasks.add_task(send_admin_email, subject, html_body)

    return Response(status_code=200, content=json.dumps({"received": True}))
