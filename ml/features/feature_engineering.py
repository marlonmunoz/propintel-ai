import pandas as pd
from pathlib import Path

# Fixed reference year matching the data collection period.
# Using datetime.now().year would cause property_age to drift by 1 every
# calendar year, making the feature mean different things on each retrain.
REFERENCE_YEAR = 2024

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = BASE_DIR / "ml/data/processed/nyc_training_data_clean.csv"
FEATURES_DIR = BASE_DIR / "ml/data/features"
OUTPUT_FILE = FEATURES_DIR / "nyc_features.csv"

def load_data():
    """Load cleaned NYC training dataset."""
    print("Loading cleaned dataset...")
    return pd.read_csv(INPUT_FILE, low_memory=False)

def clean_text_columns(df):
    """Clean string-based categorical columns."""
    for col in ["borough", "neighborhood", "building_class"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    return df


def convert_numeric_columns(df):
    """Convert relevant columns to numeric types."""
    numeric_columns = [
        "year_built",
        "sales_price",
        "gross_sqft",
        "land_sqft",
        "latitude",
        "longitude",
    ]
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
    return df


def engineer_features(df):
    """Create derived features for modeling."""
    if "year_built" in df.columns:
        df["property_age"] = REFERENCE_YEAR - df["year_built"]
    return df


def clean_rows(df):
    """Final cleanup before saving feature dataset."""
    required_columns = [
        "borough",
        "neighborhood",
        "building_class",
        "year_built",
        "sales_price",
        "gross_sqft",
        "latitude",
        "longitude",
    ]

    df = df.dropna(subset=required_columns)
    
    df = df[df["sales_price"] > 1000]
    df = df[df["gross_sqft"] > 0]
    
    if "property_age" in df.columns:
        df = df[df["property_age"] >= 0]
        df = df[df["property_age"] < 300]
    return df


def save_features(df):
    """Save engineered features dataset."""
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    print(df.columns.tolist())
    print(df.head())
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Features saved to: {OUTPUT_FILE}")
    
    

def run_feature_pipeline():
    print("Running feature engineering pipeline...")
    
    df = load_data()
    df = clean_text_columns(df)
    df = convert_numeric_columns(df)
    df = engineer_features(df)
    df = clean_rows(df)
    save_features(df)
    
if __name__ == "__main__":
    run_feature_pipeline()

