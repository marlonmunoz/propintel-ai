import logging

import jwt as pyjwt
from jwt import PyJWKClient
from slowapi import Limiter
from starlette.requests import Request

from backend.app.core.client_ip import get_client_ip

logger = logging.getLogger("propintel")


def _user_aware_key(request: Request) -> str:
    """
    Rate-limit bucket derived from the *verified* caller identity.

    Previous implementation decoded the JWT without signature verification,
    which allowed an attacker to forge any sub claim and burn a legitimate
    user's quota (targeted-DoS on paying users).

    This version performs the same cryptographic check as get_current_user:
    HS256 tokens are verified against SUPABASE_JWT_SECRET; RS256/ES256 tokens
    are verified via the cached JWKS client.  If verification fails for any
    reason (forged token, expired, bad signature), the request falls through
    to IP-based bucketing — the attacker cannot choose their bucket.

    Priority:
      1. Verified JWT sub → uid:<uuid>
      2. X-API-Key presence → api_key:service  (shared bucket for all key callers)
      3. Remote IP → fallback for unauthenticated or unverifiable requests
    """
    # Lazy import avoids a circular dependency at module-load time
    # (auth.py imports limiter indirectly through route modules).
    from backend.app.core.auth import (  # noqa: PLC0415
        SUPABASE_JWT_SECRET,
        SUPABASE_URL,
        _jwks_client,
    )

    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        try:
            header = pyjwt.get_unverified_header(token)
            alg = (header.get("alg") or "HS256").upper()
            payload: dict | None = None

            if alg == "HS256" and SUPABASE_JWT_SECRET:
                payload = pyjwt.decode(
                    token,
                    SUPABASE_JWT_SECRET,
                    algorithms=["HS256"],
                    audience="authenticated",
                    options={"verify_aud": True},
                )
            elif alg in ("RS256", "RS384", "RS512", "ES256", "ES384", "ES512"):
                client: PyJWKClient | None = _jwks_client or (
                    PyJWKClient(
                        f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json",
                        cache_keys=True,
                    )
                    if SUPABASE_URL
                    else None
                )
                if client:
                    signing_key = client.get_signing_key_from_jwt(token)
                    payload = pyjwt.decode(
                        token,
                        signing_key.key,
                        algorithms=[alg],
                        audience="authenticated",
                        issuer=f"{SUPABASE_URL}/auth/v1",
                        options={"verify_aud": True},
                    )

            if payload:
                sub = payload.get("sub")
                if sub:
                    return f"uid:{sub}"
        except Exception:
            # Verification failed (forged token, bad signature, expired, etc.)
            # Do NOT let the caller choose their bucket — fall through to IP.
            pass

    if request.headers.get("X-API-Key"):
        return "api_key:service"

    return get_client_ip(request)


limiter = Limiter(key_func=_user_aware_key)