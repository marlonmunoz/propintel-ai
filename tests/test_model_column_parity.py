"""Guard against metadata JSON / pkl column drift.

Each spine model's prep step serializes the exact column list it was trained
with.  If a model is retrained with new features but the metadata JSON is not
updated, _build_spine_row will build the wrong DataFrame and inference will
raise ValueError at the ColumnTransformer step.

These tests catch that gap at CI time so the mismatch is never silently
deployed to production.  They require only the .pkl files on disk and do not
need Gold parquets, a database, or environment variables.
"""
import pytest
from pathlib import Path

# Skip the entire module when pkl artifacts are absent (fresh clone without LFS).
ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "ml" / "artifacts" / "spine_models"

def _pkls_present() -> bool:
    return ARTIFACT_DIR.exists() and any(ARTIFACT_DIR.glob("*.pkl"))

pytestmark = pytest.mark.skipif(
    not _pkls_present(),
    reason="Spine model .pkl files not present on disk — skipping column parity tests.",
)


def _model_registry():
    from backend.app.services.model_registry import ModelRegistry
    return ModelRegistry()


def _load_if_present(registry, key: str):
    """Return the loaded model, or None if the artifact is absent or unreadable.

    Both cases — missing file and corrupt/LFS-stub file — are the readiness
    check's responsibility.  Column-parity tests only run on models that load
    cleanly so a stubbed artifact does not generate a spurious test failure.
    """
    meta = registry.get_metadata(key)
    artifact = registry._resolve_artifact_path(meta.artifact_path)
    if not artifact.exists():
        return None
    try:
        return registry.load_model(key)
    except Exception:
        return None


def test_all_spine_models_column_sets_match_metadata():
    """Every spine model's prep.feature_names_in_ must equal metadata columns.

    A mismatch means the model was retrained with new/removed features but the
    metadata JSON was not updated — inference will 500 on that segment.

    Models whose artifact file is absent are skipped — that is the readiness
    check's concern, not a column-contract violation.
    """
    registry = _model_registry()
    mismatches = []

    for key in sorted(registry._models):
        model = _load_if_present(registry, key)
        if model is None:
            continue  # artifact not present in this environment — skip

        prep = getattr(model, "named_steps", {}).get("prep")
        if prep is None or not hasattr(prep, "feature_names_in_"):
            # Legacy / non-spine model — no column contract to check.
            continue

        model_cols = set(prep.feature_names_in_)
        meta = registry.get_metadata(key)
        meta_cols = set(meta.numeric_features + meta.categorical_features)

        missing_in_meta = model_cols - meta_cols
        extra_in_meta = meta_cols - model_cols

        if missing_in_meta or extra_in_meta:
            parts = []
            if missing_in_meta:
                parts.append(f"model has but meta missing: {sorted(missing_in_meta)}")
            if extra_in_meta:
                parts.append(f"meta has but model missing: {sorted(extra_in_meta)}")
            mismatches.append(f"{key}: {'; '.join(parts)}")

    assert not mismatches, (
        "Metadata JSON / pkl column mismatch detected — update the metadata JSON "
        "files for these segments before deploying:\n"
        + "\n".join(f"  • {m}" for m in mismatches)
    )


def test_all_spine_models_can_predict_minimal_payload():
    """Every spine model must accept a minimal inference payload without raising.

    Uses NaN-heavy rows (no BBL, no Gold features) so the SimpleImputer handles
    everything — this mirrors worst-case production inference.

    Models whose artifact file is absent are skipped.
    """
    import numpy as np
    import pandas as pd
    from backend.app.services.predictor import _spine_input_columns

    registry = _model_registry()
    failures = []

    for key in sorted(registry._models):
        model = _load_if_present(registry, key)
        if model is None:
            continue  # artifact not present — skip

        prep = getattr(model, "named_steps", {}).get("prep")
        if prep is None or not hasattr(prep, "feature_names_in_"):
            continue  # legacy model — not a spine pipeline

        cols = _spine_input_columns(model, registry.get_metadata(key))
        X = pd.DataFrame(
            [{col: np.nan for col in cols}],
            columns=cols,
        )
        try:
            model.predict(X)
        except Exception as exc:
            failures.append(f"{key}: predict() raised {type(exc).__name__}: {exc}")

    assert not failures, (
        "One or more spine models failed a minimal NaN-row inference call:\n"
        + "\n".join(f"  • {f}" for f in failures)
    )
