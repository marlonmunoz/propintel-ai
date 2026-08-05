"""Tests for founder billing notifications (Option 1 — Resend email).

Covers three layers without any real Stripe or Resend network calls:
  1. send_admin_email()           — the reusable, never-raises email helper.
  2. _build_billing_notification() — subject/body construction + filtering.
  3. POST /billing/webhook         — that a notable event SCHEDULES the email
                                     and that webhook processing is unaffected.
"""

from __future__ import annotations

import os

# Must be set before backend.app.db.database is imported anywhere (including
# transitively via backend.app.main) — that module binds its engine to
# DATABASE_URL once, at import time. Also enforced repo-wide by the root
# conftest.py, but set explicitly here too so this file is safe even when
# run standalone via a tool that bypasses conftest discovery.
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

import backend.app.db.models  # noqa: F401 — register all tables on Base before create_all
from backend.app.db.database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

from backend.app.main import app
import backend.app.api.billing as billing
from backend.app.services import notifications
from backend.app.db.models import BillingCustomer, Profile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _async_ctx_client(mock_resp):
    """Wrap a mock response in an async context manager like httpx.AsyncClient."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


def _seed_profile(db, user_id: str, email: str) -> None:
    if db.query(Profile).filter(Profile.id == user_id).first() is None:
        db.add(Profile(id=user_id, email=email, role="paid"))
        db.commit()


# ---------------------------------------------------------------------------
# 1. send_admin_email — the email helper
# ---------------------------------------------------------------------------

def test_send_admin_email_skips_without_api_key(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    result = asyncio.run(notifications.send_admin_email("subj", "<p>body</p>"))
    assert result is False


def test_send_admin_email_success(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    monkeypatch.setenv("BILLING_NOTIFY_EMAIL", "marlon@propintel-ai.com")
    ok_resp = MagicMock()
    ok_resp.status_code = 200
    ok_resp.text = '{"id":"evt_1"}'
    ctx = _async_ctx_client(ok_resp)

    with patch("backend.app.services.notifications.httpx.AsyncClient", return_value=ctx):
        result = asyncio.run(notifications.send_admin_email("subj", "<p>body</p>"))

    assert result is True
    # Recipient routed to the configured founder inbox.
    sent_payload = ctx.__aenter__.return_value.post.call_args.kwargs["json"]
    assert sent_payload["to"] == ["marlon@propintel-ai.com"]
    assert sent_payload["subject"] == "subj"


def test_send_admin_email_swallows_resend_error(monkeypatch):
    """A non-2xx Resend response returns False but never raises."""
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    bad_resp = MagicMock()
    bad_resp.status_code = 403
    bad_resp.text = '{"message":"Forbidden"}'
    ctx = _async_ctx_client(bad_resp)

    with patch("backend.app.services.notifications.httpx.AsyncClient", return_value=ctx):
        result = asyncio.run(notifications.send_admin_email("subj", "<p>body</p>"))

    assert result is False


def test_send_admin_email_swallows_network_error(monkeypatch):
    """A network exception is caught and reported as False, not raised."""
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(side_effect=RuntimeError("boom"))
    ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("backend.app.services.notifications.httpx.AsyncClient", return_value=ctx):
        result = asyncio.run(notifications.send_admin_email("subj", "<p>body</p>"))

    assert result is False


# ---------------------------------------------------------------------------
# 2. _build_billing_notification — subject/body + filtering
# ---------------------------------------------------------------------------

def test_build_notification_new_subscriber():
    db = next(get_db())
    try:
        data_obj = {"mode": "subscription", "customer_email": "new@example.com"}
        out = billing._build_billing_notification(
            db, event_type="checkout.session.completed", user_id=None, data_obj=data_obj
        )
    finally:
        db.close()
    assert out is not None
    subject, body = out
    assert "New PropIntel Pro subscriber" in subject
    assert "new@example.com" in subject
    assert "subscribed to PropIntel AI Pro" in body


def test_build_notification_cancellation_prefers_profile_email():
    uid = str(uuid.uuid4())
    db = next(get_db())
    try:
        _seed_profile(db, uid, "canceller@example.com")
        data_obj = {"id": "sub_x", "customer": "cus_x", "status": "canceled"}
        out = billing._build_billing_notification(
            db, event_type="customer.subscription.deleted", user_id=uid, data_obj=data_obj
        )
    finally:
        db.close()
    assert out is not None
    subject, body = out
    assert "canceled" in subject.lower()
    assert "canceller@example.com" in subject


def test_build_notification_payment_failed():
    db = next(get_db())
    try:
        data_obj = {"customer": "cus_y", "customer_email": "late@example.com"}
        out = billing._build_billing_notification(
            db, event_type="invoice.payment_failed", user_id=None, data_obj=data_obj
        )
    finally:
        db.close()
    assert out is not None
    subject, _ = out
    assert "payment failed" in subject.lower()
    assert "late@example.com" in subject


def test_build_notification_ignores_irrelevant_event():
    db = next(get_db())
    try:
        out = billing._build_billing_notification(
            db, event_type="customer.subscription.updated", user_id=None, data_obj={}
        )
        # one-time payment checkout (not a subscription) is also ignored
        out2 = billing._build_billing_notification(
            db,
            event_type="checkout.session.completed",
            user_id=None,
            data_obj={"mode": "payment"},
        )
    finally:
        db.close()
    assert out is None
    assert out2 is None


# ---------------------------------------------------------------------------
# 3. POST /billing/webhook — schedules the notification, stays healthy
# ---------------------------------------------------------------------------

def _patch_stripe_configured(monkeypatch):
    monkeypatch.setattr(billing, "_STRIPE_SECRET_KEY", "sk_test_x")
    monkeypatch.setattr(billing, "_STRIPE_WEBHOOK_SECRET", "whsec_x")


def test_webhook_cancellation_schedules_notification(monkeypatch):
    _patch_stripe_configured(monkeypatch)
    uid = str(uuid.uuid4())
    cust_id = f"cus_{uuid.uuid4().hex[:12]}"
    event_id = f"evt_{uuid.uuid4().hex[:16]}"

    db = next(get_db())
    try:
        _seed_profile(db, uid, "cancelme@example.com")
    finally:
        db.close()

    event = {
        "id": event_id,
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": f"sub_{uuid.uuid4().hex[:12]}",
                "customer": cust_id,
                "status": "canceled",
                "metadata": {"supabase_user_id": uid},
            }
        },
    }

    notify_mock = AsyncMock(return_value=True)
    with patch.object(billing.stripe.Webhook, "construct_event", return_value=event), \
         patch.object(billing, "send_admin_email", notify_mock):
        client = TestClient(app)
        resp = client.post(
            "/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "t=1,v1=fake"},
        )

    assert resp.status_code == 200
    # Background task ran and called our notification with a cancel subject.
    notify_mock.assert_awaited_once()
    subject = notify_mock.await_args.args[0]
    assert "canceled" in subject.lower()
    assert "cancelme@example.com" in subject


def test_webhook_notification_failure_does_not_break_webhook(monkeypatch):
    """A failed email send (send_admin_email → False) must not break the webhook.

    send_admin_email never raises by contract (see unit tests above); on failure
    it returns False. The webhook must still process the event and return 200.
    """
    _patch_stripe_configured(monkeypatch)
    event_id = f"evt_{uuid.uuid4().hex[:16]}"

    event = {
        "id": event_id,
        "type": "invoice.payment_failed",
        "data": {"object": {"customer": f"cus_{uuid.uuid4().hex[:12]}",
                            "customer_email": "fail@example.com"}},
    }

    failed_send = AsyncMock(return_value=False)
    with patch.object(billing.stripe.Webhook, "construct_event", return_value=event), \
         patch.object(billing, "send_admin_email", failed_send):
        client = TestClient(app)
        resp = client.post(
            "/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "t=1,v1=fake"},
        )

    assert resp.status_code == 200
    failed_send.assert_awaited_once()
