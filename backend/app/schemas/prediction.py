from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict

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


class AnalyzerPropertyRequest(PredictionRequest):
    market_price: float = Field(..., gt=0)
    
    
class ExplanationFactor(BaseModel):
    factor: str
    value: str | float | int
    reason: str
    
    
class AnalyzePropertyResponse(BaseModel):
    predicted_price: float
    market_price: float
    price_difference: float
    roi_estimate: float
    investment_score: float
    top_drivers: list[str]
    analysis_summary: str
    global_context: list[str]
    explanation_factors: list[ExplanationFactor]
    model_version: str
    
    
class PublicPredictionRequest(BaseModel):
    gross_square_feet: float = Field(..., gt=0)
    land_square_feet: float = Field(..., gt=0)
    residential_units: float = Field(..., ge=0)
    commercial_units: float = Field(0, ge=0)
    total_units: float = Field(..., ge=0)
    numfloors: float = Field(..., ge=0)
    latitude: float
    longitude: float
    year_built: float = Field(..., gt=0)
    borough: int = Field(..., ge=1, le=5)
    building_class_category: str
    neighborhood: str
    zip_code: int


class PublicAnalyzeRequest(PublicPredictionRequest):
    market_price: float = Field(..., gt=0)
    
    
class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float
    
    
class FeatureImportanceResponse(BaseModel):
    items: list[FeatureImportanceItem]
    total: int
    
    
class ProductionPredictionRequest(BaseModel):
    borough: str = Field(..., min_length=1)
    neighborhood: str = Field(..., min_length=1)
    building_class: str = Field(..., min_length=1)
    year_built: int = Field(..., ge=1800, le=2026)
    gross_sqft: float = Field(..., gt=0)
    land_sqft: float | None = Field(default=None, ge=0)
    latitude: float = Field(..., ge=40.0, le=41.5)
    longitude: float = Field(..., ge=-75.0, le=-73.0)
    
    @field_validator("borough", "neighborhood", "building_class")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()
    
    
class ProductionPredictionResponse(BaseModel):
    predicted_price: float
    model_used: str
    model_version: Optional[str] = None
    segment: Optional[str] = None
    input_summary: Optional[dict[str, str]] = None
    warnings: list[str] = []
    model_metrics: Optional[Dict[str, float]] = None


class LLMExplanation(BaseModel):
    summary: str
    opportunity: str
    risks: str
    recommendation: str
    confidence: str
    

class ValuationBreakdown(BaseModel):
    predicted_price: float
    market_price: float
    price_difference: float
    price_difference_pct: float
    
    
class InvestmentAnalysis(BaseModel):
    roi_estimate: float
    investment_score: int
    recommendation: str
    confidence: str
    analysis_summary: str
    
    
class DriverAnalysis(BaseModel):
    top_drivers: list[str]
    global_context: list[str]
    explanation_factors: list[ExplanationFactor]
    
    
class ResponseMetadata(BaseModel):
    model_version: Optional[str] = None 


class ProductionAnalyzeResponse(BaseModel):
    valuation: ValuationBreakdown
    investment_analysis: InvestmentAnalysis
    drivers: DriverAnalysis
    explanation: LLMExplanation
    metadata: ResponseMetadata
    
    
class ProductionAnalyzeRequest(ProductionPredictionRequest):
    market_price: float