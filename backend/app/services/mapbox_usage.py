"""Persist per-user Mapbox Geocoding autocomplete usage (daily counters)."""

import logging
from datetime import date

from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from backend.app.db.models import MapboxUsage

logger = logging.getLogger("propintel")


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
