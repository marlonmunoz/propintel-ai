"""
Phase 2a enrichment pipeline — rental buildings only.

Builds a training CSV directly from the NYC Rolling Sales Excel files joined
to PLUTO on BBL (borough-block-lot).  This gives us two features that the
housing_data DB table does not have:

  assess_per_unit  — NYC DOF assessed total value ÷ total units.
                     Assessed value is a capitalisation-based government
                     estimate that partially proxies rental income, a key
                     driver of rental building sale prices.

  sqft_per_unit    — gross_sqft ÷ total_units (average unit size).
                     Already in Phase 1; recomputed here from source.

The join succeeds at 100 % for rental BBLs (every Rolling Sales rental row
has a matching PLUTO record).

Usage:
    python ml/pipelines/create_enriched_rental_data.py
"""

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

BASE_DIR = Path(__file__).resolve().parents[2]

ROLLING_SALES_FILES = {
    1: BASE_DIR / "ml/data/nyc_raw/rollingsales_manhattan.xlsx",
    2: BASE_DIR / "ml/data/nyc_raw/rollingsales_bronx.xlsx",
    3: BASE_DIR / "ml/data/nyc_raw/rollingsales_brooklyn.xlsx",
    4: BASE_DIR / "ml/data/nyc_raw/rollingsales_queens.xlsx",
    5: BASE_DIR / "ml/data/nyc_raw/rollingsales_statenisland.xlsx",
}

PLUTO_FILE = BASE_DIR / "ml/data/pluto_raw/pluto.csv"

OUTPUT_PATH = BASE_DIR / "ml/data/processed/nyc_rental_enriched_training_data.csv"

RENTAL_CLASSES = [
    "07 RENTALS - WALKUP APARTMENTS",
    "08 RENTALS - ELEVATOR APARTMENTS",
]

BOROUGH_MAP = {
    1: "Manhattan",
    2: "Bronx",
    3: "Brooklyn",
    4: "Queens",
    5: "Staten Island",
}


def load_rolling_sales() -> pd.DataFrame:
    """Load all five Rolling Sales Excel files, normalise columns, construct BBL."""
    frames = []
    for boro_code, path in ROLLING_SALES_FILES.items():
        print(f"  Loading {path.name}…")
        df = pd.read_excel(path, header=4)
        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        df["boro_code"] = boro_code
        frames.append(df)

    rs = pd.concat(frames, ignore_index=True)

    rs["bbl"] = (
        rs["borough"].astype(str)
        + rs["block"].astype(str).str.zfill(5)
        + rs["lot"].astype(str).str.zfill(4)
    ).astype("int64")

    # Map borough name so it matches housing_data / predictor conventions.
    rs["borough_name"] = rs["boro_code"].map(BOROUGH_MAP)

    # Normalise key numeric columns early.
    for col in ["sale_price", "gross_square_feet", "land_square_feet",
                "total_units", "residential_units", "year_built"]:
        rs[col] = pd.to_numeric(rs[col], errors="coerce")

    # Rename to match our ML feature names.
    rs = rs.rename(columns={
        "building_class_category":          "building_class",
        "neighborhood":                     "neighborhood",
        "gross_square_feet":                "gross_sqft",
        "land_square_feet":                 "land_sqft",
        "sale_price":                       "sales_price",
        "zip_code":                         "postcode",
    })

    return rs


def load_pluto() -> pd.DataFrame:
    """Load only the PLUTO columns we need. 409 MB CSV — usecols keeps it fast."""
    print("  Loading PLUTO (key columns only)…")
    pluto = pd.read_csv(
        PLUTO_FILE,
        usecols=["BBL", "assesstot", "latitude", "longitude"],
        low_memory=False,
    )
    pluto.columns = [c.lower() for c in pluto.columns]
    pluto["bbl"] = pd.to_numeric(pluto["bbl"], errors="coerce").astype("Int64")
    pluto = pluto.dropna(subset=["bbl"]).drop_duplicates("bbl")
    pluto["bbl"] = pluto["bbl"].astype("int64")
    return pluto


def clean_rental(df: pd.DataFrame) -> pd.DataFrame:
    """Apply the same cleaning rules as create_subtype_training_data.py."""

    before = len(df)
    df = df[df["sales_price"] > 1_000]
    print(f"  After sale_price > $1k:       {len(df):,} (removed {before - len(df):,})")

    before = len(df)
    df = df[
        df["year_built"].notna()
        & df["year_built"].between(1800, 2025)
    ]
    print(f"  After year_built filter:      {len(df):,} (removed {before - len(df):,})")

    before = len(df)
    df = df[df["latitude"].notna() & df["longitude"].notna()]
    print(f"  After lat/lng not null:       {len(df):,} (removed {before - len(df):,})")

    before = len(df)
    df = df[df["gross_sqft"].notna() & (df["gross_sqft"] > 0)]
    print(f"  After gross_sqft > 0:         {len(df):,} (removed {before - len(df):,})")

    before = len(df)
    df = df[df["total_units"].notna() & (df["total_units"] > 0)]
    print(f"  After total_units > 0:        {len(df):,} (removed {before - len(df):,})")

    # Per-unit floor — removes data errors and atypical distressed sales.
    df["price_per_unit_check"] = df["sales_price"] / df["total_units"]
    before = len(df)
    df = df[df["price_per_unit_check"] >= 30_000].drop(columns=["price_per_unit_check"])
    print(f"  After $30K/unit floor:        {len(df):,} (removed {before - len(df):,})")

    # Per-class 95th pct cap — removes institutional / portfolio mega-deals.
    capped = []
    for bc in df["building_class"].unique():
        bc_rows = df[df["building_class"] == bc]
        p95 = bc_rows["sales_price"].quantile(0.95)
        capped.append(bc_rows[bc_rows["sales_price"] <= p95])
    df = pd.concat(capped).reset_index(drop=True)
    print(f"  After per-class 95th pct cap: {len(df):,}")

    before = len(df)
    df = df.drop_duplicates()
    print(f"  After drop_duplicates:        {len(df):,} (removed {before - len(df):,})")

    return df


def main():
    print("\n=== Phase 2a: Enriched rental training data pipeline ===\n")

    print("Step 1 — Loading Rolling Sales…")
    rs = load_rolling_sales()

    # Filter to rental classes only.
    rs_rental = rs[rs["building_class"].isin(RENTAL_CLASSES)].copy()
    print(f"  Rental rows in Rolling Sales: {len(rs_rental):,}")
    print(rs_rental["building_class"].value_counts().to_string())

    print("\nStep 2 — Loading PLUTO…")
    pluto = load_pluto()
    print(f"  PLUTO unique BBLs: {len(pluto):,}")

    print("\nStep 3 — Joining on BBL…")
    merged = rs_rental.merge(pluto, on="bbl", how="left")
    matched = merged["assesstot"].notna().sum()
    print(f"  Join hit rate: {matched:,} / {len(merged):,} ({matched/len(merged)*100:.1f}%)")

    # Compute assess_per_unit — must come before cleaning so we can impute later.
    # assesstot is the NYC DOF total assessed value for the lot/building.
    merged["assesstot"] = pd.to_numeric(merged["assesstot"], errors="coerce")
    merged["assess_per_unit"] = merged["assesstot"] / merged["total_units"].clip(lower=1)

    print("\nStep 4 — Cleaning…")
    clean = clean_rental(merged)

    print(f"\n  Final row counts:")
    print(clean["building_class"].value_counts().to_string())

    # Compute sqft_per_unit (derived feature, same as Phase 1).
    clean["sqft_per_unit"] = clean["gross_sqft"] / clean["total_units"]

    # Select and rename to match what train_subtype_models.py expects.
    keep_cols = [
        "building_class", "neighborhood", "borough_name",
        "gross_sqft", "land_sqft", "sqft_per_unit",
        "total_units", "residential_units",
        "assess_per_unit",
        "year_built", "sales_price",
        "latitude", "longitude",
        "postcode",
    ]
    existing = [c for c in keep_cols if c in clean.columns]
    output = clean[existing].rename(columns={"borough_name": "borough"}).copy()

    print(f"\nassess_per_unit stats (non-null: {output['assess_per_unit'].notna().sum():,}):")
    q = output["assess_per_unit"].dropna().quantile([.05, .25, .5, .75, .95])
    print(f"  p5=${q[.05]:,.0f}  p25=${q[.25]:,.0f}  median=${q[.5]:,.0f}  p75=${q[.75]:,.0f}  p95=${q[.95]:,.0f}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT_PATH, index=False)
    print(f"\n✅ Enriched rental data saved: {OUTPUT_PATH}")
    print(f"   Rows: {len(output):,}  |  Columns: {list(output.columns)}")


if __name__ == "__main__":
    main()
