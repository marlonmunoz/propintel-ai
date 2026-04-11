"""
Admin-only operational endpoints (single-owner / internal dashboard).

All routes require require_admin — JWT users must match is_app_admin; API key
passes for CI and scripts.
"""
import os
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.core.auth import UserContext, require_admin
from backend.app.core.limiter import limiter
from backend.app.db.database import get_db
from backend.app.db.models import LLMUsage, Profile, Property

router = APIRouter(prefix="/admin", tags=["Admin"])


@limiter.limit("60/minute")
@router.get("/overview")
def admin_overview(
    request: Request,
    _: UserContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Aggregate counts for profiles, saved properties, and LLM usage (llm_usage).

    Intended for a private admin UI — not for public clients.
    """
    today = date.today().isoformat()
    week_start = (date.today() - timedelta(days=6)).isoformat()

    profiles_count = int(db.query(func.count(Profile.id)).scalar() or 0)
    properties_count = int(db.query(func.count(Property.id)).scalar() or 0)

    llm_today_total = int(
        db.query(func.coalesce(func.sum(LLMUsage.call_count), 0))
        .filter(LLMUsage.period_date == today)
        .scalar()
        or 0
    )

    llm_active_users_today = int(
        db.query(func.count(LLMUsage.id))
        .filter(LLMUsage.period_date == today, LLMUsage.call_count > 0)
        .scalar()
        or 0
    )

    daily_rows = (
        db.query(LLMUsage.period_date, func.sum(LLMUsage.call_count))
        .filter(LLMUsage.period_date >= week_start)
        .group_by(LLMUsage.period_date)
        .order_by(LLMUsage.period_date)
        .all()
    )
    llm_by_day = [
        {"period_date": row[0], "total_calls": int(row[1])} for row in daily_rows
    ]

    top_rows = (
        db.query(LLMUsage.user_id, func.sum(LLMUsage.call_count).label("calls"))
        .filter(LLMUsage.period_date >= week_start)
        .group_by(LLMUsage.user_id)
        .order_by(func.sum(LLMUsage.call_count).desc())
        .limit(20)
        .all()
    )
    llm_top_users = [
        {"user_id": uid, "calls_last_7d": int(calls)} for uid, calls in top_rows
    ]

    return {
        "profiles_count": profiles_count,
        "properties_count": properties_count,
        "llm": {
            "today_total_calls": llm_today_total,
            "today_users_with_calls": llm_active_users_today,
            "last_7_days_by_date": llm_by_day,
            "top_users_last_7_days": llm_top_users,
            "quota_free_per_day": int(os.getenv("LLM_QUOTA_FREE", "10")),
            "quota_paid_per_day": int(os.getenv("LLM_QUOTA_PAID", "200")),
        },
        "as_of": today,
    }
