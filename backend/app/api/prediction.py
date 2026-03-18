from fastapi import APIRouter
from backend.app.schemas.prediction import (
    PredictionRequest, 
    PredictionResponse, 
    AnalyzerPropertyRequest, 
    AnalyzePropertyResponse,
    PublicPredictionRequest,
    PublicAnalyzeRequest,
    FeatureImportanceResponse
)
from ml.inference.predict import (
    predict_price, 
    analyze_property,
    predict_price_public,
    analyze_property_public,
    load_feature_importance
)

router = APIRouter(tags=["Prediction"])


@router.post("/predict-price", response_model=PredictionResponse)
def predict_property_price(request: PredictionRequest):
    result = predict_price(request.model_dump())
    return result

@router.post("/analyze-property", response_model=AnalyzePropertyResponse)
def analyze_property_investment(request: AnalyzerPropertyRequest):
    result = analyze_property(request.model_dump())
    return result

@router.post("/predict", response_model=PredictionResponse)
def predict_property_price_public(request: PublicPredictionRequest):
    result = predict_price_public(request.model_dump())
    return result

@router.post("/analyze", response_model=AnalyzePropertyResponse)
def analyze_property_public_endpoint(request: PublicAnalyzeRequest):
    result = analyze_property_public(request.model_dump())
    return result

@router.get("/model/feature-importance", response_model=FeatureImportanceResponse)
def get_feature_importance(top_n: int = 10):
    result = load_feature_importance(top_n=top_n)
    return result
