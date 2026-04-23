"""Build Gold PLUTO geographic/physical features.

Unlike the DOF/ACRIS/J-51 Gold builders this file does NOT apply an as-of
filter: latitude, longitude, numfloors, lot dimensions, and built FAR are
physical attributes of a parcel that change slowly over decades.  Assessor
values (assesstot, assessland) are intentionally excluded here — the DOF
Gold builder already provides time-indexed assessment data.

Output: ml/data/gold/gold_pluto_features.parquet
  One row per unique BBL.  Join to the spine on ``bbl`` only.

Run from repo root:
    python ml/pipelines/gold_pluto_features.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.neighbors import BallTree

BASE    = Path(__file__).resolve().parents[2]
PLUTO   = BASE / "ml/data/pluto_raw/pluto.csv"
SUBWAY  = BASE / "ml/data/external/nyc_subway_stations.csv"
OUT_DIR = BASE / "ml/data/gold"
OUT_FILE = OUT_DIR / "gold_pluto_features.parquet"

# Physical / geographic columns to keep from PLUTO (excludes assessed values)
KEEP_COLS = [
    "BBL",
    "latitude",
    "longitude",
    "numfloors",
    "lotdepth",
    "builtfar",
    "bldgfront",
    "bldgdepth",
    "lotarea",
    "bldgarea",
    "unitsres",
    "yearbuilt",
    "bldgclass",
]


def _haversine_km(lat1: np.ndarray, lon1: np.ndarray,
                  lat2: float, lon2: float) -> np.ndarray:
    """Vectorised haversine distance (km)."""
    R = 6371.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2))
         * np.sin(dlon / 2) ** 2)
    return R * 2 * np.arcsin(np.sqrt(a))


def _subway_dist(pluto: pd.DataFrame, subway: pd.DataFrame) -> pd.Series:
    """Return nearest subway station distance (km) for each PLUTO row."""
    sub_coords = np.radians(
        subway[["GTFS Latitude", "GTFS Longitude"]].values.astype(float)
    )
    tree = BallTree(sub_coords, metric="haversine")

    prop_coords = np.radians(pluto[["latitude", "longitude"]].values.astype(float))
    dist_rad, _ = tree.query(prop_coords, k=1)
    return pd.Series(dist_rad[:, 0] * 6371.0, index=pluto.index)


def main() -> None:
    print("Loading PLUTO …")
    # Read all columns first, then select — usecols lambda has edge-cases with
    # PLUTO's mixed-case headers on some pandas versions.
    pluto_raw = pd.read_csv(PLUTO, dtype=str, low_memory=False)
    # Build a lowercase → original name map for robust selection
    col_map = {c.lower(): c for c in pluto_raw.columns}
    keep_original = [col_map[c.lower()] for c in KEEP_COLS if c.lower() in col_map]
    pluto = pluto_raw[keep_original].copy()
    del pluto_raw  # free memory

    # Normalise column names to lower-case (PLUTO uses 'BBL' capitalised)
    pluto.columns = [c.lower() for c in pluto.columns]
    print(f"  {len(pluto):,} rows loaded")

    # Drop rows with no coordinates — can't compute subway distance or geo features
    pluto = pluto.dropna(subset=["latitude", "longitude"])
    pluto = pluto[(pluto["latitude"] != 0) & (pluto["longitude"] != 0)]
    print(f"  {len(pluto):,} rows with valid coordinates")

    # Normalise BBL to string matching spine format
    pluto["bbl"] = pd.to_numeric(pluto["bbl"], errors="coerce")
    pluto = pluto.dropna(subset=["bbl"])
    pluto["bbl"] = pluto["bbl"].astype(int).astype(str)

    # Derived: building footprint (sq ft)
    if "bldgfront" in pluto.columns and "bldgdepth" in pluto.columns:
        front = pd.to_numeric(pluto["bldgfront"], errors="coerce")
        depth = pd.to_numeric(pluto["bldgdepth"], errors="coerce")
        pluto["bldg_footprint"] = front * depth

    # Subway distance
    print("Loading subway stations …")
    subway = pd.read_csv(SUBWAY)
    subway = subway.dropna(subset=["GTFS Latitude", "GTFS Longitude"])
    print(f"  {len(subway):,} stations")

    print("Computing nearest subway distance (BallTree) …")
    pluto["subway_dist_km"] = _subway_dist(pluto, subway)

    # Rename + prefix for clarity in downstream models
    rename = {
        "numfloors":  "pluto_numfloors",
        "lotdepth":   "pluto_lotdepth",
        "builtfar":   "pluto_builtfar",
        "bldg_footprint": "pluto_bldg_footprint",
        "lotarea":    "pluto_lotarea",
        "bldgarea":   "pluto_bldgarea",
        "unitsres":   "pluto_unitsres",
        "yearbuilt":  "pluto_yearbuilt",
        "bldgclass":  "pluto_bldgclass",
        "latitude":   "pluto_latitude",
        "longitude":  "pluto_longitude",
    }
    pluto = pluto.rename(columns={k: v for k, v in rename.items() if k in pluto.columns})

    # One row per BBL (dedup keeping first — physical features don't change within year)
    before = len(pluto)
    pluto = pluto.drop_duplicates(subset=["bbl"]).reset_index(drop=True)
    if before != len(pluto):
        print(f"  Deduped {before - len(pluto):,} duplicate BBL rows")

    # Cast numeric columns
    num_cols = [c for c in pluto.columns if c != "bbl" and c != "pluto_bldgclass"]
    for c in num_cols:
        pluto[c] = pd.to_numeric(pluto[c], errors="coerce")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pluto.to_parquet(OUT_FILE, index=False)
    print(f"\nWrote {len(pluto):,} rows × {len(pluto.columns)} cols → {OUT_FILE}")
    print(f"Columns: {pluto.columns.tolist()}")


if __name__ == "__main__":
    main()
