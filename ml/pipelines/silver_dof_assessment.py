"""Silver normalizer: DOF Property Valuation & Assessment (Tax Classes 1-2-3-4).

Input  : ml/data/external/dof_property_valuation_assessment/
         property_valuation_assessment_tax_classes_1234.csv
Output : ml/data/silver/dof_assessment/silver_dof_assessment.parquet

What this script does
---------------------
1. Reads the raw DOF assessment CSV (one row per BBL per tax year).
2. Casts types, normalises column names to snake_case.
3. Builds a 10-digit BBL from boro / block / lot (same formula used in the
   training spine so joins are key-consistent).
4. Parses appt_date where present.
5. Drops rows that cannot form a valid BBL.
6. Keeps only the columns relevant for feature engineering and writes Parquet.

Run from repo root:
    python ml/pipelines/silver_dof_assessment.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
RAW_FILE = (
    BASE
    / "ml/data/external/dof_property_valuation_assessment"
    / "property_valuation_assessment_tax_classes_1234.csv"
)
OUT_DIR = BASE / "ml/data/silver/dof_assessment"
OUT_FILE = OUT_DIR / "silver_dof_assessment.parquet"

# Columns we keep from the raw file (+ boro/block/lot used to build bbl).
KEEP_COLS = [
    # identifiers
    "boro", "block", "lot",
    "year",          # tax year (e.g. 2024)
    "period",        # "TENTATIVE", "ACTUAL", "FINAL"
    # building characteristics
    "bldg_class",
    "gross_sqft",
    "units",
    "num_bldgs",
    "yrbuilt",
    "bld_story",
    # assessed / market values — current roll
    "curacttot",     # current actual total
    "curactland",    # current actual land
    "curmkttot",     # current market total
    "curmktland",    # current market land
    "curtaxclass",
    # exemptions — current roll
    "curtrnextot",   # current transitional exemption total
    "curtxbtot",     # current taxable total
    # misc
    "appt_date",
    "owner",
    "zip_code",
]


def _to_int64(s: pd.Series) -> pd.Series:
    """Safely convert a numeric-ish series (may contain NaN) to nullable Int64."""
    s = pd.to_numeric(s, errors="coerce")
    mask = s.isna()
    out = s.fillna(0).round(0).astype(int).astype("Int64")
    out[mask] = pd.NA
    return out


def _build_bbl(boro: pd.Series, block: pd.Series, lot: pd.Series) -> pd.Series:
    return (
        _to_int64(boro) * 1_000_000_000
        + _to_int64(block) * 10_000
        + _to_int64(lot)
    ).astype("Int64")


def load_raw() -> pd.DataFrame:
    print(f"Reading {RAW_FILE} …")
    # Identify which keep-cols actually exist in the file.
    header = pd.read_csv(RAW_FILE, nrows=0).columns.tolist()
    usecols = [c for c in KEEP_COLS if c in header]
    missing = set(KEEP_COLS) - set(usecols)
    if missing:
        print(f"  [warn] cols absent in raw file, skipped: {sorted(missing)}")

    df = pd.read_csv(RAW_FILE, usecols=usecols, low_memory=False)
    print(f"  Loaded {len(df):,} rows × {len(df.columns)} cols")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    # ── types ──────────────────────────────────────────────────────────────
    int_cols = ["boro", "block", "lot", "year", "units", "num_bldgs",
                "yrbuilt", "bld_story",
                "curacttot", "curactland", "curmkttot", "curmktland",
                "curtrnextot", "curtxbtot"]
    for c in int_cols:
        if c in df.columns:
            df[c] = _to_int64(df[c])

    float_cols = ["gross_sqft", "zip_code"]
    for c in float_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if "appt_date" in df.columns:
        df["appt_date"] = pd.to_datetime(df["appt_date"], errors="coerce")

    # ── normalise strings ──────────────────────────────────────────────────
    for c in ["bldg_class", "period", "owner"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip().str.upper()
            df[c] = df[c].replace("NAN", np.nan)

    # ── BBL ────────────────────────────────────────────────────────────────
    required = {"boro", "block", "lot"}
    if required.issubset(df.columns):
        df["bbl"] = _build_bbl(df["boro"], df["block"], df["lot"])
    else:
        raise ValueError(f"Missing BBL key columns: {required - set(df.columns)}")

    # Drop rows where BBL cannot be formed (null boro / block / lot).
    before = len(df)
    df = df.dropna(subset=["bbl"]).reset_index(drop=True)
    dropped = before - len(df)
    if dropped:
        print(f"  Dropped {dropped:,} rows with null BBL keys")

    return df


def select_output(df: pd.DataFrame) -> pd.DataFrame:
    ordered = [
        "bbl", "boro", "block", "lot", "year", "period",
        "bldg_class", "gross_sqft", "units", "num_bldgs", "yrbuilt", "bld_story",
        "curacttot", "curactland", "curmkttot", "curmktland", "curtaxclass",
        "curtrnextot", "curtxbtot",
        "appt_date", "owner", "zip_code",
    ]
    cols = [c for c in ordered if c in df.columns]
    return df[cols]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_raw()
    df = clean(df)
    df = select_output(df)

    df.to_parquet(OUT_FILE, index=False)

    print(f"\n✅  Silver DOF assessment saved → {OUT_FILE}")
    print(f"   Rows  : {len(df):,}")
    print(f"   Cols  : {df.columns.tolist()}")
    print(f"   Years : {sorted(df['year'].dropna().unique().tolist())[:5]} … "
          f"{sorted(df['year'].dropna().unique().tolist())[-3:]}")
    print(f"   BBLs  : {df['bbl'].nunique():,} unique")


if __name__ == "__main__":
    main()
