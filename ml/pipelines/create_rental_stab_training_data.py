"""Build enriched rental training data.

Strategy (hybrid approach):
  - Base data: nyc_subtype_training_data.csv (housing_data DB extract, high quality)
  - Enrichment layers added to the base rows:

  1. stabilization_ratio   — neighbourhood median from DHCR rentstab via BBL join
  2. numfloors             — building height from PLUTO via lat/lon spatial join
  3. lot_coverage          — FAR proxy (bldgarea / lotarea) from PLUTO spatial join
  4. units_per_floor       — density signal: total_units / numfloors
  5. subway_dist_km        — distance to nearest NYC subway station (MTA data)

Spatial join approach for PLUTO:
  The housing_data base rows carry lat/lon but no BBL, so we use a
  sklearn BallTree nearest-neighbour search against PLUTO building
  centroids (max 150 m radius) to retrieve building-level features.

Run from the project root:
    python ml/pipelines/create_rental_stab_training_data.py
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.neighbors import BallTree

BASE_DIR      = Path(__file__).resolve().parents[2]
RAW_DIR       = BASE_DIR / "ml/data/nyc_raw"
PLUTO_CSV     = BASE_DIR / "ml/data/pluto_raw/pluto.csv"
STAB_CSV      = BASE_DIR / "ml/data/external/rentstab_counts_2023.csv"
SUBWAY_CSV    = BASE_DIR / "ml/data/external/nyc_subway_stations.csv"
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

# Max radius for PLUTO spatial join — 150 m keeps us on the same block
PLUTO_MAX_DIST_M = 150
EARTH_RADIUS_M   = 6_371_000


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
    pluto["bbl"]      = pd.to_numeric(pluto["bbl"],      errors="coerce")
    pluto["unitsres"] = pd.to_numeric(pluto["unitsres"], errors="coerce")
    pluto = pluto.dropna(subset=["bbl"]).drop_duplicates("bbl")

    rentstab = pd.read_csv(STAB_CSV, usecols=["ucbbl", "uc2023"]).rename(
        columns={"ucbbl": "bbl"}
    )
    rentstab["bbl"]    = pd.to_numeric(rentstab["bbl"],    errors="coerce")
    rentstab["uc2023"] = pd.to_numeric(rentstab["uc2023"], errors="coerce")
    rentstab = rentstab.dropna(subset=["bbl"]).drop_duplicates("bbl")

    df = sales.merge(rentstab, on="bbl", how="left")
    df = df.merge(pluto, on="bbl", how="left")
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

    neigh_median = (
        df.groupby("neighborhood")["stabilization_ratio"]
        .median()
        .to_dict()
    )
    print(f"Neighborhood medians computed: {len(neigh_median)}")
    return neigh_median


def load_pluto_spatial() -> pd.DataFrame:
    """Load PLUTO with lat/lon + density columns for spatial join."""
    cols = ["BBL", "latitude", "longitude", "unitsres",
            "numfloors", "bldgarea", "lotarea"]
    pluto = pd.read_csv(PLUTO_CSV, usecols=cols, low_memory=False)
    pluto.columns = [c.strip().lower().replace(" ", "_") for c in pluto.columns]

    for col in ["bldgarea", "lotarea"]:
        pluto[col] = (
            pluto[col].astype(str).str.replace(",", "", regex=False)
            .pipe(pd.to_numeric, errors="coerce")
        )
    for col in ["latitude", "longitude", "numfloors", "unitsres"]:
        pluto[col] = pd.to_numeric(pluto[col], errors="coerce")

    pluto = pluto.dropna(subset=["latitude", "longitude"])
    pluto = pluto[pluto["numfloors"].notna() & (pluto["numfloors"] > 0)]
    pluto = pluto.drop_duplicates(subset=["bbl"])
    print(f"PLUTO spatial index: {len(pluto):,} buildings with numfloors")
    return pluto.reset_index(drop=True)


def spatial_join_pluto(base: pd.DataFrame, pluto: pd.DataFrame) -> pd.DataFrame:
    """Attach PLUTO density features via nearest-building spatial join (≤150 m)."""
    base_coords = np.radians(base[["latitude", "longitude"]].values)
    pluto_coords = np.radians(pluto[["latitude", "longitude"]].values)

    tree = BallTree(pluto_coords, metric="haversine")
    max_rad = PLUTO_MAX_DIST_M / EARTH_RADIUS_M
    distances, indices = tree.query(base_coords, k=1, return_distance=True)

    distances = distances[:, 0]   # (n,)
    indices   = indices[:, 0]     # (n,)

    mask = distances <= max_rad
    print(f"PLUTO spatial join: {mask.sum():,}/{len(base):,} rows matched "
          f"within {PLUTO_MAX_DIST_M} m ({mask.mean()*100:.1f}%)")

    matched_pluto = pluto.iloc[indices].reset_index(drop=True)
    for col in ["numfloors", "bldgarea", "lotarea", "unitsres"]:
        base[col] = np.where(mask, matched_pluto[col].values, np.nan)

    return base


def add_density_features(base: pd.DataFrame) -> pd.DataFrame:
    """Compute units_per_floor and lot_coverage from PLUTO columns."""
    base["numfloors"] = pd.to_numeric(base["numfloors"], errors="coerce")

    tu = base.get("total_units", pd.Series(dtype=float))
    if tu.isna().all() and "unitsres" in base.columns:
        tu = base["unitsres"]
    base["units_per_floor"] = (
        tu / base["numfloors"].clip(lower=1)
    ).where(base["numfloors"].notna() & (base["numfloors"] > 0))

    base["lot_coverage"] = (
        base["bldgarea"] / base["lotarea"].clip(lower=1)
    ).where(
        base["bldgarea"].notna() & (base["bldgarea"] > 0) &
        base["lotarea"].notna()  & (base["lotarea"] > 0)
    )

    for feat in ["numfloors", "units_per_floor", "lot_coverage"]:
        cov = base[feat].notna().mean() * 100
        med = base[feat].median()
        print(f"  {feat}: {cov:.1f}% coverage  median={med:.2f}")

    return base


def add_subway_distance(base: pd.DataFrame) -> pd.DataFrame:
    """Compute distance (km) to nearest NYC subway station via BallTree."""
    if not SUBWAY_CSV.exists():
        print("Subway station file not found — skipping subway_dist_km")
        base["subway_dist_km"] = np.nan
        return base

    stations = pd.read_csv(SUBWAY_CSV, usecols=["GTFS Latitude", "GTFS Longitude"])
    stations = stations.dropna()
    stations.columns = ["lat", "lon"]

    base_coords    = np.radians(base[["latitude", "longitude"]].values)
    station_coords = np.radians(stations[["lat", "lon"]].values)

    tree = BallTree(station_coords, metric="haversine")
    dist_rad, _ = tree.query(base_coords, k=1, return_distance=True)

    base["subway_dist_km"] = dist_rad[:, 0] * (EARTH_RADIUS_M / 1000)
    print(f"subway_dist_km: median={base['subway_dist_km'].median():.3f} km  "
          f"max={base['subway_dist_km'].max():.3f} km  "
          f"coverage={base['subway_dist_km'].notna().mean()*100:.1f}%")
    return base


def main() -> None:
    print("=== Rental Enrichment Pipeline (Hybrid) ===\n")

    # --- 1. Neighbourhood stabilization lookup (from raw rolling sales + DHCR) ---
    print("--- Building neighbourhood stabilization lookup ---")
    sales = load_rolling_sales()
    neigh_stab = build_neighborhood_stab_ratios(sales)
    global_stab = float(pd.Series(list(neigh_stab.values())).median())
    print(f"Global stabilization ratio median: {global_stab:.4f}")

    # --- 2. Load high-quality base rental rows ---
    print("\n--- Loading base rental training data ---")
    base = pd.read_csv(STANDARD_CSV, low_memory=False)
    base = base[base["building_class"].isin(RENTAL_CLASSES)].copy()
    print(f"Base rental rows: {len(base)}")
    print(base["building_class"].value_counts().to_string())

    # --- 3. Attach stabilization_ratio (neighbourhood median) ---
    base["stabilization_ratio"] = (
        base["neighborhood"].map(neigh_stab).fillna(global_stab)
    )
    nonzero = (base["stabilization_ratio"] > 0).mean() * 100
    print(f"\nstabilization_ratio: {base['stabilization_ratio'].notna().mean()*100:.1f}% coverage  "
          f"rows > 0: {nonzero:.1f}%")

    # --- 4. PLUTO spatial join → numfloors, bldgarea, lotarea ---
    print("\n--- PLUTO spatial join for density features ---")
    pluto = load_pluto_spatial()
    base  = spatial_join_pluto(base.copy(), pluto)
    print("Density features:")
    base  = add_density_features(base)

    # --- 5. Subway proximity ---
    print("\n--- Subway proximity ---")
    base = add_subway_distance(base)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    base.to_csv(OUTPUT, index=False)
    print(f"\n✅ Saved {len(base):,} rows to {OUTPUT}")
    print("Columns:", list(base.columns))


if __name__ == "__main__":
    main()
