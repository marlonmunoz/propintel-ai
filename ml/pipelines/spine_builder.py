"""Build the canonical time-aware training spine (Gold layer).

Why this file exists
--------------------
The existing nyc_subtype_training_data.csv is sourced from the app DB, which
has no sale_date column.  Without sale_date we cannot do time-based evaluation
splits, which means we cannot guard against overfitting.  This pipeline builds
a richer spine directly from the Rolling Sales Excel files (which carry sale
date and block/lot) and applies the same residential-class and price filters
as create_subtype_training_data.py.

Output
------
ml/data/gold/training_spine_v1.parquet
    One row per sale event.
    Key columns: bbl (str), sale_date (date), as_of_date (date),
                 segment (str), sales_price (float), ...

Usage
-----
    python ml/pipelines/spine_builder.py
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR  = BASE_DIR / "ml/data/nyc_raw"
HIST_DIR = RAW_DIR / "historical"
GOLD_DIR = BASE_DIR / "ml/data/gold"
OUTPUT   = GOLD_DIR / "training_spine_v1.parquet"

# Current rolling sales (5 boroughs) -------------------------------------------------------
CURRENT_FILES = {
    1: RAW_DIR / "rollingsales_manhattan.xlsx",
    2: RAW_DIR / "rollingsales_bronx.xlsx",
    3: RAW_DIR / "rollingsales_brooklyn.xlsx",
    4: RAW_DIR / "rollingsales_queens.xlsx",
    5: RAW_DIR / "rollingsales_statenisland.xlsx",
}

# Historical annualized sales ---------------------------------------------------------------
HISTORICAL_FILES: dict[tuple[int, int], Path] = {
    (2022, 1): HIST_DIR / "2022_manhattan.xlsx",
    (2022, 2): HIST_DIR / "2022_bronx.xlsx",
    (2022, 3): HIST_DIR / "2022_brooklyn.xlsx",
    (2022, 4): HIST_DIR / "2022_queens.xlsx",
    (2022, 5): HIST_DIR / "2022_staten_island.xlsx",
    (2023, 1): HIST_DIR / "2023_manhattan.xlsx",
    (2023, 2): HIST_DIR / "2023_bronx.xlsx",
    (2023, 3): HIST_DIR / "2023_brooklyn.xlsx",
    (2023, 4): HIST_DIR / "2023_queens.xlsx",
    (2023, 5): HIST_DIR / "2023_staten_island.xlsx",
}

# Residential building-class categories to keep --------------------------------------------
RESIDENTIAL_CLASSES = {
    "01 ONE FAMILY DWELLINGS",
    "02 TWO FAMILY DWELLINGS",
    "03 THREE FAMILY DWELLINGS",
    "07 RENTALS - WALKUP APARTMENTS",
    "08 RENTALS - ELEVATOR APARTMENTS",
    "09 COOPS - WALKUP APARTMENTS",
    "10 COOPS - ELEVATOR APARTMENTS",
    "12 CONDOS - WALKUP APARTMENTS",
    "13 CONDOS - ELEVATOR APARTMENTS",
    "15 CONDOS - 2-10 UNIT RESIDENTIAL",
    "17 CONDO COOPS",
}

# Segment mapping (matches ModelRegistry in backend) ----------------------------------------
SEGMENT_MAP: dict[str, str] = {
    "01 ONE FAMILY DWELLINGS":           "one_family",
    "02 TWO FAMILY DWELLINGS":           "multi_family",
    "03 THREE FAMILY DWELLINGS":         "multi_family",
    "07 RENTALS - WALKUP APARTMENTS":    "rental_walkup",
    "08 RENTALS - ELEVATOR APARTMENTS":  "rental_elevator",
    "09 COOPS - WALKUP APARTMENTS":      "condo_coop",
    "10 COOPS - ELEVATOR APARTMENTS":    "condo_coop",
    "12 CONDOS - WALKUP APARTMENTS":     "condo_coop",
    "13 CONDOS - ELEVATOR APARTMENTS":   "condo_coop",
    "15 CONDOS - 2-10 UNIT RESIDENTIAL": "condo_coop",
    "17 CONDO COOPS":                    "condo_coop",
}

# Price floors/caps -------------------------------------------------------------------------
PRICE_FLOOR      = 1_000
GLOBAL_PRICE_CAP = 0.99        # quantile
RENTAL_FLOOR_PER_UNIT = 30_000
RENTAL_CLASS_PRICE_CAP = 0.95  # quantile per rental class


# -------------------------------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------------------------------

def _normalise_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Flatten multi-line / whitespace-heavy column names from historical files."""
    df.columns = [c.strip().replace("\n", " ").replace("  ", " ").lower() for c in df.columns]
    return df


def _col(df: pd.DataFrame, *candidates: str) -> str:
    """Return the first candidate column name that exists in df (case-insensitive)."""
    lower = {c.lower(): c for c in df.columns}
    for name in candidates:
        if name.lower() in lower:
            return lower[name.lower()]
    raise KeyError(f"None of {candidates} found in {df.columns.tolist()}")


def _build_bbl(borough: pd.Series, block: pd.Series, lot: pd.Series) -> pd.Series:
    """Construct zero-padded 10-digit BBL string: B BBBBB LLLL."""
    b  = pd.to_numeric(borough, errors="coerce").fillna(0).astype(int)
    bl = pd.to_numeric(block,   errors="coerce").fillna(0).astype(int)
    lt = pd.to_numeric(lot,     errors="coerce").fillna(0).astype(int)
    return (
        b.astype(str).str.zfill(1)
        + bl.astype(str).str.zfill(5)
        + lt.astype(str).str.zfill(4)
    )


def _load_current(borough_id: int, path: Path) -> pd.DataFrame | None:
    """Load a current rolling-sales Excel file."""
    if not path.exists():
        print(f"  [SKIP] not found: {path.name}", file=sys.stderr)
        return None
    df = pd.read_excel(path, skiprows=4)
    df = _normalise_cols(df)
    df["_source_borough"] = borough_id
    return df


def _load_historical(year: int, borough_id: int, path: Path) -> pd.DataFrame | None:
    """Load a historical rolling-sales Excel file (different header row)."""
    if not path.exists():
        print(f"  [SKIP] not found: {path.name}", file=sys.stderr)
        return None
    df = pd.read_excel(path, skiprows=6)
    df = _normalise_cols(df)
    df["_source_borough"] = borough_id
    df["_source_year"]    = year
    return df


def _standardise(df: pd.DataFrame) -> pd.DataFrame:
    """Rename heterogeneous column names to a uniform schema."""
    renames = {}

    # Building class category
    for raw in ("building class category", "building class category"):
        if raw in df.columns:
            renames[raw] = "building_class"
            break

    # Sale price
    for raw in ("sale price", "sale\nprice"):
        if raw in df.columns:
            renames[raw] = "sales_price"
            break

    # Sale date
    for raw in ("sale date", "sale\ndate"):
        if raw in df.columns:
            renames[raw] = "sale_date"
            break

    # Year built
    for raw in ("year built", "year\nbuilt"):
        if raw in df.columns:
            renames[raw] = "year_built"
            break

    # Units
    for raw in ("residential units", "residential\nunits", "residential \nunits"):
        if raw in df.columns:
            renames[raw] = "residential_units"
            break
    for raw in ("total units", "total \nunits", "total\nunits"):
        if raw in df.columns:
            renames[raw] = "total_units"
            break

    # sqft
    for raw in ("gross square feet", "gross \nsquare feet", "gross\nsquare feet"):
        if raw in df.columns:
            renames[raw] = "gross_sqft"
            break
    for raw in ("land square feet", "land \nsquare feet", "land\nsquare feet"):
        if raw in df.columns:
            renames[raw] = "land_sqft"
            break

    # easement (varies)
    for raw in ("easement", "ease-ment"):
        if raw in df.columns:
            renames[raw] = "easement"
            break

    # borough label → keep raw column, use _source_borough for numeric borough id
    if "borough" in df.columns:
        renames["borough"] = "borough_label"

    df = df.rename(columns=renames)
    return df


# -------------------------------------------------------------------------------------------
# Pipeline
# -------------------------------------------------------------------------------------------

def load_all_sales() -> pd.DataFrame:
    chunks: list[pd.DataFrame] = []

    print("Loading current rolling sales …")
    for bid, path in CURRENT_FILES.items():
        raw = _load_current(bid, path)
        if raw is not None:
            raw = _standardise(raw)
            raw["_file_type"] = "current"
            chunks.append(raw)

    print("Loading historical rolling sales …")
    for (yr, bid), path in HISTORICAL_FILES.items():
        raw = _load_historical(yr, bid, path)
        if raw is not None:
            raw = _standardise(raw)
            raw["_file_type"] = "historical"
            chunks.append(raw)

    df = pd.concat(chunks, ignore_index=True)
    print(f"  Combined raw rows: {len(df):,}")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    # ── Types ──────────────────────────────────────────────────────────────────
    df["sales_price"]       = pd.to_numeric(df["sales_price"],       errors="coerce")
    df["year_built"]        = pd.to_numeric(df["year_built"],        errors="coerce")
    df["gross_sqft"]        = pd.to_numeric(df.get("gross_sqft"),     errors="coerce")
    df["land_sqft"]         = pd.to_numeric(df.get("land_sqft"),      errors="coerce")
    df["total_units"]       = pd.to_numeric(df.get("total_units"),    errors="coerce")
    df["residential_units"] = pd.to_numeric(df.get("residential_units"), errors="coerce")
    df["sale_date"]         = pd.to_datetime(df["sale_date"],         errors="coerce")

    # ── Normalise building class string ────────────────────────────────────────
    df["building_class"] = df["building_class"].astype(str).str.strip().str.upper()

    # ── Residential filter ─────────────────────────────────────────────────────
    before = len(df)
    df = df[df["building_class"].isin(RESIDENTIAL_CLASSES)].copy()
    print(f"  Residential filter: {before:,} → {len(df):,}")

    # ── Price / date validity ──────────────────────────────────────────────────
    df = df[df["sales_price"].notna() & (df["sales_price"] >= PRICE_FLOOR)]
    df = df[df["sale_date"].notna()]
    df = df[df["year_built"].notna() & (df["year_built"] >= 1800) & (df["year_built"] <= 2026)]
    print(f"  After date/price/year filters: {len(df):,}")

    # ── Global 99th-pct cap ────────────────────────────────────────────────────
    p99 = df["sales_price"].quantile(GLOBAL_PRICE_CAP)
    df = df[df["sales_price"] <= p99]
    print(f"  After global 99th-pct cap ({p99:,.0f}): {len(df):,}")

    # ── Rental-specific filters ────────────────────────────────────────────────
    RENTAL_CLASSES = {
        "07 RENTALS - WALKUP APARTMENTS",
        "08 RENTALS - ELEVATOR APARTMENTS",
    }
    rental_mask = df["building_class"].isin(RENTAL_CLASSES)
    if rental_mask.any():
        non_rental = df[~rental_mask].copy()
        rental     = df[rental_mask].copy()

        rental["_ppu"] = rental["sales_price"] / rental["total_units"].clip(lower=1)
        rental = rental[rental["_ppu"] >= RENTAL_FLOOR_PER_UNIT].drop(columns=["_ppu"])

        capped = []
        for bc in rental["building_class"].unique():
            bc_rows = rental[rental["building_class"] == bc]
            p95 = bc_rows["sales_price"].quantile(RENTAL_CLASS_PRICE_CAP)
            capped.append(bc_rows[bc_rows["sales_price"] <= p95])
        rental = pd.concat(capped).reset_index(drop=True) if capped else rental

        df = pd.concat([non_rental, rental]).reset_index(drop=True)
        print(f"  After rental-specific filters: {len(df):,}")

    return df


def build_keys(df: pd.DataFrame) -> pd.DataFrame:
    """Add BBL, as_of_date, segment, borrow numeric borough from _source_borough."""
    df["borough"]   = df["_source_borough"].astype(int)
    df["block"]     = pd.to_numeric(df.get("block", np.nan), errors="coerce").fillna(0).astype(int)
    df["lot"]       = pd.to_numeric(df.get("lot",   np.nan), errors="coerce").fillna(0).astype(int)
    df["bbl"]       = _build_bbl(df["borough"], df["block"], df["lot"])
    df["as_of_date"]= (df["sale_date"] - pd.Timedelta(days=1)).dt.date
    df["sale_date"] = df["sale_date"].dt.date
    df["segment"]   = df["building_class"].map(SEGMENT_MAP).fillna("global")
    return df


def dedup(df: pd.DataFrame) -> pd.DataFrame:
    """Remove duplicate (bbl, sale_date, sales_price) triples across file overlaps."""
    before = len(df)
    df = df.drop_duplicates(subset=["bbl", "sale_date", "sales_price"]).reset_index(drop=True)
    print(f"  Dedup: {before:,} → {len(df):,}")
    return df


def select_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    keep = [
        "bbl", "sale_date", "as_of_date",
        "borough", "block", "lot",
        "neighborhood", "building_class", "segment",
        "year_built", "sales_price",
        "gross_sqft", "land_sqft",
        "total_units", "residential_units",
        "_file_type",
    ]
    # Optional columns — keep if present
    optional = ["zip code", "address", "borough_label"]
    for col in optional:
        if col in df.columns:
            keep.append(col)
    return df[[c for c in keep if c in df.columns]].copy()


def main() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    df = load_all_sales()
    df = clean(df)
    df = build_keys(df)
    df = dedup(df)
    df = select_output_columns(df)

    # Sort by sale_date for time-split consistency
    df = df.sort_values("sale_date").reset_index(drop=True)

    df.to_parquet(OUTPUT, index=False)
    print(f"\n✅  Spine saved → {OUTPUT}")
    print(f"   Rows: {len(df):,}")
    print(f"   Date range: {df['sale_date'].min()} → {df['sale_date'].max()}")
    print("\nSegment distribution:")
    print(df["segment"].value_counts().to_string())


if __name__ == "__main__":
    main()
