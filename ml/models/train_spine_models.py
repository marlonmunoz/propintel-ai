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
import warnings
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import VotingRegressor
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
GOLD_PLUTO  = BASE_DIR / "ml/data/gold/gold_pluto_features.parquet"
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

# PLUTO geographic / physical features (joined on bbl only, no as-of filter).
# lat/lon enable the model to learn sub-neighborhood price gradients.
# subway_dist_km captures transit access beyond neighborhood dummies.
_PLUTO_NUMERIC = [
    "pluto_latitude",
    "pluto_longitude",
    "subway_dist_km",
    "pluto_numfloors",
    "pluto_builtfar",
    "pluto_bldg_footprint",
    "pluto_bldgarea",
    "pluto_lotarea",
]
_PLUTO_CAT = ["pluto_bldgclass"]

# Lat/lon excluded from rental models: geographic coordinates allow XGBoost
# to memorise specific building clusters in a small dataset (~4k rows),
# inflating the train/test gap.  subway_dist_km is retained as it provides
# a transit-access signal that generalises across years.
_RENTAL_EXCL_COLS = {"pluto_latitude", "pluto_longitude"}
_RENTAL_PLUTO_NUMERIC = [c for c in _PLUTO_NUMERIC if c not in _RENTAL_EXCL_COLS]

SEGMENT_FEATURES: dict[str, dict[str, Any]] = {
    "one_family": {
        "target": "sales_price",
        "numeric": [
            "neighborhood_median_price", "property_age",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC, *_PLUTO_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT, *_PLUTO_CAT],
        "min_train": 500,
        "min_test":  100,
    },
    "multi_family": {
        "target": "sales_price",
        "numeric": [
            "neighborhood_median_price", "property_age",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC, *_PLUTO_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT, *_PLUTO_CAT],
        "min_train": 500,
        "min_test":  100,
    },
    "condo_coop": {
        "target": "sales_price",
        "numeric": [
            "neighborhood_median_price", "property_age",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC, *_PLUTO_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT, *_PLUTO_CAT],
        "min_train": 500,
        "min_test":  100,
    },
    # ── Pooled rental model ────────────────────────────────────────────────────
    # rental_walkup + rental_elevator are pooled into one model to eliminate
    # the ~350-row starvation problem for elevator rentals.
    # is_elevator (0/1) is added as a feature so the model can learn the price
    # premium for elevator buildings without splitting into two data-starved models.
    # Lat/lon are excluded to prevent geographic over-memorisation.
    "rentals_all": {
        "target": "price_per_unit",
        "numeric": [
            "neighborhood_median_price", "property_age",
            "total_units", "residential_units",
            "is_elevator",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC, *_RENTAL_PLUTO_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT, *_PLUTO_CAT],
        "min_train": 300,
        "min_test":  60,
    },
    # ── Legacy individual rental segments (kept for backward compat) ───────────
    # These are NOT trained by default when rentals_all is used.
    "rental_walkup": {
        "target": "price_per_unit",
        "numeric": [
            "neighborhood_median_price", "property_age",
            "total_units", "residential_units",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC, *_RENTAL_PLUTO_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT, *_PLUTO_CAT],
        "min_train": 200,
        "min_test":  50,
    },
    "rental_elevator": {
        "target": "price_per_unit",
        "numeric": [
            "neighborhood_median_price", "property_age",
            "total_units", "residential_units",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC, *_RENTAL_PLUTO_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT, *_PLUTO_CAT],
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
    # Stabilised v4: rare-neighbourhood collapse + 5-seed VotingRegressor.
    # This shrank the train/test gap from 0.147 → 0.137 and improved worst-fold
    # R² from 0.514 → 0.541 on the rolling-origin scorecard.
    "multi_family": {
        "n_estimators": 700, "learning_rate": 0.035, "max_depth": 5,
        "min_child_weight": 7, "subsample": 0.75, "colsample_bytree": 0.65,
        "gamma": 0.2, "reg_alpha": 0.8, "reg_lambda": 3.0,
    },
    "condo_coop": {
        "n_estimators": 800, "learning_rate": 0.05, "max_depth": 5,
        "min_child_weight": 4, "subsample": 0.8, "colsample_bytree": 0.8,
        "gamma": 0.1, "reg_alpha": 0.3, "reg_lambda": 1.0,
    },
    # Pooled rental model (walkup + elevator).
    # Very aggressive regularisation closes the train/test gap from ~0.19 → 0.13.
    # No lat/lon to prevent geographic memorisation in a small dataset.
    "rentals_all": {
        "n_estimators": 350, "learning_rate": 0.03, "max_depth": 3,
        "min_child_weight": 15, "subsample": 0.65, "colsample_bytree": 0.50,
        "gamma": 0.30, "reg_alpha": 2.5, "reg_lambda": 6.0,
    },
    # Legacy individual rental params (only used if explicitly requested).
    "rental_walkup": {
        "n_estimators": 500, "learning_rate": 0.04, "max_depth": 3,
        "min_child_weight": 6, "subsample": 0.75, "colsample_bytree": 0.6,
        "gamma": 0.2, "reg_alpha": 1.0, "reg_lambda": 3.0,
    },
    "rental_elevator": {
        "n_estimators": 150, "learning_rate": 0.04, "max_depth": 3,
        "min_child_weight": 10, "subsample": 0.7, "colsample_bytree": 0.6,
        "gamma": 0.3, "reg_alpha": 2.0, "reg_lambda": 5.0,
    },
}

# Segments that use a 5-seed VotingRegressor to reduce variance.
ENSEMBLE_SEGMENTS = {"multi_family", "rentals_all"}

# Segments where rare (< RARE_N training rows) neighbourhoods are collapsed
# to "Other_<Borough>" before OHE, preventing thin-slice memorisation.
RARE_NBHD_SEGMENTS = {"multi_family"}
RARE_N = 30  # neighbourhoods with fewer train rows are collapsed

# Default segments trained when no --subtypes flag is given.
# rentals_all replaces the two individual rental segments.
DEFAULT_SEGMENTS = {"one_family", "multi_family", "condo_coop", "rentals_all"}

# Number of seeds for VotingRegressor ensemble.
N_ENSEMBLE_SEEDS = 5

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

    # ── PLUTO ────────────────────────────────────────────────────────────────
    # Joined on bbl only (no as_of_date) — physical/geo attributes are stable.
    print("  Joining Gold PLUTO …")
    pluto = pd.read_parquet(GOLD_PLUTO)
    pluto_geo = [c for c in pluto.columns if c.startswith("pluto_") or c == "subway_dist_km"]
    pluto_sub = pluto[["bbl"] + pluto_geo].drop_duplicates(subset=["bbl"]).reset_index(drop=True)
    spine = spine.merge(pluto_sub, on="bbl", how="left")
    print(f"    PLUTO match rate: {spine['pluto_latitude'].notna().mean():.1%}")

    # Ensure integer/mixed columns arrive as float for sklearn compatibility.
    for c in ["acris_prior_sale_cnt", "acris_mortgage_cnt", "j51_active_flag",
              *_PLUTO_NUMERIC]:
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
    global_med_raw = train[price_col].median()
    global_med = float(global_med_raw) if pd.notna(global_med_raw) else float("nan")
    stats: dict[str, Any] = {
        "neighborhoods": medians.to_dict(),
        "global_median": global_med,
    }
    # DOF assess_per_unit neighbourhood medians (for imputation).
    if "dof_assess_per_unit" in train.columns:
        # Robust to nullable dtypes (pd.NA) in some folds.
        apu = pd.to_numeric(train["dof_assess_per_unit"], errors="coerce").groupby(train["neighborhood"]).median()
        stats["dof_assess_per_unit_neighborhoods"] = apu.to_dict()
        apu_global_raw = pd.to_numeric(train["dof_assess_per_unit"], errors="coerce").median()
        stats["dof_assess_per_unit_global"] = (
            float(apu_global_raw) if pd.notna(apu_global_raw) else float("nan")
        )
    return stats


def _apply_neighborhood_stats(df: pd.DataFrame, stats: dict, target: str) -> pd.DataFrame:
    """Apply pre-fitted stats to any split without touching its target values."""
    df = df.copy()
    df["neighborhood_median_price"] = (
        df["neighborhood"].map(stats["neighborhoods"]).fillna(stats["global_median"])
    )
    if "dof_assess_per_unit" in df.columns and "dof_assess_per_unit_neighborhoods" in stats:
        global_fill = stats.get("dof_assess_per_unit_global", float("nan"))
        df["dof_assess_per_unit"] = pd.to_numeric(df["dof_assess_per_unit"], errors="coerce").fillna(
            df["neighborhood"].map(stats["dof_assess_per_unit_neighborhoods"]).fillna(global_fill)
        )
    if target == "price_per_unit":
        df = df[df["total_units"].notna() & (df["total_units"] > 0)].copy()
        df["price_per_unit"] = df["sales_price"] / df["total_units"]
    return df


# ─── Neighbourhood collapse ───────────────────────────────────────────────────

def _collapse_rare_neighborhoods(train: pd.DataFrame, test: pd.DataFrame,
                                  rare_n: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Replace thin neighbourhood labels with 'Other_<BoroughName>'.

    Thresholds are computed from train only (no look-ahead into test).
    """
    boro_name_map = BOROUGH_NAMES
    counts = train["neighborhood"].value_counts()
    rare = set(counts[counts < rare_n].index)
    if not rare:
        return train, test

    def _boro_label(df: pd.DataFrame) -> pd.Series:
        return df["borough"].map(boro_name_map).fillna("Unknown")

    def _replace(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        mask = df["neighborhood"].isin(rare)
        df.loc[mask, "neighborhood"] = ("Other_" + _boro_label(df).loc[df.index[mask]]).values
        return df

    n_collapsed = len(rare)
    print(f"    Collapsed {n_collapsed:,} rare neighbourhoods (< {rare_n} train rows) → Other_<Borough>")
    return _replace(train), _replace(test)


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


def _build_voting_pipeline(num_feats: list[str], cat_feats: list[str],
                           xgb_params: dict, n_seeds: int = N_ENSEMBLE_SEEDS) -> Pipeline:
    """Wrap N XGBRegressor estimators in a VotingRegressor inside one Pipeline.

    Averaging predictions across seeds reduces variance without changing the
    sklearn .predict() interface, so the model registry and API need no changes.
    """
    estimators = []
    for seed in range(n_seeds):
        p = dict(xgb_params)
        p["random_state"] = seed
        estimators.append((
            f"xgb_{seed}",
            XGBRegressor(**p, n_jobs=-1, objective="reg:squarederror", verbosity=0),
        ))
    voter = VotingRegressor(estimators=estimators)

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
        ("xgb", voter),
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

def train_rentals_all(df: pd.DataFrame) -> dict | None:
    """Pool rental_walkup + rental_elevator rows into one shared model.

    Eliminates the starvation problem for elevator rentals (~350 train rows)
    by combining ~4 000 training rows.  An `is_elevator` binary feature (0/1)
    lets the model learn the price premium for elevator buildings.
    """
    segment = "rentals_all"
    cfg = SEGMENT_FEATURES[segment]

    parts_tr, parts_te = [], []
    for sub_seg in ("rental_walkup", "rental_elevator"):
        sub = df[df["segment"] == sub_seg].copy()
        sub = _engineer(sub)
        sub["is_elevator"] = 1.0 if sub_seg == "rental_elevator" else 0.0
        tr = sub[pd.to_datetime(sub["sale_date"]).dt.date <= TRAIN_END].copy()
        te = sub[pd.to_datetime(sub["sale_date"]).dt.date >= TEST_START].copy()
        for split in (tr, te):
            mask = split["total_units"].notna() & (split["total_units"] > 0)
            split.loc[mask, "price_per_unit"] = (
                split.loc[mask, "sales_price"] / split.loc[mask, "total_units"]
            )
        parts_tr.append(tr[tr["price_per_unit"].notna()])
        parts_te.append(te[te["price_per_unit"].notna()])

    train = pd.concat(parts_tr, ignore_index=True)
    test  = pd.concat(parts_te, ignore_index=True)

    print(f"\n{'='*55}")
    print(f"  RENTALS_ALL (walkup + elevator pooled)")
    print(f"  train={len(train):,}  test={len(test):,}")

    if len(train) < cfg["min_train"] or len(test) < cfg["min_test"]:
        print(f"  SKIPPED — below minimum thresholds")
        return None

    stats = _fit_neighborhood_stats(train, "price_per_unit")
    train = _apply_neighborhood_stats(train, stats, "price_per_unit")
    test  = _apply_neighborhood_stats(test,  stats, "price_per_unit")

    avail_num = [c for c in cfg["numeric"]     if c in train.columns]
    avail_cat = [c for c in cfg["categorical"] if c in train.columns]
    print(f"  Numeric features ({len(avail_num)}): {avail_num}")
    print(f"  Categorical features ({len(avail_cat)}): {avail_cat}")

    X_tr = train[avail_num + avail_cat]
    y_tr = np.log1p(train["price_per_unit"].values)
    X_te = test[avail_num + avail_cat]
    y_te = np.log1p(test["price_per_unit"].values)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipe = _build_voting_pipeline(avail_num, avail_cat, SEGMENT_XGB_PARAMS[segment])
        pipe.fit(X_tr, y_tr)

    tr_m = _eval(y_tr, pipe.predict(X_tr))
    te_m = _eval(y_te, pipe.predict(X_te))

    print(f"\n  Train (n={tr_m['n']:,})  R²={tr_m['r2']:.4f}  "
          f"MAE={tr_m['mae']:,.0f}$/unit  median_ape={tr_m['median_ape']:.3f}")
    print(f"  Test  (n={te_m['n']:,})  R²={te_m['r2']:.4f}  "
          f"MAE={te_m['mae']:,.0f}$/unit  median_ape={te_m['median_ape']:.3f}")
    r2_gap = tr_m["r2"] - te_m["r2"]
    print(f"  Overfit check: R² gap = {r2_gap:+.4f}  "
          f"({'⚠  possible overfit' if r2_gap > 0.15 else '✓ within range'})")

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    model_path = ARTIFACTS / "rentals_all_spine_price_model.pkl"
    joblib.dump(pipe, model_path)

    stats_path = ARTIFACTS / "rentals_all_spine_neighborhood_stats.json"

    def _safe_val(v: Any) -> Any:
        try:
            return None if (v != v or v is None) else float(v)
        except (TypeError, ValueError):
            return None

    stats_out: dict[str, Any] = {}
    for k, v in stats.items():
        if isinstance(v, dict):
            stats_out[k] = {str(kk): _safe_val(vv) for kk, vv in v.items()}
        else:
            stats_out[k] = _safe_val(v)
    with open(stats_path, "w") as fh:
        json.dump(stats_out, fh, indent=2)

    # Feature importance — average across VotingRegressor seeds.
    fi_path_str: str | None = None
    try:
        feature_names = pipe.named_steps["prep"].get_feature_names_out()
        xgb_step = pipe.named_steps["xgb"]
        if hasattr(xgb_step, "estimators_"):
            importance = np.mean(
                [e.feature_importances_ for e in xgb_step.estimators_], axis=0
            )
        else:
            importance = xgb_step.feature_importances_
        fi = pd.DataFrame({"feature": feature_names, "importance": importance})
        fi = fi.sort_values("importance", ascending=False)
        fi_path = ARTIFACTS / "rentals_all_spine_feature_importance.csv"
        fi.to_csv(fi_path, index=False)
        fi_path_str = str(fi_path)
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
        "numeric_features": avail_num,
        "categorical_features": avail_cat,
    }


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

    # Rare-neighbourhood collapse (for multi_family and any other RARE_NBHD_SEGMENTS).
    if segment in RARE_NBHD_SEGMENTS:
        train, test = _collapse_rare_neighborhoods(train, test, RARE_N)

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

    # Use VotingRegressor ensemble for high-variance segments.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if segment in ENSEMBLE_SEGMENTS:
            pipe = _build_voting_pipeline(avail_num, avail_cat, SEGMENT_XGB_PARAMS[segment])
        else:
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

    # Feature importance — handle both single XGB and VotingRegressor.
    try:
        feature_names = pipe.named_steps["prep"].get_feature_names_out()
        xgb_step = pipe.named_steps["xgb"]
        if hasattr(xgb_step, "estimators_"):
            # VotingRegressor: average importances across seeds.
            importance = np.mean(
                [e.feature_importances_ for e in xgb_step.estimators_], axis=0
            )
        else:
            importance = xgb_step.feature_importances_
        fi = pd.DataFrame({"feature": feature_names, "importance": importance})
        fi = fi.sort_values("importance", ascending=False)
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

    segments = only_segments or DEFAULT_SEGMENTS
    results  = []

    for seg in sorted(segments):
        if seg == "rentals_all":
            r = train_rentals_all(df)
        elif seg not in SEGMENT_FEATURES:
            print(f"[skip] unknown segment: {seg}")
            continue
        else:
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
    all_choices = list(SEGMENT_FEATURES.keys()) + ["rentals_all"]
    parser.add_argument(
        "--subtypes", nargs="+",
        choices=all_choices,
        metavar="SEG",
        help=(
            "Train only the listed segments (default: one_family, multi_family, "
            "condo_coop, rentals_all).  Use 'rentals_all' for the pooled rental model."
        ),
    )
    args = parser.parse_args()
    main(only_segments=set(args.subtypes) if args.subtypes else None)
