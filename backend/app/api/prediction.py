from fastapi import APIRouter
from backend.app.schemas.prediction import PredictionRequest, PredictionResponse
from ml.inference.predict import predict_price

router = APIRouter(tags=["Prediction"])


@router.post("/predict-price", response_model=PredictionResponse)
def predict_property_price(request: PredictionRequest):
    result = predict_price(request.model_dump())
    return result


