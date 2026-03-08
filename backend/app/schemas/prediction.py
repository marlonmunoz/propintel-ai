from pydantic import BaseModel, Field

class PropertyFeatures(BaseModel):
    sqft: int = Field(..., gt= 0)
    bedrooms: int = Field(..., ge= 0)
    bathrooms: int = Field(..., ge= 0)
 
class PricePrediction(BaseModel):
    predicted_price: float