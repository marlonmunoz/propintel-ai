from fastapi import APIRouter
import pandas as pd
from ml.inference.predict import predict_price
from backend.app.schemas.prediction import PropertyFeatures, PricePrediction

router = APIRouter()

@router.post ("/predict-price", response_model= PricePrediction)
def predict_property_price(features: PropertyFeatures):
    
    sqft = features.sqft
    bedrooms = features.bedrooms
    bathrooms = features.bathrooms
    
    price_per_sqft = 800
    bedroom_density = bedrooms / sqft
    bathroom_ratio = bathrooms / bedrooms if bedrooms > 0 else 0
    
    feature_dict = {
        "sqft": sqft,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "price_per_sqft": price_per_sqft,
        "bedroom_density": bedroom_density,
        "bathroom_ratio": bathroom_ratio
    }
    
    prediction = predict_price(feature_dict)
    
    return {f"predicted_price": prediction}