"""Gold builder: DOF Assessment features (as-of safe).

Input  : ml/data/silver/dof_assessment/silver_dof_assessment.parquet
         ml/data/gold/training_spine_v1.parquet  (provides bbl + as_of_date)
Output : ml/data/gold/gold_dof_assessment_asof.parquet

As-of contract
--------------
Every feature value attached to a spine row (bbl, as_of_date) comes from the
most recent DOF tax roll whose `year` is STRICTLY BEFORE the spine's
`as_of_date` (i.e. the roll was published before the sale was recorded).
The DOF rolls are annual; `year` here is the tax year (e.g. 2024 → roll
published mid-2023).  We conservatively assume a roll for year Y is available
as of Y-01-01 (first day of the assessment year).

No future data leaks into the training set.

Run from repo root:
    python ml/pipelines/gold_dof_assessment_asof.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
SILVER_FILE = BASE / "ml/data/silver/dof_assessment/silver_dof_assessment.parquet"
SPINE_FILE  = BASE / "ml/data/gold/training_spine_v1.parquet"
OUT_DIR     = BASE / "ml/data/gold"
OUT_FILE    = OUT_DIR / "gold_dof_assessment_asof.parquet"

# Feature columns to carry forward into Gold.
def _norm_bbl(s: pd.Series) -> pd.Series:
    """Return BBL as a plain string, dropping null rows (marks them NaN)."""
    out = s.astype("Int64").astype(str)
    out = out.where(out != "<NA>", other=pd.NA)
    return out


FEATURE_COLS = [
    "curacttot",      # current actual assessed value (total)
    "curactland",     # current actual assessed value (land)
    "curmkttot",      # current market value (total)
    "curmktland",     # current market value (land)
    "gross_sqft",
    "units",
    "num_bldgs",
    "yrbuilt",
    "bld_story",
    "bldg_class",     # kept as categorical label
    "curtaxclass",
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── load inputs ────────────────────────────────────────────────────────
    print("Loading silver DOF assessment …")
    dof = pd.read_parquet(SILVER_FILE, columns=["bbl", "year"] + FEATURE_COLS)
    dof["bbl"] = _norm_bbl(dof["bbl"])
    dof = dof.dropna(subset=["bbl"])
    print(f"  {len(dof):,} rows, {dof['bbl'].nunique():,} unique BBLs")

    print("Loading training spine …")
    spine = pd.read_parquet(SPINE_FILE, columns=["bbl", "as_of_date", "sale_date"])
    print(f"  {len(spine):,} spine rows")

    # ── as-of join ─────────────────────────────────────────────────────────
    # Assumption: DOF roll for `year` Y is available starting Y-01-01.
    dof["roll_available_date"] = pd.to_datetime(
        dof["year"].astype(str) + "-01-01", errors="coerce"
    ).dt.date

    spine["as_of_date"] = pd.to_datetime(spine["as_of_date"]).dt.date

    # We want: for each (bbl, as_of_date) in spine, the row in dof where
    #   dof.bbl == spine.bbl  AND  dof.roll_available_date <= spine.as_of_date
    #   picking the LATEST such roll (max year).

    # Efficient approach: merge all bbl/year combos, then filter + keep latest.
    print("Joining spine ← DOF (as-of) …")

    # Step 1: left merge on bbl only.
    merged = spine.merge(
        dof[["bbl", "year", "roll_available_date"] + FEATURE_COLS],
        on="bbl",
        how="left",
    )

    # Step 2: apply as-of filter — keep only rolls available before as_of_date.
    merged = merged[
        merged["roll_available_date"].notna()
        & (merged["roll_available_date"] <= merged["as_of_date"])
    ]

    # Step 3: for each spine row keep the latest roll.
    merged = (
        merged
        .sort_values("year", ascending=False)
        .drop_duplicates(subset=["bbl", "as_of_date"])
        .reset_index(drop=True)
    )

    # Step 4: left-join back to spine to keep all spine rows (NaN if no DOF match).
    gold = spine.merge(
        merged.drop(columns=["sale_date"]),
        on=["bbl", "as_of_date"],
        how="left",
    )

    print(f"  Gold rows      : {len(gold):,}")
    print(f"  Spine rows matched: {gold['year'].notna().sum():,} "
          f"({gold['year'].notna().mean()*100:.1f}%)")
    print(f"  Spine rows unmatched (no DOF data available): "
          f"{gold['year'].isna().sum():,}")

    # Rename to make the feature source explicit.
    gold = gold.rename(columns={
        "year":        "dof_tax_year",
        "bldg_class":  "dof_bldg_class",
        "curtaxclass": "dof_tax_class",
    })

    # Drop helper columns not needed downstream.
    gold = gold.drop(columns=["roll_available_date"], errors="ignore")

    gold.to_parquet(OUT_FILE, index=False)

    print(f"\n✅  Gold DOF assessment saved → {OUT_FILE}")
    print(f"   Rows : {len(gold):,}")
    print(f"   Cols : {gold.columns.tolist()}")
    print(f"\nFeature null rates:")
    feat_cols = [c for c in gold.columns if c not in ("bbl", "as_of_date", "sale_date")]
    for c in feat_cols:
        pct = gold[c].isna().mean() * 100
        print(f"   {c:<25} {pct:.1f}% null")


if __name__ == "__main__":
    main()
