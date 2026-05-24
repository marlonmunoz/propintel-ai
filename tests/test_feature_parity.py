"""Contract: runtime feature builder must return values consistent with Gold parquet source.

These tests guard against train/serve skew by asserting that:
  1. build_spine_gold_features_from_bbl() returns non-empty features for a known BBL.
  2. _dof_features (the production code path) returns exactly the same values as
     _dof_features_gold (the direct Gold reader) — no rename drift, no computation
     differences.
  3. Key numeric DOF features are finite numbers (not NaN, not Inf).
  4. _acris_features always returns the full set of five expected keys.
  5. build_spine_gold_features_from_bbl reports status='ok' for a BBL with Gold DOF data.

All tests are automatically skipped when Gold parquet files are absent (e.g. a fresh
repo clone or a CI runner that does not mount the ml/data/gold/ volume).
"""
import math
from datetime import date

import pandas as pd
import pytest

from backend.app.services.bbl_feature_builder import (
    GOLD_ACRIS_FEATURES,
    GOLD_DOF_FEATURES,
    _acris_features,
    _dof_features,
    _dof_features_gold,
    build_spine_gold_features_from_bbl,
    normalize_bbl,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _first_bbl_as_of(path):
    """Return (bbl_str, as_of_date) from the first non-null row of a Gold parquet.

    Calls pytest.skip when the file is absent or empty — tests using this
    fixture are skipped automatically in environments without Gold data.
    """
    if not path.exists():
        pytest.skip(f"Gold parquet not present on disk: {path.name}")
    df = pd.read_parquet(path, columns=["bbl", "as_of_date"]).dropna(
        subset=["bbl", "as_of_date"]
    )
    if df.empty:
        pytest.skip(f"Gold parquet has no usable rows: {path.name}")
    row = df.iloc[0]
    bbl = normalize_bbl(row["bbl"])
    if not bbl:
        pytest.skip(f"Could not parse BBL from first row of {path.name}")
    as_of = pd.to_datetime(row["as_of_date"]).date()
    return bbl, as_of


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def dof_sample():
    """(bbl, as_of_date) from the Gold DOF parquet — first row with real assessment data."""
    if not GOLD_DOF_FEATURES.exists():
        pytest.skip("Gold DOF parquet not present on disk")
    # Read only the columns we need to find a data-bearing row; filter to rows
    # where curacttot is populated (properties with no DOF assessment have all
    # feature columns as <NA> and would produce empty feature dicts).
    df = pd.read_parquet(
        GOLD_DOF_FEATURES, columns=["bbl", "as_of_date", "curacttot"]
    ).dropna(subset=["bbl", "as_of_date", "curacttot"])
    if df.empty:
        pytest.skip("Gold DOF parquet has no rows with curacttot data")
    row = df.iloc[0]
    bbl = normalize_bbl(row["bbl"])
    if not bbl:
        pytest.skip("Could not parse BBL from Gold DOF parquet")
    as_of = pd.to_datetime(row["as_of_date"]).date()
    return bbl, as_of


@pytest.fixture(scope="module")
def acris_sample():
    """(bbl, as_of_date) sampled from the Gold ACRIS parquet."""
    return _first_bbl_as_of(GOLD_ACRIS_FEATURES)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_dof_gold_reader_returns_features(dof_sample):
    """_dof_features_gold returns at least one dof_ key for a known BBL."""
    bbl, as_of = dof_sample
    features = _dof_features_gold(bbl, as_of)
    assert features, f"Expected non-empty DOF features for BBL {bbl!r}, got empty dict"
    assert any(k.startswith("dof_") for k in features), (
        f"No dof_* keys in feature dict for BBL {bbl!r}. Keys: {sorted(features)}"
    )


def test_dof_runtime_path_matches_gold_reader(dof_sample):
    """Production path (_dof_features) is identical to the direct Gold reader.

    If this fails, a rename mapping or computation was changed in one path but
    not the other — that is a train/serve skew bug.
    """
    bbl, as_of = dof_sample
    expected = _dof_features_gold(bbl, as_of)
    actual = _dof_features(bbl, as_of)
    assert actual == expected, (
        f"Train/serve skew detected for DOF features on BBL {bbl!r}.\n"
        f"  Gold reader  → {expected}\n"
        f"  Runtime path → {actual}"
    )


def test_dof_numeric_features_are_finite(dof_sample):
    """All numeric DOF feature values must be finite (not NaN, not Inf)."""
    bbl, as_of = dof_sample
    features = _dof_features_gold(bbl, as_of)
    non_finite = {
        k: v
        for k, v in features.items()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v))
    }
    assert not non_finite, (
        f"Non-finite DOF feature values for BBL {bbl!r}: {non_finite}"
    )


def test_acris_returns_all_expected_keys(acris_sample):
    """_acris_features always returns the complete set of five ACRIS keys.

    The model was trained with all five features present (some may be NaN for
    properties with no sales history, but the keys must always exist so
    XGBoost sees a consistent input shape).
    """
    bbl, as_of = acris_sample
    features = _acris_features(bbl, as_of)
    required = {
        "acris_prior_sale_cnt",
        "acris_last_deed_amt",
        "acris_days_since_last_deed",
        "acris_mortgage_cnt",
        "acris_last_mtge_amt",
    }
    missing = required - features.keys()
    assert not missing, (
        f"ACRIS feature dict for BBL {bbl!r} is missing keys: {sorted(missing)}\n"
        f"Got: {sorted(features.keys())}"
    )


def test_build_spine_returns_ok_status_for_known_bbl(dof_sample):
    """build_spine_gold_features_from_bbl returns status='ok' for a BBL with Gold DOF data."""
    bbl, as_of = dof_sample
    features, status = build_spine_gold_features_from_bbl(bbl, as_of)
    assert status == "ok", (
        f"Expected status='ok' for BBL {bbl!r} (present in Gold DOF), got {status!r}"
    )
    assert len(features) >= 5, (
        f"Expected ≥5 features for BBL {bbl!r}, got {len(features)}: {sorted(features)}"
    )
