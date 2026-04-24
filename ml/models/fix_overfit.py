"""Anti-overfitting experiment runner.

Applies two targeted fixes to underperforming segments and immediately
re-runs the overfit scorecard to confirm improvement before anything
touches production artifacts.

Fixes applied (one_family is never modified):
  FIX 1 – Pooled rentals
    Pool rental_walkup + rental_elevator into a single model with an
    `is_elevator` binary feature.  Eliminates the ~350-row starvation
    problem for elevator rentals and reduces variance across both segments.

  FIX 2 – Stabilised multi_family
    (a) Rare-neighbourhood collapse: train neighbourhoods with < RARE_N
        sales are mapped to "Other_<Borough>" before OHE, preventing
        the model from memorising thin slices.
    (b) Seed ensemble: average predictions from 5 random seeds.
        This consistently reduces variance without touching the data.

Outputs land in ml/artifacts/spine_models_exp/ so production artifacts
are NEVER overwritten.

Run from repo root:
    python ml/models/fix_overfit.py
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

import sys
BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ml.models.train_spine_models import (
    load_enriched_spine,
    _engineer,
    _fit_neighborhood_stats,
    _apply_neighborhood_stats,
    SEGMENT_FEATURES,
    SEGMENT_XGB_PARAMS,
    TRAIN_END,
    TEST_START,
    REFERENCE_YEAR,
    BOROUGH_NAMES,
)
from ml.pipelines.eval_protocol import GAP_DAYS, MIN_SEGMENT_TEST_ROWS

EXP_DIR = BASE_DIR / "ml/artifacts/spine_models_exp"

# Minimum training rows in a neighbourhood before it is kept as its own
# category.  Any neighbourhood with fewer rows is collapsed to "Other_<Borough>".
RARE_N = 30

# Number of XGBoost seeds to average for the ensemble.
N_SEEDS = 5


# ─── Helpers ─────────────────────────────────────────────────────────────────

@dataclass
class SplitMetrics:
    n: int
    r2: float
    mae: float
    rmse: float
    median_ape: float
    fold_r2s: list[float]

    @property
    def fold_r2_std(self) -> float | None:
        return float(np.std(self.fold_r2s, ddof=0)) if len(self.fold_r2s) > 1 else None

    @property
    def fold_r2_worst(self) -> float | None:
        return float(np.min(self.fold_r2s)) if self.fold_r2s else None


def _eval_arrays(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    ape = np.abs(y_true - y_pred) / np.maximum(y_true, 1.0)
    return {
        "n":          int(len(y_true)),
        "r2":         float(r2_score(y_true, y_pred)),
        "mae":        float(mean_absolute_error(y_true, y_pred)),
        "rmse":       float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "median_ape": float(np.median(ape)),
    }


def _build_pipeline_seeds(num_feats: list[str], cat_feats: list[str],
                           xgb_params: dict, seeds: list[int]) -> list[Pipeline]:
    """Return one fitted Pipeline per seed (caller must call .fit)."""
    pipes = []
    for seed in seeds:
        p = dict(xgb_params)
        p["random_state"] = seed
        num_pipe = Pipeline([("imp", SimpleImputer(strategy="median"))])
        cat_pipe = Pipeline([
            ("imp", SimpleImputer(strategy="most_frequent")),
            ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ])
        parts = [("num", num_pipe, num_feats)]
        if cat_feats:
            parts.append(("cat", cat_pipe, cat_feats))
        pipes.append(Pipeline([
            ("prep", ColumnTransformer(parts, remainder="drop")),
            ("xgb", XGBRegressor(**p, n_jobs=-1, objective="reg:squarederror", verbosity=0)),
        ]))
    return pipes


def _ensemble_predict(pipes: list[Pipeline], X: pd.DataFrame) -> np.ndarray:
    preds = np.array([np.expm1(np.clip(p.predict(X), 0, 20.7)) for p in pipes])
    return preds.mean(axis=0)


def _collapse_rare_neighborhoods(train: pd.DataFrame, test: pd.DataFrame,
                                   rare_n: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Replace thin neighbourhood strings with 'Other_<BoroughName>'.

    Thresholds are computed from train only — no look-ahead.
    """
    boro_name = train["borough"].map(BOROUGH_NAMES).fillna("Unknown")
    counts = train["neighborhood"].value_counts()
    rare = set(counts[counts < rare_n].index)
    if not rare:
        return train, test

    def _replace(df: pd.DataFrame, boro_series: pd.Series) -> pd.DataFrame:
        df = df.copy()
        mask = df["neighborhood"].isin(rare)
        df.loc[mask, "neighborhood"] = ("Other_" + boro_series.loc[df.index[mask]]).values
        return df

    boro_test = test["borough"].map(BOROUGH_NAMES).fillna("Unknown")
    print(f"    Collapsed {len(rare):,} rare neighbourhoods (< {rare_n} train rows) → Other_<Borough>")
    return _replace(train, boro_name), _replace(test, boro_test)


def _rolling_folds(df_seg: pd.DataFrame, max_folds: int = 3) -> list[dict]:
    years = pd.to_datetime(df_seg["sale_date"]).dt.year
    counts = years.value_counts().sort_index()
    valid = sorted([int(y) for y, c in counts.items() if c >= MIN_SEGMENT_TEST_ROWS])
    if len(valid) < 2:
        return []
    test_years = valid[-max_folds:]
    train_start = date(valid[0], 1, 1)
    folds = []
    for i, ty in enumerate(test_years):
        train_end = date(ty - 1, 12, 31)
        test_start = train_end + timedelta(days=GAP_DAYS + 1)
        folds.append({
            "fold": i + 1,
            "train_start": str(train_start),
            "train_end": str(train_end),
            "test_start": str(test_start),
            "test_end": str(date(ty, 12, 31)),
        })
    return folds


def _prep_split(df: pd.DataFrame, segment: str,
                train_end: date, test_start: date,
                rare_n: int | None = None
                ) -> tuple[pd.DataFrame, pd.DataFrame, dict] | None:
    """Return (train, test, stats) or None if too few rows."""
    sub = df[df["segment"] == segment].copy()
    sub = _engineer(sub)

    target = SEGMENT_FEATURES[segment]["target"]
    train = sub[pd.to_datetime(sub["sale_date"]).dt.date <= train_end].copy()
    test  = sub[pd.to_datetime(sub["sale_date"]).dt.date >= test_start].copy()

    if target == "price_per_unit":
        for split in (train, test):
            mask = split["total_units"].notna() & (split["total_units"] > 0)
            split.loc[mask, "price_per_unit"] = (
                split.loc[mask, "sales_price"] / split.loc[mask, "total_units"]
            )
        train = train[train["price_per_unit"].notna()].copy()
        test  = test[test["price_per_unit"].notna()].copy()

    cfg = SEGMENT_FEATURES[segment]
    if len(train) < cfg["min_train"] or len(test) < cfg["min_test"]:
        return None

    if rare_n:
        train, test = _collapse_rare_neighborhoods(train, test, rare_n)

    stats = _fit_neighborhood_stats(train, target)
    train = _apply_neighborhood_stats(train, stats, target)
    test  = _apply_neighborhood_stats(test,  stats, target)
    return train, test, stats


# ─── FIX 1: Pooled rentals ───────────────────────────────────────────────────

# Lat/lon are excluded from rental models: geographic coordinates can let
# XGBoost memorise specific building clusters in a small dataset (~4k rows),
# driving up the train/test gap.  subway_dist_km is retained as it captures
# a generalizable transit-access signal.
_RENTAL_EXCL = {"pluto_latitude", "pluto_longitude"}

RENTAL_NUMERIC_BASE = [
    c for c in SEGMENT_FEATURES["rental_walkup"]["numeric"]
    if c not in _RENTAL_EXCL
] + ["is_elevator"]
RENTAL_CAT = SEGMENT_FEATURES["rental_walkup"]["categorical"]

# Very aggressive regularization: depth-3 trees, large leaf minimum,
# strong L1+L2, column sub-sampling.  Goal: compress train R² ≈ 0.62-0.65
# to close the gap without sacrificing test R².
POOLED_PARAMS = {
    "n_estimators":     350,
    "learning_rate":    0.03,
    "max_depth":        3,
    "min_child_weight": 15,
    "subsample":        0.65,
    "colsample_bytree": 0.50,
    "gamma":            0.30,
    "reg_alpha":        2.5,
    "reg_lambda":       6.0,
}


def _build_pooled_rental(df: pd.DataFrame,
                          train_end: date, test_start: date
                          ) -> tuple[list[Pipeline], dict, pd.DataFrame, pd.DataFrame, dict] | None:
    """Pool walkup + elevator rows into one rental model."""
    segments = ["rental_walkup", "rental_elevator"]
    train_parts, test_parts = [], []
    for seg in segments:
        sub = df[df["segment"] == seg].copy()
        sub = _engineer(sub)
        sub["is_elevator"] = 1.0 if seg == "rental_elevator" else 0.0
        tr = sub[pd.to_datetime(sub["sale_date"]).dt.date <= train_end].copy()
        te = sub[pd.to_datetime(sub["sale_date"]).dt.date >= test_start].copy()
        for split in (tr, te):
            mask = split["total_units"].notna() & (split["total_units"] > 0)
            split.loc[mask, "price_per_unit"] = (
                split.loc[mask, "sales_price"] / split.loc[mask, "total_units"]
            )
        tr = tr[tr["price_per_unit"].notna()]
        te = te[te["price_per_unit"].notna()]
        train_parts.append(tr)
        test_parts.append(te)

    train = pd.concat(train_parts, ignore_index=True)
    test  = pd.concat(test_parts, ignore_index=True)

    MIN_TR = SEGMENT_FEATURES["rental_walkup"]["min_train"]
    MIN_TE = SEGMENT_FEATURES["rental_walkup"]["min_test"]
    if len(train) < MIN_TR or len(test) < MIN_TE:
        return None

    stats = _fit_neighborhood_stats(train, "price_per_unit")
    train = _apply_neighborhood_stats(train, stats, "price_per_unit")
    test  = _apply_neighborhood_stats(test,  stats, "price_per_unit")

    avail_num = [c for c in RENTAL_NUMERIC_BASE if c in train.columns]
    avail_cat = [c for c in RENTAL_CAT if c in train.columns]

    seeds = list(range(N_SEEDS))
    pipes = _build_pipeline_seeds(avail_num, avail_cat, POOLED_PARAMS, seeds)
    X_tr = train[avail_num + avail_cat]
    y_tr = np.log1p(train["price_per_unit"].values)
    X_te = test[avail_num + avail_cat]
    y_te = test["price_per_unit"].values

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for p in pipes:
            p.fit(X_tr, y_tr)

    return pipes, stats, train, test, {"avail_num": avail_num, "avail_cat": avail_cat}


def run_pooled_rental_experiment(df: pd.DataFrame) -> dict:
    print("\n" + "="*60)
    print("  FIX 1: POOLED RENTAL MODEL (walkup + elevator)")
    print("="*60)

    result = _build_pooled_rental(df, TRAIN_END, TEST_START)
    if result is None:
        print("  SKIP – too few rows")
        return {}
    pipes, stats, train, test, feat_info = result

    avail_num = feat_info["avail_num"]
    avail_cat = feat_info["avail_cat"]
    X_tr = train[avail_num + avail_cat]
    y_tr_true = train["price_per_unit"].values
    X_te = test[avail_num + avail_cat]
    y_te_true = test["price_per_unit"].values

    y_pred_tr = _ensemble_predict(pipes, X_tr)
    y_pred_te = _ensemble_predict(pipes, X_te)

    tr_m = _eval_arrays(y_tr_true, y_pred_tr)
    te_m = _eval_arrays(y_te_true, y_pred_te)

    print(f"  Pooled train n={tr_m['n']:,}  R²={tr_m['r2']:.4f}  MAE={tr_m['mae']:,.0f}$/unit")
    print(f"  Pooled test  n={te_m['n']:,}  R²={te_m['r2']:.4f}  MAE={te_m['mae']:,.0f}$/unit  median_ape={te_m['median_ape']:.3f}")
    gap = tr_m["r2"] - te_m["r2"]
    print(f"  ΔR² (gap) = {gap:+.4f}  {'⚠ overfit' if gap > 0.15 else '✓ ok'}")

    # Rolling folds on pooled data
    folds_seg = df[df["segment"].isin(["rental_walkup", "rental_elevator"])].copy()
    fold_defs = _rolling_folds(folds_seg, max_folds=3)
    fold_r2s = []
    for f in fold_defs:
        res = _build_pooled_rental(
            df,
            pd.to_datetime(f["train_end"]).date(),
            pd.to_datetime(f["test_start"]).date(),
        )
        if res is None:
            continue
        f_pipes, _, f_train, f_test, f_feats = res
        fnum = [c for c in f_feats["avail_num"] if c in f_test.columns]
        fcat = [c for c in f_feats["avail_cat"] if c in f_test.columns]
        f_Xte = f_test[fnum + fcat]
        f_yte = f_test["price_per_unit"].values
        f_pred = _ensemble_predict(f_pipes, f_Xte)
        fold_r2s.append(float(r2_score(f_yte, f_pred)))
        print(f"    Fold {f['fold']} test year={f['test_end'][:4]}  R²={fold_r2s[-1]:.4f}")

    if fold_r2s:
        print(f"  Fold R² — mean={np.mean(fold_r2s):.4f}  std={np.std(fold_r2s):.4f}  worst={np.min(fold_r2s):.4f}")

    # Save experiment artifacts
    EXP_DIR.mkdir(parents=True, exist_ok=True)
    import joblib
    for i, p in enumerate(pipes):
        joblib.dump(p, EXP_DIR / f"rentals_all_seed{i}.pkl")

    return {
        "experiment": "pooled_rental",
        "train_r2": tr_m["r2"], "test_r2": te_m["r2"], "r2_gap": gap,
        "test_mae": te_m["mae"], "test_rmse": te_m["rmse"],
        "test_median_ape": te_m["median_ape"],
        "fold_r2_mean": float(np.mean(fold_r2s)) if fold_r2s else None,
        "fold_r2_std":  float(np.std(fold_r2s)) if fold_r2s else None,
        "fold_r2_worst": float(np.min(fold_r2s)) if fold_r2s else None,
    }


# ─── FIX 2: Stabilised multi_family ─────────────────────────────────────────

STAB_MULTI_PARAMS = {
    "n_estimators":     700,
    "learning_rate":    0.035,
    "max_depth":        5,
    "min_child_weight": 7,
    "subsample":        0.75,
    "colsample_bytree": 0.65,
    "gamma":            0.2,
    "reg_alpha":        0.8,
    "reg_lambda":       3.0,
}


def run_stable_multifamily_experiment(df: pd.DataFrame) -> dict:
    print("\n" + "="*60)
    print("  FIX 2: STABILISED MULTI_FAMILY (rare-nbhd collapse + ensemble)")
    print("="*60)

    prep = _prep_split(df, "multi_family", TRAIN_END, TEST_START, rare_n=RARE_N)
    if prep is None:
        print("  SKIP – too few rows")
        return {}
    train, test, stats = prep

    cfg = SEGMENT_FEATURES["multi_family"]
    avail_num = [c for c in cfg["numeric"]     if c in train.columns]
    avail_cat = [c for c in cfg["categorical"] if c in train.columns]

    X_tr = train[avail_num + avail_cat]
    y_tr = np.log1p(train["sales_price"].values)
    X_te = test[avail_num + avail_cat]
    y_te = test["sales_price"].values

    seeds = list(range(N_SEEDS))
    pipes = _build_pipeline_seeds(avail_num, avail_cat, STAB_MULTI_PARAMS, seeds)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for p in pipes:
            p.fit(X_tr, y_tr)

    y_pred_tr = _ensemble_predict(pipes, X_tr)
    y_pred_te = _ensemble_predict(pipes, X_te)

    tr_m = _eval_arrays(np.expm1(y_tr), y_pred_tr)
    te_m = _eval_arrays(y_te, y_pred_te)

    print(f"  Train n={tr_m['n']:,}  R²={tr_m['r2']:.4f}  MAE={tr_m['mae']:,.0f}$")
    print(f"  Test  n={te_m['n']:,}  R²={te_m['r2']:.4f}  MAE={te_m['mae']:,.0f}$  median_ape={te_m['median_ape']:.3f}")
    gap = tr_m["r2"] - te_m["r2"]
    print(f"  ΔR² (gap) = {gap:+.4f}  {'⚠ overfit' if gap > 0.15 else '✓ ok'}")

    # Rolling folds
    fold_defs = _rolling_folds(df[df["segment"] == "multi_family"], max_folds=3)
    fold_r2s = []
    for f in fold_defs:
        prep_f = _prep_split(df, "multi_family",
                             pd.to_datetime(f["train_end"]).date(),
                             pd.to_datetime(f["test_start"]).date(),
                             rare_n=RARE_N)
        if prep_f is None:
            continue
        f_tr, f_te, _ = prep_f
        f_num = [c for c in avail_num if c in f_tr.columns]
        f_cat = [c for c in avail_cat if c in f_tr.columns]
        f_pipes = _build_pipeline_seeds(f_num, f_cat, STAB_MULTI_PARAMS, seeds)
        f_Xtr = f_tr[f_num + f_cat]
        f_ytr = np.log1p(f_tr["sales_price"].values)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for p in f_pipes:
                p.fit(f_Xtr, f_ytr)
        f_pred = _ensemble_predict(f_pipes, f_te[f_num + f_cat])
        fold_r2s.append(float(r2_score(f_te["sales_price"].values, f_pred)))
        print(f"    Fold {f['fold']} test year={f['test_end'][:4]}  R²={fold_r2s[-1]:.4f}")

    if fold_r2s:
        print(f"  Fold R² — mean={np.mean(fold_r2s):.4f}  std={np.std(fold_r2s):.4f}  worst={np.min(fold_r2s):.4f}")

    EXP_DIR.mkdir(parents=True, exist_ok=True)
    import joblib
    for i, p in enumerate(pipes):
        joblib.dump(p, EXP_DIR / f"multi_family_stab_seed{i}.pkl")

    return {
        "experiment": "stable_multifamily",
        "train_r2": tr_m["r2"], "test_r2": te_m["r2"], "r2_gap": gap,
        "test_mae": te_m["mae"], "test_rmse": te_m["rmse"],
        "test_median_ape": te_m["median_ape"],
        "fold_r2_mean": float(np.mean(fold_r2s)) if fold_r2s else None,
        "fold_r2_std":  float(np.std(fold_r2s)) if fold_r2s else None,
        "fold_r2_worst": float(np.min(fold_r2s)) if fold_r2s else None,
    }


# ─── Summary comparison table ────────────────────────────────────────────────

def _print_comparison(baseline: dict[str, Any], experiments: list[dict]) -> None:
    """Side-by-side baseline vs experiment for the segments touched."""
    print("\n" + "="*60)
    print("  SCORECARD COMPARISON  (baseline → experiment)")
    print("="*60)

    bline_segs = {
        "rental_walkup":   {"r2": 0.4926, "gap": 0.190, "fold_worst": 0.476},
        "rental_elevator": {"r2": 0.4596, "gap": 0.194, "fold_worst": 0.280},
        "multi_family":    {"r2": 0.6075, "gap": 0.147, "fold_worst": 0.514},
    }

    rows = []
    for exp in experiments:
        name = exp.get("experiment", "?")
        if name == "pooled_rental":
            segs = ["rental_walkup", "rental_elevator"]
            label = "rentals_all (pooled)"
        else:
            segs = ["multi_family"]
            label = "multi_family (stabilised)"

        for seg in segs:
            b = bline_segs.get(seg, {})
            rows.append({
                "segment":         seg,
                "fix":             label,
                "baseline_R²":     b.get("r2"),
                "exp_R²":          exp.get("test_r2"),
                "baseline_gap":    b.get("gap"),
                "exp_gap":         exp.get("r2_gap"),
                "baseline_worst":  b.get("fold_worst"),
                "exp_worst":       exp.get("fold_r2_worst"),
            })

    df = pd.DataFrame(rows)
    fmt = {
        "baseline_R²": "{:.4f}", "exp_R²": "{:.4f}",
        "baseline_gap": "{:.4f}", "exp_gap": "{:.4f}",
        "baseline_worst": "{:.4f}", "exp_worst": "{:.4f}",
    }
    for col, f in fmt.items():
        df[col] = df[col].map(lambda v, f=f: f.format(v) if pd.notna(v) else "–")
    print(df.to_string(index=False))
    print()

    for exp in experiments:
        gap = exp.get("r2_gap", 1.0)
        worst = exp.get("fold_r2_worst")
        gate_gap = "✅ PASS" if gap <= 0.15 else "❌ FAIL"
        gate_worst = ("✅ PASS" if worst and worst >= 0.40 else "❌ FAIL") if worst is not None else "–"
        print(f"  [{exp.get('experiment')}]  gate: gap≤0.15 → {gate_gap}  |  worst-fold≥0.40 → {gate_worst}")
    print()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Loading enriched spine …")
    df = load_enriched_spine()

    experiments = []

    r1 = run_pooled_rental_experiment(df)
    if r1:
        experiments.append(r1)

    r2 = run_stable_multifamily_experiment(df)
    if r2:
        experiments.append(r2)

    if experiments:
        _print_comparison({}, experiments)

    # Persist experiment results
    EXP_DIR.mkdir(parents=True, exist_ok=True)
    out = EXP_DIR / "fix_overfit_results.json"
    out.write_text(json.dumps(experiments, indent=2))
    print(f"  Results saved → {out}")
    print("  Experiment PKLs → ml/artifacts/spine_models_exp/")
    print("\n  ⚠  Nothing in ml/artifacts/spine_models/ was changed.")
    print("  To promote, copy the PKLs and update metadata JSONs (after your approval).")


if __name__ == "__main__":
    main()
