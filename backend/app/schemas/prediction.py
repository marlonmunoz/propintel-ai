from datetime import date
from typing import Literal, Optional, Dict

from pydantic import BaseModel, Field, field_validator

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
    borough: str = Field(
        ...,
        min_length=1,
        description="NYC borough name for the subject property, such as Manhattan, Brooklyn, Queens, Bronx, or Staten Island."
    )
    neighborhood: str = Field(
        ...,
        min_length=1,
        description="Neighborhood name used by the model as part of location-based valuation."
    )
    building_class: str = Field(
        ...,
        min_length=1,
        description="NYC building class or subtype used to identify the property category."
    )
    year_built: int = Field(
        ...,
        ge=1800,
        le=2026,
        description="Year the property was built."
    )
    gross_sqft: float = Field(
        ...,
        gt=0,
        description="Gross building square footage."
    )
    land_sqft: float | None = Field(
        default=None,
        ge=0,
        description="Land square footage, if available."
    )
    total_units: float | None = Field(
        default=None,
        ge=0,
        description="Total number of units in the building, used for rental property valuation."
    )
    residential_units: float | None = Field(
        default=None,
        ge=0,
        description="Number of residential units in the building, used for rental property valuation."
    )
    latitude: float = Field(
        ...,
        ge=40.0,
        le=41.5,
        description="Latitude coordinate of the property."
    )
    longitude: float = Field(
        ...,
        ge=-75.0,
        le=-73.0,
        description="Longitude coordinate of the property."
    )
    bbl: Optional[str] = Field(
        default=None,
        description=(
            "Optional NYC Borough-Block-Lot identifier (digits only, e.g. '3012340056'). "
            "When provided together with as_of_date, the API loads DOF / ACRIS / J-51 / PLUTO "
            "features from local Silver + Gold tables using the same as-of rules as training."
        ),
    )
    as_of_date: Optional[date] = Field(
        default=None,
        description=(
            "Optional valuation as-of date (contract date, effective date, or today). "
            "Required together with bbl to enable roll-aligned Gold features at inference."
        ),
    )

    @field_validator("borough", "neighborhood", "building_class")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("bbl")
    @classmethod
    def strip_bbl(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        s = value.strip()
        return s if s else None

    model_config = {
        "json_schema_extra": {
            "example": {
                "borough": "Brooklyn",
                "neighborhood": "Park Slope",
                "building_class": "02 TWO FAMILY DWELLINGS",
                "year_built": 1925,
                "gross_sqft": 1800,
                "land_sqft": 2000,
                "latitude": 40.6720,
                "longitude": -73.9778,
                "bbl": "3012340056",
                "as_of_date": "2025-06-15",
            }
        }
    }
    
    
class ProductionPredictionResponse(BaseModel):
    predicted_price: float = Field(
        ...,
        description="Predicted market value generated by the trained pricing model."
    )
    price_low: Optional[float] = Field(
        default=None,
        description="Lower bound of an approximate valuation range derived from training MAE.",
    )
    price_high: Optional[float] = Field(
        default=None,
        description="Upper bound of an approximate valuation range derived from training MAE.",
    )
    valuation_interval_note: Optional[str] = Field(
        default=None,
        description="Short explanation of how the low/high range was derived.",
    )
    model_used: str = Field(
        ...,
        description="Name of the model or model family used to generate the prediction."
    )
    model_version: Optional[str] = Field(
        default=None,
        description="Version of the model used for the prediction."
    )
    segment: Optional[str] = Field(
        default=None,
        description="Property segment or subtype model selected for inference, if applicable."
    )
    input_summary: Optional[dict[str, str]] = Field(
        default=None,
        description="Human-readable summary of the main input values used for prediction."
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Warnings or notes returned during prediction, such as fallback behavior or missing optional inputs."
    )
    model_metrics: Optional[Dict[str, float]] = Field(
        default=None,
        description="Optional model performance metrics associated with the prediction model."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "predicted_price": 1185000.0,
                "price_low": 980000.0,
                "price_high": 1390000.0,
                "valuation_interval_note": "Approximate range ±1× the model's training MAE for this segment (not a formal confidence interval).",
                "model_used": "subtype_model",
                "model_version": "v1",
                "segment": "multi_family",
                "input_summary": {
                    "borough": "Brooklyn",
                    "neighborhood": "Park Slope",
                    "building_class": "02 TWO FAMILY DWELLINGS"
                },
                "warnings": [],
                "model_metrics": {
                    "mae": 304808.0,
                    "rmse": 503625.0,
                    "r2": 0.6336
                }
            }
        }
    }


class LLMExplanation(BaseModel):
    summary: str = Field(
        ...,
        max_length=600,
        description="Short overall explanation of the investment outlook.",
    )
    opportunity: str = Field(
        ...,
        max_length=600,
        description="Key upside or positive angle identified for the property.",
    )
    risks: str = Field(
        ...,
        max_length=600,
        description="Main risk factors or concerns associated with the property.",
    )
    recommendation: Literal["Buy", "Hold", "Avoid"] = Field(
        ...,
        description="Must be exactly 'Buy', 'Hold', or 'Avoid'.",
    )
    confidence: Literal["Low", "Medium", "High"] = Field(
        ...,
        description="Must be exactly 'Low', 'Medium', or 'High'.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "summary": "The property appears slightly overpriced relative to model-estimated value.",
                "opportunity": "If acquired below asking price, the valuation gap may create a better entry point.",
                "risks": "Current asking price reduces margin for upside and weakens near-term return potential.",
                "recommendation": "Hold",
                "confidence": "Medium",
            }
        }
    }
    

class ValuationBreakdown(BaseModel):
    predicted_price: float = Field(
        ...,
        description="Model-estimated market value for the property."
    )
    market_price: float = Field(
        ...,
        description="User-provided listing or asking price."
    )
    price_difference: float = Field(
        ...,
        description="Difference between predicted price and market price."
    )
    price_difference_pct: float = Field(
        ...,
        description="Percentage gap between predicted value and market price."
    )
    price_low: Optional[float] = Field(
        default=None,
        description="Lower bound of an approximate valuation range (training MAE–based).",
    )
    price_high: Optional[float] = Field(
        default=None,
        description="Upper bound of an approximate valuation range (training MAE–based).",
    )
    valuation_interval_note: Optional[str] = Field(
        default=None,
        description="How the valuation range was derived.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "predicted_price": 1185000.0,
                "market_price": 1250000.0,
                "price_difference": -65000.0,
                "price_difference_pct": -5.2,
                "price_low": 980000.0,
                "price_high": 1390000.0,
                "valuation_interval_note": "Approximate range ±1× training MAE.",
            }
        }
    }
    
    
class InvestmentAnalysis(BaseModel):
    roi_estimate: float = Field(
        ...,
        description="Estimated ROI derived from the valuation gap and analysis logic."
    )
    investment_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Investment attractiveness score on a 0 to 100 scale."
    )
    deal_label: str = Field(
        ...,
        description="Deterministic deal classification such as Buy, Hold, or Avoid."
    )
    recommendation: str = Field(
        ...,
        description="Plain-language recommendation based on the investment score and valuation context."
    )
    confidence: str = Field(
        ...,
        description="Qualitative confidence level for the recommendation."
    )
    analysis_summary: str = Field(
        ...,
        description="Short human-readable summary of the investment conclusion."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "roi_estimate": -5.2,
                "investment_score": 38,
                "deal_label": "Avoid",
                "recommendation": "Do not pursue at current asking price without a significant discount.",
                "confidence": "medium",
                "analysis_summary": "The property may be overpriced relative to model-estimated value, reducing its attractiveness as an investment."
            }
        }
    }
    
    
class DriverAnalysis(BaseModel):
    top_drivers: list[str] = Field(
        ...,
        description="Top factors that most influenced the valuation and investment interpretation."
    )
    global_context: list[str] = Field(
        ...,
        description="High-level context statements about the model, market, or dataset."
    )
    explanation_factors: list[ExplanationFactor] = Field(
        ...,
        description="Structured explanation factors used to support the final analysis."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "top_drivers": [
                    "Brooklyn location meaningfully supports property value",
                    "Two-family dwelling classification is an important pricing factor",
                    "Gross square footage strongly influences valuation"
                ],
                "global_context": [
                    "Model is trained on NYC residential sales data",
                    "Location and property size are major drivers of valuation"
                ],
                "explanation_factors": [
                    {
                        "factor": "predicted_price",
                        "value": 1185000.0,
                        "reason": "Derived from the trained valuation model using property features"
                    },
                    {
                        "factor": "market_price",
                        "value": 1250000.0,
                        "reason": "Provided asking price used to assess valuation gap and ROI"
                    }
                ]
            }
        }
    }
    
    
class ResponseMetadata(BaseModel):
    model_version: Optional[str] = Field(
        default=None,
        description="Version identifier of the model used during analysis."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "model_version": "v1"
            }
        }
    }


class ProductionAnalyzeResponse(BaseModel):
    valuation: ValuationBreakdown = Field(
        ...,
        description="Valuation outputs comparing predicted value with current market price."
    )
    investment_analysis: InvestmentAnalysis = Field(
        ...,
        description="Scoring, ROI, and recommendation outputs for the deal."
    )
    drivers: DriverAnalysis = Field(
        ...,
        description="Top drivers and structured reasoning behind the analysis."
    )
    explanation: LLMExplanation = Field(
        ...,
        description="LLM-generated narrative explanation of the opportunity and risk."
    )
    metadata: ResponseMetadata = Field(
        ...,
        description="Metadata about the model and analysis run."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "valuation": {
                    "predicted_price": 1185000.0,
                    "market_price": 1250000.0,
                    "price_difference": -65000.0,
                    "price_difference_pct": -5.2,
                    "price_low": 980000.0,
                    "price_high": 1390000.0,
                    "valuation_interval_note": "Approximate range ±1× training MAE.",
                },
                "investment_analysis": {
                    "roi_estimate": -5.2,
                    "investment_score": 38,
                    "deal_label": "Avoid",
                    "recommendation": "Do not pursue at current asking price without a significant discount.",
                    "confidence": "medium",
                    "analysis_summary": "The property may be overpriced relative to model-estimated value, reducing its attractiveness as an investment."
                },
                "drivers": {
                    "top_drivers": [
                        "Brooklyn location meaningfully supports property value",
                        "Two-family dwelling classification is an important pricing factor",
                        "Gross square footage strongly influences valuation"
                    ],
                    "global_context": [
                        "Model is trained on NYC residential sales data",
                        "Location and property size are major drivers of valuation"
                    ],
                    "explanation_factors": [
                        {
                            "factor": "predicted_price",
                            "value": 1185000.0,
                            "reason": "Derived from the trained valuation model using property features"
                        },
                        {
                            "factor": "market_price",
                            "value": 1250000.0,
                            "reason": "Provided asking price used to assess valuation gap and ROI"
                        }
                    ]
                },
                "explanation": {
                    "summary": "The property appears slightly overpriced relative to model-estimated value.",
                    "opportunity": "If acquired below asking price, the valuation gap may create a better entry point.",
                    "risks": "Current asking price reduces margin for upside and weakens near-term return potential.",
                    "recommendation": "Approach cautiously and negotiate closer to model-estimated value.",
                    "confidence": "medium"
                },
                "metadata": {
                    "model_version": "v1"
                }
            }
        }
    }
    
    
class ProductionAnalyzeRequest(ProductionPredictionRequest):
    market_price: float = Field(
        ...,
        gt=0,
        description="Current listing or asking price used for investment comparison against model-estimated value."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "borough": "Brooklyn",
                "neighborhood": "Park Slope",
                "building_class": "02 TWO FAMILY DWELLINGS",
                "year_built": 1925,
                "gross_sqft": 1800,
                "land_sqft": 2000,
                "latitude": 40.6720,
                "longitude": -73.9778,
                "bbl": "3012340056",
                "as_of_date": "2025-06-15",
                "market_price": 1250000.0
            }
        }
    }