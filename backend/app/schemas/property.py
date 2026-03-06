from pydantic import BaseModel

class PropertyCreate(BaseModel):
    address: str
    zipcode: str
    bedrooms: int
    bathrooms: int
    sqft: int
    listing_price: float