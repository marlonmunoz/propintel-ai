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

This harness therefore measures five payload shapes over the same rows:

  production       — exactly what the frontend sends today (no bbl / as_of_date)
  prod_plus_units  — production plus residential_units only (already shipped)
  with_bbl         — same rows plus the true bbl + as_of_date, enabling the Gold join
  resolved_bbl     — bbl resolved server-side from the lat/lon the client already
                      sends, by nearest tax-lot centroid in Gold PLUTO. Ruled out:
                      see resolved_bbl's own history below.
  resolved_address — bbl resolved server-side from the ADDRESS the client already
                      sends, via ml/pipelines/build_address_bbl_index.py (an
                      offline index built from PLUTO raw, scored in Phase 0 at
                      99.7%+ precision for one_family/multi_family/rentals/coop).
                      Condo unit classes (12/13/15) are hard-excluded here too,
                      not just left to the index's own exclusion, because a
                      condo address resolves unambiguously to PLUTO's condo
                      MASTER lot — confident-looking and always wrong for the
                      actual unit sold. Rows the index can't confidently resolve
                      fall back to prod_plus_units behaviour (abstain, don't
                      guess), so this mode's blended result is what production
                      would actually see if shipped as-is.

The gap between production and with_bbl quantifies what the missing BBL
resolution costs in real accuracy; resolved_bbl and resolved_address measure
how much of that gap each server-side fix actually recovers. resolved_bbl
(lat/lon → nearest centroid) was measured and rejected: exact-match collapses
from 100% at 0m geocoder error to 7.3% at 25m, because NYC parcel centroids
sit closer together than typical geocoding error, and a wrong BBL is worse
than none (median APE 27.3% -> 31.8%). resolved_address is the replacement
approach under test.

Usage
-----
    PYTHONPATH=. python ml/scripts/eval_serving_path.py
    PYTHONPATH=. python ml/scripts/eval_serving_path.py --limit 400 --since 2025-06-01
    PYTHONPATH=. python ml/scripts/eval_serving_path.py --modes production
    PYTHONPATH=. python ml/scripts/eval_serving_path.py --modes resolved_address
    PYTHONPATH=. python ml/scripts/eval_serving_path.py --modes resolved_bbl --jitter-m 25
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
from typing import Any, cast

# Keep the app import side-effect free: database.py hard-fails without a
# DATABASE_URL, and this script never touches the DB.
os.environ.setdefault("DATABASE_URL", "sqlite:///./eval_harness_tmp.db")

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.schemas.prediction import ProductionPredictionRequest  # noqa: E402
from backend.app.services.address_resolver import resolve_bbl as resolve_bbl_from_address  # noqa: E402
from backend.app.services.model_registry import ModelRegistry  # noqa: E402
from backend.app.services.predictor import PredictionService  # noqa: E402

SPINE_PATH = REPO_ROOT / "ml" / "data" / "gold" / "training_spine_v1.parquet"
GOLD_PLUTO = REPO_ROOT / "ml" / "data" / "gold" / "gold_pluto_features.parquet"

# Models were trained with TRAIN_END = 2024-12-31 / TEST_START = 2025-01-31.
# Default to evaluating on the post-cutoff period so every row is out-of-sample.
DEFAULT_SINCE = date(2025, 1, 31)

MODES = ("production", "prod_plus_units", "with_bbl", "resolved_bbl", "resolved_address")

# Modes where build_payload's second return value means "did BBL resolution
# find the right lot" (True/False) rather than "not applicable" (None).
# evaluate() reports resolve-rate + precision-among-resolved only for these.
RESOLUTION_MODES = frozenset({"resolved_bbl", "resolved_address"})

EARTH_RADIUS_M = 6_371_000.0


# ─── BBL resolution from coordinates ──────────────────────────────────────────

_BBL_INDEX: tuple[Any, np.ndarray] | None = None


def _bbl_index() -> tuple[Any, np.ndarray]:
    """BallTree over every NYC tax-lot centroid in Gold PLUTO, plus BBL array.

    Used by the resolved_bbl mode to answer: if production resolved a BBL from
    the coordinates it already receives (instead of requiring the client to
    send one), how accurate would valuations be? Gold PLUTO ships in the
    Docker image already, so this needs no external geocoding service.
    """
    global _BBL_INDEX
    if _BBL_INDEX is None:
        from sklearn.neighbors import BallTree

        df = pd.read_parquet(
            GOLD_PLUTO, columns=["bbl", "pluto_latitude", "pluto_longitude"]
        ).dropna(subset=["pluto_latitude", "pluto_longitude"])
        coords = np.radians(
            df[["pluto_latitude", "pluto_longitude"]].values.astype(float)
        )
        _BBL_INDEX = (
            BallTree(coords, metric="haversine"),
            df["bbl"].astype(str).str.strip().values,
        )
    return _BBL_INDEX


def resolve_bbl(lat: float, lon: float) -> str | None:
    """Nearest tax-lot centroid to a coordinate pair."""
    tree, bbls = _bbl_index()
    _, idx = tree.query(np.radians([[lat, lon]]), k=1)
    return str(bbls[int(idx[0, 0])])


def _jitter(lat: float, lon: float, meters: float, rng: np.random.Generator) -> tuple[float, float]:
    """Offset a coordinate by `meters` in a uniformly random direction.

    Simulates real geocoder error: the harness otherwise feeds back PLUTO's own
    parcel centroid, which would resolve to the correct BBL every time and
    overstate how well resolution works on Mapbox-geocoded rooftop points.
    """
    if meters <= 0:
        return lat, lon
    bearing = rng.uniform(0, 2 * math.pi)
    d = meters / EARTH_RADIUS_M
    dlat = d * math.cos(bearing)
    dlon = d * math.sin(bearing) / math.cos(math.radians(lat))
    return lat + math.degrees(dlat), lon + math.degrees(dlon)


# ─── Typed pandas accessors ───────────────────────────────────────────────────
#
# pandas-stubs types pd.to_numeric() as a union of every possible container and
# scalar it could return, and types Series[label] as Series | ndarray | Any even
# when a single label yields one scalar. Both are wider than what these call
# sites can actually produce, so comparisons and float()/int() conversions on
# the results fail type checking. These three helpers assert the narrower real
# type once, here, instead of scattering ignores over every use.

def _num_col(values: Any) -> pd.Series:
    """Coerce a DataFrame column to numeric, typed as a Series."""
    return cast(pd.Series, pd.to_numeric(values, errors="coerce"))


def _cell(row: pd.Series, key: str) -> Any:
    """Read one scalar cell from a row Series."""
    return row[key]


def _num_cell(row: pd.Series, key: str) -> float:
    """Read one scalar cell as a float; NaN when absent or unparseable."""
    return float(cast(Any, pd.to_numeric(_cell(row, key), errors="coerce")))


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
            "total_units", "residential_units", "address",
        ],
    )

    spine["sale_date"] = pd.to_datetime(spine["sale_date"], errors="coerce")

    # One combined mask rather than three chained filters, so a 300k-row frame is
    # copied once. The date bound compares against a Timestamp instead of going
    # through .dt.date, which would build a Python date object for every row.
    keep = (
        (spine["sale_date"] >= pd.Timestamp(since))
        & (_num_col(spine["sales_price"]) > 0)
        & (_num_col(spine["gross_sqft"]) > 0)
    )
    spine = cast(pd.DataFrame, spine[keep]).dropna(
        subset=["borough_label", "neighborhood", "building_class", "year_built"]
    )

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
        & _num_col(df["year_built"]).between(1800, 2026)
    ]

    if df.empty:
        raise SystemExit(f"No eligible rows on/after {since}.")

    # Stratified sample so small segments (coop, rentals) are represented and
    # a single dominant segment can't drive the headline numbers.
    sampled = [
        group.sample(min(len(group), limit_per_segment), random_state=seed)
        for _, group in df.groupby("segment", sort=True)
    ]
    return cast(pd.DataFrame, pd.concat(sampled, ignore_index=True))


# ─── Payload construction ─────────────────────────────────────────────────────

def _opt_float(value: Any) -> float | None:
    """Coerce to a positive float, or None when absent/invalid.

    The frontend omits total_units entirely rather than sending 0, so mirror
    that: absent means absent, not zero.
    """
    raw = cast(Any, pd.to_numeric(value, errors="coerce"))
    if raw is None or (isinstance(raw, float) and math.isnan(raw)):
        return None
    num = float(raw)
    return num if num > 0 else None


def build_payload(
    row: pd.Series,
    mode: str,
    *,
    jitter_m: float = 0.0,
    rng: np.random.Generator | None = None,
) -> tuple[ProductionPredictionRequest, bool | None]:
    """Build the request exactly as production would for the given mode.

    Returns ``(payload, bbl_correct)`` where bbl_correct is True/False for
    resolved_bbl mode (did resolution recover the true BBL?) and None otherwise.
    """
    kwargs: dict[str, Any] = {
        "borough": str(_cell(row, "borough_label")).strip(),
        "neighborhood": str(_cell(row, "neighborhood")).strip(),
        "building_class": str(_cell(row, "building_class")).strip(),
        "year_built": int(_num_cell(row, "year_built")),
        "gross_sqft": _num_cell(row, "gross_sqft"),
        "land_sqft": _opt_float(row.get("land_sqft")),
        "total_units": _opt_float(row.get("total_units")),
        "latitude": _num_cell(row, "pluto_latitude"),
        "longitude": _num_cell(row, "pluto_longitude"),
        # market_price is required by the analyze flow but unused by predict();
        # the actual sale price is the label, never fed to the model.
        "market_price": _num_cell(row, "sales_price"),
    }

    if mode == "production":
        # The frontend sends neither residential_units nor bbl/as_of_date.
        return ProductionPredictionRequest(**kwargs), None

    if mode == "prod_plus_units":
        # Production payload plus residential_units only — no bbl, no Gold join.
        # residential_units is a real feature for multi_family and all three
        # rental models, and the frontend has no field for it today, so this
        # isolates the value of a form field against the cost of BBL work.
        kwargs["residential_units"] = _opt_float(row.get("residential_units"))
        return ProductionPredictionRequest(**kwargs), None

    if mode == "with_bbl":
        kwargs["residential_units"] = _opt_float(row.get("residential_units"))
        kwargs["bbl"] = str(_cell(row, "bbl")).strip()
        # As-of the sale date: the same roll-aligned rule training used, so
        # Gold features reflect what was knowable at sale time (no leakage).
        kwargs["as_of_date"] = pd.Timestamp(_cell(row, "sale_date")).date()
        return ProductionPredictionRequest(**kwargs), None

    if mode == "resolved_bbl":
        # Server-side resolution: only the coordinates the client already sends,
        # optionally jittered to emulate geocoder error. residential_units is
        # NOT set, since production doesn't send it.
        lat, lon = _jitter(
            kwargs["latitude"], kwargs["longitude"], jitter_m,
            rng or np.random.default_rng(0),
        )
        found = resolve_bbl(lat, lon)
        kwargs["bbl"] = found
        # as_of_date held to the sale date so this isolates the effect of
        # resolution accuracy alone, comparable against with_bbl.
        kwargs["as_of_date"] = pd.Timestamp(_cell(row, "sale_date")).date()
        correct = found is not None and found == str(_cell(row, "bbl")).strip()
        return ProductionPredictionRequest(**kwargs), correct

    if mode == "resolved_address":
        # residential_units is included regardless of resolution outcome —
        # it is already shipped independently of BBL work, so this mode
        # represents the actual next production state, not an isolated
        # ablation of address resolution alone.
        kwargs["residential_units"] = _opt_float(row.get("residential_units"))

        borough_num = _num_cell(row, "borough")
        found = resolve_bbl_from_address(
            row.get("address"),
            int(borough_num) if not math.isnan(borough_num) else None,
            _cell(row, "building_class"),
            kwargs["latitude"],
            kwargs["longitude"],
        )
        if found is None:
            # Abstain: no bbl / as_of_date set, same as prod_plus_units. A real
            # user whose address doesn't confidently resolve gets the same
            # median-imputed behaviour production gives them today — never a
            # guessed BBL.
            return ProductionPredictionRequest(**kwargs), None

        kwargs["bbl"] = found
        kwargs["as_of_date"] = pd.Timestamp(_cell(row, "sale_date")).date()
        correct = found == str(_cell(row, "bbl")).strip()
        return ProductionPredictionRequest(**kwargs), correct

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

def evaluate(
    df: pd.DataFrame,
    modes: tuple[str, ...],
    verbose: bool,
    jitter_m: float = 0.0,
    seed: int = 42,
) -> dict[str, Any]:
    service = PredictionService(ModelRegistry())
    results: dict[str, Any] = {}

    for mode in modes:
        per_segment: dict[str, list[dict[str, Any]]] = defaultdict(list)
        errors: dict[str, int] = defaultdict(int)
        join_status: dict[str, int] = defaultdict(int)
        bbl_hits = 0
        bbl_checked = 0
        # Fresh generator per mode so jitter is reproducible and identical
        # across runs regardless of which modes were selected.
        rng = np.random.default_rng(seed)

        for _, row in df.iterrows():
            try:
                payload, bbl_correct = build_payload(
                    row, mode, jitter_m=jitter_m, rng=rng
                )
                out = service.predict(payload)
            except Exception as exc:  # noqa: BLE001 — count, don't abort the sweep
                errors[type(exc).__name__] += 1
                if verbose:
                    print(f"  ! {type(exc).__name__}: {exc}")
                continue

            if bbl_correct is not None:
                bbl_checked += 1
                bbl_hits += int(bbl_correct)

            status = (out.get("input_summary") or {}).get("bbl_feature_status", "skipped")
            join_status[status] += 1

            per_segment[out["segment"]].append({
                "actual": _num_cell(row, "sales_price"),
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
        if mode in RESOLUTION_MODES:
            # Reported unconditionally (even at 0) for resolution modes, since
            # a 0% resolve rate is itself meaningful and shouldn't be silently
            # omitted the way "not applicable" is for with_bbl / production.
            results[mode]["resolve_rate"] = round(bbl_checked / len(flat), 4) if flat else 0.0
            results[mode]["bbl_exact_match_rate"] = (
                round(bbl_hits / bbl_checked, 4) if bbl_checked else None
            )
            if mode == "resolved_bbl":
                results[mode]["jitter_m"] = jitter_m

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
            "prod_plus_units": "PROD + residential_units (one new form field, no BBL work)",
            "with_bbl": "WITH_BBL payload (true bbl + as_of_date — Gold features enabled)",
            "resolved_bbl": "RESOLVED_BBL payload (bbl resolved server-side from lat/lon)",
            "resolved_address": "RESOLVED_ADDRESS payload (bbl resolved server-side from address)",
        }.get(mode, mode)
        print_table(f"=== {label} ===", rows)
        if mode in RESOLUTION_MODES:
            match_str = (
                f"{res['bbl_exact_match_rate'] * 100:.1f}%"
                if res.get("bbl_exact_match_rate") is not None else "n/a"
            )
            jitter_str = f"  (coordinate jitter: {res.get('jitter_m', 0):.0f} m)" if mode == "resolved_bbl" else ""
            print(f"  resolve rate: {res.get('resolve_rate', 0) * 100:.1f}%   "
                  f"precision of resolved: {match_str}{jitter_str}")
        if res["errors"]:
            print(f"  prediction errors: {res['errors']}")
        print(f"  bbl_feature_status: {res['bbl_feature_status']}")

    baseline = results.get("production", {}).get("overall")
    if not baseline or not baseline.get("n"):
        return

    for mode in ("prod_plus_units", "with_bbl", "resolved_bbl", "resolved_address"):
        target = results.get(mode, {}).get("overall")
        if not target or not target.get("n"):
            continue
        print(f"\n=== {mode} vs production ===")
        for key, label in (
            ("mae", "MAE"),
            ("median_ape", "median APE"),
            ("r2", "R2"),
            ("within_10pct", "share within 10%"),
        ):
            p, f = baseline.get(key), target.get(key)
            if p is None or f is None:
                continue
            delta_pct = (f - p) / abs(p) * 100 if p else 0.0
            print(
                f"  {label:<20} production={_fmt(p, key):>10}   "
                f"{mode}={_fmt(f, key):>10}   change={delta_pct:+.1f}%"
            )


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", default=str(DEFAULT_SINCE),
                        help=f"Only evaluate sales on/after this date (default {DEFAULT_SINCE}).")
    parser.add_argument("--limit", type=int, default=250,
                        help="Max rows sampled per segment (default 250).")
    parser.add_argument("--modes", nargs="+", choices=MODES, default=list(MODES),
                        help="Payload shapes to evaluate (default: all).")
    parser.add_argument("--jitter-m", type=float, default=0.0,
                        help=("Metres of random coordinate error applied in resolved_bbl "
                              "mode, emulating geocoder imprecision (default 0)."))
    parser.add_argument("--seed", type=int, default=42, help="Sampling seed (default 42).")
    parser.add_argument("--json-out", default=None, help="Also write results as JSON to this path.")
    parser.add_argument("--verbose", action="store_true", help="Print individual prediction errors.")
    args = parser.parse_args()

    since = datetime.strptime(args.since, "%Y-%m-%d").date()
    df = load_eval_rows(since, args.limit, args.seed)

    print(f"Evaluating {len(df):,} sales on/after {since} "
          f"({df['sale_date'].min().date()} → {df['sale_date'].max().date()})")
    print(f"Segments: {dict(df['segment'].value_counts())}")

    results = evaluate(df, tuple(args.modes), args.verbose, args.jitter_m, args.seed)
    print_report(results)

    if args.json_out:
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "since": str(since),
            "limit_per_segment": args.limit,
            "seed": args.seed,
            "jitter_m": args.jitter_m,
            "n_rows": len(df),
            "results": results,
        }
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"\nWrote {args.json_out}")


if __name__ == "__main__":
    main()
