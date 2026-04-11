import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.auth import UserContext, get_current_user


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
