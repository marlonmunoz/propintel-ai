import json
import logging
import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dotenv import load_dotenv

# Must match REFERENCE_YEAR in train_spine_models.py so property_age at
# inference equals the values seen during training.
REFERENCE_YEAR = 2024
BASE_DIR = Path(__file__).resolve().parents[3]

SUBWAY_CSV = BASE_DIR / "ml/data/external/nyc_subway_stations.csv"
EARTH_RADIUS_KM = 6_371.0

logger = logging.getLogger("propintel")
from backend.app.services.explainer import generate_explanation
from backend.app.schemas.prediction import ProductionPredictionRequest
from backend.app.services.bbl_feature_builder import (
    build_spine_gold_features_from_bbl,
    normalize_bbl,
    parse_as_of_date,
)
from backend.app.services.model_registry import ModelRegistry, RegisteredModel

VALUATION_INTERVAL_MAE_MULTIPLIER = 1.0
VALUATION_INTERVAL_NOTE = (
    "Approximate range ±1× the model's training MAE for this segment "
    "(not a formal confidence interval)."
)

load_dotenv()


# ─── Neighborhood stats helpers ───────────────────────────────────────────────

def _load_neighborhood_stats(model_key: str,
                              registry: ModelRegistry | None = None) -> dict:
    """Load the neighborhood stats JSON for a model key.

    Prefers the path recorded in the model metadata (spine models).
    Falls back to the legacy subtype_models directory.
    """
    if registry is not None:
        path = registry.stats_path_for(model_key)
    else:
        path = BASE_DIR / f"ml/artifacts/subtype_models/{model_key}_neighborhood_stats.json"
    if path is None or not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def lookup_neighborhood_median(model_key: str, neighborhood: str,
                                registry: ModelRegistry | None = None) -> float | None:
    stats = _load_neighborhood_stats(model_key, registry)
    if not stats:
        return None
    return stats["neighborhoods"].get(neighborhood, stats.get("global_median"))


def lookup_dof_assess_per_unit(model_key: str, neighborhood: str,
                                registry: ModelRegistry | None = None) -> float | None:
    """Return neighbourhood-level DOF assess-per-unit (spine models).

    Spine stats use the key 'dof_assess_per_unit_neighborhoods'.
    Legacy stats used 'assess_per_unit_neighborhoods'.
    """
    stats = _load_neighborhood_stats(model_key, registry)
    if not stats:
        return None
    for key in ("dof_assess_per_unit_neighborhoods", "assess_per_unit_neighborhoods"):
        if key in stats:
            global_key = key.replace("_neighborhoods", "_global") if "dof_" in key \
                         else "assess_per_unit_global_median"
            return stats[key].get(neighborhood, stats.get(global_key))
    return None


def lookup_subway_dist_km(lat: float | None, lon: float | None) -> float | None:
    """Return distance (km) to the nearest NYC subway station via BallTree haversine."""
    if lat is None or lon is None:
        return None
    stations = _load_subway_stations()
    if stations is None:
        return None
    from sklearn.neighbors import BallTree
    coords_rad = np.radians([[lat, lon]])
    dist_rad, _ = stations.query(coords_rad, k=1)
    return float(dist_rad[0, 0]) * EARTH_RADIUS_KM


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


# ─── Feature importance ───────────────────────────────────────────────────────

def load_model_feature_importance(model_key: str, top_n: int = 3,
                                   registry: ModelRegistry | None = None) -> list[dict]:
    if registry is not None:
        path = registry.feature_importance_path_for(model_key)
    else:
        subtype = BASE_DIR / f"ml/artifacts/subtype_models/{model_key}_feature_importance.csv"
        global_ = BASE_DIR / "ml/artifacts/feature_importance.csv"
        path = subtype if subtype.exists() else (global_ if global_.exists() else None)
    if path is None:
        return []
    try:
        df = pd.read_csv(path).sort_values("importance", ascending=False).head(top_n)
        return df[["feature", "importance"]].to_dict(orient="records")
    except Exception:
        return []


def format_feature_name(feature: str) -> str:
    """Convert raw model feature names into human-readable explanations."""
    fl = feature.lower()
    if "bldgarea" in fl or "gross_sqft" in fl:
        return "Building size significantly impacts property value"
    if "sqft_per_unit" in fl:
        return "Average unit size (sqft per unit) drives per-unit valuation"
    if "assess_per_unit" in fl:
        return "City-assessed value per unit reflects building quality and income potential"
    if "stabilization_ratio" in fl:
        return "Rent-stabilization rate affects cash-flow and resale dynamics significantly"
    if "numfloors" in fl:
        return "Building height (floors) is a key driver of condo and rental pricing"
    if "lot_coverage" in fl:
        return "Lot coverage (building density) reflects urban density and building type"
    if "units_per_floor" in fl:
        return "Units per floor captures building layout and density premium"
    if "bldg_footprint" in fl:
        return "Building footprint (front × depth) is a precise proxy for building area"
    if "builtfar" in fl:
        return "Built floor-area ratio reflects how densely the parcel is developed"
    if "lotdepth" in fl:
        return "Lot depth influences rear-yard potential and overall parcel value"
    if "subway_dist" in fl:
        return "Proximity to subway transit is a primary driver of NYC rental pricing"
    if "land_sqft" in fl:
        return "Land size contributes to overall property valuation"
    if "neighborhood_median_ppsf" in fl:
        return "Neighborhood price per sqft encodes the location-size value interaction"
    if "neighborhood_median_price" in fl:
        return "Neighborhood price level is a strong driver of property value"
    if "curmkttot" in fl or "curmkt" in fl:
        return "DOF-estimated market value is a strong indicator of property worth"
    if "curacttot" in fl or "curact" in fl:
        return "City-assessed value significantly influences estimated market price"
    if "acris_last_deed" in fl:
        return "Prior sale price captures historical market appreciation"
    if "acris_prior_sale" in fl:
        return "Number of prior sales reflects market activity for this parcel"
    if "j51" in fl:
        return "J-51 tax abatement status influences property economics"
    if "neighborhood" in fl:
        return "Neighborhood demand strongly influences pricing"
    if "borough" in fl:
        return "Location (borough) plays a key role in valuation"
    if "building_class" in fl or "bldg_class" in fl or "bldgclass" in fl:
        return "Building class is an important driver of estimated value"
    if "year_built" in fl or "property_age" in fl or "yrbuilt" in fl:
        return "Property age and build year affect valuation"
    if "total_units" in fl or "residential_units" in fl or "dof_units" in fl:
        return "Building unit count influences income potential and value"
    if "latitude" in fl or "longitude" in fl:
        return "Geographic positioning influences estimated price"
    return "Model identified this feature as influential"


# ─── Valuation interval ───────────────────────────────────────────────────────

def _valuation_interval_dollars(predicted_price: float,
                                 metadata: RegisteredModel,
                                 n_units: float) -> tuple[float, float] | None:
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
    return (max(0.0, predicted_price - half), predicted_price + half)


# ─── Spine feature row builder ────────────────────────────────────────────────

def _build_spine_row(payload: ProductionPredictionRequest,
                     metadata: RegisteredModel,
                     registry: ModelRegistry) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the feature dict expected by the spine sklearn Pipeline.

    The Pipeline's SimpleImputer(strategy="median") handles every NaN so we
    only need to populate the fields we actually have at inference time.
    Categorical NaN values are imputed with the most-frequent training class.

    Returns ``(row, join_meta)`` where ``join_meta`` describes optional BBL
    Gold-feature hydration (``bbl_join_status``: skipped | ok | partial | no_data).
    """
    model_key = metadata.segment
    neighborhood = payload.neighborhood.strip()
    n_units = max(payload.total_units or 1, 1)

    join_meta: dict[str, Any] = {"bbl_join_status": "skipped"}

    # ── Derived scalars ───────────────────────────────────────────────────────
    property_age = float(REFERENCE_YEAR - payload.year_built)

    # ── Neighborhood stats (from training-time medians) ───────────────────────
    nbhd_median_price = lookup_neighborhood_median(model_key, neighborhood, registry)
    dof_assess_per_unit = lookup_dof_assess_per_unit(model_key, neighborhood, registry)

    # ── Subway distance (exact haversine if lat/lon provided) ─────────────────
    subway_dist_km = lookup_subway_dist_km(payload.latitude, payload.longitude)

    row: dict[str, Any] = {
        # ── User-provided / directly derived ─────────────────────────────────
        "neighborhood_median_price":  nbhd_median_price,
        "property_age":               property_age,
        "total_units":                float(payload.total_units) if payload.total_units else np.nan,
        "residential_units":          float(payload.residential_units) if payload.residential_units else np.nan,

        # ── DOF features: user inputs where semantically equivalent ──────────
        # dof_gross_sqft ≈ gross_sqft from rolling sales
        "dof_gross_sqft":     float(payload.gross_sqft),
        "dof_yrbuilt":        float(payload.year_built),
        "dof_units":          float(payload.total_units) if payload.total_units else np.nan,
        "dof_assess_per_unit": dof_assess_per_unit,
        # DOF valuation columns not available at inference → pipeline median-imputes
        "dof_curmkttot":   np.nan,
        "dof_curacttot":   np.nan,
        "dof_curactland":  np.nan,
        "dof_curmktland":  np.nan,
        "dof_bld_story":   np.nan,

        # ── ACRIS features: not available at inference → median-imputed ───────
        "acris_prior_sale_cnt":       np.nan,
        "acris_last_deed_amt":        np.nan,
        "acris_days_since_last_deed": np.nan,
        "acris_mortgage_cnt":         np.nan,
        "acris_last_mtge_amt":        np.nan,

        # ── J-51 features: not available at inference → median-imputed ────────
        "j51_active_flag":    np.nan,
        "j51_last_abate_amt": np.nan,
        "j51_total_abatement": np.nan,

        # ── PLUTO geo: exact from user-provided coordinates ───────────────────
        "pluto_latitude":  payload.latitude,
        "pluto_longitude": payload.longitude,
        "subway_dist_km":  subway_dist_km,

        # ── PLUTO physical: not available at inference → median-imputed ───────
        "pluto_numfloors":      np.nan,
        "pluto_builtfar":       np.nan,
        "pluto_bldg_footprint": np.nan,
        "pluto_bldgarea":       np.nan,
        "pluto_lotarea":        np.nan,

        # ── Categorical features ──────────────────────────────────────────────
        # borough_name and neighborhood are known from the request.
        # DOF / PLUTO class codes are not available without a BBL lookup;
        # the OHE's handle_unknown="ignore" treats them as unseen categories
        # (all-zero vector), which is a safe and neutral fallback.
        "borough_name":    payload.borough,
        "neighborhood":    neighborhood,
        "dof_bldg_class":  np.nan,   # OHE: handle_unknown="ignore" → zero vector
        "dof_tax_class":   np.nan,
        "pluto_bldgclass": np.nan,
    }

    # ── Optional BBL + as_of_date → Silver / PLUTO as-of features ───────────
    bbl_raw, as_of_raw = payload.bbl, payload.as_of_date
    if (bbl_raw and not as_of_raw) or (as_of_raw and not bbl_raw):
        join_meta["bbl_join_status"] = "incomplete"
    elif bbl_raw and as_of_raw:
        bbl_n = normalize_bbl(bbl_raw)
        as_of = parse_as_of_date(as_of_raw)
        if not bbl_n or not as_of:
            join_meta["bbl_join_status"] = "invalid_bbl_or_date"
        else:
            join_meta["bbl_normalized"] = bbl_n
            join_meta["as_of_date"] = str(as_of)
            gold_feats, status = build_spine_gold_features_from_bbl(bbl_n, as_of)
            join_meta["bbl_join_status"] = status
            for k, v in gold_feats.items():
                if v is None:
                    continue
                if isinstance(v, (float, np.floating)) and bool(np.isnan(v)):
                    continue
                row[k] = v
            # Prefer DOF year-built for property_age when a roll row exists.
            yb = row.get("dof_yrbuilt")
            try:
                if yb is not None and yb == yb and float(yb) > 0:
                    row["property_age"] = float(
                        np.clip(REFERENCE_YEAR - float(yb), 0, 200)
                    )
            except (TypeError, ValueError):
                pass

    return row, join_meta


# ─── PredictionService ────────────────────────────────────────────────────────

class PredictionService:
    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def predict(self, payload: ProductionPredictionRequest) -> dict:
        model_key = self.registry.get_model_key(payload.building_class)
        warnings: list[str] = []
        join_meta: dict[str, Any] = {}

        # Rental models predict price_per_unit — need total_units to recover
        # the full building price. Fall back to global when missing.
        if model_key in ("rental_walkup", "rental_elevator"):
            if not payload.total_units or payload.total_units <= 0:
                model_key = "global"
                warnings.append(
                    "total_units was not provided for this rental building. "
                    "Falling back to the global residential model. "
                    "Supply total_units for a more accurate rental valuation."
                )

        model    = self.registry.load_model(model_key)
        metadata = self.registry.get_metadata(model_key)
        n_units  = max(payload.total_units or 1, 1)
        neighborhood = payload.neighborhood.strip()

        if metadata.is_spine_model:
            row, join_meta = _build_spine_row(payload, metadata, self.registry)
            all_features = metadata.numeric_features + metadata.categorical_features
            X = pd.DataFrame(
                [{col: row.get(col, np.nan) for col in all_features}],
                columns=all_features,
            )

            if join_meta.get("bbl_join_status") == "incomplete":
                warnings.append(
                    "Both bbl and as_of_date are required together for roll-aligned "
                    "DOF/ACRIS/J-51/PLUTO features; continuing with user fields only."
                )
            elif join_meta.get("bbl_join_status") == "invalid_bbl_or_date":
                warnings.append(
                    "Could not parse bbl or as_of_date; continuing without BBL-aligned roll features."
                )
            elif join_meta.get("bbl_join_status") == "no_data":
                warnings.append(
                    f"No Silver/PLUTO rows found for BBL {join_meta.get('bbl_normalized')!r} "
                    "at the given as_of_date (local data may be missing or BBL not in extract)."
                )
        else:
            # ── Legacy model path (global model, v1/v2 subtype models) ────────
            property_age = REFERENCE_YEAR - payload.year_built
            row = {
                "gross_sqft":         payload.gross_sqft,
                "land_sqft":          payload.land_sqft,
                "total_units":        payload.total_units,
                "residential_units":  payload.residential_units,
                "year_built":         payload.year_built,
                "property_age":       property_age,
                "latitude":           payload.latitude,
                "longitude":          payload.longitude,
                "borough":            str(payload.borough).strip(),
                "building_class":     payload.building_class.strip(),
                "neighborhood":       neighborhood,
            }
            if "sqft_per_unit" in metadata.feature_columns:
                row["sqft_per_unit"] = (payload.gross_sqft or 0) / n_units
            if "neighborhood_median_price" in metadata.feature_columns:
                row["neighborhood_median_price"] = lookup_neighborhood_median(
                    model_key, neighborhood, self.registry
                )
            if "assess_per_unit" in metadata.feature_columns:
                row["assess_per_unit"] = lookup_dof_assess_per_unit(
                    model_key, neighborhood, self.registry
                )
            X = pd.DataFrame(
                [[row.get(col) for col in metadata.feature_columns]],
                columns=metadata.feature_columns,
            )

        prediction_log = model.predict(X)[0]

        if metadata.target == "price_per_unit":
            predicted_price = float(math.expm1(prediction_log)) * n_units
        else:
            predicted_price = float(math.expm1(prediction_log))

        if model_key == "global" and not warnings:
            warnings.append(
                "Using global residential fallback model for this property type."
            )

        interval = _valuation_interval_dollars(predicted_price, metadata, n_units)
        input_summary: dict[str, Any] = {
            "borough":        payload.borough,
            "neighborhood":   neighborhood,
            "building_class": payload.building_class,
        }
        if metadata.is_spine_model and join_meta:
            if join_meta.get("bbl_normalized"):
                input_summary["bbl"] = join_meta["bbl_normalized"]
            if join_meta.get("as_of_date"):
                input_summary["as_of_date"] = join_meta["as_of_date"]
            input_summary["bbl_feature_status"] = join_meta.get("bbl_join_status", "skipped")

        out: dict = {
            "predicted_price": predicted_price,
            "model_used":      metadata.name,
            "model_version":   metadata.version,
            "segment":         metadata.segment,
            "input_summary":   input_summary,
            "warnings":      warnings,
            "model_metrics": metadata.metrics,
        }
        if interval:
            low, high = interval
            out["price_low"]               = low
            out["price_high"]              = high
            out["valuation_interval_note"] = VALUATION_INTERVAL_NOTE
        return out

    def analyze(self, request, *, user_id=None, role="user",
                auth_method="jwt", db=None):
        """Combines ML prediction with investment analysis and LLM explanation."""
        prediction_result = self.predict(request)

        predicted_price = prediction_result["predicted_price"]
        market_price    = request.market_price

        price_difference = predicted_price - market_price
        roi_estimate = (price_difference / market_price) * 100 if market_price > 0 else 0

        price_gap_pct  = (price_difference / market_price) if market_price > 0 else 0.0
        clamped_roi    = max(-20.0, min(roi_estimate, 20.0))
        roi_score      = ((clamped_roi + 20) / 40) * 100.0
        clamped_gap    = max(-0.30, min(price_gap_pct, 0.30))
        valuation_score = ((clamped_gap + 0.30) / 0.60) * 100.0
        risk_penalty   = min(abs(price_gap_pct) * 100.0, 30.0)
        raw_score = (0.60 * roi_score) + (0.30 * valuation_score) - (0.10 * risk_penalty)
        investment_score = max(0, min(100, round(raw_score)))

        if investment_score >= 70:
            deal_label = "Buy"
        elif investment_score >= 40:
            deal_label = "Hold"
        else:
            deal_label = "Avoid"

        model_key = prediction_result.get("segment", "global")
        raw_drivers = [
            format_feature_name(item["feature"])
            for item in load_model_feature_importance(
                model_key, top_n=3, registry=self.registry
            )
        ]
        seen: set[str] = set()
        top_drivers: list[str] = []
        for d in raw_drivers:
            if d not in seen:
                seen.add(d)
                top_drivers.append(d)

        if price_difference > 0:
            summary = (
                f"Property appears undervalued by approximately "
                f"${price_difference:,.0f} based on model analysis."
            )
        else:
            summary = (
                f"Property may be overpriced by approximately "
                f"${abs(price_difference):,.0f} based on model analysis."
            )

        explanation_factors = [
            {
                "factor": "predicted_price",
                "value":  predicted_price,
                "reason": "Derived from trained ML model using property features",
            },
            {
                "factor": "market_price",
                "value":  market_price,
                "reason": "User-provided listing price",
            },
        ]

        llm_explanation = generate_explanation(
            {
                "predicted_price":  predicted_price,
                "market_price":     market_price,
                "roi_estimate":     roi_estimate,
                "investment_score": investment_score,
                "top_drivers":      top_drivers,
            },
            user_id=user_id,
            role=role,
            auth_method=auth_method,
            db=db,
        )

        price_difference_pct = (
            (price_difference / market_price) * 100 if market_price > 0 else 0.0
        )
        valuation_block: dict = {
            "predicted_price":     predicted_price,
            "market_price":        market_price,
            "price_difference":    price_difference,
            "price_difference_pct": price_difference_pct,
        }
        if prediction_result.get("price_low") is not None:
            valuation_block["price_low"]  = prediction_result["price_low"]
            valuation_block["price_high"] = prediction_result["price_high"]
            valuation_block["valuation_interval_note"] = prediction_result.get(
                "valuation_interval_note"
            )

        return {
            "valuation": valuation_block,
            "investment_analysis": {
                "roi_estimate":     roi_estimate,
                "investment_score": investment_score,
                "deal_label":       deal_label,
                "recommendation":   llm_explanation.get("recommendation", "Hold"),
                "confidence":       llm_explanation.get("confidence", "Low"),
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
                "summary":        llm_explanation.get("summary", "AI explanation unavailable"),
                "opportunity":    llm_explanation.get("opportunity", "N/A"),
                "risks":          llm_explanation.get("risks", "N/A"),
                "recommendation": llm_explanation.get("recommendation", "Hold"),
                "confidence":     llm_explanation.get("confidence", "Low"),
            },
            "metadata": {
                "model_version": prediction_result.get("model_version", "v3"),
            },
        }
