import math
import pandas as pd 

from backend.app.schemas.prediction import ProductionPredictionRequest
from backend.app.services.model_registry import ModelRegistry

def format_feature_name(feature: str) -> str:
    """Convert raw model feauture names into human-readable explanations."""
    if "bldgarea" in feature:
        return "Building size significantly impacts property value"
    
    if "neighborhood" in feature:
        return "Neighborhood demand strongly influences pricing"
    
    if "borough" in feature:
        return "Location (borough) plays a key role in valuation"
    
    if "building_class" in feature:
        return f"Model identified {feature} as influential"

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
        
        # 4. Investment score (simple heuristic)
        if roi_estimate < 0:
            investment_score = 10 
        elif roi_estimate < 5:
            investment_score = 40
        elif roi_estimate < 10:
            investment_score = 65
        elif roi_estimate < 20:
            investment_score = 80
        else:
            investment_score = 90
        
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
        return {
            "predicted_price": predicted_price,
            "market_price": market_price,
            "price_difference": price_difference,
            "roi_estimate": roi_estimate,
            "investment_score": investment_score,
            "top_drivers": top_drivers,
            "analysis_summary": summary,
            "global_context": [
                "Model is trained on NYC residential sales data",
                "Neighborhood and square footage are key drivers",
            ],
            "explanation_factors": explanation_factors,
            "model_version": prediction_result.get("model_version", "v1"),
        }
