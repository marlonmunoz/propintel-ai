import joblib
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
MODEL_FILE = BASE_DIR / "ml/artifacts/price_model.pkl"

MODEL = None
MODEL_VERSION = "xgboost_residential_nyc_v1"


def load_model():
    global MODEL
    if MODEL is None:
        MODEL = joblib.load(MODEL_FILE)
    return MODEL

def map_public_payload_to_model_features(payload: dict) -> dict:
    year_built = payload["year_built"]
    building_age = max(0, pd.Timestamp.now().year - year_built)

    return {
        "gross_square_feet": payload["gross_square_feet"],
        "land_square_feet": payload["land_square_feet"],
        "residential_units": payload["residential_units"],
        "commercial_units": payload.get("commercial_units", 0),
        "total_units": payload["total_units"],
        "numfloors": payload["numfloors"],
        "unitsres": payload["residential_units"],
        "unitstotal": payload["total_units"],
        "lotarea": payload["land_square_feet"],
        "bldgarea": payload["gross_square_feet"],
        "latitude": payload["latitude"],
        "longitude": payload["longitude"],
        "pluto_year_built": year_built,
        "building_age": building_age,
        "borough": payload["borough"],
        "building_class_category": payload["building_class_category"],
        "neighborhood": payload["neighborhood"],
        "zip_code": payload["zip_code"],
    }



def predict_price(payload: dict) -> dict:
    model = load_model()

    feature_order = [
        "gross_square_feet",
        "land_square_feet",
        "residential_units",
        "commercial_units",
        "total_units",
        "numfloors",
        "unitsres",
        "unitstotal",
        "lotarea",
        "bldgarea",
        "latitude",
        "longitude",
        "pluto_year_built",
        "building_age",
        "borough",
        "building_class_category",
        "neighborhood",
        "zip_code",
    ]

    input_df = pd.DataFrame(
        [[payload[col] for col in feature_order]],
        columns=feature_order
    )

    predicted_log_price = model.predict(input_df)[0]
    predicted_price = np.expm1(predicted_log_price)

    return {
        "predicted_price": float(predicted_price),
        "model_version": MODEL_VERSION,
    }

def analyze_property(payload: dict) -> dict:
    market_price = payload.get("market_price")
    
    prediction_payload = payload.copy()
    prediction_payload.pop("market_price", None)
    
    prediction_result = predict_price(prediction_payload)
    predicted_price = prediction_result["predicted_price"]
    
    price_difference = predicted_price - market_price
    roi_estimate = (price_difference / market_price) * 100 
    
    # Simple MVP investment score:
    # center at 50, scale by ROI, clamp to 0-100
    investment_score = max(0.0, min(100.0, 50.0 + roi_estimate * 2.5))
    
    return {
        "predicted_price": float(predicted_price),
        "market_price": float(market_price),
        "price_difference": float(price_difference),
        "roi_estimate": float(roi_estimate),
        "investment_score": float(investment_score),
        "model_version": MODEL_VERSION,
    }
    
def predict_price_public(payload: dict) -> dict: 
    mapped_payload = map_public_payload_to_model_features(payload)
    return predict_price(mapped_payload)


def analyze_property_public(payload: dict) -> dict:
    market_price = payload["market_price"]
    
    mapped_payload = map_public_payload_to_model_features(payload)
    mapped_payload["market_price"] = market_price
    
    return analyze_property(mapped_payload) 