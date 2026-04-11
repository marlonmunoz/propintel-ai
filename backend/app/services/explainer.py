import json
import logging
import os
from datetime import date

from openai import OpenAI
from pydantic import ValidationError

logger = logging.getLogger("propintel")

# ---------------------------------------------------------------------------
# Tier quotas — override via environment variables without redeploying.
# Set LLM_QUOTA_FREE=0 to disable the LLM for free users entirely.
# ---------------------------------------------------------------------------
_QUOTA_FREE: int = int(os.getenv("LLM_QUOTA_FREE", "10"))    # calls / day
_QUOTA_PAID: int = int(os.getenv("LLM_QUOTA_PAID", "200"))   # calls / day

# Safe fallback returned whenever the LLM is unavailable or its output is invalid.
_SAFE_FALLBACK: dict = {
    "summary": "AI explanation unavailable.",
    "opportunity": "N/A",
    "risks": "N/A",
    "recommendation": "Hold",
    "confidence": "Low",
}

# Fallback returned when a user's daily quota is exhausted.
_QUOTA_FALLBACK: dict = {
    "summary": (
        "Daily AI explanation quota reached. "
        "Upgrade to a paid plan for more analyses."
    ),
    "opportunity": "N/A",
    "risks": "N/A",
    "recommendation": "Hold",
    "confidence": "Low",
}


# ---------------------------------------------------------------------------
# OpenAI client
# ---------------------------------------------------------------------------
def _get_openai_client() -> OpenAI | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


# ---------------------------------------------------------------------------
# Prompt builder — all inputs are numeric / model-derived; no free-form user
# text is included, which keeps prompt-injection risk very low.
# ---------------------------------------------------------------------------
def build_prompt(data: dict) -> str:
    drivers = data.get("top_drivers", [])
    drivers_text = ", ".join(drivers) if drivers else "No key drivers identified"
    return f"""
You are a senior real estate investment analyst working at a top-tier investment firm.

Your job is to evaluate property investment opportunities using quantitative model outputs and provide clear, professional, and data-driven insights.

--- PROPERTY DATA ---
Predicted Price: {data['predicted_price']}
Market Price: {data['market_price']}
ROI Estimate: {data['roi_estimate']}%
Investment Score: {data['investment_score']}

Score Interpretation Guide:
- 0 to 20 = Very weak investment profile
- 21 to 40 = Weak / speculative
- 41 to 60 = Mixed / moderate
- 61 to 80 = Strong
- 81 to 100 = Excellent

Key Drivers:
{drivers_text}

--- OUTPUT FORMAT (STRICT JSON FORMAT) ---
{{
    "summary": "Clear 1-2 sentence investment conclusion",
    "opportunity": "Specific upside potential and why it exists",
    "risks": "Concrete risks or uncertainties that could impact returns",
    "recommendation": "Buy, Hold, or Avoid",
    "confidence": "Low, Medium, or High"
}}

--- RULES ---
- NEVER contradict the provided numerical data
- DO NOT return anything outside JSON
- Your entire response MUST be a valid JSON object. No text before or after.
- DO NOT include explanations or commentary outside JSON
- Be concise, precise, and professional
- Avoid generic statements - tie reasoning to the provided data
- Interpret the investment score consistently using the score guide above
- Scores below 20 should not be described as strong, favorable, or attractive
- Negative ROI should materially weaken the recommendation
- recommendation MUST be exactly one of: Buy, Hold, Avoid
- confidence MUST be exactly one of: Low, Medium, High
"""


# ---------------------------------------------------------------------------
# Quota helpers
# ---------------------------------------------------------------------------
def _resolve_quota_limit(role: str, auth_method: str) -> int | None:
    """Return the daily call limit for this caller, or None for unlimited."""
    if auth_method == "api_key":
        return None  # service / admin key: unlimited
    if role == "admin":
        return None
    if role == "paid":
        return _QUOTA_PAID
    return _QUOTA_FREE  # "user" (free tier)


def _check_and_increment(db, user_id: str, limit: int) -> bool:
    """
    Return True if the call is within quota and increment the counter.
    Return False if the daily limit is already reached.
    """
    from backend.app.db.models import LLMUsage

    today = date.today().isoformat()
    row = (
        db.query(LLMUsage)
        .filter(LLMUsage.user_id == user_id, LLMUsage.period_date == today)
        .first()
    )
    if row is None:
        row = LLMUsage(user_id=user_id, period_date=today, call_count=0)
        db.add(row)
        db.flush()

    if row.call_count >= limit:
        logger.warning(
            "LLM quota exceeded | user_id=%s date=%s count=%d limit=%d",
            user_id,
            today,
            row.call_count,
            limit,
        )
        return False

    row.call_count += 1
    db.commit()
    return True


# ---------------------------------------------------------------------------
# Output validation
# ---------------------------------------------------------------------------
def _validate_output(raw: dict) -> dict:
    """
    Validate and coerce the LLM output against LLMExplanation.
    Returns the validated dict on success, or _SAFE_FALLBACK on failure.
    """
    from backend.app.schemas.prediction import LLMExplanation

    try:
        validated = LLMExplanation(**raw)
        return validated.model_dump()
    except (ValidationError, TypeError) as exc:
        logger.warning("LLM output failed schema validation: %s | raw=%s", exc, raw)
        return _SAFE_FALLBACK


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def generate_explanation(
    data: dict,
    *,
    user_id: str | None = None,
    role: str = "user",
    auth_method: str = "jwt",
    db=None,
) -> dict:
    """
    Generate an LLM-powered investment explanation.

    Quota is enforced when both `user_id` and `db` are provided.
    If the caller is exempt (admin / api_key) or quota is not configured,
    the LLM is called unconditionally.

    Always returns a dict with the same five keys as _SAFE_FALLBACK so callers
    never need to handle None or a missing-key response.
    """
    # ── 1. Quota gate ────────────────────────────────────────────────────────
    if user_id and db is not None:
        limit = _resolve_quota_limit(role, auth_method)
        if limit is not None:
            allowed = _check_and_increment(db, user_id, limit)
            if not allowed:
                return _QUOTA_FALLBACK

    # ── 2. Build prompt and call OpenAI ─────────────────────────────────────
    prompt = build_prompt(data)
    client = _get_openai_client()

    if client is None:
        logger.warning("LLM client unavailable: OPENAI_API_KEY not set")
        return _SAFE_FALLBACK

    try:
        response = client.responses.create(
            model="gpt-5.4-mini",
            input=prompt,
            text={"format": {"type": "json_object"}},
            max_output_tokens=300,
        )
        raw_text = response.output_text
        raw_dict = json.loads(raw_text)

    except json.JSONDecodeError as exc:
        logger.error("LLM returned non-JSON output: %s", exc)
        return _SAFE_FALLBACK
    except Exception as exc:
        logger.error("LLM API call failed: %s", exc, exc_info=True)
        return _SAFE_FALLBACK

    # ── 3. Validate output schema ────────────────────────────────────────────
    return _validate_output(raw_dict)
