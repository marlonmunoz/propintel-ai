import pandas as pd 
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
import joblib

from backend.app.core.config import FEATURE_DATA_FILE, MODEL_FILE, MODEL_DIR

def train_model():
    print("Loading feature data...")
    
    df = pd.read_csv(FEATURE_DATA_FILE)
    
    # -----------------------------
    # Select ML features
    # -----------------------------
    
    features = [
        "sqft",
        "bedrooms",
        "bathrooms",
        "price_per_sqft",
        "bedroom_density",
        "bathroom_ratio"
    ]
    
    X = df[features]
    y = df["listing_price"]
    
    # -----------------------------
    # Train/Test Split
    # -----------------------------
    
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )
    
    # -----------------------------
    # Train Model
    # -----------------------------
    
    model = LinearRegression()
    model.fit(X_train, y_train)
    if len(X_test) > 1:
        score = model.score(X_test, y_test)
        print(f"Model R² Score: {score}")
    else:
        print("Dataset too small for reliable evaluation.")
    
    
    # -----------------------------
    # Save Model
    # -----------------------------

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print("Saving model (overwriting previous version)...")
    joblib.dump(model, MODEL_FILE)
    print(f"Model saved to {MODEL_FILE}")
    
if __name__ == "__main__":
    train_model()
    
    
# RUN: python -m ml.models.train_model