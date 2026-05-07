"""
Contact-form endpoint — POST /contact.

Accepts a message from any visitor (no auth required) and delivers it to the
right inbox via Resend.  Topic routing:
  support       → support@propintel-ai.com
  partnerships  → marlon@propintel-ai.com

Rate-limited to 5 submissions / hour per IP to block spam while still being
permissive enough for legitimate multi-message conversations.
"""

from __future__ import annotations

import html
import logging
import os

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, field_validator

from backend.app.core.limiter import limiter

logger = logging.getLogger("propintel")

router = APIRouter(prefix="/contact", tags=["Contact"])

_RESEND_API_URL = "https://api.resend.com/emails"
_TOPIC_TO_EMAIL = {
    "support": "support@propintel-ai.com",
    "partnerships": "marlon@propintel-ai.com",
}
_TOPIC_LABEL = {
    "support": "Customer Support",
    "partnerships": "Partnerships / Press",
}


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ContactRequest(BaseModel):
    name: str
    email: EmailStr
    topic: str
    message: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name is required.")
        if len(v) > 100:
            raise ValueError("Name must be 100 characters or fewer.")
        return v

    @field_validator("topic")
    @classmethod
    def validate_topic(cls, v: str) -> str:
        if v not in _TOPIC_TO_EMAIL:
            raise ValueError("topic must be 'support' or 'partnerships'.")
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Message must be at least 10 characters.")
        if len(v) > 3000:
            raise ValueError("Message must be 3 000 characters or fewer.")
        return v


class ContactResponse(BaseModel):
    ok: bool
    message: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@limiter.limit("5/hour")
@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit contact form",
    description=(
        "Delivers the visitor's message to the appropriate inbox via Resend. "
        "No authentication required. Rate-limited to 5 submissions per hour per IP."
    ),
)
async def send_contact_message(
    request: Request,
    body: ContactRequest,
) -> ContactResponse:
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        logger.error("RESEND_API_KEY is not set — contact form email cannot be delivered")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service is temporarily unavailable. Please try again later.",
        )

    from_email = os.getenv("CONTACT_FROM_EMAIL", "PropIntel AI <noreply@propintel-ai.com>").strip()
    to_email = _TOPIC_TO_EMAIL[body.topic]
    topic_label = _TOPIC_LABEL[body.topic]

    name_safe = html.escape(body.name)
    email_safe = html.escape(str(body.email))
    message_safe = html.escape(body.message).replace("\n", "<br>")

    html_body = (
        f"<p><strong>From:</strong> {name_safe} &lt;{email_safe}&gt;</p>"
        f"<p><strong>Topic:</strong> {topic_label}</p>"
        f'<hr style="border:none;border-top:1px solid #e5e7eb;margin:16px 0">'
        f"<p>{message_safe}</p>"
        f'<hr style="border:none;border-top:1px solid #e5e7eb;margin:16px 0">'
        f'<p style="font-size:12px;color:#6b7280">Sent via PropIntel AI contact form</p>'
    )

    payload = {
        "from": from_email,
        "to": [to_email],
        "reply_to": str(body.email),
        "subject": f"[PropIntel Contact] {topic_label} — {body.name}",
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
    except httpx.TimeoutException:
        logger.error("Resend API timed out for contact form submission")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Email delivery timed out. Please try again later.",
        )
    except httpx.RequestError as exc:
        logger.error("Resend API network error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the email service. Please try again later.",
        )

    if resp.status_code not in (200, 201):
        logger.error(
            "Resend API error | status=%s body=%s", resp.status_code, resp.text[:500]
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to send message. Please try again or email us directly.",
        )

    logger.info(
        "Contact form email delivered | topic=%s to=%s sender_name=%s",
        body.topic,
        to_email,
        body.name,
    )
    return ContactResponse(ok=True, message="Message sent. We'll get back to you soon.")
