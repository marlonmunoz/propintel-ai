"""
Supabase JWT + API key authentication for PropIntel AI.

Priority:
  1. Authorization: Bearer <supabase_jwt>  — browser / frontend users
  2. X-API-Key: <key>                       — scripts, CI, tests

Both produce a UserContext.  Routes use Depends(get_current_user).
Admin-only routes additionally call require_admin(user, db).
"""

import os
import secrets
from dataclasses import dataclass, field

import jwt
from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from backend.app.db.database import get_db

# ---------------------------------------------------------------------------
# Configuration — set in .env
# ---------------------------------------------------------------------------
SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
API_KEY: str = os.getenv("API_KEY", "")

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


# ---------------------------------------------------------------------------
# UserContext — passed to every authenticated route
# ---------------------------------------------------------------------------
@dataclass
class UserContext:
    user_id: str | None   # Supabase auth UUID; None for service/API-key calls
    email: str | None
    auth_method: str       # "jwt" | "api_key"
    role: str = "user"     # updated by require_admin / /auth/me profile lookup


# ---------------------------------------------------------------------------
# Primary dependency
# ---------------------------------------------------------------------------
async def get_current_user(
    authorization: str | None = Header(default=None),
    api_key: str | None = Security(_API_KEY_HEADER),
) -> UserContext:
    """
    Accept either a Supabase JWT (Bearer) or the legacy X-API-Key.

    JWT path  → used by the React frontend after Supabase login.
    API-key   → used by scripts, Postman, and the test suite.
    """
    # ── JWT path ─────────────────────────────────────────────────────────────
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            if not SUPABASE_JWT_SECRET:
                raise HTTPException(
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=(
                        "SUPABASE_JWT_SECRET is not configured on the server. "
                        "Add it to your .env file (Supabase Dashboard → Project Settings → API → JWT Secret)."
                    ),
                )
            try:
                payload = jwt.decode(
                    token,
                    SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    audience="authenticated",
                    options={"verify_aud": True},
                )
                return UserContext(
                    user_id=payload.get("sub"),
                    email=payload.get("email"),
                    auth_method="jwt",
                )
            except jwt.ExpiredSignatureError:
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired. Please log in again.",
                )
            except jwt.InvalidTokenError as exc:
                raise HTTPException(
                    status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid token: {exc}",
                )

    # ── API-key path ──────────────────────────────────────────────────────────
    if api_key:
        if not API_KEY or not secrets.compare_digest(api_key, API_KEY):
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key.",
            )
        return UserContext(
            user_id=None,
            email=None,
            auth_method="api_key",
            role="admin",
        )

    # ── Nothing provided ─────────────────────────────────────────────────────
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide a Bearer token or X-API-Key header.",
    )


# ---------------------------------------------------------------------------
# Admin guard — use as an additional Depends on admin-only routes
# ---------------------------------------------------------------------------
async def require_admin(
    user: UserContext = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserContext:
    """
    Allow only users with role='admin' in the profiles table.
    API-key callers are always treated as admin (service/CI access).
    """
    if user.auth_method == "api_key":
        return user

    # Late import avoids circular dependency with models
    from backend.app.db.models import Profile  # noqa: PLC0415

    profile = db.query(Profile).filter(Profile.id == user.user_id).first()
    if not profile or profile.role != "admin":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    user.role = "admin"
    return user
