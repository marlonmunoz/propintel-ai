import joblib
import json
import numpy as np
import pandas as pd
from pathlib import Path

# Must match feature_engineering.py so property_age means the same thing
# at training time and when the feature pipeline is re-run.
REFERENCE_YEAR = 2024

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

    # Per-subtype XGBoost hyperparameters.
# Tuned based on dataset size and property class characteristics.
# No early stopping — each model trains to its full n_estimators on the
# complete 80% training split, which consistently outperforms small-validation
# early stopping on these dataset sizes.
SUBTYPE_XGB_PARAMS = {
    "one_family": {
        "n_estimators": 500,
        "learning_rate": 0.05,
        "max_depth": 6,
        "min_child_weight": 3,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "gamma": 0.1,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
    },
    "multi_family": {
        # Shallower trees for the 2+3-family building mix.
        "n_estimators": 500,
        "learning_rate": 0.05,
        "max_depth": 5,
        "min_child_weight": 3,
        "subsample": 0.8,
        "colsample_bytree": 0.7,
        "gamma": 0.1,
        "reg_alpha": 0.05,
        "reg_lambda": 1.0,
    },
    "condo_coop": {
        # Hits 300 trees easily with limited numeric features — more trees help.
        "n_estimators": 800,
        "learning_rate": 0.05,
        "max_depth": 5,
        "min_child_weight": 4,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "gamma": 0.1,
        "reg_alpha": 0.3,
        "reg_lambda": 1.0,
    },
    "rental_walkup": {
        # ~1,500 rows after cleaning — moderate capacity, moderate regularization.
        "n_estimators": 400,
        "learning_rate": 0.05,
        "max_depth": 5,
        "min_child_weight": 3,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "gamma": 0.1,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
    },
    "rental_elevator": {
        # ~250 rows after cleaning — small dataset, strong regularization to avoid
        # overfitting. Shallower trees prevent the model from memorising outliers.
        "n_estimators": 300,
        "learning_rate": 0.04,
        "max_depth": 4,
        "min_child_weight": 5,
        "subsample": 0.8,
        "colsample_bytree": 0.7,
        "gamma": 0.2,
        "reg_alpha": 0.5,
        "reg_lambda": 2.0,
    },
}

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
    "rental_walkup": [
        "07 RENTALS - WALKUP APARTMENTS",
    ],
    "rental_elevator": [
        "08 RENTALS - ELEVATOR APARTMENTS",
    ],
}

SUBTYPE_FEATURES = {
    "one_family": {
        "numeric": [
            "gross_sqft",
            "land_sqft",
            "neighborhood_median_price",
            "year_built",
            "property_age",
            "latitude",
            "longitude",
        ],
        "categorical": [
            "borough",
            "building_class",
            "neighborhood",
        ],
        "require_gross_sqft": True,
    },
    "multi_family": {
        "numeric": [
            "gross_sqft",
            "land_sqft",
            "neighborhood_median_price",
            "year_built",
            "property_age",
            "latitude",
            "longitude",
        ],
        "categorical": [
            "borough",
            "building_class",
            "neighborhood",
        ],
        "require_gross_sqft": True,
    },
    "condo_coop": {
        # NYC co-op transactions record share sales, not physical units,
        # so gross_sqft and land_sqft are almost universally null in the
        # rolling sales data. We rely on location + age + categorical signals.
        "numeric": [
            "neighborhood_median_price",
            "year_built",
            "property_age",
            "latitude",
            "longitude",
        ],
        "categorical": [
            "borough",
            "building_class",
            "neighborhood",
        ],
        "require_gross_sqft": False,
    },
    # Rental walkup (07) and elevator (08) are trained as separate models because
    # they serve different buyer profiles and price levels.
    # Both use price_per_unit as the prediction target — the model learns
    # $/unit rather than total building price, which normalises for building
    # size and produces a tighter, more learnable target distribution.
    # At inference, predicted $/unit is multiplied by total_units to recover
    # the full building price estimate.
    "rental_walkup": {
        "numeric": [
            "gross_sqft",
            "land_sqft",
            "sqft_per_unit",
            "total_units",
            "residential_units",
            "neighborhood_median_price",
            "year_built",
            "property_age",
            "latitude",
            "longitude",
        ],
        "categorical": [
            "borough",
            "building_class",
            "neighborhood",
        ],
        "require_gross_sqft": True,
        "target": "price_per_unit",
    },
    "rental_elevator": {
        "numeric": [
            "gross_sqft",
            "land_sqft",
            "sqft_per_unit",
            "total_units",
            "residential_units",
            "neighborhood_median_price",
            "year_built",
            "property_age",
            "latitude",
            "longitude",
        ],
        "categorical": [
            "borough",
            "building_class",
            "neighborhood",
        ],
        "require_gross_sqft": True,
        "target": "price_per_unit",
        # Lower minimum rows — elevator dataset is smaller after cleaning.
        "min_rows": 100,
    },
}


def load_data():
    print("Loading subtype training dataset...")
    return pd.read_csv(INPUT_FILE, low_memory=False)


def build_preprocessor(numeric_features, categorical_features) -> ColumnTransformer:
    """Return a fitted-ready ColumnTransformer for the given feature lists."""
    numeric_transformer = Pipeline(
        steps=[("imputer", SimpleImputer(strategy="median"))]
    )
    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )


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
        "total_units",
        "residential_units",
        "year_built",
        "latitude",
        "longitude",
    ]
    for col in numeric_cols:
        if col in subset.columns:
            subset[col] = pd.to_numeric(subset[col], errors="coerce")

    subset["property_age"] = REFERENCE_YEAR - subset["year_built"]

    subset = subset.dropna(subset=["sales_price", "year_built", "latitude", "longitude"])

    feature_config = SUBTYPE_FEATURES[subtype_name]

    if feature_config["require_gross_sqft"]:
        subset = subset[subset["gross_sqft"].notna() & (subset["gross_sqft"] > 0)]

    # Compute neighborhood-level median price from the filtered training data.
    # This gives the model a direct numeric signal about each neighborhood's
    # price level rather than relying solely on one-hot categorical encoding.
    neighborhood_medians = subset.groupby("neighborhood")["sales_price"].median()
    global_median = float(subset["sales_price"].median())
    subset["neighborhood_median_price"] = (
        subset["neighborhood"].map(neighborhood_medians).fillna(global_median)
    )
    neighborhood_stats = {
        "neighborhoods": neighborhood_medians.to_dict(),
        "global_median": global_median,
    }

    numeric_features = feature_config["numeric"]
    categorical_features = feature_config["categorical"]

    # Derived features for rental subtypes that use price_per_unit as target.
    target = feature_config.get("target", "sales_price")
    if target == "price_per_unit":
        # Require total_units > 0 — needed for both sqft_per_unit and the target.
        subset = subset[subset["total_units"].notna() & (subset["total_units"] > 0)]
        subset["price_per_unit"] = subset["sales_price"] / subset["total_units"]

    if "sqft_per_unit" in numeric_features:
        # gross_sqft / total_units: normalised size signal more meaningful than
        # raw sqft for income-producing buildings with variable unit counts.
        subset["sqft_per_unit"] = subset["gross_sqft"] / subset["total_units"].clip(lower=1)

    feature_columns = numeric_features + categorical_features
    existing_columns = [col for col in feature_columns if col in subset.columns]

    X = subset[existing_columns].copy()

    for col in categorical_features:
        if col in X.columns:
            X[col] = X[col].astype(str)

    if target == "price_per_unit":
        y = np.log1p(subset["price_per_unit"].copy())
    else:
        y = np.log1p(subset["sales_price"].copy())

    return subset, X, y, numeric_features, categorical_features, neighborhood_stats


def train_subtype_model(df: pd.DataFrame, subtype_name: str, building_classes: list[str]):
    subset = df[df["building_class"].isin(building_classes)].copy()

    print(f"\n=== {subtype_name.upper()} ===")
    print(f"Rows before subtype-specific filtering: {len(subset)}")

    subset, X, y, numeric_features, categorical_features, neighborhood_stats = (
        prepare_subset_for_training(subset, subtype_name)
    )

    target = SUBTYPE_FEATURES[subtype_name].get("target", "sales_price")
    min_rows = SUBTYPE_FEATURES[subtype_name].get("min_rows", 500)

    print(f"Rows after subtype-specific filtering: {len(subset)}")
    print(f"Target variable: {target}")
    print(f"Numeric features: {numeric_features}")
    print(f"Categorical features: {categorical_features}")

    if len(subset) < min_rows:
        print(f"Skipped: only {len(subset)} rows (minimum: {min_rows})")
        return None

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    xgb_params = SUBTYPE_XGB_PARAMS[subtype_name]

    preprocessor = build_preprocessor(numeric_features, categorical_features)
    X_train_proc = preprocessor.fit_transform(X_train)
    X_test_proc  = preprocessor.transform(X_test)

    regressor = XGBRegressor(
        **xgb_params,
        random_state=42,
        n_jobs=-1,
        objective="reg:squarederror",
    )
    regressor.fit(X_train_proc, y_train)

    y_pred = regressor.predict(X_test_proc)
    mae, rmse, r2 = evaluate_predictions(y_test, y_pred)

    model = Pipeline([
        ("preprocessor", preprocessor),
        ("regressor", regressor),
    ])

    unit_label = "$/unit" if target == "price_per_unit" else "$"
    print(f"MAE:  {mae:,.2f} {unit_label}")
    print(f"RMSE: {rmse:,.2f} {unit_label}")
    print(f"R²:   {r2:.4f}")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = ARTIFACTS_DIR / f"{subtype_name}_price_model.pkl"
    joblib.dump(model, model_path)

    stats_path = ARTIFACTS_DIR / f"{subtype_name}_neighborhood_stats.json"
    with open(stats_path, "w") as f:
        json.dump(neighborhood_stats, f, indent=2)
    print(f"Neighborhood stats saved: {len(neighborhood_stats['neighborhoods'])} neighborhoods")

    try:
        feature_names = model.named_steps["preprocessor"].get_feature_names_out()
        importances = model.named_steps["regressor"].feature_importances_
        fi_df = pd.DataFrame({"feature": feature_names, "importance": importances})
        fi_df = fi_df.sort_values("importance", ascending=False)
        fi_path = ARTIFACTS_DIR / f"{subtype_name}_feature_importance.csv"
        fi_df.to_csv(fi_path, index=False)
        print(f"Feature importances saved: {fi_path.name}")
    except Exception as e:
        print(f"Warning: could not save feature importances — {e}")

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