# import pandas as pd
# from backend.app.core.config import RAW_DATA_FILE, FEATURE_DATA_FILE


# def engineer_features():
    
#     print("Loading dataset...")
    
#     df = pd.read_csv(RAW_DATA_FILE)
    
#     # -----------------------------
#     # Feature Engineering
#     # -----------------------------
    
#     df["price_per_sqft"] = df["listing_price"] /df["sqft"]
    
#     df["bedroom_density"] = df["bedrooms"] / df["sqft"]
    
#     df["bathroom_ratio"] = df["bathrooms"] / df["bedrooms"]
    
    
#     # Handle division edge cases
#     df.to_csv(FEATURE_DATA_FILE, index=False)
    
#     print(f"Feature dataset saved to {FEATURE_DATA_FILE}")
    
# if __name__ == "__main__":
#     engineer_features()
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = BASE_DIR / "ml/data/processed/nyc_training_data.csv"
FEATURES_DIR = BASE_DIR / "ml/data/features"
OUTPUT_FILE = FEATURES_DIR / "nyc_features.csv"

def load_data():
    """Load merged NYC training dataset."""
    print(f"Loading merged training dataset...")
    return pd.read_csv(INPUT_FILE, low_memory=False)



def clean_column_names(df):
    """Rename columns tp cleaner snake_case names."""
    df = df.rename(columns={
        "sale price": "sale_price",
        "sale date": "sale_date",
        "gross square feet": "gross_square_feet",
        "land square feet": "land_square_feet",
        "year built": "sales_year_built",
        "zip code": "zip_code",
        "residential units": "residential_units",
        "commercial units": "commercial_units",
        "total units": "total_units",
        "building class category": "building_class_category",
        "borough_x": "borough",
        "address_x": "address",
        "yearbuilt": "pluto_year_built",
    })
    return df



def select_relevant_columns(df):
    """Keep only columns useful for MVP modeling."""
    selected_columns = [
        "sale_price",
        "sale_date",
        "borough",
        "neighborhood",
        "building_class_category",
        "address",
        "zip_code",
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
        "bbl",
    ]
    
    existing_columns = [col for col in selected_columns if col in df.columns]
    return df[existing_columns].copy()


def convert_numeric_columns(df):
    """Convert relevant columns to numeric."""
    numeric_columns = [
        "sale_price",
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
        "zip_code",
    ]
    
    for col in numeric_columns:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", "", regex=False)
                .str.strip()
            )
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
    return df



def engineer_features(df):
    """Create derived real-state features."""
    current_year = pd.Timestamp.now().year 
    
    if "pluto_year_built" in df.columns:
        df["building_age"] = current_year - df["pluto_year_built"]
    
    if "sale_price" in df.columns and "gross_square_feet" in df.columns:
        df["price_per_sqft"] = df["sale_price"] / df["gross_square_feet"]
    
    return df



def clean_rows(df):
    """Drop invalid or weak-quality rows and keep residential-only properties."""
    required_columns = [
        "sale_price",
        "gross_square_feet",
        "borough",
        "pluto_year_built",
        "building_class_category",
    ]
    
    existing_required = [col for col in required_columns if col in df.columns]
    df = df.dropna(subset=existing_required)
    
    # Remove invalid target / size values
    df = df[df["sale_price"] > 10000]
    df = df[df["gross_square_feet"] > 0]
    
    if "building_age" in df.columns:
        df = df[df["building_age"] >= 0]
        df = df[df["building_age"] < 300]
        
    # Keep residential-only categories for MVP
    
    residential_keywords = [
        "ONE FAMILY",
        "TWO FAMILY",
        "THREE FAMILY",
        "CONDO",
        "COOPS",
        "APARTMENTS", 
    ]
    
    pattern = "|".join(residential_keywords)
    df = df[
        df["building_class_category"]
        .astype(str)
        .str.upper()
        .str.contains(pattern, na=False)
    ]
        
    return df 












def save_features(df):
    """Save cleaned features dataset."""
    FEATURES_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Features dataset saved to {OUTPUT_FILE}")
    
    
def run_feature_pipeline():
    print("Running feature engineering pipeline...")
    
    df = load_data()
    df = clean_column_names(df)
    df = select_relevant_columns(df)
    df = convert_numeric_columns(df)
    df = engineer_features(df)
    df = clean_rows(df)
    save_features(df)
    
if __name__ == "__main__":
    run_feature_pipeline()