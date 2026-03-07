from pydantic import BaseModel, Field
from typing import Optional


class PropertyBase(BaseModel):
    address: str = Field(
        ...,
        min_length=3,
        examples=["45 W 34th St"]
    )

    zipcode: str = Field(
        ...,
        min_length=3,
        max_length=10,
        examples=["10001"]
    )

    bedrooms: int = Field(..., ge=0)
    bathrooms: int = Field(..., ge=0)
    sqft: int = Field(..., gt=0)
    listing_price: float = Field(..., gt=0)


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
    address: Optional[str] = None
    zipcode: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    sqft: Optional[int] = None
    listing_price: Optional[float] = None


class PropertyResponse(PropertyBase):
    id: int

    model_config = {
        "from_attributes": True
    }