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
