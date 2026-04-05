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
# Phase 2a (deprecated): enriched rental CSV from Rolling Sales + PLUTO BBL join.
INPUT_FILE_RENTAL = BASE_DIR / "ml/data/processed/nyc_rental_enriched_training_data.csv"
# Phase 2b: rental training data with stabilization_ratio from raw Excel + PLUTO + DHCR rentstab.
INPUT_FILE_RENTAL_STAB = BASE_DIR / "ml/data/processed/nyc_rental_stab_training_data.csv"
# Condo/co-op training data with assess_per_unit from raw Excel + PLUTO BBL join.
INPUT_FILE_CONDO = BASE_DIR / "ml/data/processed/nyc_condo_training_data.csv"
ARTIFACTS_DIR = BASE_DIR / "ml/artifacts/subtype_models"
METRICS_FILE = ARTIFACTS_DIR / "subtype_model_metrics.csv"

# Per-subtype XGBoost hyperparameters.
# Tuned based on dataset size and property class characteristics.
# No early stopping — each model trains to its full n_estimators on the
# complete 80% training split, which consistently outperforms small-validation
# early stopping on these dataset sizes.
# All models use reg:squarederror. Outlier inflation is controlled via
# per-class price caps in apply_price_outlier_caps() rather than switching
# objectives, which proved numerically unstable on log1p-transformed targets.
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
        # Shallower trees for the 2+3-family building mix; borough and
        # neighborhood_median_ppsf dominate — deep trees would overfit.
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
        # More trees needed on the tighter per-class filtered condo dataset.
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
        # ~1,300 rows, 15 numeric features after feature engineering.
        # Lower max_depth and colsample_bytree prevent overfitting on the
        # expanded feature set; more estimators improve generalisation.
        "n_estimators": 600,
        "learning_rate": 0.04,
        "max_depth": 4,
        "min_child_weight": 4,
        "subsample": 0.8,
        "colsample_bytree": 0.6,
        "gamma": 0.1,
        "reg_alpha": 0.2,
        "reg_lambda": 1.5,
    },
    "rental_elevator": {
        # ~150 rows after cleaning — strong regularization to avoid overfitting.
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
        # neighborhood_median_ppsf = median(sales_price / gross_sqft) by neighbourhood.
        # Encodes the borough × size interaction directly: a sqft of building in
        # Flatbush trades at a very different rate than in Manhattan or Staten Island.
        "numeric": [
            "gross_sqft",
            "land_sqft",
            "neighborhood_median_price",
            "neighborhood_median_ppsf",
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
        # NYC co-op transactions don't record individual unit sqft, so we rely
        # on PLUTO-derived building signals joined via BBL (97%+ coverage):
        #   assess_per_unit — city's valuation of unit quality / income potential
        #   numfloors       — building height; taller = higher-prestige / higher price
        #   lot_coverage    — bldgarea / lotarea; effective FAR proxy for density
        # neighborhood_median_price anchors the location price level.
        "numeric": [
            "assess_per_unit",
            "numfloors",
            "lot_coverage",
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
        "enriched_data": True,
    },
    # Rental walkup (07) and elevator (08) are trained as separate models because
    # they serve different buyer profiles and price levels.
    # Both use price_per_unit as the prediction target — the model learns
    # $/unit rather than total building price, which normalises for building
    # size and produces a tighter, more learnable target distribution.
    # At inference, predicted $/unit is multiplied by total_units to recover
    # the full building price estimate.
    "rental_walkup": {
        # Density features from PLUTO spatial join (150 m nearest-building):
        #   numfloors       — building height: more floors = more units = lower $/unit
        #   units_per_floor — density signal: compact floor plates command premium
        #   lot_coverage    — FAR proxy: high coverage = dense urban building
        # subway_dist_km — distance to nearest subway station (BallTree, MTA data);
        #   the strongest single locational predictor for walkup rental pricing in NYC.
        # stabilization_ratio — DHCR rent-stabilised units / total_units, neighbourhood median.
        "numeric": [
            "gross_sqft",
            "land_sqft",
            "sqft_per_unit",
            "total_units",
            "residential_units",
            "numfloors",
            "units_per_floor",
            "lot_coverage",
            "subway_dist_km",
            "stabilization_ratio",
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
        "enriched_data": True,
    },
    "rental_elevator": {
        "numeric": [
            "gross_sqft",
            "land_sqft",
            "sqft_per_unit",
            "total_units",
            "residential_units",
            "stabilization_ratio",
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
        "min_rows": 100,
        "enriched_data": True,
    },
}


def load_data(source: str = "standard") -> pd.DataFrame:
    """Load the appropriate training CSV.

    source:
      "standard"     – DB-based subtype training data (fallback for all models)
      "rental_stab"  – Phase 2b raw Excel + PLUTO + rentstab (rental models)
      "condo"        – raw Excel + PLUTO assess_per_unit (condo_coop model)
    """
    if source == "rental_stab" and INPUT_FILE_RENTAL_STAB.exists():
        print(f"Loading rental-stab dataset: {INPUT_FILE_RENTAL_STAB.name}")
        return pd.read_csv(INPUT_FILE_RENTAL_STAB, low_memory=False)
    if source == "condo" and INPUT_FILE_CONDO.exists():
        print(f"Loading condo dataset: {INPUT_FILE_CONDO.name}")
        return pd.read_csv(INPUT_FILE_CONDO, low_memory=False)
    print(f"Loading standard subtype dataset: {INPUT_FILE.name}")
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
    # Clip before expm1 to guard against overflow when Huber loss produces
    # large gradient updates near the training boundary.
    # log1p($1B) ≈ 20.7 — anything beyond that is clearly a runaway prediction.
    y_pred_log = np.clip(y_pred_log, 0, 20.7)
    y_test = np.expm1(y_test_log)
    y_pred = np.expm1(y_pred_log)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    return mae, rmse, r2


def apply_price_outlier_caps(subset: pd.DataFrame, subtype_name: str) -> pd.DataFrame:
    """Apply per-class price caps to reduce RMSE inflation from luxury outliers.

    Family and condo/co-op models use a 97th-pct per-class cap (tighter than
    the global 99th already applied in the data pipeline).  Rental models are
    skipped here because they have their own per-unit floor/cap logic and much
    healthier RMSE/MAE ratios.

    Also applies a price-per-sqft sanity filter for models that have gross_sqft:
    removes rows where $/sqft is below the 2nd or above the 98th neighbourhood
    percentile — these are typically data-entry errors, related-party sales, or
    land-only transactions mislabelled as improved properties.
    """
    if subtype_name in ("rental_walkup", "rental_elevator"):
        return subset

    before = len(subset)
    capped = []
    for bc in subset["building_class"].unique():
        rows = subset[subset["building_class"] == bc]
        # Condo/co-op: tighter 95th pct — Manhattan luxury coops span $100k–$15M
        # Family homes: 97th pct — removes the thin ultra-luxury tail
        pct = 0.95 if subtype_name == "condo_coop" else 0.97
        cap = rows["sales_price"].quantile(pct)
        capped.append(rows[rows["sales_price"] <= cap])

    subset = pd.concat(capped).reset_index(drop=True) if capped else subset
    print(f"  Per-class {int(pct*100)}th-pct price cap: {before} → {len(subset)} rows removed {before - len(subset)}")

    # Price-per-sqft sanity filter (only when sqft is available and meaningful)
    if "gross_sqft" in subset.columns:
        has_sqft = subset["gross_sqft"].notna() & (subset["gross_sqft"] > 0)
        if has_sqft.sum() > 100:
            subset_with_sqft = subset[has_sqft].copy()
            subset_without_sqft = subset[~has_sqft]
            subset_with_sqft["_ppsf"] = subset_with_sqft["sales_price"] / subset_with_sqft["gross_sqft"]

            # Compute neighbourhood-level P2 and P98 to define the valid range.
            # Falls back to global percentiles for neighbourhoods with few sales.
            global_p2  = subset_with_sqft["_ppsf"].quantile(0.02)
            global_p98 = subset_with_sqft["_ppsf"].quantile(0.98)

            neigh_bounds = subset_with_sqft.groupby("neighborhood")["_ppsf"].agg(
                p2=lambda x: x.quantile(0.02),
                p98=lambda x: x.quantile(0.98),
            ).reset_index()
            subset_with_sqft = subset_with_sqft.merge(neigh_bounds, on="neighborhood", how="left")
            subset_with_sqft["p2"]  = subset_with_sqft["p2"].fillna(global_p2)
            subset_with_sqft["p98"] = subset_with_sqft["p98"].fillna(global_p98)

            before_ppsf = len(subset_with_sqft)
            subset_with_sqft = subset_with_sqft[
                (subset_with_sqft["_ppsf"] >= subset_with_sqft["p2"]) &
                (subset_with_sqft["_ppsf"] <= subset_with_sqft["p98"])
            ].drop(columns=["_ppsf", "p2", "p98"])

            removed = before_ppsf - len(subset_with_sqft)
            print(f"  Price/sqft P2–P98 filter: removed {removed} anomalous rows")
            subset = pd.concat([subset_with_sqft, subset_without_sqft]).reset_index(drop=True)

    return subset


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
        # PLUTO density features
        "numfloors",
        "lot_coverage",
        "units_per_floor",
        # Rental-specific
        "subway_dist_km",
        "stabilization_ratio",
        "assess_per_unit",
    ]
    for col in numeric_cols:
        if col in subset.columns:
            subset[col] = pd.to_numeric(subset[col], errors="coerce")

    subset["property_age"] = REFERENCE_YEAR - subset["year_built"]

    subset = subset.dropna(subset=["sales_price", "year_built", "latitude", "longitude"])

    feature_config = SUBTYPE_FEATURES[subtype_name]

    if feature_config["require_gross_sqft"]:
        subset = subset[subset["gross_sqft"].notna() & (subset["gross_sqft"] > 0)]

    # Outlier reduction: tighter per-class price caps + price/sqft sanity check.
    # Applied after the basic numeric filters so gross_sqft is already clean.
    subset = apply_price_outlier_caps(subset, subtype_name)

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

    # neighborhood_median_ppsf: median price per sqft by neighbourhood.
    # Encodes the borough × size interaction — "what does a sqft of building
    # cost here?" — as a single pre-computed feature rather than leaving the
    # model to discover the interaction through sequential splits on gross_sqft
    # and lat/lon.  Only computed when gross_sqft is required and present.
    numeric_features = feature_config["numeric"]
    if "neighborhood_median_ppsf" in numeric_features and "gross_sqft" in subset.columns:
        has_sqft = subset["gross_sqft"].notna() & (subset["gross_sqft"] > 0)
        ppsf = (subset.loc[has_sqft, "sales_price"] / subset.loc[has_sqft, "gross_sqft"])
        ppsf_medians = ppsf.groupby(subset.loc[has_sqft, "neighborhood"]).median()
        global_ppsf  = float(ppsf.median())
        subset["neighborhood_median_ppsf"] = (
            subset["neighborhood"].map(ppsf_medians).fillna(global_ppsf)
        )
        neighborhood_stats["neighborhood_median_ppsf_neighborhoods"] = ppsf_medians.to_dict()
        neighborhood_stats["neighborhood_median_ppsf_global_median"]  = global_ppsf

    categorical_features = feature_config["categorical"]

    # For assess_per_unit: store neighborhood-level medians so the predictor
    # can look up a reasonable value at inference time (the user never
    # provides assesstot directly).
    if "assess_per_unit" in numeric_features and "assess_per_unit" in subset.columns:
        apu_medians = subset.groupby("neighborhood")["assess_per_unit"].median()
        apu_global = float(subset["assess_per_unit"].median())
        subset["assess_per_unit"] = subset["assess_per_unit"].fillna(
            subset["neighborhood"].map(apu_medians).fillna(apu_global)
        )
        neighborhood_stats["assess_per_unit_neighborhoods"] = apu_medians.to_dict()
        neighborhood_stats["assess_per_unit_global_median"] = apu_global

    # For stabilization_ratio: store neighborhood-level medians so the predictor
    # can look up a neighbourhood stabilization rate at inference time.
    if "stabilization_ratio" in numeric_features and "stabilization_ratio" in subset.columns:
        stab_medians = subset.groupby("neighborhood")["stabilization_ratio"].median()
        stab_global = float(subset["stabilization_ratio"].median())
        subset["stabilization_ratio"] = subset["stabilization_ratio"].fillna(stab_global)
        neighborhood_stats["stabilization_ratio_neighborhoods"] = stab_medians.to_dict()
        neighborhood_stats["stabilization_ratio_global_median"] = stab_global

    # For PLUTO density features (numfloors, lot_coverage, units_per_floor):
    # store neighbourhood medians so the predictor can fill them at inference
    # time without needing a BBL or spatial join.
    for pluto_feat in ("numfloors", "lot_coverage", "units_per_floor"):
        if pluto_feat in numeric_features and pluto_feat in subset.columns:
            feat_medians = subset.groupby("neighborhood")[pluto_feat].median()
            feat_global  = float(subset[pluto_feat].median())
            subset[pluto_feat] = subset[pluto_feat].fillna(
                subset["neighborhood"].map(feat_medians).fillna(feat_global)
            )
            neighborhood_stats[f"{pluto_feat}_neighborhoods"] = feat_medians.to_dict()
            neighborhood_stats[f"{pluto_feat}_global_median"]  = feat_global

    # For subway_dist_km: store neighbourhood medians so the predictor can
    # fall back to a neighbourhood-level estimate when lat/lon is unavailable.
    # When lat/lon IS available the predictor recomputes the exact distance.
    if "subway_dist_km" in numeric_features and "subway_dist_km" in subset.columns:
        sub_medians = subset.groupby("neighborhood")["subway_dist_km"].median()
        sub_global  = float(subset["subway_dist_km"].median())
        subset["subway_dist_km"] = subset["subway_dist_km"].fillna(
            subset["neighborhood"].map(sub_medians).fillna(sub_global)
        )
        neighborhood_stats["subway_dist_km_neighborhoods"] = sub_medians.to_dict()
        neighborhood_stats["subway_dist_km_global_median"]  = sub_global

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


def main(only_subtypes: set | None = None):
    """Train subtype models.

    Args:
        only_subtypes: When provided, train only the named subtypes and skip
                       all others. Existing model artifacts for skipped subtypes
                       are left untouched. Pass None to train all subtypes.
    """
    df_standard    = load_data("standard")
    df_rental_stab = load_data("rental_stab") if INPUT_FILE_RENTAL_STAB.exists() else None
    df_condo       = load_data("condo")        if INPUT_FILE_CONDO.exists()        else None

    if df_rental_stab is not None:
        print(f"Phase 2b rental-stab data available ({len(df_rental_stab):,} rows).")
    else:
        print("No rental-stab data found — rental subtypes will use standard data.")

    if df_condo is not None:
        print(f"Enriched condo data available ({len(df_condo):,} rows).")
    else:
        print("No enriched condo data found — condo_coop will use standard data.")

    if only_subtypes:
        print(f"\nSelective training — only: {', '.join(sorted(only_subtypes))}")
        print("All other models are left untouched.\n")

    # Route each subtype to its best available dataset.
    # "enriched_data: True" means prefer the specialised CSV over the DB-based fallback.
    DATASET_MAP = {
        "rental_walkup":   df_rental_stab,
        "rental_elevator": df_rental_stab,
        "condo_coop":      df_condo,
    }

    results = []
    for subtype_name, building_classes in SUBTYPE_GROUPS.items():
        if only_subtypes and subtype_name not in only_subtypes:
            print(f"Skipping {subtype_name} (not in --subtypes list)")
            continue
        use_enriched = SUBTYPE_FEATURES[subtype_name].get("enriched_data", False)
        specialised  = DATASET_MAP.get(subtype_name)
        df = (specialised if (use_enriched and specialised is not None) else df_standard)
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
    import argparse

    parser = argparse.ArgumentParser(description="Train subtype property valuation models.")
    parser.add_argument(
        "--subtypes",
        nargs="+",
        choices=list(SUBTYPE_GROUPS.keys()),
        metavar="SUBTYPE",
        help=(
            "Train only the listed subtypes. Omit to train all. "
            f"Available: {', '.join(SUBTYPE_GROUPS.keys())}"
        ),
    )
    args = parser.parse_args()
    main(only_subtypes=set(args.subtypes) if args.subtypes else None)