"""Gold builder: per-sale comparable-sales features (k-NN + time window).

Input  : ml/data/gold/training_spine_v1.parquet      (sale events)
         ml/data/gold/gold_pluto_features.parquet    (lat/lon by BBL)
Output : ml/data/gold/gold_comps_features.parquet
         keyed on (bbl, as_of_date, comp_segment)

What this gives the model
-------------------------
Comparable-sales (a.k.a. "comps") are the single most explanatory signal in
real-estate appraisal: a 2-family in Park Slope is worth what other 2-families
in Park Slope sold for in the last year.  XGBoost cannot learn this from
neighborhood + sale_date alone — the categorical encoder treats every
neighborhood independently and has no notion of "what did similar nearby
properties just sell for".

For every sale event in the spine we compute:

  comp_count         — # of comparable sales found in the lookup window
  comp_median_price  — median sale price of the comps (the strongest signal)
  comp_median_ppsqft — median price-per-sqft (size-normalised price)
  comp_search_dist_km— distance to the K-th nearest comp (sparsity flag)
  comp_recency_days  — days since most recent comp (data freshness flag)
  comp_p25_price     — 25th-pct comp price (low end of local market)
  comp_p75_price     — 75th-pct comp price (high end)

As-of contract
--------------
For sale event (bbl, sale_date, as_of_date):
  - We use only sales whose `sale_date` is strictly < `as_of_date`
    (no peeking at same-day sales, no future leakage).
  - We use only sales within the prior 365 days.
  - We restrict comps to the same comp_segment so 2-family comps come
    from 2-family sales — never condo or 3-family.

Comp segments
-------------
We build comps per spine_segment + building_class_prefix combination so the
neighbour search returns *like-for-like* properties:

  one_family   : segment == one_family   (no building class restriction)
  two_family   : segment == multi_family AND building_class starts with "02"
  three_family : segment == multi_family AND building_class starts with "03"
  condo_coop   : segment == condo_coop   (no building class restriction)

Each segment writes its own block of rows; the consumer joins on
(bbl, as_of_date, comp_segment).

Run from repo root:
    python ml/pipelines/gold_comps_features.py
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree

BASE        = Path(__file__).resolve().parents[2]
SPINE_FILE  = BASE / "ml/data/gold/training_spine_v1.parquet"
PLUTO_FILE  = BASE / "ml/data/gold/gold_pluto_features.parquet"
OUT_FILE    = BASE / "ml/data/gold/gold_comps_features.parquet"

# ── Comp-search hyperparameters ────────────────────────────────────────────────
# K — number of comps to aggregate.  Five is the appraisal-industry standard
# for residential 1–4-unit comps.  Smaller K (3) gives noisier medians; larger
# K (10) starts pulling in less-comparable properties.
K_COMPS                  = 5
# Time window — how far back to look.  365 days is the SOC for residential
# appraisal (Fannie/Freddie guidelines).  Shorter (90d) → too few comps in
# slow neighborhoods.  Longer (730d) → stale prices in fast-moving markets.
LOOKBACK_DAYS            = 365
# Initial spatial query — over-fetch K_QUERY nearest, then filter by date.
# Set high enough that after time-filtering we usually have ≥ K_COMPS rows.
# 50 is a comfortable margin for NYC's sale density.
K_QUERY_INITIAL          = 50
# Max search radius (km) — drop comps farther than this even if they're in
# the K-nearest set.  Anything > 5 km in NYC is effectively a different market.
MAX_COMP_DIST_KM         = 5.0
# Minimum sale price to count as a comp.  Avoids polluting comps with the
# same nominal/foreclosure transfers we filter from training.
MIN_COMP_PRICE           = 100_000
# Earth radius for haversine queries in km.
_R_EARTH                 = 6371.0

# ── Comp-segment definitions (mirror SEGMENT_FEATURES) ─────────────────────────
COMP_SEGMENTS: list[dict] = [
    {"name": "one_family",   "spine_seg": "one_family",   "bc_prefix": None},
    {"name": "two_family",   "spine_seg": "multi_family", "bc_prefix": "02"},
    {"name": "three_family", "spine_seg": "multi_family", "bc_prefix": "03"},
    {"name": "condo_coop",   "spine_seg": "condo_coop",   "bc_prefix": None},
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _slice_segment(spine: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    sub = spine[spine["segment"] == cfg["spine_seg"]].copy()
    if cfg["bc_prefix"]:
        sub = sub[
            sub["building_class"].astype(str).str.startswith(cfg["bc_prefix"])
        ].copy()
    return sub


def _prep_with_geo(sub: pd.DataFrame, pluto_geo: pd.DataFrame) -> pd.DataFrame:
    """Attach lat/lon and clean numeric fields needed for comp search."""
    out = sub.merge(pluto_geo, on="bbl", how="left")
    out["pluto_latitude"]  = pd.to_numeric(out["pluto_latitude"],  errors="coerce")
    out["pluto_longitude"] = pd.to_numeric(out["pluto_longitude"], errors="coerce")
    out["sales_price"]     = pd.to_numeric(out["sales_price"],     errors="coerce")
    out["gross_sqft"]      = pd.to_numeric(out["gross_sqft"],      errors="coerce")
    out["sale_date_dt"]    = pd.to_datetime(out["sale_date"]).dt.date
    out["as_of_date_dt"]   = pd.to_datetime(out["as_of_date"]).dt.date
    # Drop rows that can't be searched against (no geo) or are too cheap to
    # be a real comp.  Keep the originals as TARGETS even if they have low
    # price — but they will only contribute to other rows' comps if they
    # exceed MIN_COMP_PRICE.
    return out


def _build_comp_block(
    rows: pd.DataFrame,
    seg_name: str,
) -> pd.DataFrame:
    """Compute comp features for every row using a single BallTree.

    Algorithm (per segment):
      1. Build a BallTree of all sale-event lat/lons in the segment.
      2. For each sale event, query the K_QUERY_INITIAL nearest neighbours.
      3. Filter neighbours to those with sale_date strictly < as_of_date and
         sale_date >= as_of_date - LOOKBACK_DAYS, with sales_price ≥ MIN_COMP_PRICE
         and distance ≤ MAX_COMP_DIST_KM.
      4. Take the K_COMPS nearest passing rows and aggregate.
    """
    valid = rows.dropna(subset=["pluto_latitude", "pluto_longitude"]).copy()
    if valid.empty:
        return pd.DataFrame()

    # BallTree wants radians.
    coords_rad = np.deg2rad(valid[["pluto_latitude", "pluto_longitude"]].to_numpy())
    tree = BallTree(coords_rad, metric="haversine")

    # Vectorised arrays for fast inner loop.
    sale_dates  = valid["sale_date_dt"].to_numpy()
    asof_dates  = valid["as_of_date_dt"].to_numpy()
    prices      = valid["sales_price"].to_numpy(dtype=float)
    sqfts       = valid["gross_sqft"].to_numpy(dtype=float)
    bbls        = valid["bbl"].to_numpy()

    # Query k-nearest for every row in one batched call (huge speedup vs row-by-row).
    k = min(K_QUERY_INITIAL, len(valid))
    dist_rad, idx = tree.query(coords_rad, k=k)
    dist_km = dist_rad * _R_EARTH

    out_rows = []
    n        = len(valid)
    min_date = pd.Timestamp.min.date()
    for i in range(n):
        target_asof = asof_dates[i]
        window_start = target_asof - timedelta(days=LOOKBACK_DAYS)

        # Candidate neighbour indices (excluding self at position 0).
        # Note: query already returns sorted by distance ascending.
        cand_idx = idx[i]
        cand_dist = dist_km[i]
        # Drop self (same array position OR same bbl on same date — defensive).
        # The strict date comparison below already excludes same-event self,
        # but doing position-wise drop is cheap and safe.
        keep = cand_idx != i
        cand_idx  = cand_idx[keep]
        cand_dist = cand_dist[keep]

        # Filter: prior + within window + above min price + within max dist.
        cand_dates = sale_dates[cand_idx]
        cand_price = prices[cand_idx]
        cand_sqft  = sqfts[cand_idx]
        date_ok    = (cand_dates < target_asof) & (cand_dates >= window_start)
        price_ok   = cand_price >= MIN_COMP_PRICE
        dist_ok    = cand_dist <= MAX_COMP_DIST_KM
        passing    = date_ok & price_ok & dist_ok
        if not passing.any():
            continue

        sel_dist  = cand_dist[passing][:K_COMPS]
        sel_price = cand_price[passing][:K_COMPS]
        sel_sqft  = cand_sqft[passing][:K_COMPS]
        sel_dates = cand_dates[passing][:K_COMPS]

        comp_count = len(sel_price)
        # Guard the median calls — small selections are still well-defined.
        comp_median_price = float(np.median(sel_price))
        comp_p25_price    = float(np.percentile(sel_price, 25))
        comp_p75_price    = float(np.percentile(sel_price, 75))
        # Price-per-sqft only over comps with usable sqft.
        ppsqft_vals = sel_price / np.where(sel_sqft > 100, sel_sqft, np.nan)
        ppsqft_vals = ppsqft_vals[~np.isnan(ppsqft_vals)]
        comp_median_ppsqft = (
            float(np.median(ppsqft_vals)) if len(ppsqft_vals) else np.nan
        )
        # Distance to K-th nearest comp (or nearest if K-1 not reached).
        comp_search_dist_km = float(sel_dist[-1])
        # Days since most recent comp.
        most_recent = max(sel_dates)
        comp_recency_days = int((target_asof - most_recent).days)

        out_rows.append({
            "bbl":                  bbls[i],
            "as_of_date":           str(target_asof),
            "comp_segment":         seg_name,
            "comp_count":           comp_count,
            "comp_median_price":    comp_median_price,
            "comp_median_ppsqft":   comp_median_ppsqft,
            "comp_search_dist_km":  comp_search_dist_km,
            "comp_recency_days":    comp_recency_days,
            "comp_p25_price":       comp_p25_price,
            "comp_p75_price":       comp_p75_price,
        })

    return pd.DataFrame(out_rows)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"Reading spine: {SPINE_FILE}")
    spine = pd.read_parquet(SPINE_FILE)
    print(f"  rows: {len(spine):,}")

    print(f"Reading PLUTO geo: {PLUTO_FILE}")
    pluto = pd.read_parquet(PLUTO_FILE, columns=["bbl", "pluto_latitude", "pluto_longitude"])

    blocks: list[pd.DataFrame] = []
    for cfg in COMP_SEGMENTS:
        sub = _slice_segment(spine, cfg)
        if sub.empty:
            print(f"  [skip] {cfg['name']}: 0 rows")
            continue
        sub = _prep_with_geo(sub, pluto)
        n_geo = sub["pluto_latitude"].notna().sum()
        print(f"  [{cfg['name']}] {len(sub):,} sale events, {n_geo:,} with geo")
        block = _build_comp_block(sub, cfg["name"])
        print(f"    → {len(block):,} comp rows produced")
        blocks.append(block)

    if not blocks:
        print("No comp blocks built — aborting.")
        return

    out = pd.concat(blocks, ignore_index=True)
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT_FILE, index=False)
    print(f"\nWrote {len(out):,} rows → {OUT_FILE}")
    print("\nSchema:")
    print(out.dtypes)
    print("\nCoverage by segment:")
    print(out["comp_segment"].value_counts())
    print("\nFeature summary:")
    print(out.describe(include="all").T[["count", "mean", "min", "max"]])


if __name__ == "__main__":
    main()
