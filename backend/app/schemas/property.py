from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any, Optional


class PropertyBase(BaseModel):
    address: str = Field(min_length=3, examples=["45 W 34th St"])
    zipcode: str = Field(min_length=3, max_length=10, examples=["10001"])
    bedrooms: int = Field(..., ge=0)
    bathrooms: int = Field(..., ge=0)
    sqft: int = Field(..., gt=0)
    listing_price: float = Field(..., gt=0)


class PropertyCreate(PropertyBase):
    analysis: Optional[Any] = None


class PropertyUpdate(BaseModel):
    address: Optional[str] = Field(default=None, min_length=3)
    zipcode: Optional[str] = Field(default=None, min_length=3, max_length=10)
    bedrooms: Optional[int] = Field(default=None, ge=0)
    bathrooms: Optional[int] = Field(default=None, ge=0)
    sqft: Optional[int] = Field(default=None, gt=0)
    listing_price: Optional[float] = Field(default=None, gt=0)
    analysis: Optional[Any] = None


class PropertyResponse(PropertyBase):
    id: int
    analysis: Optional[Any] = None
    created_at: Optional[datetime] = None
    user_id: Optional[str] = None

    model_config = {
        "from_attributes": True
    }


class UserProfileResponse(BaseModel):
    user_id: str
    email: str
    display_name: Optional[str] = None
    role: str
    marketing_opt_in: bool

    model_config = {"from_attributes": True}