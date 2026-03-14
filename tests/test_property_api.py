import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import Base, engine

Base.metadata.create_all(bind=engine)

client = TestClient(app)

def test_create_property():
    
    payload = {
        "address": "10 Test St",
        "zipcode": "10001",
        "bedrooms": 2,
        "bathrooms": 1,
        "sqft": 900,
        "listing_price": 750000
    }
    
    response = client.post("/properties", json=payload)
    
    assert response.status_code == 200
    
    data = response.json()
    
    assert data["address"] == payload["address"]
    assert data["zipcode"] == payload["zipcode"]