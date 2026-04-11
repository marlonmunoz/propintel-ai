"""
Report Mapbox Geocoding forward-search usage (autocomplete).

The browser calls Mapbox directly; after each successful response it POSTs here
so the admin dashboard can aggregate usage like LLM calls.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.core.auth import UserContext, get_current_user
from backend.app.core.limiter import limiter
from backend.app.db.database import get_db
from backend.app.services.mapbox_usage import (
    increment_mapbox_geocode_requests,
    is_monthly_cap_exceeded,
    usage_user_key,
)

router = APIRouter(tags=["Geocode"])


@limiter.limit("120/minute")
@router.post(
    "/geocode/usage",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def record_mapbox_geocode_usage(
    request: Request,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    if is_monthly_cap_exceeded(db):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Monthly Mapbox geocoding cap reached.",
        )

    key = usage_user_key(user.auth_method, user.user_id)
    if not key:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    increment_mapbox_geocode_requests(db, key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
