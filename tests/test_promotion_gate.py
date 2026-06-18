"""
Tests for ml/scripts/promote_models.py — the model promotion gate.

These tests run without any real .pkl files or parquet data.
They use tmp_path fixtures to create synthetic spine_model_metrics.json
and metadata JSON files, then verify the promotion gate logic.
"""

import json
import sys
from pathlib import Path

import pytest

# ── Import the module under test ──────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ml.scripts.promote_models import run, _bump_version

# ── Fixtures ──────────────────────────────────────────────────────────────────

def _make_metrics_file(directory: Path, segments: list[dict]) -> Path:
    """Write a synthetic spine_model_metrics.json."""
    p = directory / "spine_model_metrics.json"
    p.write_text(json.dumps(segments, indent=2), encoding="utf-8")
    return p


def _make_metadata_file(directory: Path, segment: str, baseline_mae: float, version: str = "v1") -> Path:
    """Write a minimal metadata JSON mimicking the real format."""
    meta = {
        "name": f"{segment}_spine",
        "version": version,
        "segment": segment,
        "artifact_path": f"ml/artifacts/spine_models/{segment}_spine_price_model.pkl",
        "metrics": {
            "mae": baseline_mae,
            "rmse": baseline_mae * 1.8,
            "r2": 0.70,
            "median_ape": 0.15,
            "note": "baseline",
        },
    }
    p = directory / f"{segment}_model.json"
    p.write_text(json.dumps(meta, indent=4), encoding="utf-8")
    return p


def _candidate_row(segment: str, test_mae: float, **kwargs) -> dict:
    return {
        "segment": segment,
        "train_rows": 10000,
        "test_rows": 2000,
        "train_r2": 0.85,
        "test_r2": kwargs.get("test_r2", 0.72),
        "test_mae": test_mae,
        "test_rmse": test_mae * 1.8,
        "test_median_ape": kwargs.get("test_median_ape", 0.14),
        "model_path": f"/fake/{segment}_spine_price_model.pkl",
    }


# ── _bump_version ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("before, after", [
    ("v1",  "v2"),
    ("v2",  "v3"),
    ("v10", "v11"),
    ("1.0", "1.1"),
    ("abc", "abc.2"),
])
def test_bump_version(before, after):
    assert _bump_version(before) == after


# ── Gate logic ────────────────────────────────────────────────────────────────

def test_candidate_better_than_baseline_passes(tmp_path):
    """A lower MAE than baseline must pass."""
    import ml.scripts.promote_models as pm
    original_metadata = pm.METADATA_DIR
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    pm.METADATA_DIR = metadata_dir
    try:
        metrics_file = _make_metrics_file(tmp_path, [_candidate_row("one_family", test_mae=200_000)])
        _make_metadata_file(metadata_dir, "one_family", baseline_mae=250_000)

        code = run(
            tolerance=0.05,
            dry_run=True,
            segments=None,
            metrics_path=metrics_file,
        )
        assert code == 0
    finally:
        pm.METADATA_DIR = original_metadata


def test_candidate_within_tolerance_passes(tmp_path):
    """MAE 4% above baseline should pass with 5% tolerance."""
    import ml.scripts.promote_models as pm
    original_metadata = pm.METADATA_DIR
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    pm.METADATA_DIR = metadata_dir
    try:
        metrics_file = _make_metrics_file(tmp_path, [_candidate_row("one_family", test_mae=260_000)])
        _make_metadata_file(metadata_dir, "one_family", baseline_mae=250_000)

        code = run(
            tolerance=0.05,
            dry_run=True,
            segments=None,
            metrics_path=metrics_file,
        )
        assert code == 0
    finally:
        pm.METADATA_DIR = original_metadata


def test_candidate_exceeds_tolerance_fails(tmp_path):
    """MAE 10% above baseline must fail with 5% tolerance."""
    import ml.scripts.promote_models as pm
    original_metadata = pm.METADATA_DIR
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    pm.METADATA_DIR = metadata_dir
    try:
        metrics_file = _make_metrics_file(tmp_path, [_candidate_row("one_family", test_mae=275_001)])
        _make_metadata_file(metadata_dir, "one_family", baseline_mae=250_000)

        code = run(
            tolerance=0.05,
            dry_run=True,
            segments=None,
            metrics_path=metrics_file,
        )
        assert code == 1
    finally:
        pm.METADATA_DIR = original_metadata


def test_all_segments_must_pass(tmp_path):
    """If even one segment regresses, the whole gate fails (exit 1)."""
    import ml.scripts.promote_models as pm
    original_metadata = pm.METADATA_DIR
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    pm.METADATA_DIR = metadata_dir
    try:
        metrics_file = _make_metrics_file(tmp_path, [
            _candidate_row("one_family",  test_mae=240_000),   # passes
            _candidate_row("condo_coop",  test_mae=600_000),   # fails (baseline 400k)
        ])
        _make_metadata_file(metadata_dir, "one_family", baseline_mae=250_000)
        _make_metadata_file(metadata_dir, "condo_coop", baseline_mae=400_000)

        code = run(
            tolerance=0.05,
            dry_run=True,
            segments=None,
            metrics_path=metrics_file,
        )
        assert code == 1
    finally:
        pm.METADATA_DIR = original_metadata


def test_promotion_writes_metadata_and_bumps_version(tmp_path):
    """On full pass, metadata JSON is updated and version is bumped."""
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    eval_reports_dir = tmp_path / "eval_reports"
    # Patch the module-level paths so the script writes into tmp_path.
    import ml.scripts.promote_models as pm
    original_metadata = pm.METADATA_DIR
    original_eval_dir = pm.EVAL_REPORTS_DIR
    pm.METADATA_DIR = metadata_dir
    pm.EVAL_REPORTS_DIR = eval_reports_dir

    try:
        metrics_file = _make_metrics_file(tmp_path, [_candidate_row("two_family", test_mae=200_000)])
        _make_metadata_file(metadata_dir, "two_family", baseline_mae=250_000, version="v2")

        code = run(
            tolerance=0.05,
            dry_run=False,
            segments=None,
            metrics_path=metrics_file,
        )
        assert code == 0

        # Version bumped
        updated = json.loads((metadata_dir / "two_family_model.json").read_text())
        assert updated["version"] == "v3"

        # Metrics updated with rounded candidate value
        assert updated["metrics"]["mae"] == pytest.approx(200_000, abs=1)

        # Audit report written
        reports = list(eval_reports_dir.glob("promotion_report_*.json"))
        assert len(reports) == 1
        report = json.loads(reports[0].read_text())
        assert report["segments"][0]["segment"] == "two_family"
        assert report["segments"][0]["new_version"] == "v3"

    finally:
        pm.METADATA_DIR = original_metadata
        pm.EVAL_REPORTS_DIR = original_eval_dir


def test_dry_run_does_not_write_files(tmp_path):
    """--dry-run must not modify any files."""
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    import ml.scripts.promote_models as pm
    original_metadata = pm.METADATA_DIR
    original_eval_dir = pm.EVAL_REPORTS_DIR
    pm.METADATA_DIR = metadata_dir
    pm.EVAL_REPORTS_DIR = tmp_path / "eval_reports"

    try:
        metrics_file = _make_metrics_file(tmp_path, [_candidate_row("one_family", test_mae=200_000)])
        meta_file = _make_metadata_file(metadata_dir, "one_family", baseline_mae=250_000, version="v1")
        original_mtime = meta_file.stat().st_mtime

        code = run(
            tolerance=0.05,
            dry_run=True,
            segments=None,
            metrics_path=metrics_file,
        )
        assert code == 0
        # Metadata file untouched
        assert meta_file.stat().st_mtime == original_mtime
        # No eval report written
        assert not (tmp_path / "eval_reports").exists()

    finally:
        pm.METADATA_DIR = original_metadata
        pm.EVAL_REPORTS_DIR = original_eval_dir


def test_segment_filter_only_checks_requested(tmp_path):
    """--segments restricts the gate to only the specified segments."""
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    import ml.scripts.promote_models as pm
    original_metadata = pm.METADATA_DIR
    pm.METADATA_DIR = metadata_dir

    try:
        # condo_coop would fail, but it's not in --segments
        metrics_file = _make_metrics_file(tmp_path, [
            _candidate_row("one_family", test_mae=240_000),
            _candidate_row("condo_coop", test_mae=900_000),
        ])
        _make_metadata_file(metadata_dir, "one_family", baseline_mae=250_000)
        _make_metadata_file(metadata_dir, "condo_coop", baseline_mae=400_000)

        code = run(
            tolerance=0.05,
            dry_run=True,
            segments=["one_family"],   # ignore condo_coop
            metrics_path=metrics_file,
        )
        assert code == 0

    finally:
        pm.METADATA_DIR = original_metadata


def test_first_promotion_no_baseline_autopasses(tmp_path):
    """A segment with no baseline MAE (first-ever promotion) should auto-pass."""
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    import ml.scripts.promote_models as pm
    original_metadata = pm.METADATA_DIR
    pm.METADATA_DIR = metadata_dir

    try:
        metrics_file = _make_metrics_file(tmp_path, [_candidate_row("one_family", test_mae=300_000)])
        # metadata has no metrics.mae
        meta = {
            "name": "one_family_spine", "version": "v1", "segment": "one_family",
            "artifact_path": "ml/artifacts/spine_models/one_family_spine_price_model.pkl",
            "metrics": {},    # no mae field
        }
        (metadata_dir / "one_family_model.json").write_text(json.dumps(meta))

        code = run(
            tolerance=0.05,
            dry_run=True,
            segments=None,
            metrics_path=metrics_file,
        )
        assert code == 0

    finally:
        pm.METADATA_DIR = original_metadata
