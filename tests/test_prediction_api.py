from fastapi.testclient import TestClient
from backend.app.main import app
import backend.app.api.prediction as prediction_api
from backend.app.api.prediction import get_prediction_service

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


def test_analyze_property_endpoint(monkeypatch):
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
        "market_price": 550000,
    }

    def mock_analyze_property(_payload: dict):
        return {
            "predicted_price": 611081.6875,
            "market_price": 550000.0,
            "price_difference": 61081.6875,
            "roi_estimate": 11.105761363636365,
            "investment_score": 77.7644034090909,
            "top_drivers": [
                "large building area",
                "neighborhood signal: BATHGATE",
                "strong model upside versus market price",
            ],
            "analysis_summary": (
                "The property appears moderately undervalued. "
                "The model estimate is $611,082 versus a market price of $550,000. "
                "Key drivers include large building area, neighborhood signal: BATHGATE, "
                "strong model upside versus market price."
            ),
            "global_context": [
                "Neighborhood is one of the strongest global pricing drivers in the current model.",
                "Building area is one of the strongest global pricing drivers in the current model.",
            ],
            "explanation_factors": [
                {
                    "factor": "bldgarea",
                    "value": 1497,
                    "reason": "Building area is a strong global driver in the model.",
                },
                {
                    "factor": "neighborhood",
                    "value": "BATHGATE",
                    "reason": "Neighborhood-level signal is one of the strongest global pricing drivers.",
                },
            ],
            "model_version": "xgboost_residential_nyc_v1",
        }

    monkeypatch.setattr(prediction_api, "analyze_property", mock_analyze_property)

    response = client.post("/analyze-property", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["predicted_price"] == 611081.6875
    assert data["market_price"] == 550000.0
    assert "price_difference" in data
    assert "roi_estimate" in data
    assert "investment_score" in data
    assert "top_drivers" in data
    assert isinstance(data["top_drivers"], list)
    assert len(data["top_drivers"]) > 0
    assert "analysis_summary" in data
    assert isinstance(data["analysis_summary"], str)
    assert "global_context" in data
    assert isinstance(data["global_context"], list)
    assert "explanation_factors" in data
    assert isinstance(data["explanation_factors"], list)
    assert len(data["explanation_factors"]) > 0
    assert data["model_version"] == "xgboost_residential_nyc_v1"


def test_public_predict_endpoint(monkeypatch):
    payload = {
        "gross_square_feet": 1497,
        "land_square_feet": 1668,
        "residential_units": 1,
        "commercial_units": 0,
        "total_units": 1,
        "numfloors": 2,
        "latitude": 40.8538937,
        "longitude": -73.8962879,
        "year_built": 1899,
        "borough": 2,
        "building_class_category": "01 ONE FAMILY DWELLINGS",
        "neighborhood": "BATHGATE",
        "zip_code": 10457,
    }

    def mock_predict_price_public(_payload: dict):
        return {
            "predicted_price": 611081.6875,
            "model_version": "xgboost_residential_nyc_v1",
        }

    monkeypatch.setattr(prediction_api, "predict_price_public", mock_predict_price_public)

    response = client.post("/predict", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["predicted_price"] == 611081.6875
    assert data["model_version"] == "xgboost_residential_nyc_v1"


def test_public_analyze_endpoint(monkeypatch):
    payload = {
        "gross_square_feet": 1497,
        "land_square_feet": 1668,
        "residential_units": 1,
        "commercial_units": 0,
        "total_units": 1,
        "numfloors": 2,
        "latitude": 40.8538937,
        "longitude": -73.8962879,
        "year_built": 1899,
        "borough": 2,
        "building_class_category": "01 ONE FAMILY DWELLINGS",
        "neighborhood": "BATHGATE",
        "zip_code": 10457,
        "market_price": 550000,
    }

    def mock_analyze_property_public(_payload: dict):
        return {
            "predicted_price": 611081.6875,
            "market_price": 550000.0,
            "price_difference": 61081.6875,
            "roi_estimate": 11.105761363636365,
            "investment_score": 77.7644034090909,
            "top_drivers": [
                "large building area",
                "neighborhood signal: BATHGATE",
                "strong model upside versus market price",
            ],
            "analysis_summary": (
                "The property appears moderately undervalued. "
                "The model estimate is $611,082 versus a market price of $550,000. "
                "Key drivers include large building area, neighborhood signal: BATHGATE, "
                "strong model upside versus market price."
            ),
            "global_context": [
                "Neighborhood is one of the strongest global pricing drivers in the current model.",
                "Building area is one of the strongest global pricing drivers in the current model.",
            ],
            "explanation_factors": [
                {
                    "factor": "bldgarea",
                    "value": 1497,
                    "reason": "Building area is a strong global driver in the model.",
                },
                {
                    "factor": "neighborhood",
                    "value": "BATHGATE",
                    "reason": "Neighborhood-level signal is one of the strongest global pricing drivers.",
                },
            ],
            "model_version": "xgboost_residential_nyc_v1",
        }

    monkeypatch.setattr(
        prediction_api,
        "analyze_property_public",
        mock_analyze_property_public,
    )

    response = client.post("/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["predicted_price"] == 611081.6875
    assert data["market_price"] == 550000.0
    assert "price_difference" in data
    assert "roi_estimate" in data
    assert "investment_score" in data
    assert "top_drivers" in data
    assert isinstance(data["top_drivers"], list)
    assert len(data["top_drivers"]) > 0
    assert "analysis_summary" in data
    assert isinstance(data["analysis_summary"], str)
    assert "global_context" in data
    assert isinstance(data["global_context"], list)
    assert "explanation_factors" in data
    assert isinstance(data["explanation_factors"], list)
    assert len(data["explanation_factors"]) > 0
    assert data["model_version"] == "xgboost_residential_nyc_v1"
    
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
    def analyze(self, payload):
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
            "metadata": {
                "model_version": "v1",
            },
        }
        
def test_predict_price_v2_one_famliy_route():
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
    
    app.dependency_overrides.clear()
    

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
    
    app.dependency_overrides.clear()
    

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
    
    app.dependency_overrides.clear()
    
    
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

    assert data["metadata"]["model_version"] == "v1"
    
    app.dependency_overrides.clear()    
    
    