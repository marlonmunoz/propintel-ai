import joblib 
import pandas as pd
from backend.app.core.config import MODEL_FILE

def load_model():
    print("Loading trained model...")
    model = joblib.load(MODEL_FILE)
    return model

def predict_price(features: dict):
    model = load_model()
    df = pd.DataFrame([features])
    prediction = model.predict(df)[0]
    return prediction

if __name__ == "__main__":
    
    sample_property = {
        "sqft": 1500,
        "bedrooms": 3,
        "bathrooms": 2,
        "price_per_sqft": 300,
        "bedroom_density": 0.002,
        "bathroom_ratio": 0.67
    }
    
    price = predict_price(sample_property)
    print(f"Predicted price: ${price:,.2f}")