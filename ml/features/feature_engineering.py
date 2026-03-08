import pandas as pd
from pathlib import Path

DATA_DIR = Path("ml/data")

RAW_DATA_FILE = DATA_DIR / "housing_raw.csv"
PROCESSED_DATA_FILE = DATA_DIR / "housing_features.csv"

def engineer_features():
    
    print("Loading dataset...")
    
    df = pd.read_csv(RAW_DATA_FILE)
    
    # -----------------------------
    # Feature Engineering
    # -----------------------------
    
    df["price_per_sqft"] = df["listing_price"] /df["sqft"]
    
    df["bedroom_density"] = df["bedrooms"] / df["sqft"]
    
    df["bathroom_ratio"] = df["bathrooms"] / df["bedrooms"]
    
    
    # Handle division edge cases
    df.to_csv(PROCESSED_DATA_FILE, index=False)
    
    print(f"Feature dataset saved to {PROCESSED_DATA_FILE}")
    
if __name__ == "__main__":
    engineer_features()