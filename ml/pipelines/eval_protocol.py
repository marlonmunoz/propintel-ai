"""Time-based rolling-origin evaluation protocol (Phase A).

Purpose
-------
Replaces the existing random train/test split in train_subtype_models.py with
rolling-origin (expanding window) folds to guard against temporal overfitting.

Fold design (from spec pack)
-----------------------------
Let Y = latest calendar year in the spine with sufficient volume.

  F1: train 2022-01-01 → Y-3-12-31 | gap 30d | test Y-2
  F2: train 2022-01-01 → Y-2-12-31 | gap 30d | test Y-1
  F3: train 2022-01-01 → Y-1-12-31 | gap 30d | test Y

Metrics (per segment × fold)
-----------------------------
  median_ape, p90_ape, mae, hit_10pct, hit_25pct

Promotion criteria (gate)
--------------------------
  Averaged across folds vs baseline:
    - median_ape improves ≥ 3 pp in dominant segment
    - no segment worsens > 5 pp median_ape
    - (interval coverage checked separately when conformal added)

Output
------
  ml/artifacts/eval_reports/eval_report_<YYYYMMDD_HHMMSS>.json

Usage
-----
  python ml/pipelines/eval_protocol.py [--spine PATH]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

BASE_DIR     = Path(__file__).resolve().parents[2]
DEFAULT_SPINE = BASE_DIR / "ml/data/gold/training_spine_v1.parquet"
REPORT_DIR   = BASE_DIR / "ml/artifacts/eval_reports"

REFERENCE_YEAR = 2024   # must match train_subtype_models.py

GAP_DAYS = 30           # reporting-lag buffer between train and test

# Minimum rows per segment per fold to be included in that fold's segment metrics
MIN_SEGMENT_TEST_ROWS = 50
MIN_SEGMENT_TRAIN_ROWS = 200


# ─── Segment routing ────────────────────────────────────────────────────────────────
SEGMENT_TARGET: dict[str, str] = {
    "one_family":      "sales_price",
    "multi_family":    "sales_price",
    "condo_coop":      "sales_price",
    "rental_walkup":   "price_per_unit",
    "rental_elevator": "price_per_unit",
    "global":          "sales_price",
}


# ─── Features ───────────────────────────────────────────────────────────────────────
def _make_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build baseline feature set identical to current train_subtype_models.py logic."""
    out = df.copy()
    out["property_age"] = REFERENCE_YEAR - out["year_built"].fillna(REFERENCE_YEAR - 20)
    out["sqft_per_unit"] = (
        out["gross_sqft"].fillna(0) / out["total_units"].clip(lower=1).fillna(1)
    )
    out["land_per_unit"] = (
        out["land_sqft"].fillna(0) / out["total_units"].clip(lower=1).fillna(1)
    )
    return out


NUMERIC_FEATURES = [
    "year_built", "property_age", "gross_sqft", "land_sqft",
    "total_units", "residential_units", "sqft_per_unit", "land_per_unit",
]
CATEGORICAL_FEATURES = ["neighborhood", "borough"]


def _build_pipeline() -> Pipeline:
    num_pipe = Pipeline([("imputer", SimpleImputer(strategy="median"))])
    cat_pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("ohe",     OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    preprocessor = ColumnTransformer([
        ("num", num_pipe, NUMERIC_FEATURES),
        ("cat", cat_pipe, CATEGORICAL_FEATURES),
    ])
    return Pipeline([
        ("prep", preprocessor),
        ("xgb", XGBRegressor(
            n_estimators=400,
            learning_rate=0.05,
            max_depth=5,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            n_jobs=-1,
            verbosity=0,
        )),
    ])


# ─── Metrics ────────────────────────────────────────────────────────────────────────
def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    ape = np.abs(y_true - y_pred) / np.maximum(y_true, 1.0)
    return {
        "n":            int(len(y_true)),
        "median_ape":   float(np.median(ape)),
        "p90_ape":      float(np.percentile(ape, 90)),
        "mae":          float(np.mean(np.abs(y_true - y_pred))),
        "hit_10pct":    float(np.mean(ape <= 0.10)),
        "hit_25pct":    float(np.mean(ape <= 0.25)),
    }


# ─── Fold builder ───────────────────────────────────────────────────────────────────
def _build_folds(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Return rolling-origin fold definitions."""
    df["_sale_date"] = pd.to_datetime(df["sale_date"])
    max_year = df["_sale_date"].dt.year.max()

    train_start = date(2022, 1, 1)

    folds = []
    for test_year in range(max_year - 2, max_year + 1):
        fold_n = test_year - (max_year - 2) + 1
        train_end   = date(test_year - 1, 12, 31)
        test_start  = train_end + timedelta(days=GAP_DAYS + 1)
        test_end    = date(test_year, 12, 31)
        folds.append({
            "fold":         fold_n,
            "train_start":  str(train_start),
            "train_end":    str(train_end),
            "test_start":   str(test_start),
            "test_end":     str(test_end),
        })
    return folds


# ─── Per-segment evaluation ──────────────────────────────────────────────────────────
def _eval_segment(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    segment: str,
) -> dict[str, Any] | None:
    target_col = SEGMENT_TARGET.get(segment, "sales_price")

    # Derive target
    def _get_target(df: pd.DataFrame) -> pd.Series:
        if target_col == "price_per_unit":
            return df["sales_price"] / df["total_units"].clip(lower=1).fillna(1)
        return df["sales_price"]

    tr = _make_features(train_df)
    te = _make_features(test_df)

    y_tr = np.log1p(_get_target(tr).values)
    y_te = np.log1p(_get_target(te).values)

    if (
        len(tr) < MIN_SEGMENT_TRAIN_ROWS
        or len(te) < MIN_SEGMENT_TEST_ROWS
    ):
        return {
            "segment": segment, "skipped": True,
            "reason":  f"train={len(tr)} test={len(te)} (below minimums)",
        }

    pipe = _build_pipeline()
    try:
        pipe.fit(tr[NUMERIC_FEATURES + CATEGORICAL_FEATURES], y_tr)
    except Exception as exc:
        return {"segment": segment, "skipped": True, "reason": str(exc)}

    y_hat = pipe.predict(te[NUMERIC_FEATURES + CATEGORICAL_FEATURES])
    # Back to dollar space for interpretable metrics
    m = _metrics(np.expm1(y_te), np.expm1(y_hat))
    m["segment"] = segment
    m["target"]  = target_col
    return m


# ─── Main ────────────────────────────────────────────────────────────────────────────
def run_eval(spine_path: Path) -> dict[str, Any]:
    print(f"Loading spine: {spine_path}")
    df = pd.read_parquet(spine_path)
    df["sale_date"]  = pd.to_datetime(df["sale_date"])
    df["_sale_year"] = df["sale_date"].dt.year

    segments = sorted(df["segment"].unique())
    folds    = _build_folds(df)
    print(f"  Rows: {len(df):,}  |  Segments: {segments}")
    print(f"  Folds: {len(folds)}")

    results: list[dict[str, Any]] = []

    for fold in folds:
        f_n     = fold["fold"]
        tr_mask = (df["sale_date"] >= fold["train_start"]) & (df["sale_date"] <= fold["train_end"])
        te_mask = (df["sale_date"] >= fold["test_start"])  & (df["sale_date"] <= fold["test_end"])

        train_df = df[tr_mask].copy()
        test_df  = df[te_mask].copy()

        print(f"\nFold {f_n}: train={len(train_df):,}  test={len(test_df):,}")

        fold_result: dict[str, Any] = {
            "fold":        f_n,
            "boundaries":  fold,
            "train_n":     int(len(train_df)),
            "test_n":      int(len(test_df)),
            "segments":    [],
        }

        # Global model (all segments combined)
        global_seg = _eval_segment(train_df, test_df, "global")
        fold_result["segments"].append(global_seg)
        if global_seg and not global_seg.get("skipped"):
            print(f"  global — median_ape={global_seg['median_ape']:.3f}  hit_10={global_seg['hit_10pct']:.3f}  n={global_seg['n']}")

        # Per-segment
        for seg in segments:
            if seg == "global":
                continue
            seg_result = _eval_segment(
                train_df[train_df["segment"] == seg],
                test_df[test_df["segment"] == seg],
                seg,
            )
            if seg_result:
                fold_result["segments"].append(seg_result)
                if not seg_result.get("skipped"):
                    print(f"  {seg:<20} — median_ape={seg_result['median_ape']:.3f}  hit_10={seg_result['hit_10pct']:.3f}  n={seg_result['n']}")
                else:
                    print(f"  {seg:<20} — SKIPPED ({seg_result.get('reason', '')})")

        results.append(fold_result)

    report = {
        "created_at":   datetime.utcnow().isoformat(),
        "spine_path":   str(spine_path),
        "n_folds":      len(folds),
        "segments":     segments,
        "folds":        results,
    }
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="PropIntel rolling-origin eval protocol")
    parser.add_argument("--spine", type=Path, default=DEFAULT_SPINE,
                        help="Path to training spine parquet")
    args = parser.parse_args(argv)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    report = run_eval(args.spine)

    ts        = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path  = REPORT_DIR / f"eval_report_{ts}.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"\n✅  Eval report saved → {out_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
