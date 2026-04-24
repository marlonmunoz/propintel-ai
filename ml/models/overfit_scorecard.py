"""Overfitting scorecard for spine models (time-aware).

Goal
----
Detect overfitting reliably across segments using:
  1) Current time split (train ≤ 2024-12-31, test ≥ 2025-01-31) gap
  2) Rolling-origin fold stability (mean/std/worst across last valid years)

This script does not change any artifacts; it only reports.

Run from repo root:
    python ml/models/overfit_scorecard.py
    python ml/models/overfit_scorecard.py --folds 3
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

import sys
from pathlib import Path

# Ensure repo root is on sys.path when executed as a script.
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import warnings

from ml.models.train_spine_models import (
    load_enriched_spine,
    _engineer,
    _fit_neighborhood_stats,
    _apply_neighborhood_stats,
    _collapse_rare_neighborhoods,
    SEGMENT_FEATURES,
    SEGMENT_XGB_PARAMS,
    TRAIN_END,
    TEST_START,
    RARE_NBHD_SEGMENTS,
    RARE_N,
    ENSEMBLE_SEGMENTS,
    _build_pipeline,
    _build_voting_pipeline,
    train_rentals_all,
)

# Segments scored by the scorecard.  rentals_all replaces the individual rental segs.
SCORECARD_SEGMENTS = ["one_family", "multi_family", "condo_coop", "rentals_all"]


@dataclass
class SplitMetrics:
    n: int
    r2: float
    mae: float
    rmse: float
    median_ape: float


def _eval_regression(y_true_log: np.ndarray, y_pred_log: np.ndarray) -> SplitMetrics:
    y_pred_log = np.clip(y_pred_log, 0, 20.7)
    y_true = np.expm1(y_true_log)
    y_pred = np.expm1(y_pred_log)
    ape = np.abs(y_true - y_pred) / np.maximum(y_true, 1.0)
    return SplitMetrics(
        n=int(len(y_true)),
        # R² on dollar scale (matches train_spine_models.py reporting)
        r2=float(r2_score(y_true, y_pred)),
        mae=float(mean_absolute_error(y_true, y_pred)),
        rmse=float(np.sqrt(mean_squared_error(y_true, y_pred))),
        median_ape=float(np.median(ape)),
    )


def _as_date(s: str) -> date:
    return pd.to_datetime(s).date()


def _build_folds_for_segment(df_seg: pd.DataFrame, max_folds: int) -> list[dict[str, Any]]:
    """Data-driven rolling folds for one segment.

    Uses the last N calendar years that have at least MIN rows for this segment.
    """
    from ml.pipelines.eval_protocol import GAP_DAYS, MIN_SEGMENT_TEST_ROWS

    years = pd.to_datetime(df_seg["sale_date"]).dt.year
    year_counts = years.value_counts().sort_index()
    valid = sorted([int(y) for y, cnt in year_counts.items() if cnt >= MIN_SEGMENT_TEST_ROWS])
    if len(valid) < 2:
        return []
    test_years = valid[-max_folds:]
    train_start = date(valid[0], 1, 1)
    folds = []
    for i, test_year in enumerate(test_years):
        train_end = date(test_year - 1, 12, 31)
        test_start = train_end + timedelta(days=GAP_DAYS + 1)
        test_end = date(test_year, 12, 31)
        folds.append(
            {
                "fold": i + 1,
                "train_start": str(train_start),
                "train_end": str(train_end),
                "test_start": str(test_start),
                "test_end": str(test_end),
            }
        )
    return folds


def _pool_rentals(df: pd.DataFrame, train_end: date, test_start: date
                  ) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Pool rental_walkup + rental_elevator into one frame with is_elevator feature."""
    parts_tr, parts_te = [], []
    for sub_seg in ("rental_walkup", "rental_elevator"):
        sub = df[df["segment"] == sub_seg].copy()
        sub = _engineer(sub)
        sub["is_elevator"] = 1.0 if sub_seg == "rental_elevator" else 0.0
        tr = sub[pd.to_datetime(sub["sale_date"]).dt.date <= train_end].copy()
        te = sub[pd.to_datetime(sub["sale_date"]).dt.date >= test_start].copy()
        for split in (tr, te):
            mask = split["total_units"].notna() & (split["total_units"] > 0)
            split.loc[mask, "price_per_unit"] = split.loc[mask, "sales_price"] / split.loc[mask, "total_units"]
        parts_tr.append(tr[tr["price_per_unit"].notna()])
        parts_te.append(te[te["price_per_unit"].notna()])
    train = pd.concat(parts_tr, ignore_index=True)
    test  = pd.concat(parts_te, ignore_index=True)
    cfg = SEGMENT_FEATURES["rentals_all"]
    if len(train) < cfg["min_train"] or len(test) < cfg["min_test"]:
        return None
    stats = _fit_neighborhood_stats(train, "price_per_unit")
    train = _apply_neighborhood_stats(train, stats, "price_per_unit")
    test  = _apply_neighborhood_stats(test,  stats, "price_per_unit")
    return train, test


def _prepare_segment_split(df: pd.DataFrame, segment: str, train_end: date, test_start: date
                            ) -> tuple[pd.DataFrame, pd.DataFrame] | None:
    if segment == "rentals_all":
        return _pool_rentals(df, train_end, test_start)

    sub = df[df["segment"] == segment].copy()
    sub = _engineer(sub)
    train = sub[pd.to_datetime(sub["sale_date"]).dt.date <= train_end].copy()
    test = sub[pd.to_datetime(sub["sale_date"]).dt.date >= test_start].copy()

    target = SEGMENT_FEATURES[segment]["target"]
    if target == "price_per_unit":
        for split in (train, test):
            mask = split["total_units"].notna() & (split["total_units"] > 0)
            split.loc[mask, "price_per_unit"] = split.loc[mask, "sales_price"] / split.loc[mask, "total_units"]
        train = train[train["price_per_unit"].notna()].copy()
        test = test[test["price_per_unit"].notna()].copy()

    if segment in RARE_NBHD_SEGMENTS:
        train, test = _collapse_rare_neighborhoods(train, test, RARE_N)

    stats = _fit_neighborhood_stats(train, target)
    train = _apply_neighborhood_stats(train, stats, target)
    test = _apply_neighborhood_stats(test, stats, target)
    return train, test


def _fit_and_score(segment: str, train: pd.DataFrame, test: pd.DataFrame) -> tuple[SplitMetrics, SplitMetrics]:
    cfg = SEGMENT_FEATURES[segment]
    num_feats = [c for c in cfg["numeric"] if c in train.columns]
    cat_feats = [c for c in cfg["categorical"] if c in train.columns]

    target_col = "price_per_unit" if cfg["target"] == "price_per_unit" else "sales_price"
    X_tr = train[num_feats + cat_feats]
    y_tr = np.log1p(train[target_col].values)
    X_te = test[num_feats + cat_feats]
    y_te = np.log1p(test[target_col].values)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if segment in ENSEMBLE_SEGMENTS:
            pipe = _build_voting_pipeline(num_feats, cat_feats, SEGMENT_XGB_PARAMS[segment])
        else:
            pipe = _build_pipeline(num_feats, cat_feats, SEGMENT_XGB_PARAMS[segment])
        pipe.fit(X_tr, y_tr)

    tr_m = _eval_regression(y_tr, pipe.predict(X_tr))
    te_m = _eval_regression(y_te, pipe.predict(X_te))
    return tr_m, te_m


def _rentals_df_for_folds(df: pd.DataFrame) -> pd.DataFrame:
    """Combined rental rows for fold year counting."""
    parts = []
    for seg in ("rental_walkup", "rental_elevator"):
        parts.append(df[df["segment"] == seg][["sale_date"]].copy())
    return pd.concat(parts, ignore_index=True)


def main(max_folds: int) -> None:
    df = load_enriched_spine()

    rows: list[dict[str, Any]] = []

    for seg in SCORECARD_SEGMENTS:
        # ── Current split ──────────────────────────────────────────────────
        split = _prepare_segment_split(df, seg, TRAIN_END, TEST_START)
        if split is None:
            rows.append({"segment": seg, "status": "SKIP (too few rows)", "train_n": 0, "test_n": 0})
            continue
        train, test = split

        cfg = SEGMENT_FEATURES[seg]
        if len(train) < cfg["min_train"] or len(test) < cfg["min_test"]:
            rows.append({"segment": seg, "status": "SKIP (too few rows)", "train_n": len(train), "test_n": len(test)})
            continue

        tr_m, te_m = _fit_and_score(seg, train, test)
        gap = tr_m.r2 - te_m.r2

        # ── Rolling folds stability ───────────────────────────────────────
        fold_df = _rentals_df_for_folds(df) if seg == "rentals_all" else df[df["segment"] == seg]
        folds = _build_folds_for_segment(fold_df, max_folds=max_folds)
        fold_r2: list[float] = []
        fold_mae: list[float] = []
        fold_mape: list[float] = []
        for f in folds:
            tr_end = _as_date(f["train_end"])
            te_start = _as_date(f["test_start"])
            split_f = _prepare_segment_split(df, seg, tr_end, te_start)
            if split_f is None:
                continue
            tr_df, te_df = split_f
            if len(tr_df) < cfg["min_train"] or len(te_df) < cfg["min_test"]:
                continue
            _, te_fold = _fit_and_score(seg, tr_df, te_df)
            fold_r2.append(te_fold.r2)
            fold_mae.append(te_fold.mae)
            fold_mape.append(te_fold.median_ape)

        def _agg(xs: list[float]) -> tuple[float | None, float | None, float | None]:
            if not xs:
                return (None, None, None)
            arr = np.array(xs, dtype=float)
            return (float(arr.mean()), float(arr.std(ddof=0)), float(arr.min()))

        r2_mean, r2_std, r2_worst = _agg(fold_r2)
        mae_mean, mae_std, mae_worst = _agg(fold_mae)
        mape_mean, mape_std, mape_worst = _agg(fold_mape)

        rows.append(
            {
                "segment": seg,
                "status": "OK",
                "train_n": tr_m.n,
                "test_n": te_m.n,
                "train_r2": tr_m.r2,
                "test_r2": te_m.r2,
                "r2_gap": gap,
                "test_mae": te_m.mae,
                "test_rmse": te_m.rmse,
                "test_median_ape": te_m.median_ape,
                "folds_used": len(fold_r2),
                "fold_r2_mean": r2_mean,
                "fold_r2_std": r2_std,
                "fold_r2_worst": r2_worst,
                "fold_mape_mean": mape_mean,
                "fold_mape_std": mape_std,
                "fold_mape_worst": mape_worst,
            }
        )

    out = pd.DataFrame(rows)
    # Sort: highest risk first (gap desc, then worst-fold asc)
    if "r2_gap" in out.columns:
        out = out.sort_values(["status", "r2_gap"], ascending=[True, False])

    # Print in a compact, copy-paste friendly table
    show_cols = [
        "segment",
        "train_n",
        "test_n",
        "train_r2",
        "test_r2",
        "r2_gap",
        "test_mae",
        "test_rmse",
        "test_median_ape",
        "folds_used",
        "fold_r2_mean",
        "fold_r2_std",
        "fold_r2_worst",
    ]
    show = out[[c for c in show_cols if c in out.columns]].copy()
    with pd.option_context("display.max_rows", 200, "display.max_columns", 200, "display.width", 160):
        print(show.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Overfitting scorecard for spine models")
    parser.add_argument("--folds", type=int, default=3, help="Max rolling folds to compute (default: 3)")
    args = parser.parse_args()
    main(max_folds=args.folds)

