"""Build enriched condo/co-op training data from raw sources.

Pipeline:
  1. Load NYC Rolling Sales Excel files (classes 09, 10, 12, 13, 15, 17).
  2. Construct BBL (borough-block-lot identifier).
  3. Join with PLUTO → latitude, longitude, building area, residential units,
     total assessment.
  4. Compute building-level approximations:
       sqft_per_unit   = bldgarea / unitsres   (avg unit size)
       assess_per_unit = assesstot / unitsres   (tax assessment per unit)
  5. Apply standard price and location quality filters.
  6. Save to ml/data/processed/nyc_condo_training_data.csv.

This file is consumed by train_subtype_models.py when the
INPUT_FILE_CONDO path exists. It replaces the DB-dependent
create_subtype_training_data.py for condo_coop model training and
adds sqft_per_unit as the primary size signal (individual unit sqft
is not recorded in NYC rolling sales for co-ops or condos, so we
use the building average from PLUTO as a proxy).

Run from the project root:
    python ml/pipelines/create_condo_training_data.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR   = BASE_DIR / "ml/data/nyc_raw"
PLUTO_CSV = BASE_DIR / "ml/data/pluto_raw/pluto.csv"
OUTPUT    = BASE_DIR / "ml/data/processed/nyc_condo_training_data.csv"

CONDO_CLASSES = {
    "09 COOPS - WALKUP APARTMENTS",
    "10 COOPS - ELEVATOR APARTMENTS",
    "12 CONDOS - WALKUP APARTMENTS",
    "13 CONDOS - ELEVATOR APARTMENTS",
    "15 CONDOS - 2-10 UNIT RESIDENTIAL",
    "17 CONDO COOPS",
}

BOROUGH_FILES = {
    1: "rollingsales_manhattan.xlsx",
    2: "rollingsales_bronx.xlsx",
    3: "rollingsales_brooklyn.xlsx",
    4: "rollingsales_queens.xlsx",
    5: "rollingsales_statenisland.xlsx",
}


def load_rolling_sales() -> pd.DataFrame:
    dfs = []
    for borocode, filename in BOROUGH_FILES.items():
        path = RAW_DIR / filename
        df = pd.read_excel(path, skiprows=4)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        df["borocode"] = borocode
        dfs.append(df)
    raw = pd.concat(dfs, ignore_index=True)

    col_map = {
        "building_class_category": "building_class",
        "sale_price":              "sales_price",
        "gross_square_feet":       "gross_sqft",
        "land_square_feet":        "land_sqft",
        "zip_code":                "zipcode",
    }
    raw = raw.rename(columns={k: v for k, v in col_map.items() if k in raw.columns})

    raw = raw[raw["building_class"].isin(CONDO_CLASSES)].copy()
    print(f"Condo/co-op rows from rolling sales: {len(raw)}")
    print(raw["building_class"].value_counts().to_string())
    return raw


def construct_bbl(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["block"] = pd.to_numeric(df["block"], errors="coerce")
    df["lot"]   = pd.to_numeric(df["lot"],   errors="coerce")
    valid = df["block"].notna() & df["lot"].notna() & df["borocode"].notna()
    df = df[valid].copy()
    df["bbl"] = (
        df["borocode"].astype(np.int64) * 1_000_000_000
        + df["block"].astype(np.int64) * 10_000
        + df["lot"].astype(np.int64)
    )
    return df


def load_pluto_lookup() -> pd.DataFrame:
    cols = ["BBL", "latitude", "longitude", "unitsres", "unitstotal", "bldgarea", "assesstot"]
    pluto = pd.read_csv(PLUTO_CSV, usecols=cols, low_memory=False)
    pluto = pluto.rename(columns={"BBL": "bbl"})
    pluto["bbl"] = pd.to_numeric(pluto["bbl"], errors="coerce")
    for col in ["latitude", "longitude", "unitsres", "unitstotal", "bldgarea", "assesstot"]:
        pluto[col] = pd.to_numeric(pluto[col], errors="coerce")
    pluto = pluto.dropna(subset=["bbl", "latitude", "longitude"])
    pluto = pluto.drop_duplicates(subset=["bbl"])
    print(f"\nPLUTO lookup loaded: {len(pluto):,} unique BBLs")
    return pluto


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    numeric_cols = ["sales_price", "year_built", "latitude", "longitude"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    before = len(df)
    df = df[df["sales_price"] > 10_000]   # Individual unit sales; $10K floor
    df = df[df["year_built"].notna() & df["year_built"].between(1800, 2025)]
    df = df[df["latitude"].notna() & df["longitude"].notna()]
    print(f"After basic filters: {before} → {len(df)} rows")

    # Global 99th-pct price cap
    p99 = df["sales_price"].quantile(0.99)
    df = df[df["sales_price"] <= p99]
    print(f"After 99th pct price cap (≤ ${p99:,.0f}): {len(df)} rows")

    df = df.drop_duplicates()
    print(f"After dedup: {len(df)} rows")
    return df


def main() -> None:
    print("=== Condo/Co-op Training Data Pipeline ===\n")

    sales = load_rolling_sales()
    sales = construct_bbl(sales)

    for col in ["year_built", "total_units", "residential_units"]:
        if col in sales.columns:
            sales[col] = pd.to_numeric(sales[col], errors="coerce")
    if "total_units" not in sales.columns:
        sales["total_units"] = np.nan
    if "residential_units" not in sales.columns:
        sales["residential_units"] = np.nan

    pluto = load_pluto_lookup()

    before = len(sales)
    sales = sales.merge(
        pluto[["bbl", "latitude", "longitude", "unitsres", "bldgarea", "assesstot"]],
        on="bbl", how="left",
    )
    matched = sales["latitude"].notna().sum()
    print(f"\nPLUTO geo join: {matched}/{before} rows matched ({matched/before*100:.1f}%)")

    # Fill total_units / residential_units from PLUTO where missing
    sales["total_units"] = sales["total_units"].where(
        sales["total_units"].notna() & (sales["total_units"] > 0),
        sales["unitsres"],
    )
    sales["residential_units"] = sales["residential_units"].where(
        sales["residential_units"].notna() & (sales["residential_units"] > 0),
        sales["unitsres"],
    )

    # Keep only rows with lat/lon
    sales = sales[sales["latitude"].notna() & sales["longitude"].notna()].copy()
    print(f"Rows with valid lat/lon: {len(sales)}")

    # Building-level size and assessment signals from PLUTO.
    # For co-ops and condos the rolling sales gross_sqft is almost always null;
    # bldgarea / unitsres gives the average interior sqft per unit within the
    # building — a useful proxy for unit size and market positioning.
    units_floor = sales["unitsres"].clip(lower=1)
    sales["sqft_per_unit"]   = (sales["bldgarea"]  / units_floor).where(
        sales["bldgarea"].notna() & (sales["bldgarea"] > 0)
    )
    sales["assess_per_unit"] = (sales["assesstot"] / units_floor).where(
        sales["assesstot"].notna() & (sales["assesstot"] > 0)
    )

    sqft_cov = sales["sqft_per_unit"].notna().mean() * 100
    asmt_cov = sales["assess_per_unit"].notna().mean() * 100
    print(f"\nsqft_per_unit coverage:   {sqft_cov:.1f}%")
    print(f"assess_per_unit coverage: {asmt_cov:.1f}%")
    if sales["sqft_per_unit"].notna().any():
        print(f"sqft_per_unit range: {sales['sqft_per_unit'].min():.0f}–{sales['sqft_per_unit'].max():.0f} sqft")

    sales["sales_price"] = pd.to_numeric(sales.get("sales_price", pd.Series()), errors="coerce")

    sales = apply_filters(sales)

    keep = [
        "borough", "neighborhood", "building_class",
        "year_built", "sales_price",
        "latitude", "longitude",
        "total_units", "residential_units",
        "sqft_per_unit", "assess_per_unit",
    ]
    keep = [c for c in keep if c in sales.columns]
    sales = sales[keep]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    sales.to_csv(OUTPUT, index=False)

    print(f"\n✅ Saved {len(sales):,} rows to {OUTPUT}")
    print("\nBuilding class counts:")
    print(sales["building_class"].value_counts().to_string())
    print(f"\nsqft_per_unit non-null: {sales['sqft_per_unit'].notna().sum():,} rows")


if __name__ == "__main__":
    main()
