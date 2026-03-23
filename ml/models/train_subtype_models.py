import joblib
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

BASE_DIR = Path(__file__).resolve().parents[2]

INPUT_FILE = BASE_DIR / "ml/data/processed/nyc_subtype_training_data.csv"
ARTIFACTS_DIR = BASE_DIR / "ml/artifacts/subtype_models"
METRICS_FILE = ARTIFACTS_DIR / "subtype_model_metrics.csv"

SUBTYPE_GROUPS = {
    "one_family": [
        "01 ONE FAMILY DWELLINGS",
    ],
    "multi_family": [
        "02 TWO FAMILY DWELLINGS",
        "03 THREE FAMILY DWELLINGS",
    ],
    "condo_coop": [
        "09 COOPS - WALKUP APARTMENTS",
        "10 COOPS - ELEVATOR APARTMENTS",
        "12 CONDOS - WALKUP APARTMENTS",
        "13 CONDOS - ELEVATOR APARTMENTS",
        "15 CONDOS - 2-10 UNIT RESIDENTIAL",
        "17 CONDO COOPS",
    ],
    "rental": [
        "07 RENTALS - WALKUP APARTMENTS",
        "08 RENTALS - ELEVATOR APARTMENTS",
    ],
}


def load_data():
    print("Loading subtype training dataset...")
    return pd.read_csv(INPUT_FILE, low_memory=False)


def build_pipeline():
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
        "neighborhood",
    ]

    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
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
        steps=[
            ("preprocessor", preprocessor),
            ("regressor", XGBRegressor(
                n_estimators=300,
                learning_rate=0.05,
                max_depth=6,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
                objective="reg:squarederror",
            )),
        ]
    )

    return model


def evaluate_predictions(y_test_log, y_pred_log):
    y_test = np.expm1(y_test_log)
    y_pred = np.expm1(y_pred_log)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    return mae, rmse, r2


def prepare_subset_for_training(subset: pd.DataFrame, subtype_name: str):
    subset = subset.copy()

    numeric_cols = [
        "sales_price",
        "gross_sqft",
        "land_sqft",
        "year_built",
        "latitude",
        "longitude",
    ]
    for col in numeric_cols:
        if col in subset.columns:
            subset[col] = pd.to_numeric(subset[col], errors="coerce")

    subset["property_age"] = 2026 - subset["year_built"]

    subset = subset.dropna(subset=["sales_price", "year_built", "latitude", "longitude"])

    if subtype_name in {"one_family", "multi_family", "rental"}:
        subset = subset[subset["gross_sqft"].notna() & (subset["gross_sqft"] > 0)]

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

    existing_columns = [col for col in feature_columns if col in subset.columns]

    X = subset[existing_columns].copy()
    if "borough" in X.columns:
        X["borough"] = X["borough"].astype(str)

    y = np.log1p(subset["sales_price"].copy())

    return subset, X, y


def train_subtype_model(df: pd.DataFrame, subtype_name: str, building_classes: list[str]):
    subset = df[df["building_class"].isin(building_classes)].copy()

    print(f"\n=== {subtype_name.upper()} ===")
    print(f"Rows before subtype-specific filtering: {len(subset)}")

    subset, X, y = prepare_subset_for_training(subset, subtype_name)

    print(f"Rows after subtype-specific filtering: {len(subset)}")

    if len(subset) < 500:
        print("Skipped: not enough rows")
        return None

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = build_pipeline()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae, rmse, r2 = evaluate_predictions(y_test, y_pred)

    print(f"MAE:  {mae:,.2f}")
    print(f"RMSE: {rmse:,.2f}")
    print(f"R²:   {r2:.4f}")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = ARTIFACTS_DIR / f"{subtype_name}_price_model.pkl"
    joblib.dump(model, model_path)

    return {
        "subtype": subtype_name,
        "rows": len(subset),
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "model_path": str(model_path),
    }


def main():
    df = load_data()

    results = []
    for subtype_name, building_classes in SUBTYPE_GROUPS.items():
        result = train_subtype_model(df, subtype_name, building_classes)
        if result:
            results.append(result)

    if not results:
        print("No subtype models were trained.")
        return

    results_df = pd.DataFrame(results).sort_values("r2", ascending=False)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    results_df.to_csv(METRICS_FILE, index=False)

    print("\n=== SUBTYPE MODEL SUMMARY ===")
    print(results_df.to_string(index=False))
    print(f"\nSaved metrics to {METRICS_FILE}")


if __name__ == "__main__":
    main()