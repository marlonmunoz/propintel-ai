import joblib
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = BASE_DIR / "ml/data/features/nyc_features.csv"
ARTIFACTS_DIR = BASE_DIR / "ml/artifacts"
MODEL_FILE = ARTIFACTS_DIR / "price_model.pkl"


def load_data():
    """Load engineered NYC feature dataset."""
    print(f"Loading feature dataset...")
    return pd.read_csv(INPUT_FILE, low_memory=False)


def prepare_features(df):
    """Prepare X and y for training."""
    feature_columns = [
        "gross_square_feet",
        "land_square_feet",
        "residential_units",
        "commercial_units",
        "total_units",
        "numfloors",
        "unitsres",
        "unitstotal",
        "lotarea",
        "bldgarea",
        "latitude",
        "longitude",
        "pluto_year_built",
        "building_age",
        "borough",
        "building_class_category",
        "neighborhood",
        "zip_code",
    ]
    
    target_column = "sale_price"
    
    existing_columns = [col for col in feature_columns if col in df.columns]
    df = df.dropna(subset=[target_column])
    
    X = df[existing_columns].copy()
    y = np.log1p(df[target_column].copy())
    
    return X, y


def build_pipeline(X):
    """Build preprocessing + model pipeline."""
    numeric_features = X.select_dtypes(include=["number"]).columns.tolist()
    categorical_features = X.select_dtypes(exclude=["number"]).columns.tolist()
    
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )
    
    categorical_transformer = Pipeline(
        steps= [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )
    
    model = Pipeline(
        steps= [
            ("preprocessor", preprocessor),
            ("regressor", XGBRegressor(
                n_estimators=300,
                learning_rate=0.05,
                max_depth=6,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
            )),
        ]
    )
    
    return model



def evaluate_model(y_test_log, y_pred_log):
    """Evaluate on original dollar scale and log scale."""
    y_test = np.expm1(y_test_log)
    y_pred = np.expm1(y_pred_log)
    
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    
    print("\nModel Performance (original price scale)")
    print("-----------------------------------------")
    print(f"MAE:  {mae:,.2f}")
    print(f"RMSE: {rmse:,.2f}")
    print(f"R²:   {r2:.4f}")
    
    
def print_feature_importance(model, top_n=15):
    """Print top feature importances from the trained XGBoost pipeline."""
    preprocessor = model.named_steps["preprocessor"]
    regressor = model.named_steps["regressor"]
    
    feature_names = preprocessor.get_feature_names_out()
    importances = regressor.feature_importances_
    
    importance_df = pd.DataFrame({
        "feature": feature_names,
        "importance": importances
    }).sort_values("importance", ascending=False)
    
    print("\nTop Feature Importances")
    print("-----------------------")
    print(importance_df.head(top_n).to_string(index=False))


def save_model(model):
    """Save trained model artifact."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_FILE)
    print(f"\nModel saved to {MODEL_FILE}")
    
    

def train():
    print("Training PropIntel pricing model...")
    
    df = load_data()
    X, y = prepare_features(df)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X,y, test_size=0.2, random_state=42
    )
    
    model = build_pipeline(X)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)

    evaluate_model(y_test, y_pred)
    print_feature_importance(model)
    save_model(model)
    
if __name__ == "__main__":
    train()