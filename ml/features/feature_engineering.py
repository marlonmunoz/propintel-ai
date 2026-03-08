import pandas as pd
from backend.app.core.config import RAW_DATA_FILE, FEATURE_DATA_FILE

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
    df.to_csv(FEATURE_DATA_FILE, index=False)
    
    print(f"Feature dataset saved to {FEATURE_DATA_FILE}")
    
if __name__ == "__main__":
    engineer_features()