"""
Serving-path evaluation harness.

Scores the REAL production inference path (PredictionService.predict) against
actual recorded sale prices, rather than scoring a model in isolation on a
fully-populated feature matrix.

Why this exists
---------------
The metrics stored in ml/artifacts/metadata/*.json come from training time,
where every feature column was populated from the Gold tables. Production
requests do not look like that: the frontend posts only borough,
neighborhood, building_class, year_built, gross_sqft, land_sqft, total_units,
lat/lon and market_price — no `bbl` and no `as_of_date`. Without those two
fields the entire Gold join in _build_spine_row is skipped, so DOF / ACRIS /
J-51 / PLUTO / comp / trend features all arrive as NaN and get median-imputed.

This harness therefore measures two payload shapes over the same rows:

  production  — exactly what the frontend sends today (no bbl / as_of_date)
  with_bbl    — same rows plus bbl + as_of_date, enabling the Gold join

The gap between the two quantifies what the missing BBL resolution costs in
real accuracy, and gives a stable before/after scoreboard for feature-parity
work.

Usage
-----
    PYTHONPATH=. python ml/scripts/eval_serving_path.py
    PYTHONPATH=. python ml/scripts/eval_serving_path.py --limit 400 --since 2025-06-01
    PYTHONPATH=. python ml/scripts/eval_serving_path.py --modes production
    PYTHONPATH=. python ml/scripts/eval_serving_path.py --json-out /tmp/eval.json

Rows are sampled from sales AFTER the models' training cutoff, so this is an
out-of-sample measurement for every segment.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

# Keep the app import side-effect free: database.py hard-fails without a
# DATABASE_URL, and this script never touches the DB.
os.environ.setdefault("DATABASE_URL", "sqlite:///./eval_harness_tmp.db")

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.schemas.prediction import ProductionPredictionRequest  # noqa: E402
from backend.app.services.model_registry import ModelRegistry  # noqa: E402
from backend.app.services.predictor import PredictionService  # noqa: E402

SPINE_PATH = REPO_ROOT / "ml" / "data" / "gold" / "training_spine_v1.parquet"
GOLD_PLUTO = REPO_ROOT / "ml" / "data" / "gold" / "gold_pluto_features.parquet"

# Models were trained with TRAIN_END = 2024-12-31 / TEST_START = 2025-01-31.
# Default to evaluating on the post-cutoff period so every row is out-of-sample.
DEFAULT_SINCE = date(2025, 1, 31)

MODES = ("production", "with_bbl")


# ─── Row loading ──────────────────────────────────────────────────────────────

def load_eval_rows(since: date, limit_per_segment: int, seed: int) -> pd.DataFrame:
    """Load post-cutoff sales joined to PLUTO lat/lon, sampled per segment.

    lat/lon come from Gold PLUTO because the spine itself has no coordinates.
    In production the browser supplies coordinates from Mapbox geocoding, so
    sourcing them here is faithful to the real request shape.
    """
    if not SPINE_PATH.exists():
        raise SystemExit(f"Training spine not found: {SPINE_PATH}")

    spine = pd.read_parquet(
        SPINE_PATH,
        columns=[
            "bbl", "sale_date", "sales_price", "segment",
            "borough", "borough_label", "neighborhood", "building_class",
            "year_built", "gross_sqft", "land_sqft",
            "total_units", "residential_units",
        ],
    )

    spine["sale_date"] = pd.to_datetime(spine["sale_date"], errors="coerce")
    spine = spine[spine["sale_date"].dt.date >= since]
    spine = spine[pd.to_numeric(spine["sales_price"], errors="coerce") > 0]
    spine = spine[pd.to_numeric(spine["gross_sqft"], errors="coerce") > 0]
    spine = spine.dropna(subset=["borough_label", "neighborhood", "building_class", "year_built"])

    # Coordinates + BBL-keyed identity for the with_bbl mode.
    pluto = pd.read_parquet(GOLD_PLUTO, columns=["bbl", "pluto_latitude", "pluto_longitude"])
    pluto = pluto.dropna(subset=["pluto_latitude", "pluto_longitude"]).drop_duplicates("bbl")

    spine["bbl"] = spine["bbl"].astype(str).str.strip()
    pluto["bbl"] = pluto["bbl"].astype(str).str.strip()
    df = spine.merge(pluto, on="bbl", how="inner")

    # Schema bounds on ProductionPredictionRequest — drop rows the API itself
    # would reject so we measure model quality, not validation failures.
    df = df[
        df["pluto_latitude"].between(40.0, 41.5)
        & df["pluto_longitude"].between(-75.0, -73.0)
        & pd.to_numeric(df["year_built"], errors="coerce").between(1800, 2026)
    ]

    if df.empty:
        raise SystemExit(f"No eligible rows on/after {since}.")

    # Stratified sample so small segments (coop, rentals) are represented and
    # a single dominant segment can't drive the headline numbers.
    sampled = [
        group.sample(min(len(group), limit_per_segment), random_state=seed)
        for _, group in df.groupby("segment", sort=True)
    ]
    return pd.concat(sampled, ignore_index=True)


# ─── Payload construction ─────────────────────────────────────────────────────

def _opt_float(value: Any) -> float | None:
    """Coerce to a positive float, or None when absent/invalid.

    The frontend omits total_units entirely rather than sending 0, so mirror
    that: absent means absent, not zero.
    """
    num = pd.to_numeric(value, errors="coerce")
    if num is None or (isinstance(num, float) and math.isnan(num)):
        return None
    num = float(num)
    return num if num > 0 else None


def build_payload(row: pd.Series, mode: str) -> ProductionPredictionRequest:
    """Build the request exactly as production would for the given mode."""
    kwargs: dict[str, Any] = {
        "borough": str(row["borough_label"]).strip(),
        "neighborhood": str(row["neighborhood"]).strip(),
        "building_class": str(row["building_class"]).strip(),
        "year_built": int(pd.to_numeric(row["year_built"])),
        "gross_sqft": float(pd.to_numeric(row["gross_sqft"])),
        "land_sqft": _opt_float(row.get("land_sqft")),
        "total_units": _opt_float(row.get("total_units")),
        "latitude": float(row["pluto_latitude"]),
        "longitude": float(row["pluto_longitude"]),
        # market_price is required by the analyze flow but unused by predict();
        # the actual sale price is the label, never fed to the model.
        "market_price": float(row["sales_price"]),
    }

    if mode == "production":
        # The frontend sends neither residential_units nor bbl/as_of_date.
        return ProductionPredictionRequest(**kwargs)

    if mode == "with_bbl":
        kwargs["residential_units"] = _opt_float(row.get("residential_units"))
        kwargs["bbl"] = str(row["bbl"]).strip()
        # As-of the sale date: the same roll-aligned rule training used, so
        # Gold features reflect what was knowable at sale time (no leakage).
        kwargs["as_of_date"] = pd.Timestamp(row["sale_date"]).date()
        return ProductionPredictionRequest(**kwargs)

    raise ValueError(f"Unknown mode: {mode}")


# ─── Metrics ──────────────────────────────────────────────────────────────────

def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute error + interval-coverage metrics for one group of predictions."""
    if not records:
        return {"n": 0}

    actual = np.array([r["actual"] for r in records], dtype=float)
    pred = np.array([r["predicted"] for r in records], dtype=float)

    err = pred - actual
    ape = np.abs(err) / np.where(actual != 0, actual, np.nan)

    ss_res = float(np.sum(err ** 2))
    ss_tot = float(np.sum((actual - actual.mean()) ** 2))

    covered = [r for r in records if r.get("low") is not None and r.get("high") is not None]
    n_cov = len(covered)
    hits = sum(1 for r in covered if r["low"] <= r["actual"] <= r["high"])
    widths = [
        (r["high"] - r["low"]) / r["predicted"]
        for r in covered
        if r["predicted"]
    ]

    return {
        "n": len(records),
        "mae": round(float(np.mean(np.abs(err)))),
        "rmse": round(float(np.sqrt(np.mean(err ** 2)))),
        "median_ape": round(float(np.nanmedian(ape)), 4),
        "mean_ape": round(float(np.nanmean(ape)), 4),
        # Sign of the mean error: positive = systematically over-valuing.
        "mean_bias": round(float(np.mean(err))),
        "r2": round(1.0 - ss_res / ss_tot, 4) if ss_tot > 0 else None,
        "within_10pct": round(float(np.nanmean(ape <= 0.10)), 4),
        "within_20pct": round(float(np.nanmean(ape <= 0.20)), 4),
        "interval_n": n_cov,
        # Should sit near 0.80 for a calibrated P10/P90 band.
        "interval_coverage": round(hits / n_cov, 4) if n_cov else None,
        "interval_rel_width": round(float(np.median(widths)), 4) if widths else None,
    }


# ─── Evaluation ───────────────────────────────────────────────────────────────

def evaluate(df: pd.DataFrame, modes: tuple[str, ...], verbose: bool) -> dict[str, Any]:
    service = PredictionService(ModelRegistry())
    results: dict[str, Any] = {}

    for mode in modes:
        per_segment: dict[str, list[dict[str, Any]]] = defaultdict(list)
        errors: dict[str, int] = defaultdict(int)
        join_status: dict[str, int] = defaultdict(int)

        for _, row in df.iterrows():
            try:
                payload = build_payload(row, mode)
                out = service.predict(payload)
            except Exception as exc:  # noqa: BLE001 — count, don't abort the sweep
                errors[type(exc).__name__] += 1
                if verbose:
                    print(f"  ! {type(exc).__name__}: {exc}")
                continue

            status = (out.get("input_summary") or {}).get("bbl_feature_status", "skipped")
            join_status[status] += 1

            per_segment[out["segment"]].append({
                "actual": float(row["sales_price"]),
                "predicted": float(out["predicted_price"]),
                "low": out.get("price_low"),
                "high": out.get("price_high"),
            })

        flat = [r for rows in per_segment.values() for r in rows]
        results[mode] = {
            "overall": summarize(flat),
            "by_segment": {seg: summarize(rows) for seg, rows in sorted(per_segment.items())},
            "errors": dict(errors),
            "bbl_feature_status": dict(join_status),
        }

    return results


# ─── Reporting ────────────────────────────────────────────────────────────────

_COLS = [
    ("n", "n", 6),
    ("mae", "MAE", 12),
    ("median_ape", "medAPE", 8),
    ("r2", "R2", 8),
    ("within_10pct", "<=10%", 8),
    ("within_20pct", "<=20%", 8),
    ("interval_coverage", "cover", 8),
]


def _fmt(value: Any, key: str) -> str:
    if value is None:
        return "-"
    if key in ("median_ape", "within_10pct", "within_20pct", "interval_coverage"):
        return f"{value * 100:.1f}%"
    if key == "mae":
        return f"{int(value):,}"
    return str(value)


def print_table(title: str, rows: dict[str, dict[str, Any]]) -> None:
    print(f"\n{title}")
    header = "".join(label.rjust(width) for _, label, width in _COLS)
    print(f"{'segment':<18}{header}")
    print("-" * (18 + sum(w for _, _, w in _COLS)))
    for name, stats in rows.items():
        if not stats.get("n"):
            continue
        line = "".join(_fmt(stats.get(key), key).rjust(width) for key, _, width in _COLS)
        print(f"{name:<18}{line}")


def print_report(results: dict[str, Any]) -> None:
    for mode, res in results.items():
        rows = dict(res["by_segment"])
        rows["ALL"] = res["overall"]
        label = {
            "production": "PRODUCTION payload (no bbl/as_of_date — what the frontend sends today)",
            "with_bbl": "WITH_BBL payload (bbl + as_of_date — Gold features enabled)",
        }.get(mode, mode)
        print_table(f"=== {label} ===", rows)
        if res["errors"]:
            print(f"  prediction errors: {res['errors']}")
        print(f"  bbl_feature_status: {res['bbl_feature_status']}")

    if "production" in results and "with_bbl" in results:
        prod, full = results["production"]["overall"], results["with_bbl"]["overall"]
        if prod.get("n") and full.get("n"):
            print("\n=== Gap: what the skipped Gold join costs ===")
            for key, label in (
                ("mae", "MAE"),
                ("median_ape", "median APE"),
                ("within_10pct", "share within 10%"),
            ):
                p, f = prod.get(key), full.get(key)
                if p is None or f is None:
                    continue
                delta_pct = (f - p) / p * 100 if p else 0.0
                print(
                    f"  {label:<20} production={_fmt(p, key):>10}   "
                    f"with_bbl={_fmt(f, key):>10}   change={delta_pct:+.1f}%"
                )


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", default=str(DEFAULT_SINCE),
                        help=f"Only evaluate sales on/after this date (default {DEFAULT_SINCE}).")
    parser.add_argument("--limit", type=int, default=250,
                        help="Max rows sampled per segment (default 250).")
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES),
                        help="Payload shapes to evaluate (default: both).")
    parser.add_argument("--seed", type=int, default=42, help="Sampling seed (default 42).")
    parser.add_argument("--json-out", default=None, help="Also write results as JSON to this path.")
    parser.add_argument("--verbose", action="store_true", help="Print individual prediction errors.")
    args = parser.parse_args()

    since = datetime.strptime(args.since, "%Y-%m-%d").date()
    df = load_eval_rows(since, args.limit, args.seed)

    print(f"Evaluating {len(df):,} sales on/after {since} "
          f"({df['sale_date'].min().date()} → {df['sale_date'].max().date()})")
    print(f"Segments: {dict(df['segment'].value_counts())}")

    results = evaluate(df, tuple(args.modes), args.verbose)
    print_report(results)

    if args.json_out:
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "since": str(since),
            "limit_per_segment": args.limit,
            "seed": args.seed,
            "n_rows": len(df),
            "results": results,
        }
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json_out}")


if __name__ == "__main__":
    main()
