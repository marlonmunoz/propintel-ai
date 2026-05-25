"""Build Gold PLUTO geographic/physical features.

Unlike the DOF/ACRIS/J-51 Gold builders this file does NOT apply an as-of
filter: latitude, longitude, numfloors, lot dimensions, and built FAR are
physical attributes of a parcel that change slowly over decades.  Assessor
values (assesstot, assessland) are intentionally excluded here — the DOF
Gold builder already provides time-indexed assessment data.

Output: ml/data/gold/gold_pluto_features.parquet
  One row per unique BBL.  Join to the spine on ``bbl`` only.

Transit feature pack (v2)
--------------------------
Beyond the original ``subway_dist_km`` we now compute five transit signals
that better capture NYC's price-driving transit dynamics:

  subway_dist_km       — haversine km to nearest station (original)
  subway_n_500m        — count of stations within 0.5 km (5-min walk zone)
  subway_n_1km         — count of stations within 1.0 km (transit-rich zone)
  subway_k3_mean_dist  — mean km to 3 nearest stations (smoother density proxy)
  subway_hub_flag      — 1 if nearest station serves ≥ 2 daytime routes
  subway_cbd_dist_km   — km to nearest CBD-flagged station (commute signal)

Why each one matters
---------------------
* density (n_500m, n_1km): a corner with 3 stations within walking distance
  commands a premium over one with a single nearby stop — especially for
  multi-family and rental properties where commute options drive demand.
* k3_mean_dist: smooths out the single-station outlier; captures "overall
  transit richness" rather than one lucky nearby stop.
* hub_flag: Times Sq, Atlantic Av, Jackson Hts carry route-diversity premiums
  that nearest-distance alone cannot encode.
* cbd_dist_km: outer-borough rentals and multi-family price heavily off
  commute time to Manhattan jobs — nearest CBD station is the cleanest proxy.

Run from repo root:
    python ml/pipelines/gold_pluto_features.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.neighbors import BallTree

BASE      = Path(__file__).resolve().parents[2]
PLUTO     = BASE / "ml/data/pluto_raw/pluto.csv"
SUBWAY    = BASE / "ml/data/external/nyc_subway_stations.csv"
RENTSTAB  = BASE / "ml/data/external/rentstab_counts_2023.csv"
OUT_DIR   = BASE / "ml/data/gold"
OUT_FILE  = OUT_DIR / "gold_pluto_features.parquet"

# Earth radius (km) — used for BallTree radian → km conversions
_R_EARTH = 6371.0

# 0.5 statute miles in km (used for subway line diversity radius)
_R_05MI_KM = 0.8047

# Physical / geographic columns to keep from PLUTO (excludes assessed values)
KEEP_COLS = [
    "BBL",
    "latitude",
    "longitude",
    "numfloors",
    "lotdepth",
    "builtfar",
    "residfar",   # allowed residential FAR → used for far_utilization
    "bldgfront",
    "bldgdepth",
    "lotarea",
    "bldgarea",
    "unitsres",
    "yearbuilt",
    "bldgclass",
]


def _build_transit_features(
    pluto: pd.DataFrame,
    subway: pd.DataFrame,
) -> pd.DataFrame:
    """Compute all transit features and return as a new DataFrame aligned to pluto.index.

    Parameters
    ----------
    pluto:  DataFrame with float columns 'latitude', 'longitude'.
    subway: Raw subway station CSV as a DataFrame.

    Returns
    -------
    DataFrame with columns:
      subway_dist_km, subway_n_500m, subway_n_1km,
      subway_k3_mean_dist_km, subway_hub_flag, subway_cbd_dist_km
    """
    # ── Prepare station arrays ────────────────────────────────────────────────
    sub = subway.dropna(subset=["GTFS Latitude", "GTFS Longitude"]).copy()
    sub["lat"] = sub["GTFS Latitude"].astype(float)
    sub["lon"] = sub["GTFS Longitude"].astype(float)

    # Number of daytime routes per station (hub detection).
    # "Daytime Routes" is a space-separated string like "1 2 3" or "A C E".
    sub["n_routes"] = (
        sub["Daytime Routes"]
        .fillna("")
        .str.strip()
        .str.split()
        .str.len()
        .clip(lower=0)
    )

    # CBD flag — stations marked as CBD in MTA data (Manhattan core job centres).
    sub["is_cbd"] = sub["CBD"].astype(str).str.lower().isin(["true", "1", "yes"])

    all_coords_rad = np.radians(sub[["lat", "lon"]].values)
    tree_all = BallTree(all_coords_rad, metric="haversine")

    # Separate BallTree for CBD-only stations (for subway_cbd_dist_km)
    cbd_sub = sub[sub["is_cbd"]].reset_index(drop=True)
    cbd_coords_rad = np.radians(cbd_sub[["lat", "lon"]].values)
    tree_cbd = BallTree(cbd_coords_rad, metric="haversine")

    # ── Property coordinates ─────────────────────────────────────────────────
    prop_coords_rad = np.radians(
        pluto[["latitude", "longitude"]].values.astype(float)
    )

    # ── 1. Nearest-station distance (km) ─────────────────────────────────────
    dist_rad_1, idx_1 = tree_all.query(prop_coords_rad, k=1)
    subway_dist_km = dist_rad_1[:, 0] * _R_EARTH

    # ── 2. Hub flag — does the nearest station serve 2+ routes? ─────────────
    # This lets the model learn the "transfer hub premium" (Times Sq, Atlantic
    # Av, Jackson Hts, etc.) without encoding individual route identities.
    nearest_n_routes = sub["n_routes"].values[idx_1[:, 0]]
    subway_hub_flag = (nearest_n_routes >= 2).astype(float)

    # ── 3. Station counts within walking-distance radii ──────────────────────
    # 0.5 km ≈ 6-min walk; 1.0 km ≈ 12-min walk.
    # These density signals matter most for rentals (transit-rich pockets in
    # Astoria, Crown Heights, etc.) and outer-borough multi-family.
    r_500m = 0.5 / _R_EARTH   # radians
    r_1km  = 1.0 / _R_EARTH
    counts_500m = tree_all.query_radius(prop_coords_rad, r=r_500m, count_only=True)
    counts_1km  = tree_all.query_radius(prop_coords_rad, r=r_1km,  count_only=True)

    # ── 4. Mean distance to k=3 nearest stations ─────────────────────────────
    # Smooths out the single-lucky-station effect; captures "overall transit
    # richness" — a property near *three* stations is qualitatively different.
    k = min(3, len(sub))
    dist_rad_k, _ = tree_all.query(prop_coords_rad, k=k)
    subway_k3_mean_dist_km = dist_rad_k.mean(axis=1) * _R_EARTH

    # ── 5. Distance to nearest CBD station ───────────────────────────────────
    # The #1 outer-borough price driver for rentals/multi-family is commute
    # time to Manhattan jobs. Distance to the nearest CBD-flagged MTA station
    # is the cleanest, leakage-free proxy for that commute burden.
    if len(cbd_sub) > 0:
        dist_cbd_rad, _ = tree_cbd.query(prop_coords_rad, k=1)
        subway_cbd_dist_km = dist_cbd_rad[:, 0] * _R_EARTH
    else:
        subway_cbd_dist_km = np.full(len(pluto), np.nan)

    # ── 6. Distinct subway lines within 0.5 statute miles ────────────────────
    # Route *diversity* (how many different lines) is qualitatively different
    # from station *count* (subway_n_500m).  A corner with A/C/E + 1/2/3
    # commands a larger premium than a corner with 6 stops of the same line.
    # Returns 0 (not NaN) for properties with no stations in range — the
    # absence of transit is a meaningful zero, not missing data.
    r_05mi = _R_05MI_KM / _R_EARTH  # radians
    all_routes_arr = sub["Daytime Routes"].fillna("").str.strip().values
    station_idx_05mi = tree_all.query_radius(prop_coords_rad, r=r_05mi)
    n_lines_05mi = np.zeros(len(pluto), dtype=float)
    for i, idx_arr in enumerate(station_idx_05mi):
        if len(idx_arr) == 0:
            n_lines_05mi[i] = 0.0  # no stations → 0, not NaN (absence = signal)
        else:
            unique_routes: set[str] = set()
            for j in idx_arr:
                unique_routes.update(str(all_routes_arr[j]).split())
            # Filter out empty strings from "no route" entries
            unique_routes.discard("")
            n_lines_05mi[i] = float(len(unique_routes))

    return pd.DataFrame(
        {
            "subway_dist_km":         subway_dist_km,
            "subway_n_500m":          counts_500m.astype(float),
            "subway_n_1km":           counts_1km.astype(float),
            "subway_k3_mean_dist_km": subway_k3_mean_dist_km,
            "subway_hub_flag":        subway_hub_flag,
            "subway_cbd_dist_km":     subway_cbd_dist_km,
            "subway_n_lines_05mi":    n_lines_05mi,
        },
        index=pluto.index,
    )


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
    pluto = pluto[(pluto["latitude"] != "0") & (pluto["longitude"] != "0")]
    pluto["latitude"]  = pd.to_numeric(pluto["latitude"],  errors="coerce")
    pluto["longitude"] = pd.to_numeric(pluto["longitude"], errors="coerce")
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

    # Derived: FAR utilization — what fraction of allowed residential FAR is built.
    # Guards against residfar = 0 (parks, institutional parcels, irregular zoning)
    # which would produce inf or division-by-zero values.
    if "builtfar" in pluto.columns and "residfar" in pluto.columns:
        builtfar  = pd.to_numeric(pluto["builtfar"],  errors="coerce")
        residfar  = pd.to_numeric(pluto["residfar"],  errors="coerce").fillna(0)
        pluto["far_utilization"] = np.where(
            residfar > 0,
            builtfar / residfar,
            np.nan,  # undefined for zero-residfar lots (parks, institutions)
        )

    # Transit feature pack
    print("Loading subway stations …")
    subway = pd.read_csv(SUBWAY)
    print(f"  {len(subway):,} stations loaded")

    print("Computing transit feature pack (v2) …")
    transit = _build_transit_features(pluto, subway)
    for col in transit.columns:
        pluto[col] = transit[col].values
    print(f"  transit features: {transit.columns.tolist()}")

    # Rent stabilization join ─────────────────────────────────────────────────
    # DHCR rent stabilization counts by BBL (2023 snapshot).
    # ucbbl is a 10-digit integer matching the spine's BBL string format.
    if RENTSTAB.exists():
        print("Joining rent stabilization counts …")
        rs = pd.read_csv(RENTSTAB, usecols=["ucbbl", "uc2023"], dtype={"ucbbl": str})
        rs = rs.rename(columns={"ucbbl": "bbl", "uc2023": "rent_stab_units"})
        rs["bbl"] = rs["bbl"].str.strip().str.zfill(10)
        rs["rent_stab_units"] = pd.to_numeric(rs["rent_stab_units"], errors="coerce")
        pluto["bbl"] = pluto["bbl"].astype(str).str.zfill(10)
        pluto = pluto.merge(rs[["bbl", "rent_stab_units"]], on="bbl", how="left")
        n_matched = pluto["rent_stab_units"].notna().sum()
        print(f"  Matched {n_matched:,} / {len(pluto):,} BBLs with rent-stab data")
    else:
        print(f"  [skip] rentstab CSV not found at {RENTSTAB}")
        pluto["rent_stab_units"] = np.nan

    # Rename + prefix for clarity in downstream models
    rename = {
        "numfloors":       "pluto_numfloors",
        "lotdepth":        "pluto_lotdepth",
        "builtfar":        "pluto_builtfar",
        "far_utilization": "pluto_far_utilization",
        "bldg_footprint":  "pluto_bldg_footprint",
        "lotarea":         "pluto_lotarea",
        "bldgarea":        "pluto_bldgarea",
        "unitsres":        "pluto_unitsres",
        "yearbuilt":       "pluto_yearbuilt",
        "bldgclass":       "pluto_bldgclass",
        "latitude":        "pluto_latitude",
        "longitude":       "pluto_longitude",
    }
    pluto = pluto.rename(columns={k: v for k, v in rename.items() if k in pluto.columns})
    # Drop residfar from output — it was only needed to derive pluto_far_utilization
    pluto = pluto.drop(columns=["residfar"], errors="ignore")

    # One row per BBL (dedup keeping first — physical features don't change within year)
    before = len(pluto)
    pluto = pluto.drop_duplicates(subset=["bbl"]).reset_index(drop=True)
    if before != len(pluto):
        print(f"  Deduped {before - len(pluto):,} duplicate BBL rows")

    # Cast numeric columns (everything except bbl and bldgclass)
    skip_cast = {"bbl", "pluto_bldgclass"}
    for c in pluto.columns:
        if c not in skip_cast:
            pluto[c] = pd.to_numeric(pluto[c], errors="coerce")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pluto.to_parquet(OUT_FILE, index=False)
    print(f"\nWrote {len(pluto):,} rows × {len(pluto.columns)} cols → {OUT_FILE}")
    print(f"Columns: {pluto.columns.tolist()}")


if __name__ == "__main__":
    main()
