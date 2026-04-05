"""Build enriched condo/co-op training data from raw sources.

Pipeline:
  1. Load NYC Rolling Sales Excel files (classes 09, 10, 12, 13, 15, 17).
  2. Construct BBL (borough-block-lot identifier).
  3. Join with PLUTO → lat/lon, bldgarea, unitsres, assesstot, numfloors, lotarea.
  4. Compute building-level features:
       sqft_per_unit   = bldgarea / unitsres   (avg unit size proxy)
       assess_per_unit = assesstot / unitsres   (tax assessment per unit)
       numfloors                                 (building height in floors)
       lot_coverage    = bldgarea / lotarea      (FAR proxy — density signal)
  5. Retain zipcode from rolling sales for zip-level price lookups.
  6. Apply per-class 95th-pct price caps and dedup.
  7. Save to ml/data/processed/nyc_condo_training_data.csv.

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
    """Build BBL and a parent BBL used to look up PLUTO.

    In NYC's property mapping, individual condo units receive their own lot
    numbers in the 1000+ range (e.g. lot 1042 = unit 42 in building lot 0001).
    PLUTO stores the building-level record under lot 0001, not the unit lots.
    Co-ops use standard (< 1000) lots and match PLUTO directly.

    Strategy:
      - Standard lots (< 1000): bbl_parent = bbl  (direct match)
      - Unit lots (≥ 1000):     bbl_parent uses lot = 1 (the parent parcel)

    This lets elevator and walkup condos (classes 12, 13) join PLUTO to get
    numfloors, assesstot, and unitsres — fixing the previous 0% condo match rate.
    """
    df = df.copy()
    df["block"] = pd.to_numeric(df["block"], errors="coerce")
    df["lot"]   = pd.to_numeric(df["lot"],   errors="coerce")
    valid = df["block"].notna() & df["lot"].notna() & df["borocode"].notna()
    df = df[valid].copy()

    boro  = df["borocode"].astype(np.int64)
    block = df["block"].astype(np.int64)
    lot   = df["lot"].astype(np.int64)

    df["bbl"] = boro * 1_000_000_000 + block * 10_000 + lot

    # For unit-level lots (≥ 1000), derive the parent lot (0001) to look up
    # the building record in PLUTO.
    is_unit_lot = lot >= 1000
    parent_lot  = lot.where(~is_unit_lot, other=1)
    df["bbl_parent"] = boro * 1_000_000_000 + block * 10_000 + parent_lot

    n_unit = is_unit_lot.sum()
    print(f"BBL constructed: {len(df):,} rows  ({n_unit:,} unit-level lots remapped to parent)")
    return df


def load_pluto_lookup() -> pd.DataFrame:
    cols = [
        "BBL", "latitude", "longitude",
        "unitsres", "unitstotal",
        "bldgarea", "assesstot",
        "numfloors", "lotarea",
    ]
    pluto = pd.read_csv(PLUTO_CSV, usecols=cols, low_memory=False)
    pluto = pluto.rename(columns={"BBL": "bbl"})
    pluto["bbl"] = pd.to_numeric(pluto["bbl"], errors="coerce")

    # bldgarea and lotarea are comma-formatted integers ("1,224") in PLUTO CSV
    for col in ["bldgarea", "lotarea"]:
        pluto[col] = (
            pluto[col].astype(str).str.replace(",", "", regex=False)
            .pipe(pd.to_numeric, errors="coerce")
        )
    for col in ["latitude", "longitude", "unitsres", "unitstotal",
                "assesstot", "numfloors"]:
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

    # Per-class 95th-pct cap — tighter than the old global 99th.
    # Co-op elevator units (class 10) span $50k Bronx studios to $15M+ Fifth
    # Ave penthouses; the luxury tail inflates RMSE without improving typical
    # predictions. Per-class capping preserves the full walkup range while
    # cutting the luxury elevator outliers independently.
    capped = []
    for bc in df["building_class"].unique():
        rows = df[df["building_class"] == bc]
        cap  = rows["sales_price"].quantile(0.95)
        capped.append(rows[rows["sales_price"] <= cap])
    df = pd.concat(capped).reset_index(drop=True) if capped else df
    print(f"After per-class 95th pct cap: {len(df)} rows")
    for bc in df["building_class"].unique():
        g = df[df["building_class"] == bc]
        print(f"  {bc}: {len(g):,} rows  max=${g['sales_price'].max():,.0f}")

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
    pluto_cols = ["bbl", "latitude", "longitude", "unitsres",
                  "bldgarea", "assesstot", "numfloors", "lotarea"]
    # Join on bbl_parent so condo unit lots (1001+) match the parent building in PLUTO.
    sales = sales.merge(
        pluto[pluto_cols].rename(columns={"bbl": "bbl_parent"}),
        on="bbl_parent", how="left",
    )
    matched = sales["latitude"].notna().sum()
    print(f"\nPLUTO geo join (via bbl_parent): {matched}/{before} rows matched ({matched/before*100:.1f}%)")

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

    # --- PLUTO-derived features ---
    units_floor = sales["unitsres"].clip(lower=1)

    # sqft_per_unit: building gross area ÷ residential units — approximates
    # average unit size (individual unit sqft is not recorded in rolling sales).
    sales["sqft_per_unit"] = (sales["bldgarea"] / units_floor).where(
        sales["bldgarea"].notna() & (sales["bldgarea"] > 0)
    )

    # assess_per_unit: tax assessment ÷ residential units — proxy for city's
    # valuation of building quality and income potential.
    sales["assess_per_unit"] = (sales["assesstot"] / units_floor).where(
        sales["assesstot"].notna() & (sales["assesstot"] > 0)
    )

    # numfloors: building height in floors — taller buildings command higher
    # prices for upper-floor units and signal density / prestige.
    # (passed through directly from PLUTO)

    # lot_coverage: total building area ÷ lot area — effective FAR proxy;
    # higher values indicate denser, more urbanised buildings.
    sales["lot_coverage"] = (sales["bldgarea"] / sales["lotarea"].clip(lower=1)).where(
        sales["bldgarea"].notna() & (sales["bldgarea"] > 0) &
        sales["lotarea"].notna() & (sales["lotarea"] > 0)
    )

    for feat, label in [
        ("sqft_per_unit",   "sqft_per_unit"),
        ("assess_per_unit", "assess_per_unit"),
        ("numfloors",       "numfloors"),
        ("lot_coverage",    "lot_coverage"),
    ]:
        cov = sales[feat].notna().mean() * 100
        print(f"{label} coverage: {cov:.1f}%")

    sales["sales_price"] = pd.to_numeric(sales.get("sales_price", pd.Series()), errors="coerce")

    sales = apply_filters(sales)

    keep = [
        "borough", "neighborhood", "building_class",
        "year_built", "sales_price",
        "latitude", "longitude",
        "total_units", "residential_units",
        "sqft_per_unit", "assess_per_unit",
        "numfloors", "lot_coverage",
        "zipcode",
    ]
    keep = [c for c in keep if c in sales.columns]
    sales = sales[keep]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    sales.to_csv(OUTPUT, index=False)

    print(f"\n✅ Saved {len(sales):,} rows to {OUTPUT}")
    print("\nBuilding class counts:")
    print(sales["building_class"].value_counts().to_string())
    for feat in ["sqft_per_unit", "assess_per_unit", "numfloors", "lot_coverage", "zipcode"]:
        if feat in sales.columns:
            print(f"{feat} non-null: {sales[feat].notna().sum():,} rows ({sales[feat].notna().mean()*100:.1f}%)")


if __name__ == "__main__":
    main()
