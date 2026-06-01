"""Gold builder: DOF condo unit-level structural features (PROPMAST).

Input  : ml/data/silver/dof_condo_units/silver_dof_condo_units.parquet
         ml/data/gold/training_spine_v1.parquet  (provides bbl + segment)
Output : ml/data/gold/gold_dof_condo_units.parquet

What this adds
--------------
These are time-invariant physical attributes extracted from a single DOF
PROPMAST roll snapshot for every condo unit lot (lot 1001-6999):

  condo_gross_sqft   — net interior area of the unit (sqft)
  condo_comint_land  — unit's land common-interest % in the condo complex
  condo_comint_bldg  — unit's building common-interest % in the condo complex
  condo_yrbuilt      — year the building was constructed (falls back to DOF
                       roll value when PROPMAST is blank)
  condo_apt_no       — apartment identifier (e.g. "4A", "PHB"); kept for
                       diagnostics / debugging, not used as a model feature

Why no as-of filtering
-----------------------
Unlike assessed values (which change every fiscal year and must be time-gated),
structural unit attributes — floor area and percentage ownership — are set in
the condo declaration at recording time and only change if the unit is
physically altered or legally re-apportioned (rare).  Using a single roll
snapshot for all training rows does not leak future information because the
values reflect the building's physical reality, not its assessed worth.

Why the join is BBL-only
------------------------
The silver table has exactly one row per unit-lot BBL (one snapshot).  Each
spine row that is a condo unit sale has exactly one BBL.  A simple left join
on BBL is correct and produces no fan-out.

Run from repo root:
    python ml/pipelines/gold_dof_condo_units.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

BASE        = Path(__file__).resolve().parents[2]
SILVER_FILE = BASE / "ml/data/silver/dof_condo_units/silver_dof_condo_units.parquet"
SPINE_FILE  = BASE / "ml/data/gold/training_spine_v1.parquet"
OUT_DIR     = BASE / "ml/data/gold"
OUT_FILE    = OUT_DIR / "gold_dof_condo_units.parquet"

# Columns to carry into Gold (exclude apt_no from features — it is
# high-cardinality and leaks unit identity without adding generalizable signal).
FEATURE_COLS = [
    "condo_gross_sqft",
    "condo_comint_land",
    "condo_comint_bldg",
    "condo_yrbuilt",
    "condo_apt_no",   # diagnostic only; train_spine_models.py does not add this to features
]


def main() -> None:
    if not SILVER_FILE.exists():
        raise SystemExit(
            f"Silver file not found: {SILVER_FILE}\n"
            "Run ml/pipelines/silver_dof_condo_units.py first."
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading silver DOF condo units …")
    silver = pd.read_parquet(SILVER_FILE)
    silver["bbl"] = silver["bbl"].astype(str).str.strip()
    print(f"  {len(silver):,} unit lots, {silver['bbl'].nunique():,} unique BBLs")

    # Sanity: one row per BBL (already deduped in the silver parser, but confirm).
    before = len(silver)
    silver = silver.drop_duplicates(subset="bbl").reset_index(drop=True)
    if before != len(silver):
        print(f"  [warn] dropped {before - len(silver):,} duplicate BBLs")

    print("Loading spine (for coverage stats) …")
    spine = pd.read_parquet(SPINE_FILE, columns=["bbl", "segment"])
    spine["bbl"] = spine["bbl"].astype(str).str.strip()

    # Build the gold table: silver columns keyed on BBL, ready for a left join.
    gold = silver[["bbl"] + FEATURE_COLS].copy()

    gold.to_parquet(OUT_FILE, index=False)

    print(f"\n✅  Gold DOF condo units saved → {OUT_FILE}")
    print(f"   Rows : {len(gold):,}")
    print(f"   Cols : {gold.columns.tolist()}")

    # Coverage stats against the condo_coop spine rows (spine uses the pooled label).
    condo_sales = spine[spine["segment"] == "condo_coop"]
    gold_bbls   = set(gold["bbl"])
    n_matched   = condo_sales["bbl"].isin(gold_bbls).sum()
    pct_matched = n_matched / max(len(condo_sales), 1) * 100
    print(f"\nCoverage: {pct_matched:.1f}% of condo_coop spine rows matched "
          f"({n_matched:,} / {len(condo_sales):,})")

    print("\nFeature non-null rates (all gold rows):")
    for c in FEATURE_COLS:
        pct = gold[c].notna().mean() * 100
        print(f"   {c:<22} {pct:5.1f}%")

    print("\nSample condo_gross_sqft quantiles:")
    sq = gold["condo_gross_sqft"].dropna()
    if len(sq):
        print(f"   p10={sq.quantile(.10):,.0f}  p25={sq.quantile(.25):,.0f}  "
              f"p50={sq.quantile(.50):,.0f}  p75={sq.quantile(.75):,.0f}  "
              f"p90={sq.quantile(.90):,.0f}")


if __name__ == "__main__":
    main()
