from dataclasses import dataclass
from pathlib import Path
import json
import joblib

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
    

BASE_DIR = Path(__file__).resolve().parents[3]

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
        self._loaded_models = {}

    def load_model(self, key: str):
        if key not in self._models:
            raise ValueError(f"Unknown model key: {key}")

        if key not in self._loaded_models:
            # Resolve artifact_path relative to project root, not CWD
            artifact_path = BASE_DIR / self._models[key].artifact_path
            self._loaded_models[key] = joblib.load(artifact_path)

        return self._loaded_models[key]
    
    def _load_metadata(self, filename: str) -> RegisteredModel:
        metadata_path = self.metadata_dir / filename
        
        with open(metadata_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return RegisteredModel(
            name=data["name"],
            version=data["version"],
            segment=data["segment"],
            artifact_path=data["artifact_path"],
            feature_columns=data["feature_columns"],
            metrics=data["metrics"],
            target=data.get("target", "sales_price"),
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
        if bc == "07 RENTALS - WALKUP APARTMENTS":
            return "rental_walkup"
        if bc == "08 RENTALS - ELEVATOR APARTMENTS":
            return "rental_elevator"
        return "global"
    
    
    def get_metadata(self, key: str) -> RegisteredModel:
        if key not in self._models:
            raise ValueError(f"Unknown model key: {key}")
        return self._models[key]
        