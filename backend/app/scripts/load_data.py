import pandas as pd
from sqlalchemy.orm import Session

from backend.app.db.database import SessionLocal
from backend.app.db.models import HousingData

DATA_PATH = "ml/data/processed/nyc_training_data.csv"

def load_data():
    
    db: Session = SessionLocal()
    
    try:
        df = pd.read_csv(DATA_PATH, low_memory=False)
        df.columns = df.columns.str.strip().str.lower()
        
        df = df.rename(columns={
            "borough_x": "borough",
            "building class category": "building_class",
            "year built": "year_built",
            "sale price": "sales_price",
            "gross square feet": "gross_sqft",
            "land square feet": "land_sqft",
        })
        
        df = df[
            [
                "borough",
                "neighborhood",
                "building_class",
                "year_built",
                "sales_price",
                "gross_sqft",
                "land_sqft"
            ]
        ].copy()
        
        for col in ["year_built", "sales_price", "gross_sqft", "land_sqft"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
        print(f"Loaded {len(df)} rows")
        
        db.query(HousingData).delete()
        db.commit()
        records = []
        
        for _, row in df.iterrows():
            record = HousingData(
                borough=row["borough"],
                neighborhood=row["neighborhood"],
                building_class=row["building_class"],
                year_built=None if pd.isna(row["year_built"]) else int(row["year_built"]),
                sales_price=None if pd.isna(row["sales_price"]) else int(row["sales_price"]),
                gross_sqft=None if pd.isna(row["gross_sqft"]) else int(row["gross_sqft"]),
                land_sqft=None if pd.isna(row["land_sqft"]) else int(row["land_sqft"]),
            )
            records.append(record)
        
        db.bulk_save_objects(records)
        db.commit()
        print("✅ Data Inserted Successfully")
    
    except Exception as e:
        print("❌ Error: ", e)
        db.rollback()
        
    finally:
        db.close()

if __name__ == "__main__":
    load_data()