# import pandas as pd
# from backend.app.core.config import RAW_DATA_FILE, DATA_DIR

# def load_dataset():
#     """
#     Load housing dataset.
#     For now we simulate ingedtion with sample data.
#     Later this will pull real dataset
#     """
#     data = {
#         "address": [
#             "45 W 34th St",
#             "120 Broadway",
#             "10 Park Ave" 
#         ], 
#         "zipcode": ["10001", "10004", "10016"],
#         "bedrooms": [2, 3, 1],
#         "bathrooms": [1, 2, 1],
#         "sqft": [900, 1400, 650],
#         "listing_price": [750000, 1200000, 550000]
#     }
    
#     df = pd.DataFrame(data) # Create a DataFrame from the sample data
    
#     DATA_DIR.mkdir(parents=True, exist_ok=True) # Ensure the data directory exists
    
#     df.to_csv(RAW_DATA_FILE, index=False) # Save the dataset to a CSV file
    
#     print(f"Dataset saved to {RAW_DATA_FILE}")
    
# if __name__ == "__main__":
#     load_dataset()

import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]

# DEFINING DATA PATHS
SALES_DIR = BASE_DIR / "ml/data/nyc_raw"
PLUTO_FILE = BASE_DIR / "ml/data/pluto_raw/pluto.csv"
PROCESSED_DIR = BASE_DIR / "ml/data/processed"
OUTPUT_FILE = PROCESSED_DIR / "nyc_training_data.csv"

def load_sales_data():
    """Load and combine all borough sales files."""
    sales_files = [
        "rollingsales_bronx.xlsx",
        "rollingsales_brooklyn.xlsx",
        "rollingsales_manhattan.xlsx",
        "rollingsales_queens.xlsx",
        "rollingsales_statenisland.xlsx"
    ]

    dfs = []

    for file in sales_files:
        path = SALES_DIR / file
        print(f"Loading {path.name}")

        df = pd.read_excel(path, skiprows=4)

        dfs.append(df)

    sales_df = pd.concat(dfs, ignore_index=True)

    return sales_df



def clean_sales_data(df):
    """Clean rolling sales dataset."""

    df.columns = df.columns.str.strip().str.lower() # Standardize column names

    df = df[df["sale price"].notna()] # Remove rows with missing sale price
    df = df[df["sale price"] > 0] # Remove rows with sale price <= 0

    df["block"] = df["block"].astype(str).str.zfill(5) # Pad block number with zeros
    df["lot"] = df["lot"].astype(str).str.zfill(4) # Pad lot number with zeros

    df["borough"] = df["borough"].astype(str) # Convert borough to string

    df["bbl"] = df["borough"] + df["block"] + df["lot"] # Combine borough, block, and lot to create BBL

    return df



def load_pluto():
    """Load PLUTO dataset."""
    print("Loading PLUTO dataset...")

    pluto_df = pd.read_csv(PLUTO_FILE, low_memory=False) # Load PLUTO dataset

    pluto_df.columns = pluto_df.columns.str.lower() # Normalize column names match

    # Convert BBL to string so it matches the sales dataset
    pluto_df["bbl"] = pluto_df["bbl"].astype(str)

    return pluto_df




def merge_datasets(sales_df, pluto_df):
    """Join rolling sales with PLUTO on BBL."""
    print("Merging datasets...")

    merged_df = sales_df.merge(pluto_df, on="bbl", how="left") # Join sales data with PLUTO on BBL

    return merged_df



def save_dataset(df):
    """Save processed dataset."""

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    df.to_csv(OUTPUT_FILE, index=False)

    print(f"Training dataset saved to {OUTPUT_FILE}")





def run_pipeline(): # Orchestrate the data ingestion pipeline
    """Full Ingestion Pipeline"""
    print("Running data ingestion pipeline...")

    sales_df = load_sales_data()

    sales_df = clean_sales_data(sales_df)

    pluto_df = load_pluto()

    merged_df = merge_datasets(sales_df, pluto_df)

    save_dataset(merged_df)



if __name__ == "__main__":
    run_pipeline()