from dataclasses import dataclass, field
from pathlib import Path
import json
import joblib

BASE_DIR = Path(__file__).resolve().parents[3]


@dataclass
class RegisteredModel:
    name: str
    version: str
    segment: str
    artifact_path: str
    feature_columns: list[str]
    metrics: dict
    # "sales_price" for most models; "price_per_unit" for rental subtypes.
    # When target is "price_per_unit", the predictor multiplies the model output
    # by total_units to recover the full building sale price.
    target: str = "sales_price"
    # Spine v3 models split features into numeric + categorical separately.
    # Empty lists indicate a legacy model that uses feature_columns directly.
    numeric_features: list[str] = field(default_factory=list)
    categorical_features: list[str] = field(default_factory=list)
    # Paths to supplementary artifacts (stats JSON, feature importance CSV).
    stats_path: str | None = None
    feature_importance_path: str | None = None

    @property
    def is_spine_model(self) -> bool:
        """True when the model is a v3 spine pipeline (sklearn ColumnTransformer)."""
        return bool(self.numeric_features or self.categorical_features)


class ModelRegistry:
    def __init__(self) -> None:
        self.base_dir = BASE_DIR
        self.metadata_dir = BASE_DIR / "ml" / "artifacts" / "metadata"
        self._models = {
            "global":          self._load_metadata("global_model.json"),
            "one_family":      self._load_metadata("one_family_model.json"),
            "multi_family":    self._load_metadata("multi_family_model.json"),
            "condo_coop":      self._load_metadata("condo_coop_model.json"),
            "rental_walkup":   self._load_metadata("rental_walkup_model.json"),
            "rental_elevator": self._load_metadata("rental_elevator_model.json"),
        }
        # Promote rentals_all if its metadata exists.  When present it overrides
        # the two individual rental models in get_model_key().
        _rentals_all_meta = self.metadata_dir / "rentals_all_model.json"
        if _rentals_all_meta.exists():
            self._models["rentals_all"] = self._load_metadata("rentals_all_model.json")
        self._loaded_models = {}

    def load_model(self, key: str):
        if key not in self._models:
            raise ValueError(f"Unknown model key: {key}")
        if key not in self._loaded_models:
            artifact_path = BASE_DIR / self._models[key].artifact_path
            self._loaded_models[key] = joblib.load(artifact_path)
        return self._loaded_models[key]

    def _load_metadata(self, filename: str) -> RegisteredModel:
        metadata_path = self.metadata_dir / filename
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Legacy models store a flat feature_columns list.
        # Spine models store separate numeric_features + categorical_features.
        numeric  = data.get("numeric_features", [])
        cat      = data.get("categorical_features", [])
        # feature_columns on spine models = numeric + categorical (used by
        # legacy code paths that iterate over metadata.feature_columns).
        legacy_cols = data.get("feature_columns", numeric + cat)

        return RegisteredModel(
            name=data["name"],
            version=data["version"],
            segment=data["segment"],
            artifact_path=data["artifact_path"],
            feature_columns=legacy_cols,
            metrics=data["metrics"],
            target=data.get("target", "sales_price"),
            numeric_features=numeric,
            categorical_features=cat,
            stats_path=data.get("stats_path"),
            feature_importance_path=data.get("feature_importance_path"),
        )

    def get_model_key(self, building_class: str) -> str:
        bc = building_class.strip()

        ONE_FAMILY = {"01 ONE FAMILY DWELLINGS"}
        MULTI_FAMILY = {"02 TWO FAMILY DWELLINGS", "03 THREE FAMILY DWELLINGS"}
        CONDO_COOP = {
            "09 COOPS - WALKUP APARTMENTS",
            "10 COOPS - ELEVATOR APARTMENTS",
            "12 CONDOS - WALKUP APARTMENTS",
            "13 CONDOS - ELEVATOR APARTMENTS",
            "15 CONDOS - 2-10 UNIT RESIDENTIAL",
            "17 CONDO COOPS",
        }
        if bc in ONE_FAMILY:
            return "one_family"
        if bc in MULTI_FAMILY:
            return "multi_family"
        if bc in CONDO_COOP:
            return "condo_coop"
        # Route both rental classes to rentals_all when available (pooled model).
        if bc in ("07 RENTALS - WALKUP APARTMENTS", "08 RENTALS - ELEVATOR APARTMENTS"):
            if "rentals_all" in self._models:
                return "rentals_all"
            return "rental_walkup" if bc == "07 RENTALS - WALKUP APARTMENTS" else "rental_elevator"
        return "global"

    def get_metadata(self, key: str) -> RegisteredModel:
        if key not in self._models:
            raise ValueError(f"Unknown model key: {key}")
        return self._models[key]

    def stats_path_for(self, key: str) -> Path | None:
        """Resolve the neighborhood stats JSON path for a model key."""
        m = self._models.get(key)
        if m and m.stats_path:
            return BASE_DIR / m.stats_path
        # Legacy fallback: subtype_models directory
        legacy = BASE_DIR / f"ml/artifacts/subtype_models/{key}_neighborhood_stats.json"
        return legacy if legacy.exists() else None

    def feature_importance_path_for(self, key: str) -> Path | None:
        """Resolve the feature importance CSV path for a model key."""
        m = self._models.get(key)
        if m and m.feature_importance_path:
            p = BASE_DIR / m.feature_importance_path
            return p if p.exists() else None
        # Legacy fallbacks
        for p in [
            BASE_DIR / f"ml/artifacts/subtype_models/{key}_feature_importance.csv",
            BASE_DIR / "ml/artifacts/feature_importance.csv",
        ]:
            if p.exists():
                return p
        return None
