"""Time-based rolling-origin evaluation protocol (Phase A + D).

Purpose
-------
Measures model quality using rolling-origin (expanding-window) folds, then
compares a BASELINE feature set against three enriched Gold feature groups
(DOF assessment, ACRIS transactions, J-51 exemptions) so we can see the
incremental lift each new dataset provides.

Fold design
-----------
Let Y = latest full calendar year in the spine (partial years excluded).

  F1: train 2022-01-01 → (Y-2)-12-31 | gap 30 d | test Y-1
  F2: train 2022-01-01 → (Y-1)-12-31 | gap 30 d | test Y
  F3 (if partial year exists): train 2022-01-01 → Y-12-31 | test Y+1 partial

Metrics (per segment × fold)
-----------------------------
  median_ape, p90_ape, mae, hit_10pct, hit_25pct

Promotion criteria (gate)
--------------------------
  Vs baseline, averaged across folds:
    - median_ape improves ≥ 3 pp in dominant segment
    - no segment worsens > 5 pp median_ape

Feature sets evaluated
----------------------
  baseline   : spine columns only (year_built, gross_sqft, …)
  +dof       : adds DOF assessed/market values, gross_sqft, yrbuilt, bldg_class
  +acris     : adds ACRIS prior-sale count, deed amount, days-since-deed, mortgage
  +j51       : adds J-51 active flag, abatement amounts
  all        : baseline + dof + acris + j51

Output
------
  ml/artifacts/eval_reports/eval_report_<YYYYMMDD_HHMMSS>.json

Usage
-----
  python ml/pipelines/eval_protocol.py [--spine PATH] [--feature-set SET]
  # SET ∈ {baseline, dof, acris, j51, all, compare}  (default: compare)
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

BASE_DIR      = Path(__file__).resolve().parents[2]
DEFAULT_SPINE = BASE_DIR / "ml/data/gold/training_spine_v1.parquet"
GOLD_DOF      = BASE_DIR / "ml/data/gold/gold_dof_assessment_asof.parquet"
GOLD_ACRIS    = BASE_DIR / "ml/data/gold/gold_acris_features_asof.parquet"
GOLD_J51      = BASE_DIR / "ml/data/gold/gold_j51_features_asof.parquet"
REPORT_DIR    = BASE_DIR / "ml/artifacts/eval_reports"

REFERENCE_YEAR = 2024
GAP_DAYS       = 30
MIN_SEGMENT_TRAIN_ROWS = 200
MIN_SEGMENT_TEST_ROWS  = 50


# ─── Segment routing ─────────────────────────────────────────────────────────
SEGMENT_TARGET: dict[str, str] = {
    "one_family":      "sales_price",
    "multi_family":    "sales_price",
    "condo_coop":      "sales_price",
    "rental_walkup":   "price_per_unit",
    "rental_elevator": "price_per_unit",
    "global":          "sales_price",
}


# ─── Feature set definitions ──────────────────────────────────────────────────

BASELINE_NUMERIC: list[str] = [
    "year_built", "property_age", "gross_sqft", "land_sqft",
    "total_units", "residential_units", "sqft_per_unit", "land_per_unit",
]
BASELINE_CAT: list[str] = ["neighborhood", "borough"]

DOF_NUMERIC: list[str] = [
    "dof_curacttot", "dof_curactland", "dof_curmkttot", "dof_curmktland",
    "dof_gross_sqft", "dof_units", "dof_yrbuilt", "dof_bld_story",
]
DOF_CAT: list[str] = ["dof_bldg_class", "dof_tax_class"]

ACRIS_NUMERIC: list[str] = [
    "acris_prior_sale_cnt", "acris_last_deed_amt",
    "acris_days_since_last_deed", "acris_mortgage_cnt", "acris_last_mtge_amt",
]
ACRIS_CAT: list[str] = []

J51_NUMERIC: list[str] = [
    "j51_active_flag", "j51_last_abate_amt", "j51_total_abatement",
    "j51_last_expiry_year",
]
J51_CAT: list[str] = []

FEATURE_SETS: dict[str, dict[str, list[str]]] = {
    "baseline": {"num": BASELINE_NUMERIC,                            "cat": BASELINE_CAT},
    "+dof":     {"num": BASELINE_NUMERIC + DOF_NUMERIC,              "cat": BASELINE_CAT + DOF_CAT},
    "+acris":   {"num": BASELINE_NUMERIC + ACRIS_NUMERIC,            "cat": BASELINE_CAT},
    "+j51":     {"num": BASELINE_NUMERIC + J51_NUMERIC,              "cat": BASELINE_CAT},
    "all":      {"num": BASELINE_NUMERIC + DOF_NUMERIC + ACRIS_NUMERIC + J51_NUMERIC,
                 "cat": BASELINE_CAT + DOF_CAT},
}


# ─── Gold loader / joiner ─────────────────────────────────────────────────────

def _load_gold_features(spine: pd.DataFrame) -> pd.DataFrame:
    """Left-join all three Gold files onto the spine.  Columns are prefixed."""
    df = spine.copy()
    join_keys = ["bbl", "as_of_date"]

    # ── DOF ──────────────────────────────────────────────────────────────────
    if GOLD_DOF.exists():
        print(f"  Joining Gold DOF …")
        dof = pd.read_parquet(GOLD_DOF)
        dof["as_of_date"] = pd.to_datetime(dof["as_of_date"]).dt.date.astype(str)

        # Rename DOF feature columns to avoid collisions.
        dof_rename = {
            "curacttot":     "dof_curacttot",
            "curactland":    "dof_curactland",
            "curmkttot":     "dof_curmkttot",
            "curmktland":    "dof_curmktland",
            "gross_sqft":    "dof_gross_sqft",
            "units":         "dof_units",
            "yrbuilt":       "dof_yrbuilt",
            "bld_story":     "dof_bld_story",
            "dof_bldg_class": "dof_bldg_class",
            "dof_tax_class":  "dof_tax_class",
        }
        dof_cols = join_keys + [c for c in dof_rename if c in dof.columns] + \
                   ["dof_bldg_class", "dof_tax_class"]
        dof_cols = [c for c in dict.fromkeys(dof_cols) if c in dof.columns]
        dof_sub  = dof[dof_cols].rename(columns=dof_rename)
        df = df.merge(dof_sub, on=join_keys, how="left")
        print(f"    DOF match rate: {df['dof_curacttot'].notna().mean()*100:.1f}%")
    else:
        print(f"  [skip] Gold DOF not found: {GOLD_DOF}")

    # ── ACRIS ─────────────────────────────────────────────────────────────────
    if GOLD_ACRIS.exists():
        print(f"  Joining Gold ACRIS …")
        acris = pd.read_parquet(GOLD_ACRIS)
        acris["as_of_date"] = pd.to_datetime(acris["as_of_date"]).dt.date.astype(str)

        acris_cols = join_keys + [c for c in acris.columns if c.startswith("acris_")]
        acris_sub  = acris[[c for c in acris_cols if c in acris.columns]]
        df = df.merge(acris_sub, on=join_keys, how="left")
        print(f"    ACRIS match rate: {df['acris_prior_sale_cnt'].notna().mean()*100:.1f}%")
    else:
        print(f"  [skip] Gold ACRIS not found: {GOLD_ACRIS}")

    # ── J-51 ─────────────────────────────────────────────────────────────────
    if GOLD_J51.exists():
        print(f"  Joining Gold J-51 …")
        j51 = pd.read_parquet(GOLD_J51)
        j51["as_of_date"] = pd.to_datetime(j51["as_of_date"]).dt.date.astype(str)

        j51_cols = join_keys + [c for c in j51.columns if c.startswith("j51_")]
        j51_sub  = j51[[c for c in j51_cols if c in j51.columns]]
        df = df.merge(j51_sub, on=join_keys, how="left")
        print(f"    J-51 match rate: {df['j51_active_flag'].notna().mean()*100:.1f}%")
    else:
        print(f"  [skip] Gold J-51 not found: {GOLD_J51}")

    return df


# ─── Derived features ─────────────────────────────────────────────────────────

def _make_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute derived columns; safe to call with or without Gold columns present."""
    out = df.copy()
    ref = REFERENCE_YEAR
    out["property_age"] = ref - out["year_built"].fillna(ref - 20)
    units = out["total_units"].clip(lower=1).fillna(1)
    out["sqft_per_unit"]  = out["gross_sqft"].fillna(0) / units
    out["land_per_unit"]  = out["land_sqft"].fillna(0)  / units
    return out


# ─── Fold builder ─────────────────────────────────────────────────────────────

def _build_folds(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Return rolling-origin fold definitions.

    Strategy: data-driven, not calendar-driven.
    1. Count rows per calendar year.
    2. Keep only years with ≥ MIN_SEGMENT_TEST_ROWS rows (enough to be a test set).
    3. Use the LAST 3 such years as test years — so gaps (e.g. missing 2024 data)
       are handled automatically without producing empty test folds.
    4. Each fold's training window expands from the earliest year to
       (test_year - 1)-12-31; a 30-day reporting-lag gap separates train / test.
    """
    years = pd.to_datetime(df["sale_date"]).dt.year
    year_counts = years.value_counts().sort_index()

    valid_test_years = sorted([
        int(y) for y, cnt in year_counts.items()
        if cnt >= MIN_SEGMENT_TEST_ROWS
    ])

    if len(valid_test_years) < 2:
        raise ValueError(
            f"Need ≥ 2 years with ≥ {MIN_SEGMENT_TEST_ROWS} rows each. "
            f"Found: {dict(year_counts)}"
        )

    # Take last 3 valid years as test targets (or fewer if not enough years).
    test_years = valid_test_years[-3:]
    train_start = date(valid_test_years[0], 1, 1)

    print(f"  Data years (with ≥ {MIN_SEGMENT_TEST_ROWS} rows): {valid_test_years}")
    print(f"  Test years chosen: {test_years}")

    folds = []
    for i, test_year in enumerate(test_years):
        train_end  = date(test_year - 1, 12, 31)
        test_start = train_end + timedelta(days=GAP_DAYS + 1)
        test_end   = date(test_year, 12, 31)
        folds.append({
            "fold":        i + 1,
            "train_start": str(train_start),
            "train_end":   str(train_end),
            "test_start":  str(test_start),
            "test_end":    str(test_end),
        })

    return folds


# ─── sklearn pipeline ─────────────────────────────────────────────────────────

def _build_pipeline(numeric_feats: list[str], cat_feats: list[str]) -> Pipeline:
    num_pipe = Pipeline([("imp", SimpleImputer(strategy="median"))])
    cat_pipe = Pipeline([
        ("imp", SimpleImputer(strategy="most_frequent")),
        ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    parts = [("num", num_pipe, numeric_feats)]
    if cat_feats:
        parts.append(("cat", cat_pipe, cat_feats))

    preprocessor = ColumnTransformer(parts, remainder="drop")
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


# ─── Metrics ─────────────────────────────────────────────────────────────────

def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    ape = np.abs(y_true - y_pred) / np.maximum(y_true, 1.0)
    return {
        "n":          int(len(y_true)),
        "median_ape": float(np.median(ape)),
        "p90_ape":    float(np.percentile(ape, 90)),
        "mae":        float(np.mean(np.abs(y_true - y_pred))),
        "hit_10pct":  float(np.mean(ape <= 0.10)),
        "hit_25pct":  float(np.mean(ape <= 0.25)),
    }


# ─── Per-segment evaluation ───────────────────────────────────────────────────

def _eval_segment(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    segment: str,
    numeric_feats: list[str],
    cat_feats: list[str],
) -> dict[str, Any]:
    target_col = SEGMENT_TARGET.get(segment, "sales_price")

    def _get_target(df: pd.DataFrame) -> pd.Series:
        if target_col == "price_per_unit":
            return df["sales_price"] / df["total_units"].clip(lower=1).fillna(1)
        return df["sales_price"]

    tr = _make_features(train_df)
    te = _make_features(test_df)

    # Only keep features that actually exist in the data.
    avail_num = [c for c in numeric_feats if c in tr.columns]
    avail_cat = [c for c in cat_feats      if c in tr.columns]

    if len(tr) < MIN_SEGMENT_TRAIN_ROWS or len(te) < MIN_SEGMENT_TEST_ROWS:
        return {
            "segment": segment, "skipped": True,
            "reason": f"train={len(tr)} test={len(te)} (below minimums)",
        }
    if not avail_num:
        return {"segment": segment, "skipped": True, "reason": "no numeric features"}

    y_tr = np.log1p(_get_target(tr).values)
    y_te = np.log1p(_get_target(te).values)

    pipe = _build_pipeline(avail_num, avail_cat)
    try:
        pipe.fit(tr[avail_num + avail_cat], y_tr)
    except Exception as exc:
        return {"segment": segment, "skipped": True, "reason": str(exc)}

    y_hat = pipe.predict(te[avail_num + avail_cat])
    m = _metrics(np.expm1(y_te), np.expm1(y_hat))
    m["segment"] = segment
    m["target"]  = target_col
    m["features_used"] = avail_num + avail_cat
    return m


# ─── One full evaluation run ─────────────────────────────────────────────────

def _run_one(
    df: pd.DataFrame,
    folds: list[dict],
    numeric_feats: list[str],
    cat_feats: list[str],
    label: str,
) -> list[dict[str, Any]]:
    segments = sorted(df["segment"].unique())
    results: list[dict[str, Any]] = []

    print(f"\n{'='*60}")
    print(f"  Feature set: {label}")
    print(f"{'='*60}")

    for fold in folds:
        f_n = fold["fold"]
        sale_dt = pd.to_datetime(df["sale_date"])
        tr_mask = (sale_dt >= fold["train_start"]) & (sale_dt <= fold["train_end"])
        te_mask = (sale_dt >= fold["test_start"])  & (sale_dt <= fold["test_end"])

        train_df = df[tr_mask].copy()
        test_df  = df[te_mask].copy()
        print(f"\n  Fold {f_n}  train={len(train_df):,}  test={len(test_df):,}")

        fold_result: dict[str, Any] = {
            "fold":       f_n,
            "boundaries": fold,
            "train_n":    int(len(train_df)),
            "test_n":     int(len(test_df)),
            "segments":   [],
        }

        # Global (all segments)
        g = _eval_segment(train_df, test_df, "global", numeric_feats, cat_feats)
        fold_result["segments"].append(g)
        if g and not g.get("skipped"):
            print(f"    global               median_ape={g['median_ape']:.3f}  "
                  f"hit_10={g['hit_10pct']:.3f}  n={g['n']}")

        # Per segment
        for seg in segments:
            if seg == "global":
                continue
            r = _eval_segment(
                train_df[train_df["segment"] == seg],
                test_df[test_df["segment"] == seg],
                seg, numeric_feats, cat_feats,
            )
            if r:
                fold_result["segments"].append(r)
                if not r.get("skipped"):
                    print(f"    {seg:<20} median_ape={r['median_ape']:.3f}  "
                          f"hit_10={r['hit_10pct']:.3f}  n={r['n']}")
                else:
                    print(f"    {seg:<20} SKIPPED ({r.get('reason', '')})")

        results.append(fold_result)

    return results


# ─── Lift summary ─────────────────────────────────────────────────────────────

def _summarise(results: list[dict]) -> dict[str, dict]:
    """Average median_ape and hit_10pct per segment across all folds."""
    seg_vals: dict[str, dict[str, list]] = {}
    for fold in results:
        for seg_r in fold.get("segments", []):
            if seg_r.get("skipped"):
                continue
            seg = seg_r["segment"]
            if seg not in seg_vals:
                seg_vals[seg] = {"median_ape": [], "hit_10pct": []}
            seg_vals[seg]["median_ape"].append(seg_r["median_ape"])
            seg_vals[seg]["hit_10pct"].append(seg_r["hit_10pct"])

    return {
        seg: {
            "avg_median_ape": float(np.mean(v["median_ape"])),
            "avg_hit_10pct":  float(np.mean(v["hit_10pct"])),
        }
        for seg, v in seg_vals.items()
    }


def _print_comparison(summaries: dict[str, dict]) -> None:
    print(f"\n{'='*70}")
    print("  LIFT COMPARISON  (avg across folds, ↓ median_ape = better)")
    print(f"{'='*70}")
    print(f"  {'Segment':<22}", end="")
    for label in summaries:
        print(f"  {label:>14}", end="")
    print()
    print(f"  {'-'*22}", end="")
    for _ in summaries:
        print(f"  {'-'*14}", end="")
    print()

    # Collect all segment names.
    all_segs: set[str] = set()
    for summ in summaries.values():
        all_segs.update(summ.keys())

    for seg in sorted(all_segs):
        print(f"  {seg:<22}", end="")
        baseline_ape = None
        for label, summ in summaries.items():
            if seg in summ:
                ape = summ[seg]["avg_median_ape"]
                h10 = summ[seg]["avg_hit_10pct"]
                if baseline_ape is None:
                    baseline_ape = ape
                delta = f" ({(ape - baseline_ape)*100:+.1f}pp)" if baseline_ape is not None and label != list(summaries.keys())[0] else ""
                print(f"  {ape:.3f}/{h10:.3f}{delta:>10}", end="")
            else:
                print(f"  {'n/a':>14}", end="")
        print()
    print(f"\n  Format: median_ape/hit_10pct  (delta pp vs baseline in parens)")
    print(f"{'='*70}\n")


# ─── Main ─────────────────────────────────────────────────────────────────────

def run_eval(
    spine_path: Path,
    feature_set: str = "compare",
) -> dict[str, Any]:
    print(f"Loading spine: {spine_path}")
    df = pd.read_parquet(spine_path)
    df["sale_date"]  = pd.to_datetime(df["sale_date"])
    df["as_of_date"] = pd.to_datetime(df["as_of_date"]).dt.date.astype(str)

    segments = sorted(df["segment"].unique())
    folds    = _build_folds(df)
    print(f"  Rows: {len(df):,}  |  Segments: {segments}")
    print(f"  Folds ({len(folds)}):")
    for f in folds:
        print(f"    F{f['fold']}: train {f['train_start']} → {f['train_end']}  "
              f"test {f['test_start']} → {f['test_end']}")

    # Determine which feature sets to run.
    if feature_set == "compare":
        sets_to_run = list(FEATURE_SETS.keys())  # all four + baseline
    elif feature_set in FEATURE_SETS:
        sets_to_run = ["baseline", feature_set] if feature_set != "baseline" else ["baseline"]
    else:
        raise ValueError(f"Unknown feature set '{feature_set}'. "
                         f"Choose from: {list(FEATURE_SETS.keys()) + ['compare']}")

    # Load Gold features once if any enriched set is requested.
    need_gold = any(s != "baseline" for s in sets_to_run)
    if need_gold:
        print("\nLoading Gold feature files …")
        df = _load_gold_features(df)

    all_results: dict[str, list] = {}
    summaries:   dict[str, dict] = {}

    for label in sets_to_run:
        fset      = FEATURE_SETS[label]
        fold_res  = _run_one(df, folds, fset["num"], fset["cat"], label)
        summ      = _summarise(fold_res)
        all_results[label] = fold_res
        summaries[label]   = summ

    if len(summaries) > 1:
        _print_comparison(summaries)

    return {
        "created_at":   datetime.utcnow().isoformat(),
        "spine_path":   str(spine_path),
        "feature_set":  feature_set,
        "n_folds":      len(folds),
        "segments":     segments,
        "evaluations":  {
            label: {"folds": fold_res, "summary": summaries[label]}
            for label, fold_res in all_results.items()
        },
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="PropIntel rolling-origin eval protocol")
    parser.add_argument("--spine", type=Path, default=DEFAULT_SPINE,
                        help="Path to training spine parquet")
    parser.add_argument("--feature-set", default="compare",
                        choices=list(FEATURE_SETS.keys()) + ["compare"],
                        help="Feature set to evaluate (default: compare — runs all)")
    args = parser.parse_args(argv)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report   = run_eval(args.spine, args.feature_set)
    ts       = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = REPORT_DIR / f"eval_report_{ts}.json"
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"✅  Eval report saved → {out_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
