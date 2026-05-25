"""
Model promotion gate — Phase 6.2.

Run this script after a successful training run (train_spine_models.py) to
decide whether the new models are safe to promote to production.

HOW IT WORKS
============
1. Reads candidate metrics from:
       ml/artifacts/spine_models/spine_model_metrics.json
   (written by train_spine_models.py for every segment trained).

2. For each segment in the candidate file it reads the current promoted
   baseline from:
       ml/artifacts/metadata/{segment}_model.json
   and applies the primary gate:

       candidate_test_mae <= baseline_mae * (1 + --tolerance)

   Default tolerance is 5% (--tolerance 0.05).

3. Prints a per-segment pass/fail table with MAE, R², and median APE.

4. If every segment passes AND --dry-run is NOT set:
   • Updates metrics + bumps version in each metadata JSON.
   • Writes a timestamped audit record to:
         ml/artifacts/eval_reports/promotion_report_{timestamp}.json

5. If any segment fails (regression beyond tolerance) → exits with code 1.
   The .pkl files are NOT touched — the old models keep serving.

TYPICAL WORKFLOW
================
    # 1. Train
    python ml/models/train_spine_models.py

    # 2. Inspect (safe — reads only)
    python ml/scripts/promote_models.py --dry-run

    # 3. Promote
    python ml/scripts/promote_models.py

    # 4. Commit the updated metadata JSONs
    git add ml/artifacts/metadata/ ml/artifacts/eval_reports/
    git commit -m "promote: <segments> <version>"

EXIT CODES
==========
    0  — all segments passed (and promoted, unless --dry-run)
    1  — one or more segments regressed beyond tolerance
    2  — usage / configuration error (missing file, bad JSON, etc.)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
METADATA_DIR = BASE_DIR / "ml" / "artifacts" / "metadata"
SPINE_METRICS = BASE_DIR / "ml" / "artifacts" / "spine_models" / "spine_model_metrics.json"
EVAL_REPORTS_DIR = BASE_DIR / "ml" / "artifacts" / "eval_reports"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict | list:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[ERROR] File not found: {path}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as exc:
        print(f"[ERROR] Invalid JSON in {path}: {exc}", file=sys.stderr)
        sys.exit(2)


def _bump_version(version: str) -> str:
    """
    Increment the trailing integer in a version tag.

    "v2"   → "v3"
    "v10"  → "v11"
    "1.0"  → "1.1"    (bumps the last numeric component)
    "abc"  → "abc.2"  (appends .2 when no integer found)
    """
    m = re.search(r"(\d+)([^\d]*)$", version)
    if m:
        return version[: m.start()] + str(int(m.group(1)) + 1) + m.group(2)
    return version + ".2"


def _fmt(value: float | None, fmt: str = ".0f") -> str:
    if value is None:
        return "—"
    return format(value, fmt)


# ── Core logic ────────────────────────────────────────────────────────────────

def run(
    tolerance: float,
    dry_run: bool,
    segments: list[str] | None,
    metrics_path: Path,
) -> int:
    """
    Returns 0 on success, 1 on gate failure.
    """

    # ── 1. Load candidate metrics ─────────────────────────────────────────────
    candidates_raw: list[dict] = _load_json(metrics_path)  # type: ignore[assignment]
    if not isinstance(candidates_raw, list):
        print("[ERROR] spine_model_metrics.json must be a JSON array.", file=sys.stderr)
        sys.exit(2)

    # Index by segment; filter if caller requested specific segments.
    candidates: dict[str, dict] = {
        row["segment"]: row
        for row in candidates_raw
        if segments is None or row["segment"] in segments
    }

    if not candidates:
        print("[ERROR] No candidate metrics found for the requested segments.", file=sys.stderr)
        sys.exit(2)

    # ── 2. Compare to baselines ───────────────────────────────────────────────
    results: list[dict] = []
    all_pass = True

    for seg, cand in sorted(candidates.items()):
        meta_path = METADATA_DIR / f"{seg}_model.json"
        if not meta_path.exists():
            print(f"[WARN]  No metadata found for segment '{seg}' — skipping.", file=sys.stderr)
            continue

        meta: dict = _load_json(meta_path)  # type: ignore[assignment]
        baseline_metrics: dict = meta.get("metrics", {})
        baseline_mae: float | None = baseline_metrics.get("mae")

        cand_mae  = cand.get("test_mae")
        cand_r2   = cand.get("test_r2")
        cand_mape = cand.get("test_median_ape")

        if baseline_mae is None:
            print(
                f"[WARN]  Segment '{seg}' has no baseline MAE in metadata — "
                "treating candidate as first promotion (auto-pass).",
                file=sys.stderr,
            )
            passed = True
            note = "first-promotion"
        elif cand_mae is None:
            print(f"[WARN]  Segment '{seg}' candidate is missing test_mae — skipping.", file=sys.stderr)
            continue
        else:
            threshold = baseline_mae * (1.0 + tolerance)
            passed = cand_mae <= threshold
            pct_change = (cand_mae - baseline_mae) / baseline_mae * 100.0
            note = f"{'PASS' if passed else 'FAIL'} | Δ MAE {pct_change:+.1f}% (threshold +{tolerance*100:.0f}%)"

        if not passed:
            all_pass = False

        results.append({
            "segment":      seg,
            "passed":       passed,
            "note":         note,
            "baseline_mae": baseline_mae,
            "candidate_mae": cand_mae,
            "candidate_r2":  cand_r2,
            "candidate_mape": cand_mape,
            "baseline_version": meta.get("version"),
            "meta_path":    str(meta_path),
            "cand_row":     cand,
            "meta":         meta,
        })

    # ── 3. Print report table ─────────────────────────────────────────────────
    col = 16
    print()
    print("=" * 74)
    print(f"  Model Promotion Gate  |  tolerance={tolerance*100:.0f}%  |  "
          f"{'DRY RUN — no changes written' if dry_run else 'live mode'}")
    print("=" * 74)
    header = (
        f"  {'Segment':<18} {'Result':<8} "
        f"{'Baseline MAE':>14} {'Candidate MAE':>14} "
        f"{'R²':>6} {'MdAPE':>7}"
    )
    print(header)
    print("  " + "-" * 70)
    for r in results:
        icon = "✅" if r["passed"] else "❌"
        print(
            f"  {r['segment']:<18} {icon:<8} "
            f"{_fmt(r['baseline_mae']):>14} {_fmt(r['candidate_mae']):>14} "
            f"{_fmt(r['candidate_r2'], '.3f'):>6} {_fmt(r['candidate_mape'], '.3f'):>7}"
        )
    print()

    if not all_pass:
        failed = [r["segment"] for r in results if not r["passed"]]
        print(f"  ❌ GATE FAILED — {len(failed)} segment(s) regressed: {failed}")
        print(
            "\n  The old production models are unchanged.\n"
            "  Fix the regression or re-train with a wider feature set, then re-run.\n"
        )
        return 1

    print(f"  ✅ ALL SEGMENTS PASSED ({len(results)} / {len(results)})")

    if dry_run:
        print("\n  --dry-run active — metadata NOT updated.\n")
        return 0

    # ── 4. Promote: update metadata JSON files ────────────────────────────────
    print()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    promoted: list[dict] = []

    for r in results:
        if not r["passed"]:
            continue

        meta: dict = r["meta"]
        old_version = meta.get("version", "v1")
        new_version = _bump_version(old_version)

        cand_row = r["cand_row"]

        # Round to same precision as the existing metadata format.
        new_metrics: dict = {
            "mae":        round(cand_row["test_mae"], 1) if cand_row.get("test_mae") is not None else meta["metrics"].get("mae"),
            "rmse":       round(cand_row["test_rmse"], 1) if cand_row.get("test_rmse") is not None else meta["metrics"].get("rmse"),
            "r2":         round(cand_row["test_r2"], 4) if cand_row.get("test_r2") is not None else meta["metrics"].get("r2"),
            "median_ape": round(cand_row["test_median_ape"], 4) if cand_row.get("test_median_ape") is not None else meta["metrics"].get("median_ape"),
            "note": (
                f"{new_version}: promoted {now_str} by promote_models.py "
                f"(train_rows={cand_row.get('train_rows')}, test_rows={cand_row.get('test_rows')}, "
                f"test_mae={_fmt(cand_row.get('test_mae'))}, test_r2={_fmt(cand_row.get('test_r2'), '.4f')}, "
                f"baseline_mae={_fmt(r['baseline_mae'])}, tolerance={tolerance*100:.0f}%)"
            ),
        }

        meta["version"] = new_version
        meta["metrics"] = new_metrics

        meta_path = Path(r["meta_path"])
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=4)
            f.write("\n")

        print(f"  ✓ {r['segment']:20s}  {old_version} → {new_version}  |  MAE {_fmt(r['baseline_mae'])} → {_fmt(r['candidate_mae'])}")
        promoted.append({
            "segment":      r["segment"],
            "old_version":  old_version,
            "new_version":  new_version,
            "baseline_mae": r["baseline_mae"],
            "promoted_mae": r["candidate_mae"],
            "promoted_r2":  r["candidate_r2"],
            "promoted_mape": r["candidate_mape"],
        })

    # ── 5. Write audit record ─────────────────────────────────────────────────
    EVAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = EVAL_REPORTS_DIR / f"promotion_report_{ts}.json"
    report = {
        "promoted_at":  now_str,
        "tolerance_pct": tolerance * 100,
        "segments":     promoted,
        "all_results":  [
            {k: v for k, v in r.items() if k not in ("meta", "cand_row", "meta_path")}
            for r in results
        ],
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    try:
        display = report_path.relative_to(BASE_DIR)
    except ValueError:
        display = report_path
    print(f"\n  Audit report: {display}")
    print()
    return 0


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--metrics",
        default=str(SPINE_METRICS),
        help=f"Path to spine_model_metrics.json (default: {SPINE_METRICS.relative_to(BASE_DIR)})",
    )
    parser.add_argument(
        "--segments",
        nargs="+",
        default=None,
        metavar="SEG",
        help="Only gate these segments (default: all segments in the metrics file)",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=0.05,
        help="Allowed MAE regression as a fraction, e.g. 0.05 = 5%% (default: 0.05)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the gate result without writing any files",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()

    if args.tolerance < 0 or args.tolerance > 1:
        print("[ERROR] --tolerance must be between 0 and 1 (e.g. 0.05 for 5%).", file=sys.stderr)
        sys.exit(2)

    code = run(
        tolerance=args.tolerance,
        dry_run=args.dry_run,
        segments=args.segments,
        metrics_path=Path(args.metrics),
    )
    sys.exit(code)
