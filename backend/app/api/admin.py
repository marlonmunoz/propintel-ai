"""
Admin-only operational endpoints (single-owner / internal dashboard).

All routes require require_admin — JWT users must match is_app_admin; API key
passes for CI and scripts.
"""
import logging
import os
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from backend.app.core.auth import UserContext, require_admin
from backend.app.core.limiter import limiter
from backend.app.db.database import get_db
from backend.app.db.models import LLMUsage, MapboxUsage, Profile, Property
from backend.app.schemas.property import AdminRoleUpdate

logger = logging.getLogger("propintel")

router = APIRouter(prefix="/admin", tags=["Admin"])


@limiter.limit("60/minute")
@router.get("/overview")
def admin_overview(
    request: Request,
    _: UserContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Aggregate counts for profiles, saved properties, LLM usage (llm_usage),
    and Mapbox geocode usage (mapbox_usage).

    Intended for a private admin UI — not for public clients.
    """
    today_d = date.today()
    today = today_d.isoformat()
    week_start = (today_d - timedelta(days=6)).isoformat()
    month_start = today_d.replace(day=1).isoformat()
    mapbox_free_cap = int(os.getenv("MAPBOX_MONTHLY_FREE_REQUEST_CAP", "100000"))

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

    mapbox_payload = {
        "today_total_requests": 0,
        "today_users_with_requests": 0,
        "requests_last_7_days_total": 0,
        "requests_month_to_date_utc": 0,
        "monthly_free_requests_cap": mapbox_free_cap,
        "month_utc_label": today_d.strftime("%Y-%m"),
        "last_7_days_by_date": [],
        "top_users_last_7_days": [],
    }
    try:
        mapbox_today_total = int(
            db.query(func.coalesce(func.sum(MapboxUsage.call_count), 0))
            .filter(MapboxUsage.period_date == today)
            .scalar()
            or 0
        )

        mapbox_active_users_today = int(
            db.query(func.count(MapboxUsage.id))
            .filter(MapboxUsage.period_date == today, MapboxUsage.call_count > 0)
            .scalar()
            or 0
        )

        mapbox_daily_rows = (
            db.query(MapboxUsage.period_date, func.sum(MapboxUsage.call_count))
            .filter(MapboxUsage.period_date >= week_start)
            .group_by(MapboxUsage.period_date)
            .order_by(MapboxUsage.period_date)
            .all()
        )
        mapbox_by_day = [
            {"period_date": row[0], "total_requests": int(row[1])} for row in mapbox_daily_rows
        ]

        mapbox_top_rows = (
            db.query(MapboxUsage.user_id, func.sum(MapboxUsage.call_count).label("reqs"))
            .filter(MapboxUsage.period_date >= week_start)
            .group_by(MapboxUsage.user_id)
            .order_by(func.sum(MapboxUsage.call_count).desc())
            .limit(20)
            .all()
        )
        mapbox_top_users = [
            {"user_id": uid, "requests_last_7d": int(reqs)} for uid, reqs in mapbox_top_rows
        ]

        mapbox_week_total = int(
            db.query(func.coalesce(func.sum(MapboxUsage.call_count), 0))
            .filter(MapboxUsage.period_date >= week_start)
            .scalar()
            or 0
        )

        mapbox_mtd = int(
            db.query(func.coalesce(func.sum(MapboxUsage.call_count), 0))
            .filter(
                MapboxUsage.period_date >= month_start,
                MapboxUsage.period_date <= today,
            )
            .scalar()
            or 0
        )

        mapbox_payload = {
            "today_total_requests": mapbox_today_total,
            "today_users_with_requests": mapbox_active_users_today,
            "requests_last_7_days_total": mapbox_week_total,
            "requests_month_to_date_utc": mapbox_mtd,
            "monthly_free_requests_cap": mapbox_free_cap,
            "month_utc_label": today_d.strftime("%Y-%m"),
            "last_7_days_by_date": mapbox_by_day,
            "top_users_last_7_days": mapbox_top_users,
        }
    except (ProgrammingError, OperationalError) as exc:
        db.rollback()
        logger.warning(
            "admin overview: mapbox_usage unavailable (create table or run init_db): %s",
            exc,
        )

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
        "mapbox": mapbox_payload,
        "as_of": today,
    }


@limiter.limit("30/minute")
@router.patch("/users/{user_id}/role", summary="Set a user's role (admin only)")
def set_user_role(
    request: Request,
    user_id: str,
    body: AdminRoleUpdate,
    _: UserContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Update the role of any user profile.  Valid values are "user", "paid",
    and "admin".  This is the authoritative way to grant paid-tier LLM quota
    or admin privileges without touching the database directly.
    """
    profile = (
        db.query(Profile)
        .filter(func.lower(Profile.id) == user_id.strip().lower())
        .first()
    )
    if not profile:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="User profile not found.")

    previous_role = profile.role
    profile.role = body.role
    db.commit()
    db.refresh(profile)

    logger.info(
        "admin role update | user_id=%s | %s -> %s",
        profile.id,
        previous_role,
        profile.role,
    )
    return {"user_id": profile.id, "role": profile.role}
