import math
import pandas as pd 

from backend.app.schemas.prediction import ProductionPredictionRequest
from backend.app.services.model_registry import ModelRegistry


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