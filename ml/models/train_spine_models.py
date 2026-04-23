"""Train per-segment valuation models from the Gold spine + DOF/ACRIS/J-51 features.

This is the Phase E production-ready successor to train_subtype_models.py.

Differences from train_subtype_models.py
-----------------------------------------
1. Input: Gold spine parquet + three Gold feature parquets (no DB-derived CSVs).
2. Split: time-based (train ≤ 2024-12-31, test ≥ 2025-01-31) instead of random 80/20.
   This matches the rolling-origin eval protocol and eliminates temporal leakage.
3. Aggregates (neighborhood_median_price, assess_per_unit) are computed from the
   training split only and applied to the test split — same anti-leakage pattern
   as train_subtype_models.py.
4. Outputs land in ml/artifacts/spine_models/ so existing production artifacts
   are untouched until you're ready to promote.

Run from repo root:
    python ml/models/train_spine_models.py [--subtypes one_family condo_coop …]
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

BASE_DIR = Path(__file__).resolve().parents[2]

SPINE_FILE  = BASE_DIR / "ml/data/gold/training_spine_v1.parquet"
GOLD_DOF    = BASE_DIR / "ml/data/gold/gold_dof_assessment_asof.parquet"
GOLD_ACRIS  = BASE_DIR / "ml/data/gold/gold_acris_features_asof.parquet"
GOLD_J51    = BASE_DIR / "ml/data/gold/gold_j51_features_asof.parquet"
ARTIFACTS   = BASE_DIR / "ml/artifacts/spine_models"
METRICS_FILE = ARTIFACTS / "spine_model_metrics.json"

REFERENCE_YEAR = 2024

# Time-based split boundary (matches eval_protocol.py fold design)
TRAIN_END   = date(2024, 12, 31)
TEST_START  = date(2025, 1, 31)   # 30-day reporting-lag gap


# ─── Feature definitions ──────────────────────────────────────────────────────

# Common Gold features available across all segments.
_DOF_NUMERIC = [
    "dof_curmkttot",      # DOF market value (total) — strongest single predictor
    "dof_curacttot",      # DOF actual assessed value
    "dof_curactland",     # DOF assessed land value
    "dof_assess_per_unit",# derived: dof_curacttot / dof_units
    "dof_gross_sqft",     # sqft from DOF roll (more reliable than rolling-sales)
    "dof_bld_story",      # number of storeys
    "dof_units",          # units from DOF roll
    "dof_yrbuilt",        # year built from DOF roll
]
_DOF_CAT = ["dof_bldg_class", "dof_tax_class"]

_ACRIS_NUMERIC = [
    "acris_prior_sale_cnt",
    "acris_last_deed_amt",
    "acris_days_since_last_deed",
    "acris_mortgage_cnt",
    "acris_last_mtge_amt",
]

_J51_NUMERIC = [
    "j51_active_flag",
    "j51_last_abate_amt",
    "j51_total_abatement",
]

SEGMENT_FEATURES: dict[str, dict[str, Any]] = {
    "one_family": {
        "target": "sales_price",
        "numeric": [
            "neighborhood_median_price", "property_age",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT],
        "min_train": 500,
        "min_test":  100,
    },
    "multi_family": {
        "target": "sales_price",
        "numeric": [
            "neighborhood_median_price", "property_age",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT],
        "min_train": 500,
        "min_test":  100,
    },
    "condo_coop": {
        "target": "sales_price",
        "numeric": [
            "neighborhood_median_price", "property_age",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT],
        "min_train": 500,
        "min_test":  100,
    },
    "rental_walkup": {
        "target": "price_per_unit",
        "numeric": [
            "neighborhood_median_price", "property_age",
            "total_units", "residential_units",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT],
        "min_train": 200,
        "min_test":  50,
    },
    "rental_elevator": {
        "target": "price_per_unit",
        "numeric": [
            "neighborhood_median_price", "property_age",
            "total_units", "residential_units",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT],
        "min_train": 100,
        "min_test":  20,
    },
}

SEGMENT_XGB_PARAMS: dict[str, dict[str, Any]] = {
    "one_family": {
        "n_estimators": 500, "learning_rate": 0.05, "max_depth": 6,
        "min_child_weight": 3, "subsample": 0.8, "colsample_bytree": 0.8,
        "gamma": 0.1, "reg_alpha": 0.1, "reg_lambda": 1.0,
    },
    "multi_family": {
        "n_estimators": 600, "learning_rate": 0.04, "max_depth": 6,
        "min_child_weight": 3, "subsample": 0.8, "colsample_bytree": 0.7,
        "gamma": 0.1, "reg_alpha": 0.05, "reg_lambda": 1.0,
    },
    "condo_coop": {
        "n_estimators": 800, "learning_rate": 0.05, "max_depth": 5,
        "min_child_weight": 4, "subsample": 0.8, "colsample_bytree": 0.8,
        "gamma": 0.1, "reg_alpha": 0.3, "reg_lambda": 1.0,
    },
    "rental_walkup": {
        "n_estimators": 600, "learning_rate": 0.04, "max_depth": 4,
        "min_child_weight": 4, "subsample": 0.8, "colsample_bytree": 0.6,
        "gamma": 0.1, "reg_alpha": 0.2, "reg_lambda": 1.5,
    },
    "rental_elevator": {
        "n_estimators": 300, "learning_rate": 0.04, "max_depth": 4,
        "min_child_weight": 5, "subsample": 0.8, "colsample_bytree": 0.7,
        "gamma": 0.2, "reg_alpha": 0.5, "reg_lambda": 2.0,
    },
}

BOROUGH_NAMES = {1: "Manhattan", 2: "Bronx", 3: "Brooklyn", 4: "Queens", 5: "Staten Island"}


# ─── Data loading ─────────────────────────────────────────────────────────────

def load_enriched_spine() -> pd.DataFrame:
    """Load spine and left-join all three Gold feature files."""
    print("Loading spine …")
    spine = pd.read_parquet(SPINE_FILE)
    spine["sale_date"]  = pd.to_datetime(spine["sale_date"]).dt.date
    spine["as_of_date"] = pd.to_datetime(spine["as_of_date"]).dt.date.astype(str)
    print(f"  Spine rows: {len(spine):,}")

    join_keys = ["bbl", "as_of_date"]

    def _dedup(df: pd.DataFrame, label: str) -> pd.DataFrame:
        """Drop duplicate (bbl, as_of_date) rows, keeping the first.
        The spine itself can have two sales on the same day for the same BBL;
        without deduplication a left join would explode row counts."""
        before = len(df)
        df = df.drop_duplicates(subset=join_keys).reset_index(drop=True)
        if before != len(df):
            print(f"    [{label}] deduped {before - len(df):,} duplicate join keys")
        return df

    # ── DOF ──────────────────────────────────────────────────────────────────
    print("  Joining Gold DOF …")
    dof = pd.read_parquet(GOLD_DOF)
    dof["as_of_date"] = pd.to_datetime(dof["as_of_date"]).dt.date.astype(str)
    dof_rename = {
        "curacttot": "dof_curacttot", "curactland": "dof_curactland",
        "curmkttot": "dof_curmkttot", "curmktland": "dof_curmktland",
        "gross_sqft": "dof_gross_sqft", "units": "dof_units",
        "yrbuilt": "dof_yrbuilt", "bld_story": "dof_bld_story",
    }
    dof_keep = join_keys + [c for c in dof_rename if c in dof.columns] + \
               ["dof_bldg_class", "dof_tax_class"]
    dof_keep = list(dict.fromkeys(c for c in dof_keep if c in dof.columns))
    dof_sub  = _dedup(dof[dof_keep].rename(columns=dof_rename), "DOF")
    spine = spine.merge(dof_sub, on=join_keys, how="left")

    # ── ACRIS ─────────────────────────────────────────────────────────────────
    print("  Joining Gold ACRIS …")
    acris = pd.read_parquet(GOLD_ACRIS)
    acris["as_of_date"] = pd.to_datetime(acris["as_of_date"]).dt.date.astype(str)
    acris_cols = join_keys + [c for c in acris.columns if c.startswith("acris_")]
    acris_sub  = _dedup(acris[[c for c in acris_cols if c in acris.columns]], "ACRIS")
    spine = spine.merge(acris_sub, on=join_keys, how="left")

    # ── J-51 ─────────────────────────────────────────────────────────────────
    print("  Joining Gold J-51 …")
    j51 = pd.read_parquet(GOLD_J51)
    j51["as_of_date"] = pd.to_datetime(j51["as_of_date"]).dt.date.astype(str)
    j51_cols = join_keys + [c for c in j51.columns if c.startswith("j51_")]
    j51_sub  = _dedup(j51[[c for c in j51_cols if c in j51.columns]], "J51")
    spine = spine.merge(j51_sub, on=join_keys, how="left")

    # Ensure integer columns arrive as float for sklearn compatibility.
    for c in ["acris_prior_sale_cnt", "acris_mortgage_cnt", "j51_active_flag"]:
        if c in spine.columns:
            spine[c] = pd.to_numeric(spine[c], errors="coerce").astype(float)

    print(f"  Enriched rows: {len(spine):,}  cols: {len(spine.columns)}")
    return spine


# ─── Feature engineering ──────────────────────────────────────────────────────

def _engineer(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived columns that don't use target values."""
    df = df.copy()
    # Borough name for the categorical encoder.
    if "borough" in df.columns:
        df["borough_name"] = df["borough"].map(BOROUGH_NAMES).fillna("Unknown")

    # Property age from DOF year-built (fall back to spine year_built).
    yr = df.get("dof_yrbuilt", df.get("year_built"))
    if yr is not None:
        df["property_age"] = REFERENCE_YEAR - pd.to_numeric(yr, errors="coerce")
        df["property_age"] = df["property_age"].clip(0, 200)

    # Assessed value per unit (the PLUTO assess_per_unit equivalent).
    if "dof_curacttot" in df.columns and "dof_units" in df.columns:
        units = pd.to_numeric(df["dof_units"], errors="coerce").clip(lower=1)
        df["dof_assess_per_unit"] = (
            pd.to_numeric(df["dof_curacttot"], errors="coerce") / units
        )

    # sales_price must be positive.
    df = df[pd.to_numeric(df["sales_price"], errors="coerce").gt(0)]
    df["sales_price"] = pd.to_numeric(df["sales_price"], errors="coerce")

    return df


# ─── Neighbourhood aggregates (train rows only) ───────────────────────────────

def _fit_neighborhood_stats(train: pd.DataFrame, target: str) -> dict:
    """Compute neighbourhood stats from training rows only — no leakage."""
    price_col = "sales_price" if target == "sales_price" else "price_per_unit"
    medians = train.groupby("neighborhood")[price_col].median()
    global_med = float(train[price_col].median())
    stats: dict[str, Any] = {
        "neighborhoods": medians.to_dict(),
        "global_median": global_med,
    }
    # DOF assess_per_unit neighbourhood medians (for imputation).
    if "dof_assess_per_unit" in train.columns:
        apu = train.groupby("neighborhood")["dof_assess_per_unit"].median()
        stats["dof_assess_per_unit_neighborhoods"] = apu.to_dict()
        stats["dof_assess_per_unit_global"] = float(train["dof_assess_per_unit"].median())
    return stats


def _apply_neighborhood_stats(df: pd.DataFrame, stats: dict, target: str) -> pd.DataFrame:
    """Apply pre-fitted stats to any split without touching its target values."""
    df = df.copy()
    df["neighborhood_median_price"] = (
        df["neighborhood"].map(stats["neighborhoods"]).fillna(stats["global_median"])
    )
    if "dof_assess_per_unit" in df.columns and "dof_assess_per_unit_neighborhoods" in stats:
        df["dof_assess_per_unit"] = df["dof_assess_per_unit"].fillna(
            df["neighborhood"].map(stats["dof_assess_per_unit_neighborhoods"])
            .fillna(stats["dof_assess_per_unit_global"])
        )
    if target == "price_per_unit":
        df = df[df["total_units"].notna() & (df["total_units"] > 0)].copy()
        df["price_per_unit"] = df["sales_price"] / df["total_units"]
    return df


# ─── sklearn pipeline ─────────────────────────────────────────────────────────

def _build_pipeline(num_feats: list[str], cat_feats: list[str],
                    xgb_params: dict) -> Pipeline:
    num_pipe = Pipeline([("imp", SimpleImputer(strategy="median"))])
    cat_pipe = Pipeline([
        ("imp", SimpleImputer(strategy="most_frequent")),
        ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    parts = [("num", num_pipe, num_feats)]
    if cat_feats:
        parts.append(("cat", cat_pipe, cat_feats))
    return Pipeline([
        ("prep", ColumnTransformer(parts, remainder="drop")),
        ("xgb", XGBRegressor(**xgb_params, random_state=42, n_jobs=-1,
                             objective="reg:squarederror", verbosity=0)),
    ])


# ─── Metrics ─────────────────────────────────────────────────────────────────

def _eval(y_true_log: np.ndarray, y_pred_log: np.ndarray) -> dict:
    y_pred_log = np.clip(y_pred_log, 0, 20.7)
    y_true = np.expm1(y_true_log)
    y_pred = np.expm1(y_pred_log)
    ape = np.abs(y_true - y_pred) / np.maximum(y_true, 1.0)
    return {
        "n":          int(len(y_true)),
        "mae":        float(mean_absolute_error(y_true, y_pred)),
        "rmse":       float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2":         float(r2_score(y_true, y_pred)),
        "median_ape": float(np.median(ape)),
        "hit_10pct":  float(np.mean(ape <= 0.10)),
        "hit_25pct":  float(np.mean(ape <= 0.25)),
    }


# ─── Per-segment training ─────────────────────────────────────────────────────

def train_segment(df: pd.DataFrame, segment: str) -> dict | None:
    cfg        = SEGMENT_FEATURES[segment]
    target     = cfg["target"]
    num_feats  = cfg["numeric"]
    cat_feats  = cfg["categorical"]

    sub = df[df["segment"] == segment].copy()
    sub = _engineer(sub)

    # Time-based split.
    train = sub[pd.to_datetime(sub["sale_date"]).dt.date <= TRAIN_END].copy()
    test  = sub[pd.to_datetime(sub["sale_date"]).dt.date >= TEST_START].copy()

    print(f"\n{'='*55}")
    print(f"  {segment.upper()}")
    print(f"  train={len(train):,}  test={len(test):,}")

    if len(train) < cfg["min_train"] or len(test) < cfg["min_test"]:
        print(f"  SKIPPED — below minimum thresholds "
              f"(need train≥{cfg['min_train']}, test≥{cfg['min_test']})")
        return None

    # For price_per_unit targets, derive the column before fitting stats.
    if target == "price_per_unit":
        for split in (train, test):
            mask = split["total_units"].notna() & (split["total_units"] > 0)
            split.loc[mask, "price_per_unit"] = (
                split.loc[mask, "sales_price"] / split.loc[mask, "total_units"]
            )
        train = train[train["price_per_unit"].notna()].copy()
        test  = test[test["price_per_unit"].notna()].copy()

    # Neighbourhood stats fitted on train only.
    stats = _fit_neighborhood_stats(train, target)
    train = _apply_neighborhood_stats(train, stats, target)
    test  = _apply_neighborhood_stats(test,  stats, target)

    # Only keep features actually present in the data.
    avail_num = [c for c in num_feats if c in train.columns]
    avail_cat = [c for c in cat_feats if c in train.columns]
    print(f"  Numeric features ({len(avail_num)}): {avail_num}")
    print(f"  Categorical features ({len(avail_cat)}): {avail_cat}")

    target_col = "price_per_unit" if target == "price_per_unit" else "sales_price"
    if target_col not in train.columns:
        print(f"  SKIPPED — target column '{target_col}' missing")
        return None

    X_tr = train[avail_num + avail_cat]
    y_tr = np.log1p(train[target_col].values)
    X_te = test[avail_num + avail_cat]
    y_te = np.log1p(test[target_col].values)

    pipe = _build_pipeline(avail_num, avail_cat, SEGMENT_XGB_PARAMS[segment])
    pipe.fit(X_tr, y_tr)

    tr_m = _eval(y_tr, pipe.predict(X_tr))
    te_m = _eval(y_te, pipe.predict(X_te))

    unit = "$/unit" if target == "price_per_unit" else "$"
    print(f"\n  Train (n={tr_m['n']:,})  R²={tr_m['r2']:.4f}  "
          f"MAE={tr_m['mae']:,.0f}{unit}  median_ape={tr_m['median_ape']:.3f}")
    print(f"  Test  (n={te_m['n']:,})  R²={te_m['r2']:.4f}  "
          f"MAE={te_m['mae']:,.0f}{unit}  median_ape={te_m['median_ape']:.3f}")
    r2_gap = tr_m["r2"] - te_m["r2"]
    print(f"  Overfit check: R² gap = {r2_gap:+.4f}  "
          f"({'⚠  possible overfit' if r2_gap > 0.10 else '✓ within range'})")

    # Save model.
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    model_path = ARTIFACTS / f"{segment}_spine_price_model.pkl"
    joblib.dump(pipe, model_path)

    stats_path = ARTIFACTS / f"{segment}_spine_neighborhood_stats.json"

    def _safe_val(v: Any) -> Any:
        """Convert NaN / NA → None so json.dump doesn't choke."""
        try:
            return None if (v != v or v is None) else float(v)  # NaN check
        except (TypeError, ValueError):
            return None

    stats_out: dict[str, Any] = {}
    for k, v in stats.items():
        if isinstance(v, dict):
            stats_out[k] = {str(kk): _safe_val(vv) for kk, vv in v.items()}
        else:
            stats_out[k] = _safe_val(v)
    with open(stats_path, "w") as f:
        json.dump(stats_out, f, indent=2)

    # Feature importance.
    try:
        fi = pd.DataFrame({
            "feature":    pipe.named_steps["prep"].get_feature_names_out(),
            "importance": pipe.named_steps["xgb"].feature_importances_,
        }).sort_values("importance", ascending=False)
        fi.to_csv(ARTIFACTS / f"{segment}_spine_feature_importance.csv", index=False)
        print(f"\n  Top-5 features:")
        for _, row in fi.head(5).iterrows():
            print(f"    {row['feature']:<45} {row['importance']:.4f}")
    except Exception as e:
        print(f"  [warn] feature importance: {e}")

    return {
        "segment": segment,
        "train_rows": tr_m["n"],
        "test_rows":  te_m["n"],
        "train_r2":   tr_m["r2"],
        "test_r2":    te_m["r2"],
        "test_mae":   te_m["mae"],
        "test_rmse":  float(np.sqrt(mean_squared_error(
            np.expm1(y_te), np.clip(np.expm1(pipe.predict(X_te)), 0, None)
        ))),
        "test_median_ape": te_m["median_ape"],
        "test_hit_10pct":  te_m["hit_10pct"],
        "model_path":      str(model_path),
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def main(only_segments: set[str] | None = None) -> None:
    df = load_enriched_spine()

    segments = only_segments or set(SEGMENT_FEATURES.keys())
    results  = []

    for seg in sorted(segments):
        if seg not in SEGMENT_FEATURES:
            print(f"[skip] unknown segment: {seg}")
            continue
        r = train_segment(df, seg)
        if r:
            results.append(r)

    if not results:
        print("\nNo segments were trained.")
        return

    print(f"\n{'='*55}")
    print("  SPINE MODEL SUMMARY")
    print(f"{'='*55}")
    fmt = f"  {{:<18}} {{:>8}} {{:>8}} {{:>10}} {{:>12}}"
    print(fmt.format("segment", "train_n", "test_n", "test_R²", "median_ape"))
    print("  " + "-"*53)
    for r in sorted(results, key=lambda x: -x["test_r2"]):
        print(fmt.format(
            r["segment"], r["train_rows"], r["test_rows"],
            f"{r['test_r2']:.4f}", f"{r['test_median_ape']:.3f}",
        ))

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with open(METRICS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Metrics saved → {METRICS_FILE}")
    print(f"  Models saved  → {ARTIFACTS}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train Gold-spine valuation models (time-based split)"
    )
    parser.add_argument(
        "--subtypes", nargs="+",
        choices=list(SEGMENT_FEATURES.keys()),
        metavar="SEG",
        help="Train only the listed segments (default: all)",
    )
    args = parser.parse_args()
    main(only_segments=set(args.subtypes) if args.subtypes else None)
