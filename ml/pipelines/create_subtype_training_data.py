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
    land_sqft,
    latitude,
    longitude,
    total_units,
    residential_units
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

OUTPUT_PATH = "ml/data/processed/nyc_subtype_training_data.csv"


def main():
    df = pd.read_sql(QUERY, engine)
    
    print(f"Raw rows: {len(df)}")
    
    df = df[df["building_class"].isin(RESIDENTIAL_CLASSES)].copy()
    print(f"After residential filter: {len(df)}")
    
    numeric_cols = [
        "sales_price",
        "gross_sqft",
        "land_sqft",
        "year_built",
        "latitude",
        "longitude",
        "total_units",
        "residential_units",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        
    df = df[df["sales_price"] > 1000]
    print(f"After valide sales_price filter: {len(df)}")
    
    df = df[
        df["year_built"].notna() 
        & (df["year_built"] >= 1800) 
        & (df["year_built"] <= 2025)
    ]
    print(f"After year_built filter: {len(df)}")
    
    df = df[df["latitude"].notna() & df["longitude"].notna()]
    print(f"After latitude/longitude filter: {len(df)}")
    
    price_cap = df["sales_price"].quantile(0.99)
    print(f"99th percentile sales_price: {price_cap:,.2f}")
    
    df = df[df["sales_price"] <= price_cap]
    print(f"After outlier removal: {len(df)}")

    # Rental buildings are income-producing assets whose sale prices vary by building
    # size (unit count). Apply two additional filters specific to rental classes:
    #   1. Per-unit floor of $30K — rows below this are data errors or distressed
    #      sales that would mislead a price-per-unit model.
    #   2. Per-class 95th percentile cap — tighter than the global 99th already
    #      applied; catches portfolio / institutional mega-deals that differ
    #      fundamentally from typical arm's-length building sales.
    RENTAL_CLASSES = {
        "07 RENTALS - WALKUP APARTMENTS",
        "08 RENTALS - ELEVATOR APARTMENTS",
    }
    rental_mask = df["building_class"].isin(RENTAL_CLASSES)
    if rental_mask.any() and "total_units" in df.columns:
        non_rental = df[~rental_mask].copy()
        rental = df[rental_mask].copy()

        rental["_price_per_unit"] = rental["sales_price"] / rental["total_units"].clip(lower=1)
        before = len(rental)
        rental = rental[rental["_price_per_unit"] >= 30_000].drop(columns=["_price_per_unit"])
        print(f"Rental per-unit floor ($30K): {before} → {len(rental)} rows")

        capped = []
        for bc in rental["building_class"].unique():
            bc_rows = rental[rental["building_class"] == bc]
            p95 = bc_rows["sales_price"].quantile(0.95)
            capped.append(bc_rows[bc_rows["sales_price"] <= p95])
        rental = pd.concat(capped).reset_index(drop=True) if capped else rental
        print(f"Rental per-class 95th pct cap: {len(rental)} rows remain")
        print(rental["building_class"].value_counts().to_string())

        df = pd.concat([non_rental, rental]).reset_index(drop=True)

    df = df.drop_duplicates()
    print(f"After dropping duplicates: {len(df)}")
    
    os.makedirs("ml/data/processed/", exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    
    print(f"✅ Subtype training data saved to: {OUTPUT_PATH}")
    print("\nBuilding class counts:")
    print(df["building_class"].value_counts().to_string())
    
if __name__ == "__main__":
    main()
    
    