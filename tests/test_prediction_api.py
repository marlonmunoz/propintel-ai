from fastapi.testclient import TestClient
from backend.app.main import app
import backend.app.api.prediction as prediction_api

client = TestClient(app)


def test_predict_price_endpoint(monkeypatch):
    payload = {
        "gross_square_feet": 1497,
        "land_square_feet": 1668,
        "residential_units": 1,
        "commercial_units": 0,
        "total_units": 1,
        "numfloors": 2,
        "unitsres": 1,
        "unitstotal": 1,
        "lotarea": 1668,
        "bldgarea": 1497,
        "latitude": 40.8538937,
        "longitude": -73.8962879,
        "pluto_year_built": 1899,
        "building_age": 127,
        "borough": 2,
        "building_class_category": "01 ONE FAMILY DWELLINGS",
        "neighborhood": "BATHGATE",
        "zip_code": 10457,
    }

    def mock_predict_price(_payload: dict):
        return {
            "predicted_price": 611081.6875,
            "model_version": "xgboost_residential_nyc_v1",
        }

    monkeypatch.setattr(prediction_api, "predict_price", mock_predict_price)

    response = client.post("/predict-price", json=payload)

    assert response.status_code == 200

    data = response.json()
    assert "predicted_price" in data
    assert "model_version" in data
    assert isinstance(data["predicted_price"], float)
    assert data["model_version"] == "xgboost_residential_nyc_v1"
