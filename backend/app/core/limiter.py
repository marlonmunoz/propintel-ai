import logging

import jwt as pyjwt
from slowapi import Limiter
from starlette.requests import Request

from backend.app.core.client_ip import get_client_ip

logger = logging.getLogger("propintel")


def _user_aware_key(request: Request) -> str:
    """
    Choose the rate-limit bucket by the caller's identity, not just their IP.

    Priority:
      1. JWT sub (user_id) — decoded without signature verification; used only
         for bucketing, not for authentication.  Real verification still happens
         inside get_current_user.
      2. X-API-Key presence — service / admin callers share one named bucket so
         they don't collide with JWT users.
      3. Remote IP — fallback for unauthenticated or malformed requests.
    """
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        try:
            payload = pyjwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False},
                algorithms=["HS256", "RS256", "ES256"],
            )
            sub = payload.get("sub")
            if sub:
                return f"uid:{sub}"
        except Exception:
            pass

    if request.headers.get("X-API-Key"):
        return "api_key:service"

    return get_client_ip(request)


limiter = Limiter(key_func=_user_aware_key)