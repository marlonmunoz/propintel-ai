from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    gross_square_feet: float = Field(..., gt=0)
    land_square_feet: float = Field(..., gt=0)
    residential_units: float = Field(..., ge=0)
    commercial_units: float = Field(..., ge=0)
    total_units: float = Field(..., ge=0)
    numfloors: float = Field(..., ge=0)
    unitsres: float = Field(..., ge=0)
    unitstotal: float = Field(..., ge=0)
    lotarea: float = Field(..., gt=0)
    bldgarea: float = Field(..., gt=0)
    latitude: float
    longitude: float
    pluto_year_built: float = Field(..., gt=0)
    building_age: float = Field(..., ge=0)
    borough: int = Field(..., ge=1, le=5)
    building_class_category: str
    neighborhood: str
    zip_code: int


class PredictionResponse(BaseModel):
    predicted_price: float
    model_version: str
