from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_predict_price_endpoint():
    
    payload = {
        "sqft": 1000,
        "bedrooms": 2,
        "bathrooms": 1
    }
    
    response = client.post("/predict-price", json=payload)
    
    assert response.status_code == 200
    
    data = response.json()
    
    assert "predicted_price" in data
    assert isinstance(data["predicted_price"], (int, float))