import os
import joblib
import pandas as pd 
import numpy as np 
from pathlib import Path

from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.model_selection import train_test_split
from catboost import CatBoostRegressor, Pool


BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = BASE_DIR / "ml/data/features/nyc_features.csv"
ARTIFACTS_DIR = BASE_DIR / "ml/artifacts"
MODEL_FILE = ARTIFACTS_DIR / "catboost_model.joblib"

def load_data():
    print("Laodind feature dataset...")
    return pd.read_csv(INPUT_FILE, low_memory=False)


def prepare_features(df):
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
    
    df = df.dropna(subset=[target_column]).copy()
    
    X = df[feature_columns].copy()
    y = np.log1p(df[target_column].copy())
    
    categorical_features = ["borough", "building_class", "neighborhood"]
    
    for col in categorical_features:
        X[col] = X[col].astype(str) 
        
    return X, y, categorical_features

def evaluate_model(y_test_log, y_pred_log):
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
    
    return mae, rmse, r2

def train():
    print("Training PropIntel Catboost pricing model...")
    
    df = load_data()
    X, y, categorical_features = prepare_features(df)
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    cat_feature_indices = [X.columns.get_loc(col) for col in categorical_features]
    
    model = CatBoostRegressor(
        iterations=1000,
        learning_rate=0.05,
        depth=6,
        loss_function="RMSE",
        eval_metric="RMSE",
        random_seed=42,
        verbose=100
    )
    
    model.fit(
        X_train,
        y_train,
        cat_features=cat_feature_indices,
        eval_set=(X_test, y_test),
        use_best_model=True
    )
    
    y_pred = model.predict(X_test)
    
    evaluate_model(y_test, y_pred)
    
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_FILE)
    print(f"\nModel saved to {MODEL_FILE}")
    
if __name__ == "__main__":
    train()