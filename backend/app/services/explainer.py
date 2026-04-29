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
    Atomically increment the daily counter if below ``limit``.

    Uses ``UPDATE … WHERE call_count < limit`` so concurrent requests cannot
    overshoot; first call of the day ``INSERT``s a row (``IntegrityError`` →
    retry ``UPDATE``). Safe on SQLite (tests) and Postgres (production).
    """
    from sqlalchemy import insert, update
    from sqlalchemy.exc import IntegrityError

    from backend.app.db.models import LLMUsage

    if limit <= 0:
        logger.warning("LLM quota disabled (limit<=0) | user_id=%s", user_id)
        return False

    today = date.today().isoformat()

    upd = (
        update(LLMUsage)
        .where(LLMUsage.user_id == user_id)
        .where(LLMUsage.period_date == today)
        .where(LLMUsage.call_count < limit)
        .values(call_count=LLMUsage.call_count + 1)
    )
    result = db.execute(upd)
    if result.rowcount == 1:
        db.commit()
        return True

    try:
        db.execute(
            insert(LLMUsage).values(
                user_id=user_id,
                period_date=today,
                call_count=1,
            )
        )
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        result = db.execute(upd)
        if result.rowcount == 1:
            db.commit()
            return True

        row = (
            db.query(LLMUsage)
            .filter(LLMUsage.user_id == user_id, LLMUsage.period_date == today)
            .first()
        )
        cnt = row.call_count if row else 0
        logger.warning(
            "LLM quota exceeded | user_id=%s date=%s count=%d limit=%d",
            user_id,
            today,
            cnt,
            limit,
        )
        return False


# ---------------------------------------------------------------------------
# Output validation
# ---------------------------------------------------------------------------
def _validate_output(raw: dict) -> tuple[dict, bool]:
    """
    Validate and coerce the LLM output against LLMExplanation.
    Returns (dict, True) on success, or (_SAFE_FALLBACK copy, False) on failure.
    """
    from backend.app.schemas.prediction import LLMExplanation

    try:
        validated = LLMExplanation(**raw)
        return validated.model_dump(), True
    except (ValidationError, TypeError) as exc:
        logger.warning("LLM output failed schema validation: %s | raw=%s", exc, raw)
        return dict(_SAFE_FALLBACK), False


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
) -> tuple[dict, str]:
    """
    Generate an LLM-powered investment explanation.

    Quota is enforced when both `user_id` and `db` are provided.
    If the caller is exempt (admin / api_key) or quota is not configured,
    the LLM is called unconditionally.

    Returns (explanation_dict, status) where status is one of:
      - "ok" — LLM output validated
      - "quota_exhausted" — daily limit reached (same shape as _QUOTA_FALLBACK)
      - "unavailable" — no API key, LLM error, invalid JSON, or schema failure

    The explanation dict always has the same five keys as _SAFE_FALLBACK.
    """
    # ── 1. Quota gate ────────────────────────────────────────────────────────
    if user_id and db is not None:
        limit = _resolve_quota_limit(role, auth_method)
        if limit is not None:
            allowed = _check_and_increment(db, user_id, limit)
            if not allowed:
                return dict(_QUOTA_FALLBACK), "quota_exhausted"

    # ── 2. Build prompt and call OpenAI ─────────────────────────────────────
    prompt = build_prompt(data)
    client = _get_openai_client()

    if client is None:
        logger.warning("LLM client unavailable: OPENAI_API_KEY not set")
        return dict(_SAFE_FALLBACK), "unavailable"

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
        return dict(_SAFE_FALLBACK), "unavailable"
    except Exception as exc:
        logger.error("LLM API call failed: %s", exc, exc_info=True)
        return dict(_SAFE_FALLBACK), "unavailable"

    # ── 3. Validate output schema ────────────────────────────────────────────
    out, ok = _validate_output(raw_dict)
    return out, "ok" if ok else "unavailable"
