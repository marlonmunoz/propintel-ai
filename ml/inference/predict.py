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
    market_price = payload["market_price"]

    prediction_payload = payload.copy()
    prediction_payload.pop("market_price", None)

    prediction_result = predict_price(prediction_payload)
    predicted_price = prediction_result["predicted_price"]

    price_difference = predicted_price - market_price
    roi_estimate = (price_difference / market_price) * 100

    investment_score = max(0.0, min(100.0, 50.0 + roi_estimate * 2.5))

    top_drivers = generate_top_drivers(prediction_payload, roi_estimate)
    analysis_summary = generate_analysis_summary(
        predicted_price=predicted_price,
        market_price=market_price,
        roi_estimate=roi_estimate,
        top_drivers=top_drivers,
    )

    top_global_features = get_top_global_features(top_n=10)
    global_context = build_global_context(prediction_payload, top_global_features)
    explanation_factors = build_explanation_factors(prediction_payload, top_global_features)

    return {
        "predicted_price": float(predicted_price),
        "market_price": float(market_price),
        "price_difference": float(price_difference),
        "roi_estimate": float(roi_estimate),
        "investment_score": float(investment_score),
        "top_drivers": top_drivers,
        "analysis_summary": analysis_summary,
        "global_context": global_context,
        "explanation_factors": explanation_factors,
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

def generate_top_drivers(payload: dict, roi_estimate: float) -> list[str]:
    drivers = []
    
    if payload.get("bldgarea", 0) > 1500:
        drivers.append("Large building area")
    
    if payload.get("gross_square_feet", 0) >= 1400:
        drivers.append("above-average gross square footage")
        
    building_class = str(payload.get("building_class_category", "")).upper()
    if "ONE FAMILY" in building_class:
        drivers.append("favorable one-family residential class")
    elif "TWO FAMILY" in building_class:
        drivers.append("two-family income potential")
    elif "RENTALS" in building_class:
        drivers.append("rental building profile")
        
    neighborhood = str(payload.get("neighborhood", "")).upper()
    if neighborhood:
        drivers.append(f"neighborhood signal: {neighborhood}")
        
    if roi_estimate > 10:
        drivers.append("strong model upside versus market price")
    elif roi_estimate > 0:
        drivers.append("positive valuation spread")
        

def generate_analysis_summary(
    predicted_price: float, 
    market_price: float, 
    roi_estimate: float,
    top_drivers: list[str],
) -> str:
    if roi_estimate >= 10:
        outlook = "appears moderately undervalued"
    elif roi_estimate > 0:
        outlook = "appears slightly undervalued"
    elif roi_estimate > - 5:
        outlook = "appears close to fair value"
    else:
        outlook = "appears overpriced relative to the model estimate"
        
    driver_text = ", ".join(top_drivers) if top_drivers else "mixed property signals"
    
    return (
        f"The property {outlook}. "
        f"The model estimate is ${predicted_price:,.0f} versus a market proce of ${market_price:,.0f}. "
        f"Key drivers include: {driver_text}."
    )
    
def load_feature_importance(top_n: int = 10) -> dict:
    feature_importance_file = BASE_DIR / "ml/artifacts/feature_importance.csv"
    
    df = pd.read_csv(feature_importance_file)
    df = df.head(top_n)
    
    items = [
        {
            "feature": row["feature"],
            "importance": float(row["importance"]),
        }
        for _, row in df.iterrows()
    ]
    
    return {
        "items": items,
        "total": len(items)
    }
    
def get_top_global_features(top_n: int = 10) -> list[str]:
    feature_importance_file = BASE_DIR / "ml/artifacts/feature_importance.csv"
    df = pd.read_csv(feature_importance_file)
    return df.head(top_n)["feature"].tolist()


def build_global_context(payload: dict, top_global_features: list[str]) -> list[str]:
    context = []

    if any("neighborhood" in feature for feature in top_global_features):
        context.append("Neighborhood is one of the strongest global pricing drivers in the current model.")

    if any("bldgarea" in feature for feature in top_global_features):
        context.append("Building area is one of the strongest global pricing drivers in the current model.")

    if any("borough" in feature for feature in top_global_features):
        context.append("Borough-level location signal is an important global pricing factor.")

    if any("total_units" in feature for feature in top_global_features):
        context.append("Total unit count influences valuation in the current model.")

    return context[:3]


def build_explanation_factors(payload: dict, top_global_features: list[str]) -> list[dict]:
    factors = []

    if any("bldgarea" in feature for feature in top_global_features):
        factors.append({
            "factor": "bldgarea",
            "value": payload.get("bldgarea", 0),
            "reason": "Building area is a strong global driver in the model.",
        })

    if any("gross_square_feet" in feature for feature in top_global_features):
        factors.append({
            "factor": "gross_square_feet",
            "value": payload.get("gross_square_feet", 0),
            "reason": "Gross square footage contributes to valuation strength.",
        })

    if any("neighborhood" in feature for feature in top_global_features):
        factors.append({
            "factor": "neighborhood",
            "value": payload.get("neighborhood", ""),
            "reason": "Neighborhood-level signal is one of the strongest global pricing drivers.",
        })

    if any("borough" in feature for feature in top_global_features):
        factors.append({
            "factor": "borough",
            "value": payload.get("borough", ""),
            "reason": "Borough is an important location signal in the model.",
        })

    if any("total_units" in feature for feature in top_global_features):
        factors.append({
            "factor": "total_units",
            "value": payload.get("total_units", 0),
            "reason": "Total unit count affects the valuation model.",
        })

    return factors[:4]
    