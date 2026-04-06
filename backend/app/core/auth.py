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
from dataclasses import dataclass

import jwt
from jwt import PyJWKClient
from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from backend.app.db.database import get_db

# ---------------------------------------------------------------------------
# Configuration — set in .env
# ---------------------------------------------------------------------------
SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")
# Same project URL as frontend VITE_SUPABASE_URL (e.g. https://xxxx.supabase.co).
# Required when Supabase signs access tokens with asymmetric keys (RS256 / ES256).
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "").rstrip("/")
API_KEY: str = os.getenv("API_KEY", "")

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def _decode_supabase_access_token(token: str) -> dict:
    """
    Verify a Supabase user access token.

    Supabase may sign with:
      - HS256 + shared secret (legacy JWT secret or imported HMAC key), or
      - RS256 / ES256 + JWKS (JWT Signing Keys — recommended).

    We branch on the unverified header's `alg` field.
    """
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token header: {exc}",
        ) from exc

    alg = (header.get("alg") or "HS256").upper()

    # ── Symmetric (HS256) ───────────────────────────────────────────────────
    if alg == "HS256":
        if not SUPABASE_JWT_SECRET:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "SUPABASE_JWT_SECRET is not configured. "
                    "Add it for HS256 tokens (Supabase Dashboard → Project Settings → API → JWT Secret)."
                ),
            )
        try:
            return jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
                options={"verify_aud": True},
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
            ) from exc

    # ── Asymmetric (RS256, ES256, …) via JWKS ────────────────────────────────
    if alg in ("RS256", "RS384", "RS512", "ES256", "ES384", "ES512"):
        if not SUPABASE_URL:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    f"Access tokens are signed with {alg}; set SUPABASE_URL in your backend .env "
                    "(same value as VITE_SUPABASE_URL, e.g. https://YOUR_PROJECT.supabase.co) "
                    "so the API can fetch JWKS and verify the signature."
                ),
            )
        jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        try:
            jwks_client = PyJWKClient(jwks_url, cache_keys=True)
            signing_key = jwks_client.get_signing_key_from_jwt(token)
        except Exception as exc:
            raise HTTPException(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not load signing key from JWKS ({jwks_url}): {exc}",
            ) from exc

        issuer = f"{SUPABASE_URL}/auth/v1"
        try:
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                audience="authenticated",
                issuer=issuer,
                options={"verify_aud": True},
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
            ) from exc

    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail=f"Unsupported JWT algorithm: {alg}",
    )


# ---------------------------------------------------------------------------
# UserContext — passed to every authenticated route
# ---------------------------------------------------------------------------
@dataclass
class UserContext:
    user_id: str | None   # Supabase auth UUID; None for service/API-key calls
    email: str | None
    auth_method: str       # "jwt" | "api_key"
    role: str = "user"     # updated by require_admin / /auth/me profile lookup
    # From Supabase JWT (`user_metadata` claim) — e.g. display_name from sign-up.
    user_metadata: dict | None = None


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
            payload = _decode_supabase_access_token(token)
            meta = payload.get("user_metadata")
            return UserContext(
                user_id=payload.get("sub"),
                email=payload.get("email"),
                auth_method="jwt",
                user_metadata=meta if isinstance(meta, dict) else None,
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
            user_metadata=None,
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
