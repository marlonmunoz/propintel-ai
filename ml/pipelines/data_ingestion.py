import pandas as pd
from pathlib import Path

DATA_DIR = Path("ml/data")
RAW_DATA_FILE = DATA_DIR / "housing_raw.csv"

def load_dataset():
    """
    Load housing dataset.
    For now we simulate ingedtion with sample data.
    Later this will pull real dataset
    """
    data = {
        "address": [
            "45 W 34th St",
            "120 Broadway",
            "10 Park Ave" 
        ], 
        "zipcode": ["10001", "10004", "10016"],
        "bedrooms": [2, 3, 1],
        "bathrooms": [1, 2, 1],
        "sqft": [900, 1400, 650],
        "listing_price": [750000, 1200000, 550000]
    }
    
    df = pd.DataFrame(data) # Create a DataFrame from the sample data
    
    DATA_DIR.mkdir(parents=True, exist_ok=True) # Ensure the data directory exists
    
    df.to_csv(RAW_DATA_FILE, index=False) # Save the dataset to a CSV file
    
    print(f"Dataset saved to {RAW_DATA_FILE}")
    
if __name__ == "__main__":
    load_dataset()
    
    