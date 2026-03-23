import joblib
import numpy as np
import pandas as pd
from pathlib import Path 

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = BASE_DIR / "ml/data/features/nyc_features.csv"
ARTIFACTS_DIR = BASE_DIR / "ml/artifacts"
MODEL_FILE = ARTIFACTS_DIR / "price_model.pkl"
FEATURE_IMPORTANCE_FILE = ARTIFACTS_DIR / "feature_importance.csv"


def load_data():
    """Load engineered NYC feature dataset."""
    print(f"Loading feature dataset...")
    return pd.read_csv(INPUT_FILE, low_memory=False)


def prepare_features(df):
    """Prepare X and y for training."""
    feature_columns = [
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
    
    target_column = "sales_price"
    
    existing_columns = [col for col in feature_columns if col in df.columns]
    df = df.dropna(subset=[target_column])
    
    X = df[existing_columns].copy()
    
    if "borough" in X.columns:
        X["borough"] = X["borough"].astype(str)
        
    y = np.log1p(df[target_column].copy())
    
    return X, y


def build_pipeline():
    """Build preprocessing + model pipeline."""
    # numeric_features = X.select_dtypes(include=["number"]).columns.tolist()
    # categorical_features = X.select_dtypes(exclude=["number"]).columns.tolist()
    numeric_features = [
        "gross_sqft", 
        "land_sqft", 
        "year_built", 
        "property_age",
        "latitude",
        "longitude",
    ]
    
    categorical_features = [
        "borough", 
        "building_class", 
        "neighborhood"
    ]
    
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
                random_state=42,
                n_jobs=-1,
                objective="reg:squarederror",
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
    """Print and save top feature importances."""
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

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    importance_df.to_csv(FEATURE_IMPORTANCE_FILE, index=False)

    print(f"\nFeature importance saved to {FEATURE_IMPORTANCE_FILE}")


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
    
    pipeline = build_pipeline()
    
    param_grid = {
        "regressor__n_estimators": [200, 300],
        "regressor__learning_rate": [0.03, 0.05],
        "regressor__max_depth": [4, 6],
        "regressor__subsample": [0.8, 1.0],
        "regressor__colsample_bytree": [0.8, 1.0],
    }
    
    grid_search = GridSearchCV(
        estimator=pipeline,
        param_grid=param_grid,
        scoring="neg_mean_absolute_error",
        cv=3,
        verbose=2,
        n_jobs=-1,
    )
    
    grid_search.fit(X_train, y_train)
    
    print("Best Params")
    print("-----------")
    print(grid_search.best_params_)
    
    best_model = grid_search.best_estimator_
  
    
    y_pred = best_model.predict(X_test)

    evaluate_model(y_test, y_pred)
    print_feature_importance(best_model)
    save_model(best_model)
    
if __name__ == "__main__":
    train()