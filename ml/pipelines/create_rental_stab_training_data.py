"""Build enriched rental training data by adding stabilization_ratio.

Strategy (hybrid approach):
  - Base data: nyc_subtype_training_data.csv (housing_data DB extract, high quality)
  - Enrichment: DHCR rentstab counts joined via raw rolling sales → PLUTO BBL

Pipeline:
  1. Load raw NYC Rolling Sales (07, 08) and DHCR rentstab counts.
  2. Join rolling sales → PLUTO (BBL) → rentstab to get per-building
     stabilization_ratio = rent-stabilized units / total_units.
  3. Aggregate stabilization_ratio to neighborhood-level medians.
  4. Join those medians onto the high-quality housing_data rental rows
     (nyc_subtype_training_data.csv) by neighborhood name.
  5. Save to nyc_rental_stab_training_data.csv.

This preserves the data quality of the housing_data base while adding a
meaningful income-regulation signal at the neighbourhood level.  At inference
time the predictor looks up the same neighbourhood median from the saved
neighbourhood stats JSON.

Run from the project root:
    python ml/pipelines/create_rental_stab_training_data.py
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR      = Path(__file__).resolve().parents[2]
RAW_DIR       = BASE_DIR / "ml/data/nyc_raw"
PLUTO_CSV     = BASE_DIR / "ml/data/pluto_raw/pluto.csv"
STAB_CSV      = BASE_DIR / "ml/data/external/rentstab_counts_2023.csv"
STANDARD_CSV  = BASE_DIR / "ml/data/processed/nyc_subtype_training_data.csv"
OUTPUT        = BASE_DIR / "ml/data/processed/nyc_rental_stab_training_data.csv"

RENTAL_CLASSES = {
    "07 RENTALS - WALKUP APARTMENTS",
    "08 RENTALS - ELEVATOR APARTMENTS",
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
        "total_units":             "total_units",
    }
    raw = raw.rename(columns={k: v for k, v in col_map.items() if k in raw.columns})
    raw = raw[raw["building_class"].isin(RENTAL_CLASSES)].copy()
    raw["block"] = pd.to_numeric(raw["block"], errors="coerce")
    raw["lot"]   = pd.to_numeric(raw["lot"],   errors="coerce")
    raw["total_units"] = pd.to_numeric(raw["total_units"], errors="coerce")
    raw = raw[raw["block"].notna() & raw["lot"].notna()]
    raw["bbl"] = (
        raw["borocode"].astype(np.int64) * 1_000_000_000
        + raw["block"].astype(np.int64) * 10_000
        + raw["lot"].astype(np.int64)
    )
    print(f"Rolling-sales rental rows: {len(raw)}")
    return raw[["neighborhood", "building_class", "bbl", "total_units"]]


def build_neighborhood_stab_ratios(sales: pd.DataFrame) -> dict[str, float]:
    """Return {neighborhood: median_stabilization_ratio} computed from raw data."""
    pluto = pd.read_csv(
        PLUTO_CSV, usecols=["BBL", "unitsres"], low_memory=False
    ).rename(columns={"BBL": "bbl"})
    pluto["bbl"]     = pd.to_numeric(pluto["bbl"],     errors="coerce")
    pluto["unitsres"] = pd.to_numeric(pluto["unitsres"], errors="coerce")
    pluto = pluto.dropna(subset=["bbl"]).drop_duplicates("bbl")

    rentstab = pd.read_csv(STAB_CSV, usecols=["ucbbl", "uc2023"]).rename(
        columns={"ucbbl": "bbl"}
    )
    rentstab["bbl"]    = pd.to_numeric(rentstab["bbl"],    errors="coerce")
    rentstab["uc2023"] = pd.to_numeric(rentstab["uc2023"], errors="coerce")
    rentstab = rentstab.dropna(subset=["bbl"]).drop_duplicates("bbl")

    # Join to get stabilized units
    df = sales.merge(rentstab, on="bbl", how="left")
    df = df.merge(pluto, on="bbl", how="left")

    # Use PLUTO unitsres as total_units where rolling sales value is missing
    df["total_units"] = df["total_units"].where(
        df["total_units"].notna() & (df["total_units"] > 0),
        df["unitsres"],
    )

    df["uc2023"] = df["uc2023"].fillna(0)
    df["stabilization_ratio"] = (
        df["uc2023"] / df["total_units"].clip(lower=1)
    ).clip(0, 1)

    matched_pct = (df["uc2023"] > 0).mean() * 100
    print(f"Buildings with rentstab data: {matched_pct:.1f}%")

    # Neighbourhood median — robust to outliers and appropriate for inference
    neigh_median = (
        df.groupby("neighborhood")["stabilization_ratio"]
        .median()
        .to_dict()
    )
    print(f"Neighborhood medians computed: {len(neigh_median)}")
    return neigh_median


def main() -> None:
    print("=== Rental Stabilization Enrichment Pipeline (Hybrid) ===\n")

    # Step 1: Build neighbourhood stabilization lookup from raw sources
    print("--- Building neighbourhood stabilization lookup ---")
    sales = load_rolling_sales()
    neigh_stab = build_neighborhood_stab_ratios(sales)

    global_stab = float(pd.Series(list(neigh_stab.values())).median())
    print(f"Global stabilization ratio median: {global_stab:.4f}")

    # Step 2: Load high-quality housing_data rental rows (base dataset)
    print("\n--- Loading base rental training data ---")
    base = pd.read_csv(STANDARD_CSV, low_memory=False)
    base = base[base["building_class"].isin(RENTAL_CLASSES)].copy()
    print(f"Base rental rows: {len(base)}")
    print(base["building_class"].value_counts().to_string())

    # Step 3: Add neighbourhood-level stabilization_ratio
    base["stabilization_ratio"] = (
        base["neighborhood"].map(neigh_stab).fillna(global_stab)
    )
    nonzero = (base["stabilization_ratio"] > 0).mean() * 100
    print(f"\nstabilization_ratio coverage: {base['stabilization_ratio'].notna().mean()*100:.1f}%")
    print(f"Rows with ratio > 0: {nonzero:.1f}%")
    print(base["stabilization_ratio"].describe().to_string())

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    base.to_csv(OUTPUT, index=False)

    print(f"\n✅ Saved {len(base):,} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
