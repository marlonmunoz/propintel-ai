import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

logger = logging.getLogger("propintel")

# ---------------------------------------------------------------------------
# Legacy route deprecation metadata.
# Sunset = 2026-06-07 (14 days from 2026-05-24 shipping date).
# After that date, confirm zero log hits, then hard-delete in a follow-up.
# ---------------------------------------------------------------------------
_DEPRECATION_HEADERS = {
    "Deprecation": "true",
    "Sunset": "Sun, 07 Jun 2026 00:00:00 GMT",
}
_LEGACY_ROUTES = {
    "/predict-price":    "/predict-price-v2",
    "/analyze-property": "/analyze-property-v2",
    "/predict":          "/predict-price-v2",
    "/analyze":          "/analyze-property-v2",
}


def _deprecation_headers(path: str) -> dict[str, str]:
    successor = _LEGACY_ROUTES.get(path, "/predict-price-v2")
    return {
        **_DEPRECATION_HEADERS,
        "Link": f'<{successor}>; rel="successor-version"',
    }

from backend.app.db.database import get_db
from backend.app.schemas.prediction import (
    PredictionRequest,
    PredictionResponse,
    AnalyzerPropertyRequest,
    AnalyzePropertyResponse,
    PublicPredictionRequest,
    PublicAnalyzeRequest,
    FeatureImportanceResponse,
    ProductionPredictionRequest,
    ProductionPredictionResponse,
    ProductionAnalyzeRequest,
    ProductionAnalyzeResponse,
    ExplanationRequest,
    ExplanationResponse,
    LLMExplanation,
)
from backend.app.services.model_registry import ModelRegistry
from backend.app.services.predictor import PredictionService
from backend.app.services.explainer import generate_explanation
from backend.app.core.auth import UserContext, get_current_user, get_current_user_with_role
from backend.app.core.limiter import limiter
from ml.inference.predict import (
    predict_price,
    analyze_property,
    predict_price_public,
    analyze_property_public,
    load_feature_importance,
)

router = APIRouter(tags=["Prediction"])


@limiter.limit("20/minute")
@router.post(
    "/predict-price",
    response_model=PredictionResponse,
    deprecated=True,
    summary="[DEPRECATED] Predict property value — use /predict-price-v2",
    description=(
        "**Deprecated** — will be removed after 2026-06-07. "
        "Use `POST /predict-price-v2` instead. "
        "Returns a predicted property price using the legacy internal feature payload."
    ),
    response_description="Predicted property value and model version.",
)
def predict_property_price(
    request: Request,
    response: Response,
    payload: PredictionRequest,
    _: UserContext = Depends(get_current_user),
):
    logger.warning("legacy_route_called | path=/predict-price | sunset=2026-06-07")
    response.headers.update(_deprecation_headers("/predict-price"))
    return predict_price(payload.model_dump())


@limiter.limit("20/minute")
@router.post(
    "/analyze-property",
    response_model=AnalyzePropertyResponse,
    deprecated=True,
    summary="[DEPRECATED] Analyze property investment — use /analyze-property-v2",
    description=(
        "**Deprecated** — will be removed after 2026-06-07. "
        "Use `POST /analyze-property-v2` instead. "
        "Runs legacy investment analysis using the older internal feature payload."
    ),
    response_description="Legacy investment analysis response.",
)
def analyze_property_investment(
    request: Request,
    response: Response,
    payload: AnalyzerPropertyRequest,
    _: UserContext = Depends(get_current_user),
):
    logger.warning("legacy_route_called | path=/analyze-property | sunset=2026-06-07")
    response.headers.update(_deprecation_headers("/analyze-property"))
    return analyze_property(payload.model_dump())


@limiter.limit("10/minute")
@router.post(
    "/predict",
    response_model=PredictionResponse,
    deprecated=True,
    summary="[DEPRECATED] Predict property value (public) — use /predict-price-v2",
    description=(
        "**Deprecated** — will be removed after 2026-06-07. "
        "Use `POST /predict-price-v2` instead. "
        "Returns a predicted property price using the simplified legacy public request body."
    ),
    response_description="Predicted property value and model version.",
)
def predict_property_price_public(
    request: Request,
    response: Response,
    payload: PublicPredictionRequest,
    _: UserContext = Depends(get_current_user),
):
    logger.warning("legacy_route_called | path=/predict | sunset=2026-06-07")
    response.headers.update(_deprecation_headers("/predict"))
    return predict_price_public(payload.model_dump())


@limiter.limit("10/minute")
@router.post(
    "/analyze",
    response_model=AnalyzePropertyResponse,
    deprecated=True,
    summary="[DEPRECATED] Analyze property (public) — use /analyze-property-v2",
    description=(
        "**Deprecated** — will be removed after 2026-06-07. "
        "Use `POST /analyze-property-v2` instead. "
        "Runs legacy investment analysis using the simplified public request body."
    ),
    response_description="Legacy public investment analysis response.",
)
def analyze_property_public_endpoint(
    request: Request,
    response: Response,
    payload: PublicAnalyzeRequest,
    _: UserContext = Depends(get_current_user),
):
    logger.warning("legacy_route_called | path=/analyze | sunset=2026-06-07")
    response.headers.update(_deprecation_headers("/analyze"))
    return analyze_property_public(payload.model_dump())


@limiter.limit("60/minute")
@router.get(
    "/model/feature-importance",
    response_model=FeatureImportanceResponse,
    summary="Get top feature importance values",
    description=(
        "Returns the top globally important model features from the saved feature importance artifact. "
        "Useful for explainability, documentation, and understanding which signals drive valuation most strongly."
    ),
    response_description="Top feature importance items and total count."
)
def get_feature_importance(
    request: Request,
    top_n: int = 10,
    _: UserContext = Depends(get_current_user),
):
    result = load_feature_importance(top_n=top_n)
    return result


@lru_cache
def get_model_registry():
    return ModelRegistry()


def get_prediction_service() -> PredictionService:
    registry = get_model_registry()
    return PredictionService(registry)


@limiter.limit("20/minute")
@router.post(
    "/predict-price-v2",
    response_model=ProductionPredictionResponse,
    summary="Predict property value (v2 production route)",
    description=(
        "Returns a production-style property valuation using the current standardized request schema. "
        "This is the recommended prediction endpoint for frontend integration and product demos. "
        "The response includes predicted price, model selection details, warnings, and model metrics."
    ),
    response_description="Production prediction response with valuation details and model metadata."
)
def predict_property_price_v2(
    request: Request,
    payload: ProductionPredictionRequest,
    service: PredictionService = Depends(get_prediction_service),
    _: UserContext = Depends(get_current_user),
) -> ProductionPredictionResponse:
    result = service.predict(payload)
    return ProductionPredictionResponse(**result)


@limiter.limit("20/minute")
@router.post(
    "/analyze-property-v2",
    response_model=ProductionAnalyzeResponse,
    summary="Analyze property investment potential (v2 production route — fast path)",
    description=(
        "Returns a fast production-style investment analysis without the LLM explanation. "
        "The response includes valuation, investment score, drivers, and metadata immediately. "
        "Fetch the AI explanation separately via POST /analyze-property-v2/explanation. "
        "The response is grouped into valuation, investment analysis, drivers, explanation, and metadata sections."
    ),
    response_description="Production investment analysis response (explanation_status='pending' until fetched separately)."
)
def analyze_property_v2(
    request: Request,
    payload: ProductionAnalyzeRequest,
    service: PredictionService = Depends(get_prediction_service),
    user: UserContext = Depends(get_current_user_with_role),
    db: Session = Depends(get_db),
):
    # Skip the OpenAI call here — the frontend fires a second request to
    # /analyze-property-v2/explanation so valuation results appear instantly.
    result = service.analyze(
        payload,
        user_id=user.user_id,
        role=user.role,
        auth_method=user.auth_method,
        db=db,
        include_explanation=False,
    )
    return result


@limiter.limit("10/minute")
@router.post(
    "/analyze-property-v2/explanation",
    response_model=ExplanationResponse,
    summary="Fetch AI explanation for a completed analysis (v2)",
    description=(
        "Calls OpenAI to generate the narrative explanation for a property analysis. "
        "Accepts the pre-computed prediction values returned by POST /analyze-property-v2 "
        "so the ML model does not need to run a second time. "
        "Enforces the same per-user daily quota as the combined endpoint."
    ),
    response_description="LLM explanation and status flag.",
)
def analyze_property_v2_explanation(
    request: Request,
    payload: ExplanationRequest,
    user: UserContext = Depends(get_current_user_with_role),
    db: Session = Depends(get_db),
) -> ExplanationResponse:
    llm_data, status = generate_explanation(
        {
            "predicted_price":  payload.predicted_price,
            "market_price":     payload.market_price,
            "roi_estimate":     payload.roi_estimate,
            "investment_score": payload.investment_score,
            "top_drivers":      payload.top_drivers,
        },
        user_id=user.user_id,
        role=user.role,
        auth_method=user.auth_method,
        db=db,
    )
    return ExplanationResponse(
        explanation=LLMExplanation(**llm_data),
        explanation_status=status,  # type: ignore[arg-type]
    )