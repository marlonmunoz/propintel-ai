"""Gold builder: borough/neighbourhood market-trend features (as-of safe).

Input  : ml/data/gold/training_spine_v1.parquet
Output : ml/data/gold/gold_market_trends.parquet
         keyed on (as_of_date, borough, neighborhood, comp_segment)

What this gives the model
-------------------------
The static `neighborhood_median_price` feature is computed from training rows
*globally* — it cannot tell the model whether the neighbourhood is currently
hot or cooling.  Comp features (gold_comps_features) capture the local price
level at the sale date but say nothing about *direction*.  This builder
captures the trend itself:

  nbhd_median_l365          — median sale price in this nbhd over prior 365 days
  nbhd_yoy_growth           — (current 365d median) / (365–730d median) − 1
  borough_median_l365       — borough-level prior-365d median (smoother)
  borough_yoy_growth        — borough-level YoY growth (stable signal)
  nbhd_sale_count_l365      — # sales in nbhd over prior 365 days (liquidity)

Why YoY ratios matter
---------------------
A 2-family sold in mid-2024 in Bed-Stuy at $1.4M is statistically different
from one sold in mid-2025 at $1.4M *if* Bed-Stuy prices grew 8% YoY — the
2025 listing is effectively cheaper for its market.  YoY growth gives the
model a market-direction signal it cannot derive from sale_date alone (the
date is just a number; the ratio is a regime indicator).

As-of contract
--------------
For an event at as_of_date D:
  - "current" window  : sales with sale_date in [D − 365, D)        (strictly prior)
  - "year-ago" window : sales with sale_date in [D − 730, D − 365)  (the comparison)

The "year-ago" window has zero overlap with the current window so the YoY
ratio is leakage-safe.

Comp segments
-------------
Trend medians are computed *per spine-segment slice* so two_family trends
are derived from 2-family sales only, etc.  This mirrors gold_comps_features
and prevents condo trends polluting house trends.

Run from repo root:
    python ml/pipelines/gold_market_trends.py
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

BASE       = Path(__file__).resolve().parents[2]
SPINE_FILE = BASE / "ml/data/gold/training_spine_v1.parquet"
OUT_FILE   = BASE / "ml/data/gold/gold_market_trends.parquet"

LOOKBACK_DAYS    = 365
MIN_TREND_PRICE  = 100_000  # mirror comp filter — exclude nominal transfers
MIN_GROUP_SIZE   = 5        # below this, returned median is unreliable

# Same definition as gold_comps_features so join keys align.
COMP_SEGMENTS: list[dict] = [
    {"name": "one_family",   "spine_seg": "one_family",   "bc_prefix": None},
    {"name": "two_family",   "spine_seg": "multi_family", "bc_prefix": "02"},
    {"name": "three_family", "spine_seg": "multi_family", "bc_prefix": "03"},
    {"name": "condo_coop",   "spine_seg": "condo_coop",   "bc_prefix": None},
]


def _slice_segment(spine: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    sub = spine[spine["segment"] == cfg["spine_seg"]].copy()
    if cfg["bc_prefix"]:
        sub = sub[
            sub["building_class"].astype(str).str.startswith(cfg["bc_prefix"])
        ].copy()
    return sub


def _prep(sub: pd.DataFrame) -> pd.DataFrame:
    out = sub.copy()
    out["sales_price"] = pd.to_numeric(out["sales_price"], errors="coerce")
    out = out[out["sales_price"] >= MIN_COMP_PRICE_FALLBACK]
    out["sale_date_dt"]  = pd.to_datetime(out["sale_date"]).dt.date
    out["as_of_date_dt"] = pd.to_datetime(out["as_of_date"]).dt.date
    out["neighborhood"]  = out["neighborhood"].astype(str)
    out["borough"]       = out["borough"].astype(int)
    return out

# Local alias so we don't shadow the module constant via the helper.
MIN_COMP_PRICE_FALLBACK = MIN_TREND_PRICE


# ── Trend computation (vectorised by date bucket) ──────────────────────────────
#
# Algorithm (per segment):
#   1. Bucket sales by month (sale_date → year-month).
#   2. For each unique as_of_date in the spine, compute the rolling 365-day
#      median price per (borough, neighbourhood).  We use a sorted-merge join
#      rather than per-row searches.
#
# Implementation: for each (segment) slice we loop over the unique as_of_dates
# in chunks (e.g. 1 per day).  For each as_of_date D we pick the slice of
# sales with sale_date in [D−365, D) and group-by neighbourhood.  This is
# O(unique_dates * N) which for ~1000 unique dates × 30k rows = 30M ops —
# still fast since the grouping is vectorised.
#
# To keep the runtime in check we compute trends at *unique-date* granularity:
# every spine row with the same as_of_date gets the same medians.

def _trend_for_dates(
    sales: pd.DataFrame, asof_dates: list[pd.Timestamp.date]
) -> pd.DataFrame:
    """Return per-(as_of_date, borough, neighborhood) medians using current
    (D−365, D) and year-ago (D−730, D−365) windows."""
    rows: list[dict] = []
    sale_arr = sales["sale_date_dt"].to_numpy()
    price_arr = sales["sales_price"].to_numpy(dtype=float)
    nbhd_arr  = sales["neighborhood"].to_numpy()
    boro_arr  = sales["borough"].to_numpy()

    for D in asof_dates:
        cur_lo = D - timedelta(days=LOOKBACK_DAYS)
        cur_hi = D
        prv_lo = D - timedelta(days=LOOKBACK_DAYS * 2)
        prv_hi = D - timedelta(days=LOOKBACK_DAYS)

        cur_mask = (sale_arr >= cur_lo) & (sale_arr < cur_hi)
        prv_mask = (sale_arr >= prv_lo) & (sale_arr < prv_hi)

        if not cur_mask.any():
            continue

        # Group current window by (borough, neighborhood).
        cur_df = pd.DataFrame({
            "borough":      boro_arr[cur_mask],
            "neighborhood": nbhd_arr[cur_mask],
            "price":        price_arr[cur_mask],
        })
        cur_grp_nbhd = (
            cur_df.groupby(["borough", "neighborhood"])
            .agg(nbhd_median_l365=("price", "median"),
                 nbhd_sale_count_l365=("price", "size"))
            .reset_index()
        )
        cur_grp_boro = (
            cur_df.groupby(["borough"])
            .agg(borough_median_l365=("price", "median"),
                 borough_sale_count_l365=("price", "size"))
            .reset_index()
        )

        # Year-ago windows for YoY denominator.
        prv_df = pd.DataFrame({
            "borough":      boro_arr[prv_mask],
            "neighborhood": nbhd_arr[prv_mask],
            "price":        price_arr[prv_mask],
        })
        prv_grp_nbhd = (
            prv_df.groupby(["borough", "neighborhood"])
            .agg(nbhd_median_prev365=("price", "median"),
                 nbhd_count_prev365=("price", "size"))
            .reset_index()
        )
        prv_grp_boro = (
            prv_df.groupby(["borough"])
            .agg(borough_median_prev365=("price", "median"),
                 borough_count_prev365=("price", "size"))
            .reset_index()
        )

        merged = cur_grp_nbhd.merge(prv_grp_nbhd, on=["borough", "neighborhood"], how="left")
        merged = merged.merge(cur_grp_boro, on="borough", how="left")
        merged = merged.merge(prv_grp_boro, on="borough", how="left")

        # Suppress YoY where year-ago group is too thin (median noisy).
        nbhd_prev_ok = merged["nbhd_count_prev365"].fillna(0) >= MIN_GROUP_SIZE
        boro_prev_ok = merged["borough_count_prev365"].fillna(0) >= MIN_GROUP_SIZE
        merged["nbhd_yoy_growth"] = np.where(
            nbhd_prev_ok & merged["nbhd_median_prev365"].gt(0),
            merged["nbhd_median_l365"] / merged["nbhd_median_prev365"] - 1.0,
            np.nan,
        )
        merged["borough_yoy_growth"] = np.where(
            boro_prev_ok & merged["borough_median_prev365"].gt(0),
            merged["borough_median_l365"] / merged["borough_median_prev365"] - 1.0,
            np.nan,
        )

        merged["as_of_date"] = str(D)
        rows.append(merged[[
            "as_of_date", "borough", "neighborhood",
            "nbhd_median_l365", "nbhd_yoy_growth", "nbhd_sale_count_l365",
            "borough_median_l365", "borough_yoy_growth",
        ]])

    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def main() -> None:
    print(f"Reading spine: {SPINE_FILE}")
    spine = pd.read_parquet(SPINE_FILE)
    print(f"  rows: {len(spine):,}")

    blocks: list[pd.DataFrame] = []
    for cfg in COMP_SEGMENTS:
        sub = _slice_segment(spine, cfg)
        if sub.empty:
            print(f"  [skip] {cfg['name']}: 0 rows")
            continue
        sub = _prep(sub)

        # Limit to spine as_of_dates that actually appear.  We sample at unique
        # dates so all rows on the same as_of_date get the same trend snapshot.
        asof_unique = sorted(sub["as_of_date_dt"].unique())
        print(f"  [{cfg['name']}] {len(sub):,} sales, "
              f"{len(asof_unique):,} unique as_of_dates")

        block = _trend_for_dates(sub, asof_unique)
        if block.empty:
            print("    → no trend rows produced")
            continue
        block["comp_segment"] = cfg["name"]
        # Tighten dtypes for parquet.
        block["borough"] = block["borough"].astype("int64")
        print(f"    → {len(block):,} trend rows produced")
        blocks.append(block)

    if not blocks:
        print("No trend blocks built — aborting.")
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
