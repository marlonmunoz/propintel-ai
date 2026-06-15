from backend.app.services.model_confidence import (
    build_model_confidence_metadata,
    resolve_confidence_tier,
    segment_display_name,
)


def test_resolve_confidence_tier_high_segments():
    assert resolve_confidence_tier("one_family") == "high"
    assert resolve_confidence_tier("condo") == "high"
    assert resolve_confidence_tier("multi_family") == "high"


def test_resolve_confidence_tier_directional_segments():
    assert resolve_confidence_tier("coop") == "directional"
    assert resolve_confidence_tier("rentals_all") == "directional"


def test_resolve_confidence_tier_fallback():
    assert resolve_confidence_tier("global") == "fallback"
    assert resolve_confidence_tier(None) == "fallback"


def test_build_model_confidence_metadata_includes_median_ape():
    meta = build_model_confidence_metadata(
        "coop",
        {"median_ape": 0.244},
    )
    assert meta["segment"] == "coop"
    assert meta["segment_label"] == "Co-op"
    assert meta["model_confidence_tier"] == "directional"
    assert meta["model_confidence_label"] == "Directional estimate"
    assert "24.4%" in meta["model_confidence_note"]


def test_segment_display_name_unknown():
    assert segment_display_name("custom_segment") == "Custom Segment"
