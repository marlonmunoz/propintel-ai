from fastapi import APIRouter
from backend.app.schemas.prediction import (
    PredictionRequest, 
    PredictionResponse, 
    AnalyzerPropertyRequest, 
    AnalyzerPropertyResponse,
    PublicPredictionRequest,
    PublicAnalyzeRequest
)
from ml.inference.predict import (
    predict_price, 
    analyze_property,
    predict_price_public,
    analyze_property_public,
)

router = APIRouter(tags=["Prediction"])


@router.post("/predict-price", response_model=PredictionResponse)
def predict_property_price(request: PredictionRequest):
    result = predict_price(request.model_dump())
    return result

@router.post("/analyze-property", response_model=AnalyzerPropertyResponse)
def analyze_property_investment(request: AnalyzerPropertyRequest):
    result = analyze_property(request.model_dump())
    return result

@router.post("/predict", response_model=PredictionResponse)
def predict_property_price_public(request: PublicPredictionRequest):
    result = predict_price_public(request.model_dump())
    return result

@router.post("/analyze", response_model=AnalyzerPropertyResponse)
def analyze_property_public_endpoint(request: PublicAnalyzeRequest):
    result = analyze_property_public(request.model_dump())
    return result

