"""
Contract test: every building class value in the frontend dropdown must route
to a dedicated (non-global) segment model in the backend registry.

This test reads the canonical list from
  frontend/src/constants/buildingClasses.json
and asserts that ModelRegistry.get_model_key(value) != "global" for each entry.

If this test fails, a building class value in the FE dropdown will silently
fall back to the weakest global model in production.  Fix by either:
  - updating the value string in buildingClasses.json to match the backend, or
  - adding the new class to the appropriate set in ModelRegistry.get_model_key().
"""
import json
from pathlib import Path

import pytest

from backend.app.services.model_registry import ModelRegistry

BUILDING_CLASSES_JSON = (
    Path(__file__).resolve().parents[1]
    / "frontend/src/constants/buildingClasses.json"
)


@pytest.fixture(scope="module")
def registry():
    return ModelRegistry()


@pytest.fixture(scope="module")
def building_classes():
    return json.loads(BUILDING_CLASSES_JSON.read_text(encoding="utf-8"))


def test_building_classes_json_exists():
    assert BUILDING_CLASSES_JSON.exists(), (
        f"Canonical building class list not found at {BUILDING_CLASSES_JSON}. "
        "Run: touch frontend/src/constants/buildingClasses.json"
    )


def test_building_classes_json_not_empty(building_classes):
    assert len(building_classes) > 0, "buildingClasses.json must not be empty."


@pytest.mark.parametrize("cls", json.loads(BUILDING_CLASSES_JSON.read_text()))
def test_building_class_routes_to_dedicated_segment(cls, registry):
    """Assert the value routes to a dedicated model, not the global fallback."""
    value = cls["value"]
    model_key = registry.get_model_key(value)
    assert model_key != "global", (
        f"Building class {value!r} routes to the global fallback model.\n"
        "This means users selecting this class will get the least accurate predictions.\n"
        "Fix: update ModelRegistry.get_model_key() to handle this class, "
        "or remove/correct it in frontend/src/constants/buildingClasses.json."
    )


def test_rental_classes_flagged_correctly(building_classes, registry):
    """Assert all is_rental=True entries are the ones that trigger rental routing."""
    rental_values = {c["value"] for c in building_classes if c["is_rental"]}
    for value in rental_values:
        key = registry.get_model_key(value)
        assert key in ("rentals_all", "rental_walkup", "rental_elevator"), (
            f"Rental class {value!r} routes to {key!r} instead of a rental segment. "
            "Update is_rental in buildingClasses.json or fix the registry routing."
        )
