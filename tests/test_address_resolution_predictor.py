"""Integration: PredictionService resolves a BBL from address when the client
doesn't send one directly, and always prefers a client-supplied bbl.

Guards the wiring added to backend/app/services/predictor.py (Phase 2 of
address-based BBL resolution — productionizes the resolved_address mode
measured in ml/scripts/eval_serving_path.py).
"""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from backend.app.schemas.prediction import ProductionAnalyzeRequest, ProductionPredictionRequest
from backend.app.services.address_resolver import ADDRESS_INDEX_PATH
from backend.app.services.model_registry import ModelRegistry
from backend.app.services.predictor import PredictionService

REPO_ROOT = Path(__file__).resolve().parents[1]
SPINE_PATH = REPO_ROOT / "ml" / "data" / "gold" / "training_spine_v1.parquet"
GOLD_PLUTO = REPO_ROOT / "ml" / "data" / "gold" / "gold_pluto_features.parquet"
ARTIFACT_DIR = REPO_ROOT / "ml" / "artifacts" / "spine_models"

# Reverse of BOROUGH_NUM in predictor.py. The spine's own "borough_label"
# column is the numeric 1-5 code, not a name — a real client request sends a
# name like "Brooklyn" (see ProductionPredictionRequest.borough), which is
# what predictor.py needs to resolve borough_num for address lookup. Building
# the payload from the numeric code directly (as eval_serving_path.py does,
# for a different reason — it isolates the *model's* behavior from parsing)
# would silently skip resolution here instead of testing it.
BOROUGH_NAME = {1: "Manhattan", 2: "Bronx", 3: "Brooklyn", 4: "Queens", 5: "Staten Island"}


def _pkls_present() -> bool:
    return ARTIFACT_DIR.exists() and any(ARTIFACT_DIR.glob("*.pkl"))


pytestmark = pytest.mark.skipif(
    not (_pkls_present() and ADDRESS_INDEX_PATH.exists()),
    reason="Spine model artifacts or address index not present on disk.",
)


@pytest.fixture(scope="module")
def known_one_family_sale():
    """A real one_family spine row this deployment's address index resolves correctly."""
    if not SPINE_PATH.exists() or not GOLD_PLUTO.exists():
        pytest.skip("Gold parquet files not present on disk")

    from backend.app.services.address_resolver import resolve_bbl

    spine = pd.read_parquet(
        SPINE_PATH,
        columns=["address", "borough", "borough_label", "neighborhood", "bbl",
                 "segment", "building_class", "year_built", "gross_sqft"],
    )
    spine = spine[spine["segment"] == "one_family"].dropna(
        subset=["address", "borough", "bbl", "neighborhood", "year_built", "gross_sqft"]
    )
    pluto = pd.read_parquet(
        GOLD_PLUTO, columns=["bbl", "pluto_latitude", "pluto_longitude"]
    ).dropna(subset=["pluto_latitude", "pluto_longitude"])
    pluto["bbl"] = pluto["bbl"].astype(str).str.strip()
    spine["bbl"] = spine["bbl"].astype(str).str.strip()
    merged = spine.merge(pluto, on="bbl", how="inner")

    for _, row in merged.head(200).iterrows():
        found = resolve_bbl(row["address"], int(row["borough"]), row["building_class"])
        if found == row["bbl"]:
            return row
    pytest.skip("No resolvable one_family row found in the first 200 sampled rows")


def _payload(row, **overrides) -> ProductionPredictionRequest:
    kwargs = dict(
        borough=BOROUGH_NAME[int(row["borough"])],
        neighborhood=str(row["neighborhood"]),
        building_class=str(row["building_class"]),
        year_built=int(row["year_built"]),
        gross_sqft=float(row["gross_sqft"]),
        latitude=float(row["pluto_latitude"]),
        longitude=float(row["pluto_longitude"]),
    )
    kwargs.update(overrides)
    return ProductionPredictionRequest(**kwargs)


def test_predict_resolves_bbl_from_address_when_none_supplied(known_one_family_sale):
    row = known_one_family_sale
    service = PredictionService(ModelRegistry())
    payload = _payload(row, address=row["address"])

    out = service.predict(payload)

    assert out["input_summary"]["bbl_source"] == "address"
    assert out["input_summary"]["bbl"] == row["bbl"]
    assert out["input_summary"]["bbl_feature_status"] in ("ok", "partial")


def test_predict_prefers_client_bbl_over_address(known_one_family_sale):
    """A client-supplied bbl always wins — address resolution is a fallback only."""
    row = known_one_family_sale
    service = PredictionService(ModelRegistry())
    payload = _payload(
        row,
        address="1 SOME OTHER STREET THAT WOULD NOT RESOLVE",
        bbl=row["bbl"],
        as_of_date=date.today(),
    )

    out = service.predict(payload)

    assert out["input_summary"]["bbl_source"] == "client"
    assert out["input_summary"]["bbl"] == row["bbl"]


def test_predict_falls_back_gracefully_for_unresolvable_address(known_one_family_sale):
    row = known_one_family_sale
    service = PredictionService(ModelRegistry())
    payload = _payload(row, address="1 COMPLETELY MADE UP STREET THAT DOES NOT EXIST")

    out = service.predict(payload)

    assert "bbl_source" not in out["input_summary"]
    assert out["input_summary"]["bbl_feature_status"] == "skipped"
    assert out["predicted_price"] > 0


def test_predict_without_address_or_bbl_is_unaffected(known_one_family_sale):
    """No address, no bbl — behaves exactly as before this feature existed."""
    row = known_one_family_sale
    service = PredictionService(ModelRegistry())
    payload = _payload(row)

    out = service.predict(payload)

    assert "bbl_source" not in out["input_summary"]
    assert out["input_summary"]["bbl_feature_status"] == "skipped"


def test_analyze_surfaces_bbl_enhancement_in_metadata(known_one_family_sale):
    """analyze() (used by /analyze-property-v2) must expose bbl_source /
    bbl_enhanced too — predict() already did, but analyze() previously
    dropped input_summary entirely, leaving the UI with no way to show
    whether a valuation actually used resolved property records."""
    row = known_one_family_sale
    service = PredictionService(ModelRegistry())
    kwargs = _payload(row, address=row["address"]).model_dump()
    payload = ProductionAnalyzeRequest(**kwargs, market_price=500_000.0)

    out = service.analyze(payload, include_explanation=False)

    assert out["metadata"]["bbl_source"] == "address"
    assert out["metadata"]["bbl_enhanced"] is True


def test_analyze_omits_bbl_metadata_when_no_bbl_resolved(known_one_family_sale):
    row = known_one_family_sale
    service = PredictionService(ModelRegistry())
    kwargs = _payload(row).model_dump()
    payload = ProductionAnalyzeRequest(**kwargs, market_price=500_000.0)

    out = service.analyze(payload, include_explanation=False)

    assert "bbl_source" not in out["metadata"]
    assert "bbl_enhanced" not in out["metadata"]
