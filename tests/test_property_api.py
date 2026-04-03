import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import Base, engine, SessionLocal
from backend.app.db.models import HousingData
from backend.app.core.security import verify_api_key

app.dependency_overrides[verify_api_key] = lambda: "test_key"

Base.metadata.drop_all(bind=engine)
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


# ── /housing/lookup tests ────────────────────────────────────────────────────

def _seed_housing_row(
    lat=40.6720, lng=-73.9778, borough="Brooklyn", neighborhood="PARK SLOPE"
):
    """Insert one HousingData row and return its id for cleanup."""
    db = SessionLocal()
    row = HousingData(
        borough=borough,
        neighborhood=neighborhood,
        building_class="02 TWO FAMILY DWELLINGS",
        year_built=1920,
        sales_price=1200000.0,
        gross_sqft=2400.0,
        land_sqft=2000.0,
        latitude=lat,
        longitude=lng,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    row_id = row.id
    db.close()
    return row_id


def _delete_housing_row(row_id):
    db = SessionLocal()
    row = db.query(HousingData).filter(HousingData.id == row_id).first()
    if row:
        db.delete(row)
        db.commit()
    db.close()


def test_housing_lookup_returns_nearest():
    row_id = _seed_housing_row(lat=40.6720, lng=-73.9778, borough="Brooklyn")
    try:
        response = client.get("/housing/lookup", params={"lat": 40.6721, "lng": -73.9779})
        assert response.status_code == 200
        data = response.json()
        assert "year_built" in data
        assert "gross_sqft" in data
        assert "building_class" in data
        assert "neighborhood" in data
        assert "borough" in data
    finally:
        _delete_housing_row(row_id)


def test_housing_lookup_borough_filter():
    row_id = _seed_housing_row(lat=40.6720, lng=-73.9778, borough="Brooklyn")
    try:
        response = client.get(
            "/housing/lookup",
            params={"lat": 40.6720, "lng": -73.9778, "borough": "Brooklyn"},
        )
        assert response.status_code == 200
        assert response.json()["borough"].lower() == "brooklyn"
    finally:
        _delete_housing_row(row_id)


def test_housing_lookup_missing_params():
    """lat and lng are required — omitting them should return 422."""
    response = client.get("/housing/lookup")
    assert response.status_code == 422


def test_housing_lookup_no_results():
    """With an empty housing_data table and an impossible location, expect 404."""
    db = SessionLocal()
    db.query(HousingData).delete()
    db.commit()
    db.close()
    response = client.get("/housing/lookup", params={"lat": 0.0, "lng": 0.0})
    assert response.status_code == 404