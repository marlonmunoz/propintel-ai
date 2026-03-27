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
    

class ModelRegistry:
    def __init__(self) -> None:
        self.metadata_dir = Path("ml/artifacts/metadata")
        self._models = {
            "global": self._load_metadata("global_model.json"),
            "one_family": self._load_metadata("one_family_model.json"),
        }
        self._loaded_models = {}
    
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
        )
        
    def get_model_key(self, building_class: str) -> str:
        if building_class.strip() == "01 ONE FAMILY DWELLINGS":
            return "one_family"
        return "global"
    
    
    def load_model(self, key: str):
        if key not in self._models:
            raise ValueError(f"Unknown model key: {key}")
        
        if key not in self._loaded_models:
            artifact_path = self._models[key].artifact_path
            self._loaded_models[key] = joblib.load(artifact_path)
            
        return self._loaded_models[key]
    
    
    def get_metadata(self, key: str) -> RegisteredModel:
        if key not in self._models:
            raise ValueError(f"Unknown model key: {key}")
        return self._models[key]
        