from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3]

DATA_DIR = BASE_DIR / "ml" / "data"

RAW_DATA_FILE = DATA_DIR / "housing_raw.csv"

FEATURE_DATA_FILE = DATA_DIR / "housing_features.csv"

MODEL_DIR = BASE_DIR / "ml" / "models"

MODEL_FILE = MODEL_DIR / "price_model.pkl"
