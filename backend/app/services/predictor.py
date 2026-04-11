import json
import logging
import math
import os
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Must match REFERENCE_YEAR in train_subtype_models.py and feature_engineering.py
# so property_age at inference equals the values seen during training.
REFERENCE_YEAR = 2024
BASE_DIR = Path(__file__).resolve().parents[3]

SUBWAY_CSV = BASE_DIR / "ml/data/external/nyc_subway_stations.csv"
EARTH_RADIUS_KM = 6_371.0

logger = logging.getLogger("propintel")
from backend.app.services.explainer import generate_explanation
from backend.app.schemas.prediction import ProductionPredictionRequest
from backend.app.services.model_registry import ModelRegistry, RegisteredModel

# Symmetric dollar band around the point estimate using training-set MAE for the
# active model. Rental subtypes report MAE in $/unit — scale by total_units.
VALUATION_INTERVAL_MAE_MULTIPLIER = 1.0
VALUATION_INTERVAL_NOTE = (
    "Approximate range ±1× the model's training MAE for this segment "
    "(not a formal confidence interval)."
)

load_dotenv()

def _load_neighborhood_stats(model_key: str) -> dict:
    """Load and cache the neighborhood stats JSON for a model key."""
    stats_path = BASE_DIR / f"ml/artifacts/subtype_models/{model_key}_neighborhood_stats.json"
    if not stats_path.exists():
        return {}
    with open(stats_path) as f:
        return json.load(f)


def lookup_neighborhood_median(model_key: str, neighborhood: str) -> float | None:
    """Return the pre-computed median sale price for a neighborhood.

    Falls back to the global training median when the neighborhood is not
    found, and returns None if the stats file doesn't exist yet.
    """
    stats = _load_neighborhood_stats(model_key)
    if not stats:
        return None
    return stats["neighborhoods"].get(neighborhood, stats.get("global_median"))


def lookup_assess_per_unit(model_key: str, neighborhood: str) -> float | None:
    """Return the pre-computed median assessed-value-per-unit for a neighborhood.

    Used at inference time for condo_coop because the user never provides
    assesstot directly. Falls back to the global training median, then None.
    """
    stats = _load_neighborhood_stats(model_key)
    if not stats or "assess_per_unit_neighborhoods" not in stats:
        return None
    return stats["assess_per_unit_neighborhoods"].get(
        neighborhood, stats.get("assess_per_unit_global_median")
    )


def lookup_stabilization_ratio(model_key: str, neighborhood: str) -> float:
    """Return the neighborhood-level median rent-stabilization ratio.

    stabilization_ratio = DHCR stabilized units / total residential units.
    Returns 0.0 (no regulated units assumed) when the neighborhood is not found
    or when the stats file has no stabilization data.
    """
    stats = _load_neighborhood_stats(model_key)
    if not stats or "stabilization_ratio_neighborhoods" not in stats:
        return 0.0
    return stats["stabilization_ratio_neighborhoods"].get(
        neighborhood, stats.get("stabilization_ratio_global_median", 0.0)
    )


def lookup_pluto_stat(model_key: str, neighborhood: str, stat_name: str) -> float | None:
    """Return a neighbourhood-level median for any PLUTO-derived stat.

    Covers: numfloors, lot_coverage, units_per_floor.
    Falls back to the global training median, then None if no data exists.
    """
    stats = _load_neighborhood_stats(model_key)
    key = f"{stat_name}_neighborhoods"
    if not stats or key not in stats:
        return None
    return stats[key].get(neighborhood, stats.get(f"{stat_name}_global_median"))


def lookup_subway_dist_km(
    lat: float | None,
    lon: float | None,
    model_key: str,
    neighborhood: str,
) -> float | None:
    """Return distance (km) to the nearest NYC subway station.

    When lat/lon are available uses a BallTree haversine query for an exact
    distance.  Falls back to the neighbourhood-level training median stored
    in neighborhood_stats when coordinates are missing.
    """
    if lat is not None and lon is not None:
        stations = _load_subway_stations()
        if stations is not None:
            from sklearn.neighbors import BallTree
            coords_rad = np.radians([[lat, lon]])
            dist_rad, _ = stations.query(coords_rad, k=1)
            return float(dist_rad[0, 0]) * EARTH_RADIUS_KM

    # Fallback: neighbourhood training median
    stats = _load_neighborhood_stats(model_key)
    if stats and "subway_dist_km_neighborhoods" in stats:
        return stats["subway_dist_km_neighborhoods"].get(
            neighborhood, stats.get("subway_dist_km_global_median")
        )
    return None


@lru_cache(maxsize=1)
def _load_subway_stations():
    """Load and cache a BallTree over NYC subway station coordinates."""
    if not SUBWAY_CSV.exists():
        return None
    try:
        from sklearn.neighbors import BallTree
        df = pd.read_csv(SUBWAY_CSV, usecols=["GTFS Latitude", "GTFS Longitude"]).dropna()
        coords = np.radians(df[["GTFS Latitude", "GTFS Longitude"]].values)
        return BallTree(coords, metric="haversine")
    except Exception:
        return None


def load_model_feature_importance(model_key: str, top_n: int = 3) -> list[dict]:
    """Load the top-N feature importances for the given model.

    Prefers the subtype-specific CSV; falls back to the global model CSV so
    we never silently return an empty list.
    """
    subtype_path = BASE_DIR / f"ml/artifacts/subtype_models/{model_key}_feature_importance.csv"
    global_path  = BASE_DIR / "ml/artifacts/feature_importance.csv"

    path = subtype_path if subtype_path.exists() else global_path
    if not path.exists():
        return []

    try:
        df = pd.read_csv(path).sort_values("importance", ascending=False).head(top_n)
        return df[["feature", "importance"]].to_dict(orient="records")
    except Exception:
        return []


def format_feature_name(feature: str) -> str:
    """Convert raw model feature names into human-readable explanations."""
    feature_lower = feature.lower()

    if "bldgarea" in feature_lower or "gross_sqft" in feature_lower:
        return "Building size significantly impacts property value"

    if "sqft_per_unit" in feature_lower:
        return "Average unit size (sqft per unit) drives per-unit valuation"

    if "assess_per_unit" in feature_lower:
        return "City-assessed value per unit reflects building quality and income potential"

    if "stabilization_ratio" in feature_lower:
        return "Rent-stabilization rate affects cash-flow and resale dynamics significantly"

    if "numfloors" in feature_lower:
        return "Building height (floors) is a key driver of condo and rental pricing"

    if "lot_coverage" in feature_lower:
        return "Lot coverage (building density) reflects urban density and building type"

    if "units_per_floor" in feature_lower:
        return "Units per floor captures building layout and density premium"

    if "bldg_footprint" in feature_lower:
        return "Building footprint (front × depth) is a precise proxy for building area"

    if "builtfar" in feature_lower:
        return "Built floor-area ratio reflects how densely the parcel is developed"

    if "lotdepth" in feature_lower:
        return "Lot depth influences rear-yard potential and overall parcel value"

    if "subway_dist" in feature_lower:
        return "Proximity to subway transit is a primary driver of NYC rental pricing"

    if "land_sqft" in feature_lower:
        return "Land size contributes to overall property valuation"

    if "neighborhood_median_ppsf" in feature_lower:
        return "Neighborhood price per sqft encodes the location-size value interaction"

    if "neighborhood_median_price" in feature_lower:
        return "Neighborhood price level is a strong driver of property value"

    if "neighborhood" in feature_lower:
        return "Neighborhood demand strongly influences pricing"

    if "borough" in feature_lower:
        return "Location (borough) plays a key role in valuation"

    if "building_class" in feature_lower:
        return "Building class is an important driver of estimated value"

    if "year_built" in feature_lower or "property_age" in feature_lower:
        return "Property age and build year affect valuation"

    if "total_units" in feature_lower or "residential_units" in feature_lower:
        return "Building unit count influences income potential and value"

    if "latitude" in feature_lower or "longitude" in feature_lower:
        return "Geographic positioning influences estimated price"

    return "Model identified this feature as influential"


def _valuation_interval_dollars(
    predicted_price: float,
    metadata: RegisteredModel,
    n_units: float,
) -> tuple[float, float] | None:
    """Return (price_low, price_high) from training MAE, or None if unavailable."""
    metrics = metadata.metrics or {}
    mae_raw = metrics.get("mae")
    if mae_raw is None:
        return None
    try:
        mae = float(mae_raw)
    except (TypeError, ValueError):
        return None
    if mae <= 0 or predicted_price < 0:
        return None
    if metadata.target == "price_per_unit":
        half = mae * max(float(n_units), 1.0) * VALUATION_INTERVAL_MAE_MULTIPLIER
    else:
        half = mae * VALUATION_INTERVAL_MAE_MULTIPLIER
    low = max(0.0, predicted_price - half)
    high = predicted_price + half
    return (low, high)


class PredictionService:
    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry
        
    def predict(self, payload: ProductionPredictionRequest) -> dict:
        model_key = self.registry.get_model_key(payload.building_class)

        # Rental models predict price_per_unit and require total_units to
        # reconstruct the full building price. Fall back to the global model
        # when total_units is missing so the API never returns a zero price.
        warnings = []
        if model_key in ("rental_walkup", "rental_elevator"):
            if not payload.total_units or payload.total_units <= 0:
                model_key = "global"
                warnings.append(
                    "total_units was not provided for this rental building. "
                    "Falling back to the global residential model. "
                    "Supply total_units for a more accurate rental valuation."
                )

        model = self.registry.load_model(model_key)
        metadata = self.registry.get_metadata(model_key)

        property_age = REFERENCE_YEAR - payload.year_built
        neighborhood = payload.neighborhood.strip()
        n_units = max(payload.total_units or 1, 1)

        row = {
            "gross_sqft": payload.gross_sqft,
            "land_sqft": payload.land_sqft,
            "total_units": payload.total_units,
            "residential_units": payload.residential_units,
            "year_built": payload.year_built,
            "property_age": property_age,
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "borough": str(payload.borough).strip(),
            "building_class": payload.building_class.strip(),
            "neighborhood": neighborhood,
        }

        if "sqft_per_unit" in metadata.feature_columns:
            row["sqft_per_unit"] = (payload.gross_sqft or 0) / n_units

        if "neighborhood_median_price" in metadata.feature_columns:
            row["neighborhood_median_price"] = lookup_neighborhood_median(
                model_key, neighborhood
            )

        if "neighborhood_median_ppsf" in metadata.feature_columns:
            row["neighborhood_median_ppsf"] = lookup_pluto_stat(
                model_key, neighborhood, "neighborhood_median_ppsf"
            )

        if "assess_per_unit" in metadata.feature_columns:
            row["assess_per_unit"] = lookup_assess_per_unit(model_key, neighborhood)

        if "stabilization_ratio" in metadata.feature_columns:
            row["stabilization_ratio"] = lookup_stabilization_ratio(model_key, neighborhood)

        # PLUTO features — looked up from neighbourhood medians saved at training
        # time; no BBL or spatial join needed at inference.
        for pluto_feat in ("numfloors", "lot_coverage", "units_per_floor",
                           "bldg_footprint", "builtfar", "lotdepth"):
            if pluto_feat in metadata.feature_columns:
                row[pluto_feat] = lookup_pluto_stat(model_key, neighborhood, pluto_feat)

        # Subway proximity — exact haversine distance when lat/lon available,
        # neighbourhood median fallback otherwise.
        if "subway_dist_km" in metadata.feature_columns:
            row["subway_dist_km"] = lookup_subway_dist_km(
                payload.latitude, payload.longitude, model_key, neighborhood
            )

        X = pd.DataFrame(
            [[row.get(col) for col in metadata.feature_columns]],
            columns=metadata.feature_columns,
        )

        prediction_log = model.predict(X)[0]

        # Price-per-unit models: multiply back by total_units to get full price.
        if metadata.target == "price_per_unit":
            predicted_price = float(math.expm1(prediction_log)) * n_units
        else:
            predicted_price = float(math.expm1(prediction_log))

        if model_key == "global" and not warnings:
            warnings.append(
                "Using global residential fallback model for this property type."
            )
        interval = _valuation_interval_dollars(predicted_price, metadata, n_units)
        out: dict = {
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
        if interval:
            low, high = interval
            out["price_low"] = low
            out["price_high"] = high
            out["valuation_interval_note"] = VALUATION_INTERVAL_NOTE
        return out
        
        
        
        
        
    def analyze(self, request, *, user_id=None, role="user", auth_method="jwt", db=None):
        """
        Combines ML predictions with investment analysis logic.

        Optional keyword arguments (user_id, role, auth_method, db) are
        forwarded to generate_explanation for per-user LLM quota enforcement.
        Callers that omit them get the same behaviour as before this change.
        """
        
        # 1. Run prediciton 
        prediction_result = self.predict(request)
        
        predicted_price = prediction_result["predicted_price"]
        market_price = request.market_price
        
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
        valuation_score = ((clamped_gap + 0.30) / 0.60) * 100.0
        
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
        
        # 4b. Deterministic deal label
        if investment_score >= 70:
            deal_label = "Buy"
        elif investment_score >= 40:
            deal_label = "Hold"
        else:
            deal_label = "Avoid"
        
        # 5. Top drivers — loaded from the model that actually made the prediction.
        # model_used is the metadata name, which matches the model key.
        model_key = prediction_result.get("model_used", "global")
        raw_drivers = [
            format_feature_name(item["feature"])
            for item in load_model_feature_importance(model_key, top_n=3)
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
        
        llm_explanation = generate_explanation(
            {
                "predicted_price": predicted_price,
                "market_price": market_price,
                "roi_estimate": roi_estimate,
                "investment_score": investment_score,
                "top_drivers": top_drivers,
            },
            user_id=user_id,
            role=role,
            auth_method=auth_method,
            db=db,
        )
        
        
        price_difference_pct = (price_difference / market_price) * 100 if market_price > 0 else 0.0

        valuation_block: dict = {
            "predicted_price": predicted_price,
            "market_price": market_price,
            "price_difference": price_difference,
            "price_difference_pct": price_difference_pct,
        }
        if prediction_result.get("price_low") is not None:
            valuation_block["price_low"] = prediction_result["price_low"]
            valuation_block["price_high"] = prediction_result["price_high"]
            valuation_block["valuation_interval_note"] = prediction_result.get(
                "valuation_interval_note"
            )

        return {
            "valuation": valuation_block,
            "investment_analysis": {
                "roi_estimate": roi_estimate,
                "investment_score": investment_score,
                "deal_label": deal_label,
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
