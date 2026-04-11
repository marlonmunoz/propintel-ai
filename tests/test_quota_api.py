"""
Tests for GET /auth/quota — tier, daily limit, usage, and remaining.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import backend.app.db.models  # noqa: F401
from backend.app.db.database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.auth import UserContext, get_current_user, get_current_user_with_role
from backend.app.db.models import LLMUsage, Profile
import backend.app.services.explainer as _explainer
from datetime import date


def _override(fn):
    prev = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = fn

    def restore():
        if prev is not None:
            app.dependency_overrides[get_current_user] = prev
        else:
            app.dependency_overrides.pop(get_current_user, None)

    return restore


def _override_with_role(fn):
    prev = app.dependency_overrides.get(get_current_user_with_role)
    app.dependency_overrides[get_current_user_with_role] = fn

    def restore():
        if prev is not None:
            app.dependency_overrides[get_current_user_with_role] = prev
        else:
            app.dependency_overrides.pop(get_current_user_with_role, None)

    return restore


def _seed_usage(db: Session, user_id: str, count: int):
    today = date.today().isoformat()
    db.query(LLMUsage).filter(
        LLMUsage.user_id == user_id, LLMUsage.period_date == today
    ).delete()
    row = LLMUsage(user_id=user_id, period_date=today, call_count=count)
    db.add(row)
    db.commit()


def test_quota_free_user_no_usage():
    """Free user with no calls today: used=0, limit=_QUOTA_FREE, remaining=_QUOTA_FREE."""
    quota_free = _explainer._QUOTA_FREE
    uid = "quota-free-no-usage"
    restore = _override_with_role(lambda: UserContext(
        user_id=uid, email="f@test.com", auth_method="jwt", role="user"
    ))
    try:
        client = TestClient(app)
        r = client.get("/auth/quota")
        assert r.status_code == 200
        data = r.json()
        assert data["role"] == "user"
        assert data["daily_limit"] == quota_free
        assert data["used_today"] == 0
        assert data["remaining"] == quota_free
        assert data["resets_at"] is not None
    finally:
        restore()


def test_quota_free_user_with_usage():
    """Free user who has made calls: remaining decrements correctly."""
    quota_free = _explainer._QUOTA_FREE
    uid = "quota-free-with-usage"
    used = min(3, quota_free)
    db = next(get_db())
    _seed_usage(db, uid, used)
    db.close()

    restore = _override_with_role(lambda: UserContext(
        user_id=uid, email="f2@test.com", auth_method="jwt", role="user"
    ))
    try:
        client = TestClient(app)
        r = client.get("/auth/quota")
        assert r.status_code == 200
        data = r.json()
        assert data["used_today"] == used
        assert data["remaining"] == max(0, quota_free - used)
    finally:
        restore()


def test_quota_free_user_exhausted():
    """Free user who has hit the cap: remaining must be 0, not negative."""
    quota_free = _explainer._QUOTA_FREE
    uid = "quota-free-exhausted"
    db = next(get_db())
    _seed_usage(db, uid, quota_free)
    db.close()

    restore = _override_with_role(lambda: UserContext(
        user_id=uid, email="f3@test.com", auth_method="jwt", role="user"
    ))
    try:
        client = TestClient(app)
        r = client.get("/auth/quota")
        assert r.status_code == 200
        data = r.json()
        assert data["remaining"] == 0
        assert data["used_today"] == quota_free
    finally:
        restore()


def test_quota_paid_user():
    """Paid user gets daily_limit=_QUOTA_PAID and remaining=_QUOTA_PAID (no usage)."""
    quota_free = _explainer._QUOTA_FREE
    quota_paid = _explainer._QUOTA_PAID
    uid = "quota-paid-user"
    restore = _override_with_role(lambda: UserContext(
        user_id=uid, email="p@test.com", auth_method="jwt", role="paid"
    ))
    try:
        client = TestClient(app)
        r = client.get("/auth/quota")
        assert r.status_code == 200
        data = r.json()
        assert data["role"] == "paid"
        assert data["daily_limit"] == quota_paid
        assert data["remaining"] == quota_paid
        assert quota_paid > quota_free
    finally:
        restore()


def test_quota_admin_is_unlimited():
    """Admin JWT users get daily_limit=null (unlimited)."""
    uid = "quota-admin-user"
    restore = _override_with_role(lambda: UserContext(
        user_id=uid, email="a@test.com", auth_method="jwt", role="admin"
    ))
    try:
        client = TestClient(app)
        r = client.get("/auth/quota")
        assert r.status_code == 200
        data = r.json()
        assert data["role"] == "admin"
        assert data["daily_limit"] is None
        assert data["remaining"] is None
    finally:
        restore()


def test_quota_api_key_is_unlimited():
    """API-key callers get daily_limit=null (unlimited)."""
    restore = _override_with_role(lambda: UserContext(
        user_id=None, email=None, auth_method="api_key", role="admin"
    ))
    try:
        client = TestClient(app)
        r = client.get("/auth/quota")
        assert r.status_code == 200
        data = r.json()
        assert data["daily_limit"] is None
        assert data["remaining"] is None
    finally:
        restore()


def test_quota_requires_auth():
    """Without any auth override active, the endpoint returns 401."""
    prev_cu = app.dependency_overrides.pop(get_current_user, None)
    prev_cwr = app.dependency_overrides.pop(get_current_user_with_role, None)
    try:
        client = TestClient(app)
        r = client.get("/auth/quota")
        assert r.status_code == 401
    finally:
        if prev_cu is not None:
            app.dependency_overrides[get_current_user] = prev_cu
        if prev_cwr is not None:
            app.dependency_overrides[get_current_user_with_role] = prev_cwr
