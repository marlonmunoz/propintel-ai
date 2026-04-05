"""Build enriched multi-family (2- and 3-family) training data from all sources.

Pipeline:
  1. Load NYC Rolling Sales: current file + 2022 + 2023 annualized archives (all 5 boroughs).
  2. Standardise column names — current and historical files use different formats.
  3. Construct BBL (standard lots; 2-3 family homes do not use unit lots).
  4. Join PLUTO via BBL → bldgfront, bldgdepth, lotdepth, builtfar, assesstot.
  5. Compute derived features:
       assess_per_unit = assesstot / total_units
       bldg_footprint  = bldgfront × bldgdepth   (building area proxy)
  6. Apply per-borough × per-class price caps (97th pct) to keep Manhattan
     luxury townhouses without contaminating outer-borough distributions.
  7. Apply price-per-sqft P2–P98 neighbourhood sanity filter.
  8. Deduplicate by (bbl, sale_price) across all year files.
  9. Save to ml/data/processed/nyc_multifamily_training_data.csv.

Why this file exists:
  housing_data (the DB extract) covers only the most recent rolling-sales
  window (~12 months) and has no BBL, so PLUTO enrichment requires a spatial
  approximation.  This pipeline loads three years of public rolling-sales data,
  joins PLUTO exactly via BBL, and produces a 3× larger, richer training set.

Run from the project root:
    python ml/pipelines/create_multifamily_training_data.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
RAW_DIR  = BASE_DIR / "ml/data/nyc_raw"
HIST_DIR = RAW_DIR / "historical"
PLUTO_CSV = BASE_DIR / "ml/data/pluto_raw/pluto.csv"
OUTPUT    = BASE_DIR / "ml/data/processed/nyc_multifamily_training_data.csv"

MF_CLASSES = {
    "02 TWO FAMILY DWELLINGS",
    "03 THREE FAMILY DWELLINGS",
}

CURRENT_FILES = {
    1: RAW_DIR / "rollingsales_manhattan.xlsx",
    2: RAW_DIR / "rollingsales_bronx.xlsx",
    3: RAW_DIR / "rollingsales_brooklyn.xlsx",
    4: RAW_DIR / "rollingsales_queens.xlsx",
    5: RAW_DIR / "rollingsales_statenisland.xlsx",
}

HISTORICAL_FILES = {
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

BOROUGH_NAMES = {1: "Manhattan", 2: "Bronx", 3: "Brooklyn", 4: "Queens", 5: "Staten Island"}


def _clean_col(c: str) -> str:
    """Normalise a column name from either file format."""
    return c.strip().replace("\n", "_").lower().replace(" ", "_")


def load_current_files() -> pd.DataFrame:
    """Load the current 12-month rolling sales files (skiprows=4)."""
    dfs = []
    for borocode, path in CURRENT_FILES.items():
        df = pd.read_excel(path, skiprows=4)
        df.columns = [_clean_col(c) for c in df.columns]
        df["borocode"] = borocode
        df["source_year"] = "current"
        dfs.append(df)
    raw = pd.concat(dfs, ignore_index=True)

    raw = raw.rename(columns={
        "building_class_category": "building_class",
        "sale_price":              "sales_price",
        "gross_square_feet":       "gross_sqft",
        "land_square_feet":        "land_sqft",
    })
    return raw


def load_historical_files() -> pd.DataFrame:
    """Load 2022 + 2023 annualized rolling sales files (skiprows=6)."""
    dfs = []
    for (year, borocode), path in HISTORICAL_FILES.items():
        df = pd.read_excel(path, skiprows=6)
        df.columns = [_clean_col(c) for c in df.columns]
        df["borocode"] = borocode
        df["source_year"] = str(year)

        # Annualized files use slightly different column names
        rename = {}
        for col in df.columns:
            if "building_class_category" in col:
                rename[col] = "building_class"
            elif col in ("land__square_feet", "land_\nsquare_feet",
                         "land_square_feet", "land__square__feet"):
                rename[col] = "land_sqft"
            elif col in ("gross__square_feet", "gross_\nsquare_feet",
                         "gross_square_feet", "gross__square__feet"):
                rename[col] = "gross_sqft"
            elif col in ("total__units", "total_\nunits", "total_units"):
                rename[col] = "total_units"
            elif col in ("residential__units", "residential_\nunits", "residential_units"):
                rename[col] = "residential_units"
            elif col == "sale_price":
                rename[col] = "sales_price"
        df = df.rename(columns=rename)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)


def load_all_mf_sales() -> pd.DataFrame:
    print("Loading current rolling sales …")
    current = load_current_files()
    print(f"  {len(current)} total rows")

    print("Loading historical annualized files (2022 + 2023) …")
    hist = load_historical_files()
    print(f"  {len(hist)} total rows")

    raw = pd.concat([current, hist], ignore_index=True)
    raw["building_class"] = raw["building_class"].astype(str).str.strip()
    raw = raw[raw["building_class"].isin(MF_CLASSES)].copy()
    print(f"Multi-family rows across all files: {len(raw)}")
    print(raw["building_class"].value_counts().to_string())

    for col in ["sales_price", "gross_sqft", "land_sqft",
                "total_units", "residential_units", "year_built"]:
        if col in raw.columns:
            raw[col] = pd.to_numeric(raw[col], errors="coerce")

    # Basic quality filters
    raw = raw[
        (raw["sales_price"] > 50_000) &
        (raw["gross_sqft"] > 0) &
        raw["year_built"].between(1800, 2025)
    ].copy()
    print(f"After basic quality filters: {len(raw)}")
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


def load_pluto() -> pd.DataFrame:
    """Load PLUTO with building dimension and assessment columns."""
    cols = ["BBL", "latitude", "longitude", "unitsres",
            "numfloors", "bldgfront", "bldgdepth",
            "lotfront", "lotdepth", "builtfar",
            "assesstot", "assessland"]
    pluto = pd.read_csv(PLUTO_CSV, usecols=cols, low_memory=False)
    pluto.columns = [c.strip().lower() for c in pluto.columns]
    pluto = pluto.rename(columns={"bbl": "bbl"})
    pluto["bbl"] = pd.to_numeric(pluto["bbl"], errors="coerce")

    for col in ["latitude", "longitude", "unitsres", "numfloors",
                "bldgfront", "bldgdepth", "lotfront", "lotdepth",
                "builtfar", "assesstot", "assessland"]:
        pluto[col] = pd.to_numeric(pluto[col], errors="coerce")

    pluto = pluto.dropna(subset=["bbl", "latitude", "longitude"])
    pluto = pluto.drop_duplicates(subset=["bbl"])
    print(f"\nPLUTO loaded: {len(pluto):,} unique BBLs")
    return pluto


def apply_per_borough_class_caps(df: pd.DataFrame) -> pd.DataFrame:
    """Apply 97th-pct price cap per (borough, building_class) combination.

    The old per-class-only cap used a single 97th pct across all boroughs,
    which effectively set the cap at the outer-borough level (Brooklyn/Queens
    dominate ~80% of rows) and silently dropped legitimate Manhattan 2-family
    townhouses above $3M.  Per-borough caps preserve each borough's price
    distribution independently.
    """
    before = len(df)
    capped = []
    for (boro, bc), grp in df.groupby(["borocode", "building_class"]):
        cap = grp["sales_price"].quantile(0.97)
        capped.append(grp[grp["sales_price"] <= cap])
    df = pd.concat(capped).reset_index(drop=True) if capped else df
    print(f"Per-borough×class 97th-pct cap: {before} → {len(df)} rows (removed {before-len(df)})")
    for boro in sorted(df["borocode"].unique()):
        g = df[df["borocode"] == boro]
        print(f"  Borough {boro} ({BOROUGH_NAMES[boro]}): {len(g):,} rows  "
              f"max=${g['sales_price'].max():,.0f}")
    return df


def apply_ppsf_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Neighbourhood-level P2–P98 price-per-sqft sanity filter."""
    has_sqft = df["gross_sqft"].notna() & (df["gross_sqft"] > 0)
    if has_sqft.sum() < 100:
        return df

    sub  = df[has_sqft].copy()
    rest = df[~has_sqft]
    sub["_ppsf"] = sub["sales_price"] / sub["gross_sqft"]

    global_p2, global_p98 = sub["_ppsf"].quantile(0.02), sub["_ppsf"].quantile(0.98)
    bounds = sub.groupby("neighborhood")["_ppsf"].agg(
        p2=lambda x: x.quantile(0.02),
        p98=lambda x: x.quantile(0.98),
    ).reset_index()
    sub = sub.merge(bounds, on="neighborhood", how="left")
    sub["p2"]  = sub["p2"].fillna(global_p2)
    sub["p98"] = sub["p98"].fillna(global_p98)

    before = len(sub)
    sub = sub[(sub["_ppsf"] >= sub["p2"]) & (sub["_ppsf"] <= sub["p98"])]
    sub = sub.drop(columns=["_ppsf", "p2", "p98"])
    print(f"Price/sqft P2–P98 filter: removed {before - len(sub)} anomalous rows")
    return pd.concat([sub, rest]).reset_index(drop=True)


def main() -> None:
    print("=== Multi-Family Training Data Pipeline ===\n")

    # --- 1. Load all rolling sales ---
    sales = load_all_mf_sales()
    sales = construct_bbl(sales)

    # --- 2. PLUTO join ---
    pluto = load_pluto()
    pluto_cols = ["bbl", "latitude", "longitude", "unitsres",
                  "numfloors", "bldgfront", "bldgdepth",
                  "lotdepth", "builtfar", "assesstot"]
    before = len(sales)
    sales = sales.merge(pluto[pluto_cols], on="bbl", how="inner")
    print(f"PLUTO BBL join (inner): {len(sales):,} / {before:,} rows matched "
          f"({len(sales)/before*100:.1f}%)")

    # --- 3. Derived features ---
    units = sales["total_units"].where(
        sales["total_units"].notna() & (sales["total_units"] > 0),
        sales["unitsres"].clip(lower=1),
    ).clip(lower=1)

    # assess_per_unit: city's per-unit assessment — same quality signal
    # that pushed condo_coop from 0.55 → 0.80.
    sales["assess_per_unit"] = (sales["assesstot"] / units).where(
        sales["assesstot"].notna() & (sales["assesstot"] > 0)
    )

    # bldg_footprint: bldgfront × bldgdepth — exact building area in sqft,
    # more precise than gross_sqft for 2-3 family homes.
    sales["bldg_footprint"] = (
        sales["bldgfront"] * sales["bldgdepth"]
    ).where(
        sales["bldgfront"].notna() & (sales["bldgfront"] > 0) &
        sales["bldgdepth"].notna() & (sales["bldgdepth"] > 0)
    )

    for feat in ["assess_per_unit", "bldg_footprint", "numfloors", "builtfar", "lotdepth"]:
        cov = sales[feat].notna().mean() * 100 if feat in sales.columns else 0
        med = sales[feat].median() if feat in sales.columns else float("nan")
        print(f"  {feat}: {cov:.1f}% coverage  median={med:.2f}")

    # --- 4. Fill total_units / residential_units from PLUTO where missing ---
    sales["total_units"] = sales["total_units"].where(
        sales["total_units"].notna() & (sales["total_units"] > 0),
        sales["unitsres"],
    )
    sales["residential_units"] = sales.get(
        "residential_units", pd.Series(dtype=float)
    ).where(
        sales.get("residential_units", pd.Series(dtype=float)).notna() &
        (sales.get("residential_units", pd.Series(dtype=float)) > 0),
        sales["unitsres"],
    )

    # --- 5. Borough name ---
    sales["borough"] = sales["borocode"].map(BOROUGH_NAMES)

    # --- 6. Per-borough × per-class price caps ---
    sales = apply_per_borough_class_caps(sales)

    # --- 7. Price/sqft sanity filter ---
    sales = apply_ppsf_filter(sales)

    # --- 8. Deduplicate across year files (same sale can appear in rolling + annualized) ---
    before = len(sales)
    sales = sales.drop_duplicates(subset=["bbl", "sales_price"])
    print(f"Dedup by (bbl, sales_price): {before} → {len(sales)} rows (removed {before-len(sales)})")

    # --- 9. Select output columns ---
    keep = [
        "borough", "neighborhood", "building_class",
        "year_built", "sales_price",
        "gross_sqft", "land_sqft",
        "latitude", "longitude",
        "total_units", "residential_units",
        "assess_per_unit",
        "bldg_footprint",
        "numfloors",
        "builtfar",
        "lotdepth",
    ]
    keep = [c for c in keep if c in sales.columns]
    sales = sales[keep]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    sales.to_csv(OUTPUT, index=False)

    print(f"\n✅ Saved {len(sales):,} rows → {OUTPUT}")
    print("\nBuilding class distribution:")
    print(sales["building_class"].value_counts().to_string())
    print("\nBorough distribution:")
    print(sales["borough"].value_counts().to_string())
    for feat in ["assess_per_unit", "bldg_footprint", "numfloors", "builtfar", "lotdepth"]:
        if feat in sales.columns:
            pct = sales[feat].notna().mean() * 100
            print(f"{feat}: {pct:.1f}% non-null")


if __name__ == "__main__":
    main()
