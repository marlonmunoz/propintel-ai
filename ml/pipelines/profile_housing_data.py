import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

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

def main():
    df = pd.read_sql(QUERY, engine)
    
    print("\n=== DATASET SHAPE ===")
    print(df.shape)
    
    print("\n=== DATASET NAMES ===")
    print(df.columns.tolist())
    
    print("\n=== NULL COUNTS ===")
    print(df.isnull().sum())
    
    print("\n=== SALES PRICE SUMMARY ===")
    print(df["sales_price"].describe())
    
    print("\n=== GROSS SQFT SUMMARY ===")
    print(df["gross_sqft"].describe())
    
    print("\n=== LAND SQFT SUMMARY ===")
    print(df["land_sqft"].describe())
    
    print("\n=== YEAR BUILT SUMMARY ===")
    print(df["year_built"].describe())
    
    print("\n=== TOP BUILDING CLASSES ===")
    print(df["building_class"].value_counts().head(20))
    
    print("\n=== TOP BOROUGHS ===")
    print(df["borough"].value_counts())
    
    print("\n=== SUSPICIOUS SALES PRICES SQFT ===")
    print(df[df["sales_price"].fillna(0) <= 100][
        ["borough", "neighborhood", "building_class", "sales_price"]
    ].head(20))
    
    print("\n=== ROWS WITH MISSING GROSS SQFT ===")
    print(df[df["gross_sqft"].isna()][
        ["borough", "neighborhood", "building_class", "sales_price", "gross_sqft"]
    ].head(20))
    
if __name__ == "__main__":
    main()