"""
Client IP for logging and rate-limit bucketing behind reverse proxies.

Only trust ``X-Forwarded-For`` when ``TRUST_PROXY_HEADERS=1`` (or ``true`` /
``yes`` / ``on``). Enabling this without a real proxy allows clients to spoof
their IP — use only in production behind a load balancer or ingress you control.
"""

from __future__ import annotations

import ipaddress
import os

from starlette.requests import Request


def _truthy_env(name: str) -> bool:
    v = os.getenv(name, "").strip().lower()
    return v in ("1", "true", "yes", "on")


def trust_proxy_headers() -> bool:
    return _truthy_env("TRUST_PROXY_HEADERS")


def _parse_x_forwarded_for(value: str) -> str | None:
    """Return the first valid IP in the chain (typical original client)."""
    for part in value.split(","):
        raw = part.strip()
        if not raw:
            continue
        # IPv6 zone id (e.g. fe80::1%eth0)
        addr = raw.split("%", 1)[0]
        try:
            ipaddress.ip_address(addr)
        except ValueError:
            continue
        return raw
    return None


def get_client_ip(request: Request) -> str:
    """
    Best-effort client IP for metrics and rate-limit fallback.

    When ``TRUST_PROXY_HEADERS`` is set, uses the first valid hop in
    ``X-Forwarded-For``. Otherwise uses the TCP peer address.
    """
    if trust_proxy_headers():
        xff = request.headers.get("x-forwarded-for")
        if xff:
            parsed = _parse_x_forwarded_for(xff)
            if parsed:
                return parsed

    if request.client and request.client.host:
        return request.client.host
    return "unknown"
