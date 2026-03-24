from dataclasses import dataclass
import joblib

@dataclass
class RegisteredModel:
    name: str
    version: str
    segment: str
    artifact_path: str
    feature_columns: list[str]
    
GLOBAL_FEATURES = [
    "gross_sqft",
    "land_sqft",
    "year_built",
    "property_age",
    "latitude",
    "longitude",
    "borough",
    "building_class",
    "neighborhood",
]

ONE_FAMILY_FEATURES = [
    "gross_sqft",
    "land_sqft",
    "year_built",
    "property_age",
    "latitude",
    "longitude",
    "borough",
    "building_class",
    "neighborhood",
]

class ModelRegistry:
    def __init__(self) -> None:
        self._models = {
            "global": RegisteredModel(
                name="global",
                version="v1",
                segment="all_residential",
                artifact_path="ml/artifacts/price_model.pkl",
                feature_columns=GLOBAL_FEATURES,
            ),
            "one_family": RegisteredModel(
                name="one_family",
                version="v1",
                segment="one_family",
                artifact_path="ml/artifacts/subtype_models/one_family_price_model.pkl",
                feature_columns=ONE_FAMILY_FEATURES,
            ),
        }
        self._loaded_models = {}
        
        
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
        