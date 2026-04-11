"""
Tests for GET /auth/me and PATCH /auth/me.

Covers:
- Profile auto-creation on first GET for a new JWT user
- Display-name backfill from user_metadata
- Admin role auto-promotion via ADMIN_USER_IDS
- API-key returns synthetic service profile
- PATCH updates display_name and marketing_opt_in
- PATCH with blank display_name sets it to None
- PATCH for API-key callers returns 400
- Unauthenticated requests return 401
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import backend.app.db.models  # noqa: F401
from backend.app.db.database import Base, engine, get_db

Base.metadata.create_all(bind=engine)

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.core.auth import UserContext, get_current_user
from backend.app.db.models import Profile


def _override(fn):
    prev = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = fn

    def restore():
        if prev is not None:
            app.dependency_overrides[get_current_user] = prev
        else:
            app.dependency_overrides.pop(get_current_user, None)

    return restore


def _clean_profile(uid: str):
    db: Session = next(get_db())
    db.query(Profile).filter(Profile.id == uid).delete()
    db.commit()
    db.close()


# ── GET /auth/me ─────────────────────────────────────────────────────────────

def test_get_me_api_key_returns_service_account():
    """API-key callers always get the synthetic service-account profile."""
    restore = _override(lambda: UserContext(
        user_id=None, email=None, auth_method="api_key", role="admin"
    ))
    try:
        r = TestClient(app).get("/auth/me")
        assert r.status_code == 200
        data = r.json()
        assert data["user_id"] == "service"
        assert data["role"] == "admin"
        assert data["display_name"] == "Service Account"
    finally:
        restore()


def test_get_me_creates_profile_on_first_call():
    """A brand-new JWT user gets a profile row created automatically."""
    uid = "authme-new-user-001"
    _clean_profile(uid)
    restore = _override(lambda: UserContext(
        user_id=uid, email="new@test.com", auth_method="jwt", role="user"
    ))
    try:
        r = TestClient(app).get("/auth/me")
        assert r.status_code == 200
        data = r.json()
        assert data["user_id"] == uid
        assert data["email"] == "new@test.com"
        assert data["role"] == "user"
    finally:
        restore()
        _clean_profile(uid)


def test_get_me_backfills_display_name_from_metadata():
    """display_name is set from user_metadata when the DB row has none."""
    uid = "authme-metadata-dn-001"
    _clean_profile(uid)
    restore = _override(lambda: UserContext(
        user_id=uid,
        email="dn@test.com",
        auth_method="jwt",
        role="user",
        user_metadata={"full_name": "Jane Doe"},
    ))
    try:
        r = TestClient(app).get("/auth/me")
        assert r.status_code == 200
        assert r.json()["display_name"] == "Jane Doe"
    finally:
        restore()
        _clean_profile(uid)


def test_get_me_subsequent_call_returns_existing_profile():
    """Second GET for the same user returns the stored row, not a new one."""
    uid = "authme-existing-001"
    _clean_profile(uid)
    user_fn = lambda: UserContext(  # noqa: E731
        user_id=uid, email="exist@test.com", auth_method="jwt", role="user"
    )
    restore = _override(user_fn)
    try:
        client = TestClient(app)
        r1 = client.get("/auth/me")
        r2 = client.get("/auth/me")
        assert r1.status_code == r2.status_code == 200
        assert r1.json()["user_id"] == r2.json()["user_id"] == uid
    finally:
        restore()
        _clean_profile(uid)


def test_get_me_admin_user_ids_promotes_role(monkeypatch):
    """A user listed in ADMIN_USER_IDS gets role=admin in the response."""
    uid = "authme-admin-promo-001"
    _clean_profile(uid)
    monkeypatch.setenv("ADMIN_USER_IDS", uid)
    restore = _override(lambda: UserContext(
        user_id=uid, email="admin@test.com", auth_method="jwt", role="user"
    ))
    try:
        r = TestClient(app).get("/auth/me")
        assert r.status_code == 200
        assert r.json()["role"] == "admin"
    finally:
        restore()
        _clean_profile(uid)


def test_get_me_unauthenticated_returns_401():
    """Without any auth, GET /auth/me returns 401."""
    prev = app.dependency_overrides.pop(get_current_user, None)
    try:
        r = TestClient(app).get("/auth/me")
        assert r.status_code == 401
    finally:
        if prev is not None:
            app.dependency_overrides[get_current_user] = prev


# ── PATCH /auth/me ────────────────────────────────────────────────────────────

def test_patch_me_updates_display_name():
    """PATCH updates the display_name field and persists it."""
    uid = "authme-patch-dn-001"
    _clean_profile(uid)
    restore = _override(lambda: UserContext(
        user_id=uid, email="patch@test.com", auth_method="jwt", role="user"
    ))
    try:
        client = TestClient(app)
        client.get("/auth/me")  # create profile
        r = client.patch("/auth/me", json={"display_name": "Patched Name"})
        assert r.status_code == 200
        assert r.json()["display_name"] == "Patched Name"
    finally:
        restore()
        _clean_profile(uid)


def test_patch_me_blank_display_name_sets_null():
    """PATCH with an all-whitespace display_name sets the field to None."""
    uid = "authme-patch-blank-001"
    _clean_profile(uid)
    restore = _override(lambda: UserContext(
        user_id=uid, email="blank@test.com", auth_method="jwt", role="user"
    ))
    try:
        client = TestClient(app)
        client.get("/auth/me")
        r = client.patch("/auth/me", json={"display_name": "   "})
        assert r.status_code == 200
        assert r.json()["display_name"] is None
    finally:
        restore()
        _clean_profile(uid)


def test_patch_me_updates_marketing_opt_in():
    """PATCH toggles marketing_opt_in correctly."""
    uid = "authme-patch-mkt-001"
    _clean_profile(uid)
    restore = _override(lambda: UserContext(
        user_id=uid, email="mkt@test.com", auth_method="jwt", role="user"
    ))
    try:
        client = TestClient(app)
        client.get("/auth/me")
        r = client.patch("/auth/me", json={"marketing_opt_in": True})
        assert r.status_code == 200
        assert r.json()["marketing_opt_in"] is True
    finally:
        restore()
        _clean_profile(uid)


def test_patch_me_api_key_returns_400():
    """API-key callers cannot patch the service account — returns 400."""
    restore = _override(lambda: UserContext(
        user_id=None, email=None, auth_method="api_key", role="admin"
    ))
    try:
        r = TestClient(app).patch("/auth/me", json={"display_name": "nope"})
        assert r.status_code == 400
    finally:
        restore()


def test_patch_me_unauthenticated_returns_401():
    """Without any auth, PATCH /auth/me returns 401."""
    prev = app.dependency_overrides.pop(get_current_user, None)
    try:
        r = TestClient(app).patch("/auth/me", json={"display_name": "x"})
        assert r.status_code == 401
    finally:
        if prev is not None:
            app.dependency_overrides[get_current_user] = prev
