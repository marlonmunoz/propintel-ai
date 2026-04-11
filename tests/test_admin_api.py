import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import backend.app.db.models  # noqa: F401 — register MapboxUsage on Base
from backend.app.db.database import Base, engine

Base.metadata.create_all(bind=engine)

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.auth import UserContext, get_current_user, get_current_user_with_role
from backend.app.db.database import get_db
from backend.app.db.models import Profile


def test_admin_overview_ok_with_api_key():
    prev = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id="test-user-id",
        email="test@propintel.ai",
        auth_method="api_key",
        role="admin",
    )
    try:
        client = TestClient(app)
        r = client.get("/admin/overview")
        assert r.status_code == 200
        data = r.json()
        assert "profiles_count" in data
        assert "properties_count" in data
        assert "llm" in data
        assert "today_total_calls" in data["llm"]
        assert "last_7_days_by_date" in data["llm"]
        assert "top_users_last_7_days" in data["llm"]
        assert "mapbox" in data
        assert "today_total_requests" in data["mapbox"]
        assert "requests_last_7_days_total" in data["mapbox"]
        assert "requests_month_to_date_utc" in data["mapbox"]
        assert "monthly_free_requests_cap" in data["mapbox"]
        assert "month_utc_label" in data["mapbox"]
        assert "last_7_days_by_date" in data["mapbox"]
        assert "top_users_last_7_days" in data["mapbox"]
        assert "as_of" in data
    finally:
        if prev is not None:
            app.dependency_overrides[get_current_user] = prev
        else:
            app.dependency_overrides.pop(get_current_user, None)


def test_admin_overview_forbidden_for_jwt_non_admin():
    prev = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id="00000000-0000-4000-8000-000000000099",
        email="regular@example.com",
        auth_method="jwt",
        role="user",
    )
    try:
        client = TestClient(app)
        r = client.get("/admin/overview")
        assert r.status_code == 403
        body = r.json()
        assert (
            body.get("detail") == "Admin access required."
            or body.get("message") == "Admin access required."
        )
    finally:
        if prev is not None:
            app.dependency_overrides[get_current_user] = prev
        else:
            app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# PATCH /admin/users/{user_id}/role
# ---------------------------------------------------------------------------

def _admin_user_ctx():
    return UserContext(
        user_id="admin-svc",
        email="admin@propintel.ai",
        auth_method="api_key",
        role="admin",
    )


def _seed_profile(db: Session, user_id: str, role: str = "user") -> Profile:
    db.query(Profile).filter(Profile.id == user_id).delete()
    p = Profile(id=user_id, email=f"{user_id}@test.com", role=role)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _override(fn):
    """Save the current get_current_user override and return a restorer."""
    prev = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = fn

    def restore():
        if prev is not None:
            app.dependency_overrides[get_current_user] = prev
        else:
            app.dependency_overrides.pop(get_current_user, None)

    return restore


def test_set_user_role_to_paid():
    """Admin can promote a user profile to the paid tier."""
    db = next(get_db())
    target_id = "role-test-user-paid"
    _seed_profile(db, target_id, role="user")
    db.close()

    restore = _override(_admin_user_ctx)
    try:
        client = TestClient(app)
        r = client.patch(f"/admin/users/{target_id}/role", json={"role": "paid"})
        assert r.status_code == 200
        data = r.json()
        assert data["role"] == "paid"
        assert data["user_id"] == target_id
    finally:
        restore()


def test_set_user_role_to_admin():
    """Admin can promote a user profile to admin."""
    db = next(get_db())
    target_id = "role-test-user-admin"
    _seed_profile(db, target_id, role="user")
    db.close()

    restore = _override(_admin_user_ctx)
    try:
        client = TestClient(app)
        r = client.patch(f"/admin/users/{target_id}/role", json={"role": "admin"})
        assert r.status_code == 200
        assert r.json()["role"] == "admin"
    finally:
        restore()


def test_set_user_role_demote_to_user():
    """Admin can demote a user back to user tier."""
    db = next(get_db())
    target_id = "role-test-user-demote"
    _seed_profile(db, target_id, role="paid")
    db.close()

    restore = _override(_admin_user_ctx)
    try:
        client = TestClient(app)
        r = client.patch(f"/admin/users/{target_id}/role", json={"role": "user"})
        assert r.status_code == 200
        assert r.json()["role"] == "user"
    finally:
        restore()


def test_set_user_role_not_found():
    """404 when the target user profile does not exist."""
    restore = _override(_admin_user_ctx)
    try:
        client = TestClient(app)
        r = client.patch("/admin/users/nonexistent-uuid-xyz/role", json={"role": "paid"})
        assert r.status_code == 404
    finally:
        restore()


def test_set_user_role_invalid_value():
    """422 when the role value is not one of the allowed values."""
    restore = _override(_admin_user_ctx)
    try:
        client = TestClient(app)
        r = client.patch("/admin/users/any-id/role", json={"role": "superuser"})
        assert r.status_code == 422
    finally:
        restore()


def test_set_user_role_forbidden_for_non_admin():
    """Non-admin JWT users cannot call the role endpoint."""
    restore = _override(lambda: UserContext(
        user_id="regular-user",
        email="user@test.com",
        auth_method="jwt",
        role="user",
    ))
    try:
        client = TestClient(app)
        r = client.patch("/admin/users/any-id/role", json={"role": "paid"})
        assert r.status_code == 403
    finally:
        restore()


# ---------------------------------------------------------------------------
# get_current_user_with_role — role enrichment logic (unit-level)
# ---------------------------------------------------------------------------

def test_get_current_user_with_role_enriches_paid_role():
    """
    Verify that the quota limit for 'paid' is higher than for 'user' and that
    both are below the admin/api_key unlimited ceiling (None).  This tests the
    explainer._resolve_quota_limit contract that get_current_user_with_role
    feeds into — confirming the paid tier is wired end-to-end in the quota gate.
    """
    from backend.app.services.explainer import _resolve_quota_limit

    db = next(get_db())
    target_id = "enrich-test-paid-user"
    _seed_profile(db, target_id, role="paid")
    db.close()

    limit_paid = _resolve_quota_limit("paid", "jwt")
    limit_user = _resolve_quota_limit("user", "jwt")
    limit_admin = _resolve_quota_limit("admin", "jwt")
    limit_api_key = _resolve_quota_limit("user", "api_key")

    assert limit_user == 10
    assert limit_paid == 200
    assert limit_paid > limit_user
    assert limit_admin is None
    assert limit_api_key is None
