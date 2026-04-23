"""Silver normalizer: J-51 Exemption and Abatement (Historical).

Input  : ml/data/external/j51_exemption_abatement_historical/
         j51_exemption_abatement_historical.csv
Output : ml/data/silver/j51/silver_j51.parquet

What this script does
---------------------
1. Reads the raw J-51 CSV (~4.2 M rows, tax years up to 2018).
2. Normalises column names to snake_case.
3. Builds a 10-digit BBL from Borough Code / BLOCK / LOT.
4. Casts financial / numeric columns to appropriate types.
5. Drops rows with invalid BBL keys or null tax_year.
6. Writes a compact Parquet file for downstream Gold builders.

Run from repo root:
    python ml/pipelines/silver_j51.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
RAW_FILE = (
    BASE
    / "ml/data/external/j51_exemption_abatement_historical"
    / "j51_exemption_abatement_historical.csv"
)
OUT_DIR  = BASE / "ml/data/silver/j51"
OUT_FILE = OUT_DIR / "silver_j51.parquet"

# Raw → normalised column name map.
RENAME = {
    "Borough Code": "boro",
    "BLOCK":        "block",
    "LOT":          "lot",
    "Easement":     "easement",
    "INIT_YEAR":    "init_year",
    "QTR":          "init_quarter",
    "EX_YEARS":     "exempt_years",
    "AB_PCT":       "abate_pct",
    "TAX_YEAR":     "tax_year",
    "EXEMPT_AMT":   "exempt_amt",
    "COST_OF_ALT":  "cost_of_alt",
    "ABATE_GRANT":  "abate_grant",
    "AMT_REMAIN":   "amt_remain",
    "TOTAL_TAX":    "total_tax",
    "ABATEMENT":    "abatement",
}


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
    df = pd.read_csv(RAW_FILE, low_memory=False)
    print(f"  Loaded {len(df):,} rows × {len(df.columns)} cols")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    # ── rename ─────────────────────────────────────────────────────────────
    df = df.rename(columns={k: v for k, v in RENAME.items() if k in df.columns})

    # ── types ──────────────────────────────────────────────────────────────
    int_cols = ["boro", "block", "lot", "init_year", "exempt_years",
                "abate_pct", "tax_year"]
    for c in int_cols:
        if c in df.columns:
            df[c] = _to_int64(df[c])

    float_cols = ["init_quarter", "exempt_amt", "cost_of_alt",
                  "abate_grant", "amt_remain", "total_tax", "abatement"]
    for c in float_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # ── BBL ────────────────────────────────────────────────────────────────
    df["bbl"] = _build_bbl(df["boro"], df["block"], df["lot"])

    # ── drop unresolvable rows ─────────────────────────────────────────────
    before = len(df)
    df = df.dropna(subset=["bbl", "tax_year"]).reset_index(drop=True)
    dropped = before - len(df)
    if dropped:
        print(f"  Dropped {dropped:,} rows with null bbl or tax_year")

    # ── derived: year of J-51 expiry ───────────────────────────────────────
    if "init_year" in df.columns and "exempt_years" in df.columns:
        df["expiry_year"] = (df["init_year"] + df["exempt_years"]).astype("Int64")

    return df


def select_output(df: pd.DataFrame) -> pd.DataFrame:
    ordered = [
        "bbl", "boro", "block", "lot",
        "tax_year", "init_year", "init_quarter", "exempt_years", "expiry_year",
        "abate_pct", "exempt_amt", "cost_of_alt",
        "abate_grant", "amt_remain", "total_tax", "abatement",
    ]
    cols = [c for c in ordered if c in df.columns]
    return df[cols]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_raw()
    df = clean(df)
    df = select_output(df)

    df.to_parquet(OUT_FILE, index=False)

    print(f"\n✅  Silver J-51 saved → {OUT_FILE}")
    print(f"   Rows     : {len(df):,}")
    print(f"   BBLs     : {df['bbl'].nunique():,} unique")
    print(f"   Tax years: {int(df['tax_year'].min())} – {int(df['tax_year'].max())}")
    print(f"   Cols     : {df.columns.tolist()}")


if __name__ == "__main__":
    main()
