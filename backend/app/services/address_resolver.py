"""
Server-side BBL resolution from a free-form address string.

Production implementation of the ``resolved_address`` mode measured in
``ml/scripts/eval_serving_path.py`` (Phase 1 result: 94.2% resolve rate,
100% precision among resolved, on 905 out-of-sample 2025-26 sales — median
APE 28.4% -> 21.1%, R2 0.30 -> 0.75). That script imports ``resolve_bbl``
from this module rather than re-implementing it, so the accuracy measured
offline is guaranteed to be the accuracy served here — see the module
docstring in ``ml/features/address_normalize.py`` for why that guarantee
matters.

Loads the offline index built by ``ml/pipelines/build_address_bbl_index.py``
from PLUTO raw (``ml/data/gold/address_bbl_index.parquet`` — included in the
Docker image, same as every other Gold table).

Abstains (returns None) rather than guesses whenever there is doubt. A wrong
BBL was measured to be worse than none: the lat/lon-based alternative
(``resolved_bbl`` mode) was rejected for exactly this reason — see that
mode's docstring in eval_serving_path.py.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from ml.features.address_normalize import normalize_address

logger = logging.getLogger("propintel")

BASE_DIR = Path(__file__).resolve().parents[3]
ADDRESS_INDEX_PATH = BASE_DIR / "ml/data/gold/address_bbl_index.parquet"
GOLD_PLUTO = BASE_DIR / "ml/data/gold/gold_pluto_features.parquet"

# Condo unit classes (real-property unit lots, not the base parcel). A condo
# address resolves unambiguously to PLUTO's condo MASTER/billing lot, which
# looks confident and is never the unit actually sold (measured at 0%
# precision in ml/pipelines/build_address_bbl_index.py). Hard-excluded here
# too, not just at index-build time, as defense in depth against that file
# ever being rebuilt without the same exclusion.
CONDO_UNIT_CLASSES = ("12", "13", "15")

# A resolved lot's PLUTO centroid should sit near the coordinates the client
# already sent (from Mapbox geocoding the same address). Anything farther is
# treated as a normalization collision or mismatched borough, not a real
# match. This guard has no effect on the Phase 1 backtest numbers above —
# there, latitude/longitude come from the TRUE bbl's own centroid, so a
# correct resolution always has ~0 drift — it exists purely to catch cases
# real production traffic can hit that a historical backtest can't.
MAX_CENTROID_DRIFT_KM = 1.0
EARTH_RADIUS_KM = 6_371.0


@lru_cache(maxsize=1)
def _address_index() -> dict[tuple[str, int], str] | None:
    """(normalized_address, borough_num) -> bbl. None when the artifact is missing.

    lru_cache(maxsize=1) both memoizes the ~800k-row parquet across requests
    and caches a missing/failed load as None, so a bad deployment doesn't
    retry the read on every single analyze call.
    """
    if not ADDRESS_INDEX_PATH.exists():
        logger.warning(
            "address_resolver: index not found at %s — address-based BBL "
            "resolution disabled for this deployment.", ADDRESS_INDEX_PATH,
        )
        return None
    try:
        idx = pd.read_parquet(ADDRESS_INDEX_PATH)
        return dict(
            zip(zip(idx["norm_address"], idx["borough_num"].astype(int)), idx["bbl"])
        )
    except Exception:
        logger.exception("address_resolver: failed to load %s", ADDRESS_INDEX_PATH)
        return None


@lru_cache(maxsize=1)
def _pluto_centroids() -> dict[str, tuple[float, float]] | None:
    """bbl -> (lat, lon), used only for the post-resolution drift guard."""
    if not GOLD_PLUTO.exists():
        return None
    try:
        df = pd.read_parquet(
            GOLD_PLUTO, columns=["bbl", "pluto_latitude", "pluto_longitude"]
        ).dropna(subset=["pluto_latitude", "pluto_longitude"])
        return dict(zip(
            df["bbl"].astype(str).str.strip(),
            zip(df["pluto_latitude"].astype(float), df["pluto_longitude"].astype(float)),
        ))
    except Exception:
        logger.exception("address_resolver: failed to load %s", GOLD_PLUTO)
        return None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dlambda / 2) ** 2
    return float(2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a)))


def resolve_bbl(
    address: str | None,
    borough_num: int | None,
    building_class: str | None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> str | None:
    """Resolve a BBL from a free-form address, or None to abstain.

    ``borough_num`` is the numeric 1-5 code (Manhattan=1 ... Staten Island=5),
    matching the index built by build_address_bbl_index.py. Abstains for: an
    unparseable address, a condo unit class, no unambiguous index entry, or
    (when lat/lon are supplied) a resolved lot whose PLUTO centroid sits
    implausibly far from the client's coordinates.
    """
    if building_class and str(building_class).strip().startswith(CONDO_UNIT_CLASSES):
        return None

    norm = normalize_address(address)
    if norm is None or borough_num is None:
        return None

    index = _address_index()
    if index is None:
        return None

    found = index.get((norm, int(borough_num)))
    if found is None:
        return None

    if latitude is not None and longitude is not None:
        centroids = _pluto_centroids()
        centroid = centroids.get(found) if centroids else None
        if centroid is not None:
            drift_km = _haversine_km(float(latitude), float(longitude), centroid[0], centroid[1])
            if drift_km > MAX_CENTROID_DRIFT_KM:
                logger.info(
                    "address_resolver: abstaining on bbl=%s — resolved centroid "
                    "%.2f km from client coordinates (guard: %.1f km)",
                    found, drift_km, MAX_CENTROID_DRIFT_KM,
                )
                return None

    return found
