import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()   

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

engine = create_engine(DATABASE_URL)

QUERY = """
SELECT
    id,
    borough,
    neighborhood,
    building_class,
    year_built,
    sales_price,
    gross_sqft,
    land_sqft
FROM housing_data
"""

RESIDENTIAL_CLASSES = [
    "01 ONE FAMILY DWELLINGS",
    "02 TWO FAMILY DWELLINGS",
    "03 THREE FAMILY DWELLINGS",
    "07 RENTALS - WALKUP APARTMENTS",
    "08 RENTALS - ELEVATOR APARTMENTS",
    "09 COOPS - WALKUP APARTMENTS",
    "10 COOPS - ELEVATOR APARTMENTS",
    "12 CONDOS - WALKUP APARTMENTS",
    "13 CONDOS - ELEVATOR APARTMENTS",
    "15 CONDOS - 2-10 UNIT RESIDENTIAL",
    "17 CONDO COOPS",
]

OUTPUT_PATH = "ml/data/processed/nyc_training_data_clean.csv"

def main():
    df = pd.read_sql(QUERY, engine)
    
    print(f"Raw rows: {len(df)}")
    
    df = df[df["building_class"].isin(RESIDENTIAL_CLASSES)].copy()
    print(f"After residential filter: {len(df)}")
    
    df["sales_price"] = pd.to_numeric(df["sales_price"], errors="coerce")
    df["gross_sqft"] = pd.to_numeric(df["gross_sqft"], errors="coerce")
    df["land_sqft"] = pd.to_numeric(df["land_sqft"], errors="coerce")
    df["year_built"] = pd.to_numeric(df["year_built"], errors="coerce")
    
    df = df[df["sales_price"] > 1000]
    print(f"After valide sales_price filter: {len(df)}")
    
    df = df[df["gross_sqft"].notna() & (df["gross_sqft"] > 0)]
    print(f"After valid gross_sqft filter: {len(df)}")
    
    
    df = df[
        df["year_built"].notna() 
        & (df["year_built"] > 1800) 
        & (df["year_built"] <= 2025)
    ]
    print(f"After year_built filter: {len(df)}")
    
    price_cap = df["sales_price"].quantile(0.99)
    print(f"99th percentile sales_price: {price_cap:,.2f}")
    
    df = df[df["sales_price"] <= price_cap]
    print(f"After outlier removal: {len(df)}")
    
    df = df.drop_duplicates()
    print(f"After dropping duplicates: {len(df)}")
    
    os.makedirs("ml/data/processed", exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    
    print(f"✅ Clean training data saved to: {OUTPUT_PATH}")
    print("\nSample:")
    print(df.head())
    
if __name__ == "__main__":
    main()
    