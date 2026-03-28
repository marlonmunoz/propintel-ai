import math
import pandas as pd 

import os 
from dotenv import load_dotenv
from backend.app.services.explainer import generate_explanation
from backend.app.schemas.prediction import ProductionPredictionRequest
from backend.app.services.model_registry import ModelRegistry

load_dotenv()

def format_feature_name(feature: str) -> str:
    """Convert raw model feature names into human-readable explanations."""
    feature_lower = feature.lower()

    if "bldgarea" in feature_lower or "gross_sqft" in feature_lower:
        return "Building size significantly impacts property value"

    if "land_sqft" in feature_lower:
        return "Land size contributes to overall property valuation"

    if "neighborhood" in feature_lower:
        return "Neighborhood demand strongly influences pricing"

    if "borough" in feature_lower:
        return "Location (borough) plays a key role in valuation"

    if "building_class" in feature_lower:
        return "Building class is an important driver of estimated value"

    if "year_built" in feature_lower or "property_age" in feature_lower:
        return "Property age and build year affect valuation"

    if "latitude" in feature_lower or "longitude" in feature_lower:
        return "Geographic positioning influences estimated price"

    return "Model identified this feature as influential"

class PredictionService:
    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry
        
    def predict(self, payload: ProductionPredictionRequest) -> dict:
        model_key = self.registry.get_model_key(payload.building_class)
        model = self.registry.load_model(model_key)
        metadata = self.registry.get_metadata(model_key)
        
        property_age = 2026 - payload.year_built
        
        row = {
            "gross_sqft": payload.gross_sqft,
            "land_sqft": payload.land_sqft,
            "year_built": payload.year_built,
            "property_age": property_age,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "borough": str(payload.borough).strip(),
            "building_class": payload.building_class.strip(),
            "neighborhood": payload.neighborhood.strip(),
        }
        
        X = pd.DataFrame(
            [[row[col] for col in metadata.feature_columns]],
            columns=metadata.feature_columns,
        )
        
        prediction_log = model.predict(X)[0]
        predicted_price = float(math.expm1(prediction_log))
        
        warnings = []
        if payload.building_class.strip() != "01 ONE FAMILY DWELLINGS":
            warnings.append(
                "Using global residential fallback model for this property type."
            )
        return {
            "predicted_price": predicted_price,
            "model_used": metadata.name,
            "model_version": metadata.version,
            "segment": metadata.segment,
            "input_summary": {
                "borough": row["borough"],
                "neighborhood": row["neighborhood"],
                "building_class": row["building_class"],
            },
            "warnings": warnings,
            "model_metrics": metadata.metrics,
        }
        
        
        
        
        
    def analyze(self, request):
        """
        Combines ML predictions with investment analysis logic.
        """
        
        # 1. Run prediciton 
        prediction_result = self.predict(request)
        
        predicted_price = prediction_result["predicted_price"]
        market_price = request.market_price
        
        from ml.inference.predict import load_feature_importance
        
        # 2. Compute price difference
        price_difference = predicted_price - market_price
        
        # 3. ROI estimated (simple version for now)
        roi_estimate = (price_difference / market_price) * 100 if market_price > 0 else 0
        
        # 4. Investment score (ROI + valuation gap + risk)
        # Convert valuation gap into a percentage of market price
        price_gap_pct = (price_difference / market_price) if market_price > 0 else 0.0
        
        # ROI component:
        # Clamp ROI into a reasonable range so extreme values do not distort the score.
        # Range used here: -20% to + 20%, then scaled to 0-100.
        clamped_roi = max(-20.0, min(roi_estimate, 20.0))
        roi_score = ((clamped_roi + 20) / 40) * 100.0
        
        # Valuation component:
        # Positive gap means undervalued relative to market asl.
        # Negative gap means overpriced.
        # Clamp to -30% to +30% and scale to 0-100.
        clamped_gap = max(-0.30, min(price_gap_pct, 0.30))
        valuation_score = ((clamped_gap + 0.30) /0.60) * 100.0
        
        # Risk Penalty:
        # Bigger pricing dislocations imply more uncertainty / execution risk.
        risk_penalty = min(abs(price_gap_pct) * 100.0, 30.0)
        
        # Weighted final score:
        # ROI is the main driver, valuation supports it, risk pulls the score down.
        raw_score = (
            (0.60 * roi_score) +
            (0.30 * valuation_score) -
            (0.10 * risk_penalty)
        )
        
        # Final normalized score
        investment_score = max(0, min(100, round(raw_score)))
        
        
        # 5. Top drivers 
        feature_data = load_feature_importance(top_n=3)
        
        raw_drivers = [
            format_feature_name(item["feature"])
            for item in feature_data["items"]
        ]
        
        seen = set()
        top_drivers = []
        
        for driver in raw_drivers:
            if driver not in seen:
                seen.add(driver)
                top_drivers.append(driver)
        
        # 6. Summary
        if price_difference > 0:
            summary = f"Property appears undervalued by approximately ${price_difference:,.0f} based on model analysis."
        else:
            summary = f"Property may be overpriced by approximately ${abs(price_difference):,.0f} based on model analysis."
            
        # 7. Explanation factors (basic version)
        explanation_factors = [
            {
                "factor": "predicted_price",
                "value": predicted_price,
                "reason": "Derived from trained ML model using property features",
            },
            {
                "factor": "market_price",
                "value": market_price,
                "reason": "User-provided listing price",
            },
        ]
        
        try:
            llm_explanation = generate_explanation({
                "predicted_price": predicted_price,
                "market_price": market_price,
                "roi_estimate": roi_estimate,
                "investment_score": investment_score,
                "top_drivers": top_drivers,
            })
            if not isinstance(llm_explanation, dict):
                raise ValueError("Invalid LLM explanation format")
        except Exception as e:
            print("LLM ERROR:", str(e))
            llm_explanation = {
                "summary": "AI explanation unavailable",
                "opportunity": "N/A",
                "risks": "N/A",
                "recommendation": "Hold",
                "confidence": "Low"
            }
        
        
        price_difference_pct = (price_difference / market_price) * 100 if market_price > 0 else 0.0

        return {
            "valuation": {
                "predicted_price": predicted_price,
                "market_price": market_price,
                "price_difference": price_difference,
                "price_difference_pct": price_difference_pct,
            },
            "investment_analysis": {
                "roi_estimate": roi_estimate,
                "investment_score": investment_score,
                "recommendation": llm_explanation.get("recommendation", "Hold"),
                "confidence": llm_explanation.get("confidence", "Low"),
                "analysis_summary": summary,
            },
            "drivers": {
                "top_drivers": top_drivers,
                "global_context": [
                    "Model is trained on NYC residential sales data",
                    "Location, size, and building characteristics influence estimated value",
                ],
                "explanation_factors": explanation_factors,
            },
            "explanation": {
                "summary": llm_explanation.get("summary", "AI explanation unavailable"),
                "opportunity": llm_explanation.get("opportunity", "N/A"),
                "risks": llm_explanation.get("risks", "N/A"),
                "recommendation": llm_explanation.get("recommendation", "Hold"),
                "confidence": llm_explanation.get("confidence", "Low"),
            },
            "metadata": {
                "model_version": prediction_result.get("model_version", "v1"),
            },
        }
