"""
Auth endpoints for PropIntel AI.

GET   /auth/me  — returns the current user's profile, creating it on first call.
PATCH /auth/me  — update display name and marketing preferences.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.core.auth import UserContext, get_current_user
from backend.app.core.limiter import limiter
from backend.app.db.database import get_db
from backend.app.db.models import Profile
from backend.app.schemas.property import UserProfileResponse, UserProfileUpdate

router = APIRouter(prefix="/auth", tags=["Auth"])


def _display_name_from_user_metadata(meta: dict | None) -> str | None:
    if not meta:
        return None
    for key in ("display_name", "full_name", "name"):
        val = meta.get(key)
        if val is not None and str(val).strip():
            return str(val).strip()
    return None


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
    meta = user.user_metadata or {}

    if not profile:
        profile = Profile(
            id=user.user_id,
            email=user.email or "",
            display_name=_display_name_from_user_metadata(user.user_metadata),
            role="user",
            marketing_opt_in=bool(meta.get("marketing_opt_in", False)),
        )
        db.add(profile)
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        db.refresh(profile)
    else:
        # Backfill display name from JWT metadata if DB still empty (e.g. row created before sync).
        changed = False
        if profile.display_name is None:
            dn = _display_name_from_user_metadata(user.user_metadata)
            if dn:
                profile.display_name = dn
                changed = True
        if changed:
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


@limiter.limit("30/minute")
@router.patch(
    "/me",
    response_model=UserProfileResponse,
    summary="Update current user profile",
)
def patch_me(
    request: Request,
    body: UserProfileUpdate,
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    if user.auth_method == "api_key":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Cannot patch service account profile.")

    profile = db.query(Profile).filter(Profile.id == user.user_id).first()
    if not profile:
        # Create minimal row then apply patch
        meta = user.user_metadata or {}
        profile = Profile(
            id=user.user_id,
            email=user.email or "",
            display_name=_display_name_from_user_metadata(user.user_metadata),
            role="user",
            marketing_opt_in=bool(meta.get("marketing_opt_in", False)),
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    if body.display_name is not None:
        stripped = body.display_name.strip()
        profile.display_name = stripped if stripped else None

    if body.marketing_opt_in is not None:
        profile.marketing_opt_in = body.marketing_opt_in

    if profile.email != (user.email or "") and user.email:
        profile.email = user.email

    db.commit()
    db.refresh(profile)

    return UserProfileResponse(
        user_id=profile.id,
        email=profile.email,
        display_name=profile.display_name,
        role=profile.role,
        marketing_opt_in=profile.marketing_opt_in,
    )
