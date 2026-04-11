"""Persist per-user Mapbox Geocoding autocomplete usage (daily counters)."""

import logging
import os
from datetime import date

from sqlalchemy import func
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from backend.app.db.models import MapboxUsage

logger = logging.getLogger("propintel")

MAPBOX_MONTHLY_CAP: int = int(os.getenv("MAPBOX_MONTHLY_FREE_REQUEST_CAP", "100000"))


def get_monthly_total(db: Session, month_prefix: str) -> int:
    """
    Return the total Mapbox geocode calls across ALL users for a given month.

    month_prefix must be a YYYY-MM string (e.g. "2026-04").  All period_date
    rows that start with that prefix are summed so the cap is org-wide, not
    per-user.
    """
    try:
        result = (
            db.query(func.sum(MapboxUsage.call_count))
            .filter(MapboxUsage.period_date.like(f"{month_prefix}%"))
            .scalar()
        )
        return int(result or 0)
    except (ProgrammingError, OperationalError):
        return 0


def is_monthly_cap_exceeded(db: Session) -> bool:
    """Return True if org-wide Mapbox usage has hit the monthly free-tier cap."""
    month_prefix = date.today().strftime("%Y-%m")
    total = get_monthly_total(db, month_prefix)
    return total >= MAPBOX_MONTHLY_CAP


def usage_user_key(auth_method: str, user_id: str | None) -> str | None:
    if auth_method == "jwt" and user_id and user_id.strip():
        return user_id.strip()
    if auth_method == "api_key":
        return "api_key:service"
    return None


def increment_mapbox_geocode_requests(db: Session, user_key: str) -> None:
    today = date.today().isoformat()
    try:
        row = (
            db.query(MapboxUsage)
            .filter(MapboxUsage.user_id == user_key, MapboxUsage.period_date == today)
            .first()
        )
        if row is None:
            row = MapboxUsage(user_id=user_key, period_date=today, call_count=0)
            db.add(row)
            db.flush()
        row.call_count += 1
        db.commit()
    except (ProgrammingError, OperationalError) as exc:
        db.rollback()
        logger.warning(
            "mapbox_usage table missing or DB error; run migration (see MapboxUsage model docstring): %s",
            exc,
        )
