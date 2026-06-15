"""Per-segment model confidence tiers for API responses and UI disclosure."""

from __future__ import annotations

from typing import Any, Literal

ModelConfidenceTier = Literal["high", "directional", "fallback"]

_HIGH_CONFIDENCE_SEGMENTS = frozenset({
    "one_family",
    "multi_family",
    "condo",
    "two_family",
    "three_family",
})

_DIRECTIONAL_SEGMENTS = frozenset({
    "coop",
    "rentals_all",
    "rental_walkup",
    "rental_elevator",
    "condo_coop",
})

_SEGMENT_LABELS: dict[str, str] = {
    "one_family": "One-family",
    "multi_family": "Multi-family",
    "two_family": "Two-family",
    "three_family": "Three-family",
    "condo": "Condo",
    "coop": "Co-op",
    "condo_coop": "Condo / Co-op",
    "rentals_all": "Rental building",
    "rental_walkup": "Walk-up rental",
    "rental_elevator": "Elevator rental",
    "global": "General residential",
}

_TIER_LABELS: dict[ModelConfidenceTier, str] = {
    "high": "High confidence",
    "directional": "Directional estimate",
    "fallback": "Broad estimate",
}

_TIER_NOTES: dict[ModelConfidenceTier, str] = {
    "high": (
        "This segment model is trained on sufficient NYC sales data for this "
        "building type. Use the valuation as a primary underwriting input."
    ),
    "directional": (
        "This segment has weaker public data coverage (e.g. co-op shares or "
        "rental income signals). Treat the valuation as directional — useful "
        "for comparison, not as a precise price target."
    ),
    "fallback": (
        "No dedicated segment model matched this building class. A general "
        "citywide residential model was used instead — expect wider error."
    ),
}


def segment_display_name(segment: str | None) -> str:
    if not segment:
        return "Unknown segment"
    return _SEGMENT_LABELS.get(segment, segment.replace("_", " ").title())


def resolve_confidence_tier(segment: str | None) -> ModelConfidenceTier:
    key = (segment or "").strip().lower()
    if key in _HIGH_CONFIDENCE_SEGMENTS:
        return "high"
    if key in _DIRECTIONAL_SEGMENTS:
        return "directional"
    return "fallback"


def build_model_confidence_metadata(
    segment: str | None,
    model_metrics: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Return metadata fields for ProductionAnalyzeResponse.metadata."""
    tier = resolve_confidence_tier(segment)
    note = _TIER_NOTES[tier]
    median_ape = (model_metrics or {}).get("median_ape")
    if median_ape is not None:
        try:
            pct = round(float(median_ape) * 100, 1)
            note = f"{note} Typical median error for this segment: ~{pct}%."
        except (TypeError, ValueError):
            pass

    return {
        "segment": segment or "global",
        "segment_label": segment_display_name(segment),
        "model_confidence_tier": tier,
        "model_confidence_label": _TIER_LABELS[tier],
        "model_confidence_note": note,
    }
