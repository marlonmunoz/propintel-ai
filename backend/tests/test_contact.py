"""
Unit tests for POST /contact.

These tests run without a real database or Resend account — all external
calls are patched via monkeypatch / unittest.mock.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Test client with the full FastAPI app (no DB / external network)."""
    from backend.app.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


VALID_PAYLOAD = {
    "name": "Jane Smith",
    "email": "jane@example.com",
    "topic": "support",
    "message": "Hello, I need help with my account. This is detailed enough.",
}


def _mock_resend_ok():
    """Return an httpx-like response object that indicates success."""
    resp = MagicMock()
    resp.status_code = 200
    resp.text = '{"id":"abc123"}'
    return resp


def _async_context_manager_client(mock_resp):
    """Wrap a mock response in an async context manager matching httpx.AsyncClient."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_contact_success_support(client, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    mock_ctx = _async_context_manager_client(_mock_resend_ok())

    with patch("backend.app.api.contact.httpx.AsyncClient", return_value=mock_ctx):
        resp = client.post("/contact", json=VALID_PAYLOAD)

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "get back to you" in data["message"]


def test_contact_success_partnerships(client, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    mock_ctx = _async_context_manager_client(_mock_resend_ok())
    payload = {**VALID_PAYLOAD, "topic": "partnerships"}

    with patch("backend.app.api.contact.httpx.AsyncClient", return_value=mock_ctx):
        resp = client.post("/contact", json=payload)

    assert resp.status_code == 200
    assert resp.json()["ok"] is True


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "override,expected_fragment",
    [
        ({"name": ""}, "Name is required"),
        ({"name": "x" * 101}, "100 characters or fewer"),
        ({"topic": "billing"}, "support"),            # invalid topic — error mentions valid values
        ({"message": "short"}, "10 characters"),
        ({"message": "x" * 3001}, "3 000 characters"),
        ({"email": "not-an-email"}, ""),              # Pydantic EmailStr validation
    ],
)
def test_contact_validation(client, monkeypatch, override, expected_fragment):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    payload = {**VALID_PAYLOAD, **override}
    resp = client.post("/contact", json=payload)
    assert resp.status_code == 422
    body = resp.text
    if expected_fragment:
        assert expected_fragment in body


# ---------------------------------------------------------------------------
# Service unavailable when RESEND_API_KEY is missing
# ---------------------------------------------------------------------------

def test_contact_missing_api_key(client, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    resp = client.post("/contact", json=VALID_PAYLOAD)
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# Resend API failure propagation
# ---------------------------------------------------------------------------

def test_contact_resend_error_response(client, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test_key")
    bad_resp = MagicMock()
    bad_resp.status_code = 403
    bad_resp.text = '{"message":"Forbidden"}'
    mock_ctx = _async_context_manager_client(bad_resp)

    with patch("backend.app.api.contact.httpx.AsyncClient", return_value=mock_ctx):
        resp = client.post("/contact", json=VALID_PAYLOAD)

    assert resp.status_code == 502
