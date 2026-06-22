"""Founder/admin notifications via Resend (best-effort, fire-and-forget).

Used for out-of-band business signals — e.g. Stripe billing events — that the
operator wants delivered to their inbox.  Sends are intentionally best-effort:
any failure (missing key, network error, Resend rejection) is logged and
swallowed so the caller is never broken by an email problem.  This matters most
for the Stripe webhook: if a notification raised, FastAPI would return 500 and
Stripe would retry the (already-processed) event.

Configuration (all reused from the existing contact-form setup):
  RESEND_API_KEY      — required; without it sends are skipped.
  CONTACT_FROM_EMAIL  — verified "From" address (shared with the contact form).
  BILLING_NOTIFY_EMAIL — recipient inbox; defaults to marlon@propintel-ai.com.
"""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger("propintel")

_RESEND_API_URL = "https://api.resend.com/emails"
_DEFAULT_FROM = "PropIntel AI <noreply@propintel-ai.com>"
_DEFAULT_NOTIFY_TO = "marlon@propintel-ai.com"


def admin_notify_email() -> str:
    """Resolve the operator inbox for admin notifications."""
    return (os.getenv("BILLING_NOTIFY_EMAIL") or _DEFAULT_NOTIFY_TO).strip()


async def send_admin_email(subject: str, html_body: str) -> bool:
    """Send a notification email to the operator inbox. Never raises.

    Returns True if Resend accepted the message, False otherwise (including when
    RESEND_API_KEY is unset).  Callers should treat the result as advisory only.
    """
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        logger.warning("send_admin_email skipped: RESEND_API_KEY not set")
        return False

    from_email = (os.getenv("CONTACT_FROM_EMAIL") or _DEFAULT_FROM).strip()
    to_email = admin_notify_email()

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                _RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except Exception as exc:  # noqa: BLE001 — notifications must never raise
        logger.error("send_admin_email failed (network): %s", exc)
        return False

    if resp.status_code not in (200, 201):
        logger.error(
            "send_admin_email Resend error | status=%s body=%s",
            resp.status_code,
            resp.text[:300],
        )
        return False

    logger.info("Admin notification sent | subject=%r to=%s", subject, to_email)
    return True
