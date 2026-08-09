"""
Phase 0 of address-based BBL resolution — build the offline index and measure
whether it is accurate enough to serve.

WHAT THIS BUILDS
================
An artifact mapping (normalized_address, borough_num) -> bbl, derived from
PLUTO raw (857k NYC tax lots, already on disk — no download, no external
geocoder). Written to ml/data/gold/address_bbl_index.parquet in the same
format the other Gold tables use, so it can ship in the Docker image.

Any (address, borough) pair matching more than one BBL in PLUTO is dropped
from the servable index rather than guessing — condo/coop unit lots are the
main source of this, since many units in one building share the same street
address in PLUTO with only the BBL differing. Ambiguous cases are reported
separately, not resolved, matching the same abstain-over-guess rule that
ruled out coordinate-based resolution (measured in eval_serving_path.py:
a wrong BBL is worse than no BBL).

WHAT THIS MEASURES
==================
Scores the index against the training spine, which carries the ADDRESS the
sale was recorded under AND the TRUE bbl for every one of 323k sales — a
ground-truth set no production traffic can give us. This lets Phase 0 answer
"is this viable at all" before any serving code exists to fail loudly on.

Usage
-----
    PYTHONPATH=. python ml/pipelines/build_address_bbl_index.py
    PYTHONPATH=. python ml/pipelines/build_address_bbl_index.py --no-write
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ml.features.address_normalize import normalize_address, pluto_borough_to_num  # noqa: E402

PLUTO_RAW = REPO_ROOT / "ml" / "data" / "pluto_raw" / "pluto.csv"
SPINE_PATH = REPO_ROOT / "ml" / "data" / "gold" / "training_spine_v1.parquet"
INDEX_OUT = REPO_ROOT / "ml" / "data" / "gold" / "address_bbl_index.parquet"


def build_index(verbose: bool = True) -> pd.DataFrame:
    """Build the servable (normalized_address, borough_num) -> bbl index.

    Two rows are excluded, never guessed at:

    1. Condo unit lots (PLUTO "Tax lot" >= 1000). Measured against the spine's
       true per-sale BBL, these resolve address -> PLUTO's condo MASTER/BILLING
       lot (observed lot range 7501-7503) with 0% precision — same block as
       the real unit 99.98% of the time, but never the unit itself, because
       PLUTO carries no per-unit address. The address correctly identifies the
       building, never the unit, so this is excluded at the source rather than
       relying on the ambiguity filter below to catch it (it often doesn't:
       one building address can map to exactly one master lot, which looks
       unambiguous while still being wrong for every unit sale).

    2. Any (address, borough) pair matching more than one BBL after (1) —
       guessing among them is exactly the failure mode that made
       coordinate-based resolution worse than no resolution at all.
    """
    if not PLUTO_RAW.exists():
        raise SystemExit(f"PLUTO raw not found: {PLUTO_RAW}")

    raw = pd.read_csv(
        PLUTO_RAW, usecols=["address", "borough", "BBL", "Tax lot"], low_memory=False
    )
    raw["norm_address"] = raw["address"].map(normalize_address)
    raw["borough_num"] = raw["borough"].map(pluto_borough_to_num)
    raw["bbl"] = raw["BBL"].astype(str).str.strip()
    raw = raw.dropna(subset=["norm_address", "borough_num"])

    is_condo_lot = pd.to_numeric(raw["Tax lot"], errors="coerce").fillna(0) >= 1000
    candidates = raw[~is_condo_lot].copy()

    grouped = candidates.groupby(["norm_address", "borough_num"])["bbl"].nunique()
    ambiguous_keys = set(grouped[grouped > 1].index)
    candidates["is_ambiguous"] = candidates.set_index(
        ["norm_address", "borough_num"]
    ).index.isin(ambiguous_keys)

    index = (
        candidates[~candidates["is_ambiguous"]][["norm_address", "borough_num", "bbl"]]
        .drop_duplicates(subset=["norm_address", "borough_num"])
        .reset_index(drop=True)
    )

    if verbose:
        n_condo_lots = int(is_condo_lot.sum())
        n_ambiguous = int(candidates["is_ambiguous"].sum())
        print(f"PLUTO lots scanned      : {len(raw):,}")
        print(f"Excluded condo-unit lots (Tax lot >= 1000): {n_condo_lots:,}")
        print(f"Ambiguous among the rest: {n_ambiguous:,} "
              f"({n_ambiguous / max(len(candidates), 1) * 100:.1f}% of non-condo lots)")
        print(f"Servable index entries  : {len(index):,}")

    return index


def score_against_spine(index: pd.DataFrame, verbose: bool = True) -> dict:
    """Measure precision/abstain rate of the index against 323k ground-truth sales.

    A row "abstains" when its normalized (address, borough) has no entry in
    the servable index — either PLUTO never had that address, or it was
    dropped as ambiguous. Abstaining is the safe outcome being measured FOR,
    not a failure: the gate that matters is precision among rows that DID
    resolve, since a wrong match is worse than no match.
    """
    spine = pd.read_parquet(
        SPINE_PATH, columns=["address", "borough", "bbl", "segment", "building_class"]
    )
    spine["norm_address"] = spine["address"].map(normalize_address)
    spine["borough_num"] = pd.to_numeric(spine["borough"], errors="coerce")
    spine["true_bbl"] = spine["bbl"].astype(str).str.strip()

    # condo_coop is one segment in routing but two very different address
    # situations: co-ops are a single real tax lot (address is unambiguous),
    # condos are unit lots PLUTO can't address-distinguish (see build_index).
    # Reporting them together would hide that condos should never be attempted.
    is_coop = spine["building_class"].astype(str).str.strip().str.startswith(("09", "10", "17"))
    spine["report_segment"] = spine["segment"]
    spine.loc[(spine["segment"] == "condo_coop") & is_coop, "report_segment"] = "coop"
    spine.loc[(spine["segment"] == "condo_coop") & ~is_coop, "report_segment"] = "condo"

    merged = spine.merge(
        index.rename(columns={"bbl": "resolved_bbl"}),
        on=["norm_address", "borough_num"],
        how="left",
    )

    resolved = merged["resolved_bbl"].notna()
    correct = resolved & (merged["resolved_bbl"] == merged["true_bbl"])

    report: dict = {
        "n_total": int(len(merged)),
        "n_resolved": int(resolved.sum()),
        "resolve_rate": round(float(resolved.mean()), 4),
        "n_correct_of_resolved": int(correct.sum()),
        "precision_of_resolved": round(float(correct.sum() / resolved.sum()), 4) if resolved.sum() else None,
    }

    if verbose:
        print(f"\nSpine rows scored       : {report['n_total']:,}")
        print(f"Resolved (non-abstain)  : {report['n_resolved']:,} ({report['resolve_rate'] * 100:.1f}%)")
        print(f"Precision of resolved   : {report['precision_of_resolved'] * 100:.1f}%  "
              f"({report['n_correct_of_resolved']:,}/{report['n_resolved']:,} correct)")

        print("\nBy segment:")
        print(f"  {'segment':<18} {'n':>8} {'resolve%':>10} {'precision%':>12}")
        for seg, grp in merged.groupby("report_segment", sort=True):
            r = grp["resolved_bbl"].notna()
            c = r & (grp["resolved_bbl"] == grp["true_bbl"])
            prec = f"{c.sum() / r.sum() * 100:.1f}" if r.sum() else "n/a"
            print(f"  {seg:<18} {len(grp):>8,} {r.mean() * 100:>9.1f}% {prec:>11}%")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--no-write", action="store_true",
        help="Build and score the index in memory only; don't write the parquet artifact.",
    )
    args = parser.parse_args()

    idx = build_index()
    score_against_spine(idx)

    if not args.no_write:
        idx.to_parquet(INDEX_OUT, index=False)
        print(f"\nWrote {INDEX_OUT}  ({len(idx):,} rows)")
    else:
        print("\n--no-write set: artifact not saved.")
