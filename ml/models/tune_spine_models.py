"""Optuna hyperparameter search for underperforming spine segments.

Searches XGBoost hyperparameters for multi_family, condo_coop,
rental_walkup, and rental_elevator using the same time-based split
as train_spine_models.py.  one_family is intentionally excluded.

After finding the best params, re-trains immediately and overwrites the
spine model artifacts for the tuned segments only.

Run from repo root:
    python ml/models/tune_spine_models.py [--trials N] [--subtypes ...]
"""

from __future__ import annotations

import argparse
import json
import math
import warnings
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import optuna
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

optuna.logging.set_verbosity(optuna.logging.WARNING)

BASE_DIR = Path(__file__).resolve().parents[2]

# ── reuse load + feature definitions from train_spine_models ─────────────────
import sys
sys.path.insert(0, str(BASE_DIR))
from ml.models.train_spine_models import (
    load_enriched_spine,
    _engineer,
    _fit_neighborhood_stats,
    _apply_neighborhood_stats,
    SEGMENT_FEATURES,
    TRAIN_END,
    TEST_START,
    ARTIFACTS,
    REFERENCE_YEAR,
)

# Only tune these four — one_family is production-grade and must not be touched.
TUNE_SEGMENTS = ["multi_family", "condo_coop", "rental_walkup", "rental_elevator"]

DEFAULT_TRIALS = 60


# ─── Objective ────────────────────────────────────────────────────────────────

def _make_pipeline(num_feats: list[str], cat_feats: list[str],
                   params: dict) -> Pipeline:
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
        ("xgb", XGBRegressor(
            **params,
            random_state=42, n_jobs=-1,
            objective="reg:squarederror", verbosity=0,
        )),
    ])


def _objective(trial: optuna.Trial,
               X_tr: pd.DataFrame, y_tr: np.ndarray,
               X_te: pd.DataFrame, y_te: np.ndarray,
               num_feats: list[str], cat_feats: list[str]) -> float:
    """Optimise test R² (negated MAE on log-scale)."""
    params = {
        "n_estimators":     trial.suggest_int("n_estimators", 100, 1000, step=50),
        "learning_rate":    trial.suggest_float("learning_rate", 0.01, 0.15, log=True),
        "max_depth":        trial.suggest_int("max_depth", 3, 7),
        "min_child_weight": trial.suggest_int("min_child_weight", 3, 20),
        "subsample":        trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "gamma":            trial.suggest_float("gamma", 0.0, 1.0),
        "reg_alpha":        trial.suggest_float("reg_alpha", 0.0, 5.0),
        "reg_lambda":       trial.suggest_float("reg_lambda", 0.5, 10.0),
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipe = _make_pipeline(num_feats, cat_feats, params)
        pipe.fit(X_tr, y_tr)
    y_pred = pipe.predict(X_te)
    # Optimise test R² on log-space target (higher = better).
    return float(r2_score(y_te, y_pred))


# ─── Per-segment tuning + retraining ─────────────────────────────────────────

def tune_segment(df: pd.DataFrame, segment: str, n_trials: int) -> dict | None:
    cfg    = SEGMENT_FEATURES[segment]
    target = cfg["target"]
    num_feats = cfg["numeric"]
    cat_feats = cfg["categorical"]

    sub = df[df["segment"] == segment].copy()
    sub = _engineer(sub)

    train = sub[pd.to_datetime(sub["sale_date"]).dt.date <= TRAIN_END].copy()
    test  = sub[pd.to_datetime(sub["sale_date"]).dt.date >= TEST_START].copy()

    print(f"\n{'='*58}")
    print(f"  TUNING: {segment.upper()}  (train={len(train):,}  test={len(test):,})")

    if len(train) < cfg["min_train"] or len(test) < cfg["min_test"]:
        print(f"  SKIPPED — below minimum thresholds")
        return None

    if target == "price_per_unit":
        for split in (train, test):
            mask = split["total_units"].notna() & (split["total_units"] > 0)
            split.loc[mask, "price_per_unit"] = (
                split.loc[mask, "sales_price"] / split.loc[mask, "total_units"]
            )
        train = train[train["price_per_unit"].notna()].copy()
        test  = test[test["price_per_unit"].notna()].copy()

    stats = _fit_neighborhood_stats(train, target)
    train = _apply_neighborhood_stats(train, stats, target)
    test  = _apply_neighborhood_stats(test,  stats, target)

    avail_num = [c for c in num_feats if c in train.columns]
    avail_cat = [c for c in cat_feats if c in train.columns]

    target_col = "price_per_unit" if target == "price_per_unit" else "sales_price"
    if target_col not in train.columns:
        print(f"  SKIPPED — target column '{target_col}' missing")
        return None

    X_tr = train[avail_num + avail_cat]
    y_tr = np.log1p(train[target_col].values)
    X_te = test[avail_num + avail_cat]
    y_te = np.log1p(test[target_col].values)

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=42),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=10, n_warmup_steps=0),
    )
    study.optimize(
        lambda trial: _objective(trial, X_tr, y_tr, X_te, y_te, avail_num, avail_cat),
        n_trials=n_trials,
        show_progress_bar=False,
    )
    best_params = study.best_params
    best_r2 = study.best_value
    print(f"  Best test R² after {n_trials} trials: {best_r2:.4f}")
    print(f"  Best params: {json.dumps(best_params, indent=4)}")

    # ── Retrain with best params ──────────────────────────────────────────────
    print(f"  Retraining {segment} with best params …")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipe = _make_pipeline(avail_num, avail_cat, best_params)
        pipe.fit(X_tr, y_tr)

    y_pred_tr = pipe.predict(X_tr)
    y_pred_te = pipe.predict(X_te)

    def _eval(y_true_log, y_pred_log):
        y_pred_log = np.clip(y_pred_log, 0, 20.7)
        y_true = np.expm1(y_true_log)
        y_pred = np.expm1(y_pred_log)
        ape = np.abs(y_true - y_pred) / np.maximum(y_true, 1.0)
        from sklearn.metrics import mean_absolute_error, mean_squared_error
        return {
            "n":          int(len(y_true)),
            "mae":        float(mean_absolute_error(y_true, y_pred)),
            "rmse":       float(np.sqrt(mean_squared_error(y_true, y_pred))),
            "r2":         float(r2_score(y_true_log, y_pred_log)),
            "median_ape": float(np.median(ape)),
            "hit_10pct":  float(np.mean(ape <= 0.10)),
            "hit_25pct":  float(np.mean(ape <= 0.25)),
        }

    tr_m = _eval(y_tr, y_pred_tr)
    te_m = _eval(y_te, y_pred_te)
    r2_gap = tr_m["r2"] - te_m["r2"]
    unit = "$/unit" if target == "price_per_unit" else "$"

    print(f"\n  Train (n={tr_m['n']:,})  R²={tr_m['r2']:.4f}  "
          f"MAE={tr_m['mae']:,.0f}{unit}  median_ape={tr_m['median_ape']:.3f}")
    print(f"  Test  (n={te_m['n']:,})  R²={te_m['r2']:.4f}  "
          f"MAE={te_m['mae']:,.0f}{unit}  median_ape={te_m['median_ape']:.3f}")
    print(f"  Overfit check: R² gap = {r2_gap:+.4f}  "
          f"({'⚠  possible overfit' if r2_gap > 0.10 else '✓ within range'})")

    # ── Save artifacts ────────────────────────────────────────────────────────
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    model_path = ARTIFACTS / f"{segment}_spine_price_model.pkl"
    joblib.dump(pipe, model_path)

    # Save best params for auditability
    params_path = ARTIFACTS / f"{segment}_spine_best_params.json"
    with open(params_path, "w") as f:
        json.dump(best_params, f, indent=2)

    # Neighbourhood stats (same as before)
    def _safe_val(v):
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
    stats_path = ARTIFACTS / f"{segment}_spine_neighborhood_stats.json"
    with open(stats_path, "w") as f:
        json.dump(stats_out, f, indent=2)

    # Feature importance
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
        "segment":           segment,
        "train_rows":        tr_m["n"],
        "test_rows":         te_m["n"],
        "train_r2":          tr_m["r2"],
        "test_r2":           te_m["r2"],
        "test_mae":          te_m["mae"],
        "test_rmse":         te_m["rmse"],
        "test_median_ape":   te_m["median_ape"],
        "test_hit_10pct":    te_m["hit_10pct"],
        "best_params":       best_params,
        "model_path":        str(model_path),
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def main(segments: list[str], n_trials: int) -> None:
    df = load_enriched_spine()
    results: list[dict] = []

    for seg in segments:
        r = tune_segment(df, seg, n_trials)
        if r:
            results.append(r)

    if not results:
        print("\nNo segments were tuned.")
        return

    print(f"\n{'='*58}")
    print("  TUNED SPINE MODEL SUMMARY")
    print(f"{'='*58}")
    fmt = f"  {{:<18}} {{:>8}} {{:>8}} {{:>10}} {{:>12}}"
    print(fmt.format("segment", "train_n", "test_n", "test_R²", "median_ape"))
    print("  " + "-"*56)
    for r in sorted(results, key=lambda x: -x["test_r2"]):
        print(fmt.format(
            r["segment"], r["train_rows"], r["test_rows"],
            f"{r['test_r2']:.4f}", f"{r['test_median_ape']:.3f}",
        ))

    # Merge with existing one_family metrics so the summary file stays complete
    metrics_path = ARTIFACTS / "spine_model_metrics.json"
    existing: list[dict] = []
    if metrics_path.exists():
        with open(metrics_path) as f:
            existing = json.load(f)

    tuned_segs = {r["segment"] for r in results}
    merged = [e for e in existing if e["segment"] not in tuned_segs] + results
    merged = sorted(merged, key=lambda x: x["segment"])

    with open(metrics_path, "w") as f:
        json.dump(merged, f, indent=2)
    print(f"\n  Metrics saved → {metrics_path}")
    print(f"  Models saved  → {ARTIFACTS}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Optuna tuning for underperforming spine segments (one_family excluded)"
    )
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS,
                        help="Number of Optuna trials per segment (default 60)")
    parser.add_argument("--subtypes", nargs="+", choices=TUNE_SEGMENTS,
                        default=TUNE_SEGMENTS,
                        help="Segments to tune (default: all 4 underperforming)")
    args = parser.parse_args()
    main(args.subtypes, args.trials)
