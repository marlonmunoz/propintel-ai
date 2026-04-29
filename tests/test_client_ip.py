"""Tests for proxy-aware client IP (rate limits + request logs)."""

from starlette.requests import Request

from backend.app.core.client_ip import get_client_ip
from backend.app.core.limiter import _user_aware_key


def _request(
    *,
    client_host: str = "198.51.100.2",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "root_path": "",
        "query_string": b"",
        "headers": headers or [],
        "client": (client_host, 12345),
        "server": ("testserver", 80),
    }
    return Request(scope)


class TestGetClientIp:
    def test_without_trust_ignores_xff(self, monkeypatch):
        monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)
        req = _request(
            client_host="10.0.0.1",
            headers=[(b"x-forwarded-for", b"203.0.113.1, 10.0.0.2")],
        )
        assert get_client_ip(req) == "10.0.0.1"

    def test_with_trust_uses_first_valid_xff_hop(self, monkeypatch):
        monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
        req = _request(
            client_host="10.0.0.1",
            headers=[(b"x-forwarded-for", b"203.0.113.1, 10.0.0.2")],
        )
        assert get_client_ip(req) == "203.0.113.1"

    def test_with_trust_ipv6(self, monkeypatch):
        monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
        req = _request(
            client_host="::1",
            headers=[(b"x-forwarded-for", b"2001:db8::1")],
        )
        assert get_client_ip(req) == "2001:db8::1"

    def test_with_trust_invalid_xff_falls_back_to_peer(self, monkeypatch):
        monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
        req = _request(
            client_host="10.0.0.1",
            headers=[(b"x-forwarded-for", b"not-an-ip, also-bad")],
        )
        assert get_client_ip(req) == "10.0.0.1"

    def test_no_client_returns_unknown(self, monkeypatch):
        monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)
        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/",
            "raw_path": b"/",
            "root_path": "",
            "query_string": b"",
            "headers": [],
            "client": None,
            "server": ("testserver", 80),
        }
        assert get_client_ip(Request(scope)) == "unknown"


class TestLimiterUsesClientIp:
    def test_unauthenticated_uses_client_ip_when_trust_on(self, monkeypatch):
        monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
        req = _request(
            client_host="10.0.0.1",
            headers=[(b"x-forwarded-for", b"198.51.100.99")],
        )
        assert _user_aware_key(req) == "198.51.100.99"

    def test_unauthenticated_uses_peer_when_trust_off(self, monkeypatch):
        monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)
        req = _request(
            client_host="10.0.0.1",
            headers=[(b"x-forwarded-for", b"198.51.100.99")],
        )
        assert _user_aware_key(req) == "10.0.0.1"
