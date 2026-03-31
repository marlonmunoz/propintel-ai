import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import Base, engine
from backend.app.core.security import verify_api_key

app.dependency_overrides[verify_api_key] = lambda: "test_key"

Base.metadata.create_all(bind=engine)

client = TestClient(app)

PROPERTY_PAYLOAD = {
    "address": "10 Test St",
    "zipcode": "10001",
    "bedrooms": 2,
    "bathrooms": 1,
    "sqft": 900,
    "listing_price": 750000,
}


def test_create_property():
    response = client.post("/properties/", json=PROPERTY_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    assert data["address"] == PROPERTY_PAYLOAD["address"]
    assert data["zipcode"] == PROPERTY_PAYLOAD["zipcode"]
    assert "id" in data


def test_get_properties():
    response = client.get("/properties/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_property_by_id():
    create = client.post("/properties/", json=PROPERTY_PAYLOAD)
    property_id = create.json()["id"]

    response = client.get(f"/properties/{property_id}")
    assert response.status_code == 200
    assert response.json()["id"] == property_id


def test_get_property_not_found():
    response = client.get("/properties/999999")
    assert response.status_code == 404
    assert response.json()["error"] is True
    assert "message" in response.json()


def test_update_property():
    create = client.post("/properties/", json=PROPERTY_PAYLOAD)
    property_id = create.json()["id"]

    response = client.patch(f"/properties/{property_id}", json={"bedrooms": 4})
    assert response.status_code == 200
    assert response.json()["bedrooms"] == 4


def test_delete_property():
    create = client.post("/properties/", json=PROPERTY_PAYLOAD)
    property_id = create.json()["id"]

    response = client.delete(f"/properties/{property_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Property deleted successfully"

    gone = client.get(f"/properties/{property_id}")
    assert gone.status_code == 404


def test_create_property_missing_api_key():
    app.dependency_overrides.pop(verify_api_key, None)
    response = client.post("/properties/", json=PROPERTY_PAYLOAD)
    app.dependency_overrides[verify_api_key] = lambda: "test_key"
    assert response.status_code == 401
    assert response.json()["error"] is True