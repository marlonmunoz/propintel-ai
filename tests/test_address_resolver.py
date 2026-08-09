"""Contract tests for server-side address-based BBL resolution.

Guards backend/app/services/address_resolver.py — the production twin of the
resolved_address mode measured in ml/scripts/eval_serving_path.py (Phase 1
result: 94.2% resolve rate, 100% precision among resolved, on 905
out-of-sample 2025-26 sales; median APE 28.4% -> 21.1%).

Skipped entirely when the address index artifact is absent (fresh clone
without the ml/data/gold/ volume) — same convention as test_feature_parity.py.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from backend.app.services.address_resolver import (
    ADDRESS_INDEX_PATH,
    CONDO_UNIT_CLASSES,
    resolve_bbl,
)
from ml.features.address_normalize import normalize_address

pytestmark = pytest.mark.skipif(
    not ADDRESS_INDEX_PATH.exists(),
    reason="address_bbl_index.parquet not present on disk — skipping resolver tests.",
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SPINE_PATH = REPO_ROOT / "ml" / "data" / "gold" / "training_spine_v1.parquet"
GOLD_PLUTO = REPO_ROOT / "ml" / "data" / "gold" / "gold_pluto_features.parquet"


@pytest.fixture(scope="module")
def known_match():
    """(address, borough_num, bbl, lat, lon) for a real, resolvable one_family sale.

    Sourced from the training spine joined to Gold PLUTO — real addresses the
    index is known to resolve at >99% precision for one_family (measured in
    ml/pipelines/build_address_bbl_index.py).
    """
    if not SPINE_PATH.exists() or not GOLD_PLUTO.exists():
        pytest.skip("Training spine or Gold PLUTO parquet not present on disk")

    spine = pd.read_parquet(
        SPINE_PATH, columns=["address", "borough", "bbl", "segment"]
    )
    spine = spine[spine["segment"] == "one_family"].dropna(
        subset=["address", "borough", "bbl"]
    )
    pluto = pd.read_parquet(
        GOLD_PLUTO, columns=["bbl", "pluto_latitude", "pluto_longitude"]
    ).dropna(subset=["pluto_latitude", "pluto_longitude"])
    pluto["bbl"] = pluto["bbl"].astype(str).str.strip()
    spine["bbl"] = spine["bbl"].astype(str).str.strip()

    merged = spine.merge(pluto, on="bbl", how="inner")
    if merged.empty:
        pytest.skip("No one_family spine row with a Gold PLUTO coordinate match")

    for _, row in merged.head(200).iterrows():
        borough_num = int(row["borough"])
        true_bbl = str(row["bbl"]).strip()
        found = resolve_bbl(row["address"], borough_num, "01 ONE FAMILY DWELLINGS")
        if found == true_bbl:
            return {
                "address": row["address"],
                "borough_num": borough_num,
                "bbl": true_bbl,
                "lat": float(row["pluto_latitude"]),
                "lon": float(row["pluto_longitude"]),
            }
    pytest.skip("No resolvable one_family row found in the first 200 sampled rows")


def test_resolve_known_address_returns_correct_bbl(known_match):
    found = resolve_bbl(
        known_match["address"], known_match["borough_num"], "01 ONE FAMILY DWELLINGS"
    )
    assert found == known_match["bbl"]


def test_resolve_with_correct_coordinates_does_not_abstain(known_match):
    """The drift guard must not reject a match whose centroid genuinely agrees."""
    found = resolve_bbl(
        known_match["address"], known_match["borough_num"], "01 ONE FAMILY DWELLINGS",
        latitude=known_match["lat"], longitude=known_match["lon"],
    )
    assert found == known_match["bbl"]


def test_resolve_abstains_when_coordinates_are_far_away(known_match):
    """Coordinate drift guard: a resolved lot whose PLUTO centroid is far from
    the client's coordinates is treated as a mismatch, not trusted — even
    though the address itself matched. ~1 degree latitude is ~111 km."""
    found = resolve_bbl(
        known_match["address"], known_match["borough_num"], "01 ONE FAMILY DWELLINGS",
        latitude=known_match["lat"] + 1.0, longitude=known_match["lon"],
    )
    assert found is None


@pytest.mark.parametrize("condo_class", CONDO_UNIT_CLASSES)
def test_resolve_abstains_for_condo_unit_classes(known_match, condo_class):
    """Condo unit classes never resolve, even for an address that would
    otherwise match — a condo address resolves to PLUTO's master lot, not
    the individual unit sold (see build_address_bbl_index.py)."""
    found = resolve_bbl(
        known_match["address"], known_match["borough_num"], f"{condo_class} CONDOS"
    )
    assert found is None


def test_resolve_abstains_for_blank_address():
    assert resolve_bbl("", 1, "01 ONE FAMILY DWELLINGS") is None
    assert resolve_bbl(None, 1, "01 ONE FAMILY DWELLINGS") is None


def test_resolve_abstains_for_unknown_borough(known_match):
    assert resolve_bbl(known_match["address"], None, "01 ONE FAMILY DWELLINGS") is None


def test_resolve_abstains_for_unmatched_address():
    assert resolve_bbl("1 COMPLETELY MADE UP STREET THAT DOES NOT EXIST", 1,
                        "01 ONE FAMILY DWELLINGS") is None


def test_resolve_sample_address_normalizes_to_a_real_key(known_match):
    """Sanity check on the fixture itself, not just the resolver."""
    assert normalize_address(known_match["address"]) is not None


def test_resolve_returns_none_when_index_missing(monkeypatch):
    """A missing/corrupt index artifact must fail closed (abstain), never raise."""
    import backend.app.services.address_resolver as resolver

    resolver._address_index.cache_clear()
    monkeypatch.setattr(resolver, "ADDRESS_INDEX_PATH", Path("/nonexistent/path.parquet"))
    try:
        assert resolver.resolve_bbl("123 MAIN ST", 1, "01 ONE FAMILY DWELLINGS") is None
    finally:
        resolver._address_index.cache_clear()
