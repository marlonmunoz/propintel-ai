import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

import backend.app.db.models  # noqa: F401
from backend.app.db.database import Base, engine

Base.metadata.create_all(bind=engine)

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.auth import UserContext, get_current_user


def test_geocode_usage_post_records_for_api_key_user():
    prev = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: UserContext(
        user_id=None,
        email=None,
        auth_method="api_key",
        role="admin",
    )
    try:
        client = TestClient(app)
        r = client.post("/geocode/usage")
        assert r.status_code == 204
        assert r.content == b""

        r2 = client.get("/admin/overview")
        assert r2.status_code == 200
        m = r2.json()["mapbox"]
        assert m["today_total_requests"] >= 1
        assert m["requests_last_7_days_total"] >= 1
    finally:
        if prev is not None:
            app.dependency_overrides[get_current_user] = prev
        else:
            app.dependency_overrides.pop(get_current_user, None)
