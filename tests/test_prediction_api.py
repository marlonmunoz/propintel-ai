import os
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from fastapi.testclient import TestClient
from backend.app.main import app
import backend.app.api.prediction as prediction_api
from backend.app.api.prediction import get_prediction_service
from backend.app.core.auth import UserContext, get_current_user

app.dependency_overrides[get_current_user] = lambda: UserContext(
    user_id="test-user-id",
    email="test@propintel.ai",
    auth_method="api_key",
    role="admin",
)

client = TestClient(app)


def test_feature_importance_endpoint(monkeypatch):
    def mock_load_feature_importance(top_n: int = 10):
        return {
            "items": [
                {
                    "feature": "cat__neighborhood_HIGHBRIDGE/MORRIS HEIGHTS",
                    "importance": 0.048351333,
                },
                {
                    "feature": "num__bldgarea",
                    "importance": 0.048019238,
                },
            ],
            "total": 2,
        }

    monkeypatch.setattr(
        prediction_api,
        "load_feature_importance",
        mock_load_feature_importance,
    )

    response = client.get("/model/feature-importance?top_n=2")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["feature"] == "cat__neighborhood_HIGHBRIDGE/MORRIS HEIGHTS"
    
    
class MockPredictionServiceOneFamily:
    def predict(self, payload):
        return {
            "predicted_price": 659430.07,
            "price_low": 519590.44,
            "price_high": 799269.70,
            "valuation_interval_note": "mock interval note",
            "model_used": "one_family",
            "model_version": "v1",
            "segment": "one_family",
            "input_summary": {
                "borough": payload.borough,
                "neighborhood": payload.neighborhood,
                "building_class": payload.building_class,
            },
            "warnings": [],
        }
        
class MockPredictionServiceGlobal: 
    def predict(self, payload):
        return {
            "predicted_price": 650980.91,
            "price_low": 300524.66,
            "price_high": 1001437.16,
            "valuation_interval_note": "mock interval note",
            "model_used": "global",
            "model_version": "v1",
            "segment": "all_residential",
            "input_summary": {
                "borough": payload.borough,
                "neighborhood": payload.neighborhood,
                "building_class": payload.building_class,
            },
            "warnings": [
                "Using global residential fallback model for this property type."
            ],
        }
    def analyze(self, payload, **_kwargs):
        predicted_price = 650980.91
        market_price = payload.market_price
    
        price_difference = predicted_price - market_price
        roi_estimate = (price_difference / market_price) * 100
    
        return {
            "valuation": {
                "predicted_price": 650980.91,
                "market_price": 550000.0,
                "price_difference": 100980.91000000003,
                "price_difference_pct": 18.36016545454546,
                "price_low": 300524.66,
                "price_high": 1001437.16,
                "valuation_interval_note": "mock interval note",
            },
            "investment_analysis": {
                "roi_estimate": 18.36016545454546,
                "investment_score": 55,
                "deal_label": "Hold",
                "recommendation": "Hold",
                "confidence": "Medium",
                "analysis_summary": "mock summary",
            },
            "drivers": {
                "top_drivers": ["mock driver"],
                "global_context": ["mock context"],
                "explanation_factors": [
                    {
                        "factor": "mock",
                        "value": 1,
                        "reason": "mock reason",
                    }
                ],
            },
            "explanation": {
                "summary": "mock summary",
                "opportunity": "mock opportunity",
                "risks": "mock risk",
                "recommendation": "Hold",
                "confidence": "Medium",
            },
            "explanation_status": "ok",
            "metadata": {
                "model_version": "v1",
                "segment": "global",
                "segment_label": "General residential",
                "model_confidence_tier": "fallback",
                "model_confidence_label": "Broad estimate",
                "model_confidence_note": "Global fallback model used.",
            },
        }
        
def test_predict_price_v2_one_family_route():
    app.dependency_overrides[get_prediction_service] = lambda: MockPredictionServiceOneFamily()
    
    payload = {
        "borough": "2",
        "neighborhood": "BATHGATE",
        "building_class": "01 ONE FAMILY DWELLINGS",
        "year_built": 1910,
        "gross_sqft": 1516,
        "land_sqft": 1173,
        "latitude": 40.850163,
        "longitude": -73.895065,
    }
    
    response = client.post("/predict-price-v2", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["predicted_price"] == 659430.07
    assert data["model_used"] == "one_family"
    assert data["model_version"] == "v1"
    assert data["segment"] == "one_family"
    assert data["input_summary"]["building_class"] == "01 ONE FAMILY DWELLINGS"
    assert data["warnings"] == []
    assert data["price_low"] == 519590.44
    assert data["price_high"] == 799269.70
    assert data["valuation_interval_note"] == "mock interval note"

    app.dependency_overrides.pop(get_prediction_service, None)
    

def test_predict_price_v2_global_fallback_route():
    app.dependency_overrides[get_prediction_service] = lambda: MockPredictionServiceGlobal()
    
    payload = {
        "borough": "2",
        "neighborhood": "BATHGATE",
        "building_class": "02 TWO FAMILY DWELLINGS",
        "year_built": 1910,
        "gross_sqft": 1516,
        "land_sqft": 1173,
        "latitude": 40.850163,
        "longitude": -73.895065,
    }
    
    response = client.post("/predict-price-v2", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["predicted_price"] == 650980.91
    assert data["model_used"] == "global"
    assert data["model_version"] == "v1"
    assert data["segment"] == "all_residential"
    assert data["input_summary"]["building_class"] == "02 TWO FAMILY DWELLINGS"
    assert len(data["warnings"]) == 1
    assert "fallback model" in data["warnings"][0].lower()
    assert data["price_low"] == 300524.66
    assert data["price_high"] == 1001437.16

    app.dependency_overrides.pop(get_prediction_service, None)
    

def test_predict_price_v2_validation_error():
    app.dependency_overrides[get_prediction_service] = lambda: MockPredictionServiceGlobal()
    payload = {
        "borough": "2",
        "neighborhood": "BATHGATE",
        "building_class": "01 ONE FAMILY DWELLINGS",
        "year_built": 1700, # invalid
        "gross_sqft": -100, # invalid
        "land_sqft": 1173,
        "latitude": 10.0, # invalid for NYC bounds
        "longitude": -73.895065,
    }
    
    response = client.post("/predict-price-v2", json=payload)
    
    assert response.status_code == 422
    
    app.dependency_overrides.pop(get_prediction_service, None)
    
    
def test_analyze_property_v2():
    app.dependency_overrides[get_prediction_service] = lambda: MockPredictionServiceGlobal()
    
    payload = {
        "borough": "2",
        "neighborhood": "BATHGATE",
        "building_class": "01 ONE FAMILY DWELLINGS",
        "year_built": 1910,
        "gross_sqft": 1516,
        "land_sqft": 1173,
        "latitude": 40.850163,
        "longitude": -73.895065,
        "market_price": 550000,
    }
    
    response = client.post("/analyze-property-v2", json=payload)
    
    assert response.status_code == 200
    data = response.json()

    assert "valuation" in data
    assert "investment_analysis" in data
    assert "drivers" in data
    assert "explanation" in data
    assert "metadata" in data

    assert data["valuation"]["predicted_price"] == 650980.91
    assert data["valuation"]["market_price"] == 550000.0
    assert "price_difference" in data["valuation"]
    assert "price_difference_pct" in data["valuation"]
    assert data["valuation"]["price_low"] == 300524.66
    assert data["valuation"]["price_high"] == 1001437.16
    assert data["valuation"]["valuation_interval_note"] == "mock interval note"

    assert "roi_estimate" in data["investment_analysis"]
    assert "investment_score" in data["investment_analysis"]
    assert "recommendation" in data["investment_analysis"]
    assert "confidence" in data["investment_analysis"]
    assert isinstance(data["investment_analysis"]["analysis_summary"], str)

    assert isinstance(data["drivers"]["top_drivers"], list)
    assert isinstance(data["drivers"]["global_context"], list)
    assert isinstance(data["drivers"]["explanation_factors"], list)

    assert "summary" in data["explanation"]
    assert "opportunity" in data["explanation"]
    assert "risks" in data["explanation"]
    assert "recommendation" in data["explanation"]
    assert "confidence" in data["explanation"]
    assert data["explanation_status"] == "ok"

    assert data["metadata"]["model_version"] == "v1"
    assert data["metadata"]["model_confidence_tier"] == "fallback"
    assert data["metadata"]["segment"] == "global"
    
    app.dependency_overrides.pop(get_prediction_service, None)
    
    