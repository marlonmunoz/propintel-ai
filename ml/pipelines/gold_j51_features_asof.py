"""Gold builder: J-51 Exemption/Abatement features (as-of safe).

Input  : ml/data/silver/j51/silver_j51.parquet
         ml/data/gold/training_spine_v1.parquet  (provides bbl + as_of_date)
Output : ml/data/gold/gold_j51_features_asof.parquet

As-of contract
--------------
A J-51 record for (bbl, tax_year) is considered available as-of Y-01-01
for that tax year.  We only use records whose `tax_year` < the spine's
`as_of_date`.year, ensuring no future exemption data leaks into training.

Features produced (all computed relative to as_of_date)
--------------------------------------------------------
j51_active_flag      : 1 if BBL had an active J-51 exemption at as_of_date
                       (i.e. expiry_year >= as_of_date.year AND tax_year < as_of_year)
j51_last_tax_year    : most recent tax year with a J-51 record before as_of_date
j51_last_abate_amt   : abatement amount in most recent J-51 record
j51_last_exempt_amt  : exempt amount in most recent J-51 record
j51_last_expiry_year : expiry year of the most recent J-51 grant
j51_init_year        : initial year J-51 was granted (earliest record for BBL)
j51_total_abatement  : cumulative abatement received before as_of_date

Run from repo root:
    python ml/pipelines/gold_j51_features_asof.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]


def _norm_bbl(s: pd.Series) -> pd.Series:
    """Return BBL as a plain string, compatible with spine's str BBL dtype."""
    out = s.astype("Int64").astype(str)
    return out.where(out != "<NA>", other=pd.NA)
SILVER_FILE = BASE / "ml/data/silver/j51/silver_j51.parquet"
SPINE_FILE  = BASE / "ml/data/gold/training_spine_v1.parquet"
OUT_DIR     = BASE / "ml/data/gold"
OUT_FILE    = OUT_DIR / "gold_j51_features_asof.parquet"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── load ────────────────────────────────────────────────────────────────
    print("Loading silver J-51 …")
    j51 = pd.read_parquet(SILVER_FILE)
    j51["bbl"] = _norm_bbl(j51["bbl"])
    j51 = j51.dropna(subset=["bbl"])
    print(f"  {len(j51):,} rows, {j51['bbl'].nunique():,} unique BBLs")

    print("Loading training spine …")
    spine = pd.read_parquet(SPINE_FILE, columns=["bbl", "as_of_date", "sale_date"])
    spine["as_of_date"] = pd.to_datetime(spine["as_of_date"]).dt.date
    spine["as_of_year"] = pd.to_datetime(spine["as_of_date"]).dt.year
    print(f"  {len(spine):,} spine rows")

    # Cast J-51 int columns to plain int (needed for comparisons).
    for c in ["tax_year", "init_year", "expiry_year"]:
        if c in j51.columns:
            j51[c] = pd.to_numeric(j51[c], errors="coerce")

    # Restrict J-51 to spine BBLs (perf).
    spine_bbls = set(spine["bbl"].dropna().unique())
    j51 = j51[j51["bbl"].isin(spine_bbls)].copy()
    print(f"  J-51 rows after BBL filter: {len(j51):,}")

    # ── as-of join ──────────────────────────────────────────────────────────
    # Merge all (bbl, tax_year) to (bbl, as_of_year) then filter.
    print("Joining spine ← J-51 (as-of) …")
    merged = spine[["bbl", "as_of_date", "as_of_year"]].merge(
        j51, on="bbl", how="left"
    )

    # As-of filter: only use J-51 records for tax_year < as_of_year.
    merged = merged[
        merged["tax_year"].notna()
        & (merged["tax_year"] < merged["as_of_year"])
    ]

    # ── aggregate features ──────────────────────────────────────────────────

    # Most recent J-51 record per spine row.
    latest = (
        merged.sort_values("tax_year", ascending=False)
        .drop_duplicates(subset=["bbl", "as_of_date"])
        [["bbl", "as_of_date", "tax_year", "abatement",
          "exempt_amt", "expiry_year", "init_year"]]
        .rename(columns={
            "tax_year":    "j51_last_tax_year",
            "abatement":   "j51_last_abate_amt",
            "exempt_amt":  "j51_last_exempt_amt",
            "expiry_year": "j51_last_expiry_year",
            "init_year":   "j51_init_year",
        })
    )

    # Cumulative abatement.
    cum_abate = (
        merged.groupby(["bbl", "as_of_date"])["abatement"]
        .sum()
        .rename("j51_total_abatement")
        .reset_index()
    )

    # Earliest grant year.
    earliest = (
        merged.groupby(["bbl", "as_of_date"])["init_year"]
        .min()
        .rename("j51_earliest_init_year")
        .reset_index()
    )

    # ── assemble gold ───────────────────────────────────────────────────────
    gold = spine.copy()
    gold = gold.merge(latest,      on=["bbl", "as_of_date"], how="left")
    gold = gold.merge(cum_abate,   on=["bbl", "as_of_date"], how="left")
    gold = gold.merge(earliest,    on=["bbl", "as_of_date"], how="left")

    # Active flag: expiry_year >= as_of_year.
    gold["j51_active_flag"] = (
        gold["j51_last_expiry_year"].notna()
        & (gold["j51_last_expiry_year"] >= gold["as_of_year"])
    ).astype("Int64")
    gold.loc[gold["j51_last_expiry_year"].isna(), "j51_active_flag"] = pd.NA

    # Clean up helper column.
    gold = gold.drop(columns=["as_of_year"], errors="ignore")

    gold.to_parquet(OUT_FILE, index=False)

    print(f"\n✅  Gold J-51 features saved → {OUT_FILE}")
    print(f"   Rows : {len(gold):,}")
    feat_cols = [c for c in gold.columns if c.startswith("j51_")]
    print(f"   Feature columns: {feat_cols}")
    print(f"\nFeature null rates (nulls = no J-51 record for this BBL):")
    for c in feat_cols:
        pct = gold[c].isna().mean() * 100
        print(f"   {c:<35} {pct:.1f}% null")
    if "j51_active_flag" in gold.columns:
        active_pct = (gold["j51_active_flag"] == 1).mean() * 100
        print(f"\n   Active J-51 records in spine: {active_pct:.1f}%")


if __name__ == "__main__":
    main()
