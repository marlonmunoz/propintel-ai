"""
Auth endpoints for PropIntel AI.

GET /auth/me  — returns the current user's profile, creating it on first call.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.core.auth import UserContext, get_current_user
from backend.app.core.limiter import limiter
from backend.app.db.database import get_db
from backend.app.db.models import Profile
from backend.app.schemas.property import UserProfileResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@limiter.limit("60/minute")
@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get current user profile",
    description=(
        "Returns the profile of the authenticated user. "
        "The profile is created automatically on first call after Supabase sign-up."
    ),
)
def get_me(
    request: Request,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    if user.auth_method == "api_key":
        return UserProfileResponse(
            user_id="service",
            email="service@propintel.ai",
            display_name="Service Account",
            role="admin",
            marketing_opt_in=False,
        )

    profile = db.query(Profile).filter(Profile.id == user.user_id).first()

    if not profile:
        profile = Profile(
            id=user.user_id,
            email=user.email or "",
            display_name=None,
            role="user",
            marketing_opt_in=False,
        )
        db.add(profile)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(profile)

    return UserProfileResponse(
        user_id=profile.id,
        email=profile.email,
        display_name=profile.display_name,
        role=profile.role,
        marketing_opt_in=profile.marketing_opt_in,
    )
