"""Silver normalizer: DOF condo *unit-level* structural features (PROPMAST).

Input  : the DOF Property Master tab-delimited roll for Tax Classes 2/3/4, e.g.
         PROPMAST_TC234_T2027_TENT.TXT  (downloaded manually from DOF — see below)
Output : ml/data/silver/dof_condo_units/silver_dof_condo_units.parquet

Why this exists
---------------
The pooled DOF assessment CSV (`8y4t-faws`) only covers ~39% of condo *unit*
lots (lot 1001-6999), and it does not expose the condo common-interest %.  The
raw PROPMAST roll has one record per tax lot — INCLUDING every condo unit — plus
two fields that are gold for condo valuation and exist in no other dataset we
hold:
  * gross square footage of the unit, and
  * the unit's common-interest % (its proportional ownership/value share of the
    whole condominium).

Leakage note
------------
This is a SINGLE roll snapshot (T2027 tentative, published Jan 2026).  Its
*assessed/market values* are point-in-time and would leak future information
into historical training sales, so we DO NOT extract them here.  We extract only
**time-invariant structural** attributes (sqft, year built, units, common
interest, apartment number, building class) which are valid to join to a sale
in any year by BBL.

Field map (1-based tab-field index → meaning), validated empirically against
real residential condo records (4A/4B/4C… in a single building) rather than the
2015 RPAD fixed-width dictionary, whose positions do NOT align 1:1 with this
140-field PTS export:

    [1]   BBL (boro + 5-digit block + 4-digit lot, already in spine format)
    [72]  building class      (e.g. R4 = residential unit in elevator bldg)
    [91]  year built
    [99]  units
    [101] apartment number    (e.g. "4A", "PHB", "RES")
    [114] common interest — land %
    [115] common interest — building %
    [122] gross square feet (interior area of the unit)

Manual download
---------------
DOF publishes these rolls on the property-tax page (no stable URL pattern):
  https://www.nyc.gov/site/finance/property/property-assessment-roll-archives.page
Download the Tax Class 2/3/4 master file (.TXT) and place it at the --input path
below.  The raw .TXT is large (~840 MB) and .gitignored.

Run from repo root:
    python ml/pipelines/silver_dof_condo_units.py \
        --input ml/data/external/dof_assessment_roll/PROPMAST_TC234_T2027_TENT.TXT
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    BASE / "ml/data/external/dof_assessment_roll/PROPMAST_TC234_T2027_TENT.TXT"
)
OUT_DIR = BASE / "ml/data/silver/dof_condo_units"
OUT_FILE = OUT_DIR / "silver_dof_condo_units.parquet"

# Number of tab fields in a well-formed PROPMAST PTS record.
_EXPECTED_FIELDS = 140

# 0-based field indices (the docstring lists them 1-based for readability).
_IDX_BBL          = 0
_IDX_LOT          = 3
_IDX_BLDG_CLASS   = 71
_IDX_YRBUILT      = 90
_IDX_UNITS        = 98
_IDX_APT_NO       = 100
_IDX_COMINT_LAND  = 113
_IDX_COMINT_BLDG  = 114
_IDX_GROSS_SQFT   = 121

# Condo unit lots live in the 1001-6999 range; billing lots (7501-7599) and
# normal lots are excluded — only unit lots map 1:1 to a sold condo BBL.
_UNIT_LOT_LO = 1001
_UNIT_LOT_HI = 6999


def _num(raw: str) -> float | None:
    """Parse a DOF signed numeric token ('+000000720', '+000.3599998') → float.

    Returns None for blank / all-zero tokens so they become NaN downstream.
    """
    s = raw.strip()
    if not s:
        return None
    try:
        val = float(s.replace("+", ""))
    except ValueError:
        return None
    return val if val != 0.0 else None


def parse(input_path: Path) -> pd.DataFrame:
    print(f"Reading {input_path} …")
    rows: list[dict[str, object]] = []
    skipped_short = 0
    scanned = 0

    with open(input_path, encoding="latin-1") as fh:
        for line in fh:
            scanned += 1
            f = line.rstrip("\n").split("\t")
            if len(f) < _EXPECTED_FIELDS:
                skipped_short += 1
                continue

            lot_raw = f[_IDX_LOT].strip()
            if not lot_raw.isdigit():
                continue
            lot = int(lot_raw)
            if not (_UNIT_LOT_LO <= lot <= _UNIT_LOT_HI):
                continue

            bbl = f[_IDX_BBL].strip()
            if not bbl.isdigit():
                continue

            rows.append({
                "bbl":               bbl,
                "condo_bldg_class":  f[_IDX_BLDG_CLASS].strip().upper() or None,
                "condo_yrbuilt":     _num(f[_IDX_YRBUILT]),
                "condo_units":       _num(f[_IDX_UNITS]),
                "condo_apt_no":      f[_IDX_APT_NO].strip() or None,
                "condo_comint_land": _num(f[_IDX_COMINT_LAND]),
                "condo_comint_bldg": _num(f[_IDX_COMINT_BLDG]),
                "condo_gross_sqft":  _num(f[_IDX_GROSS_SQFT]),
            })

    print(f"  Scanned {scanned:,} records, kept {len(rows):,} condo unit lots "
          f"({skipped_short:,} malformed/short rows skipped)")

    df = pd.DataFrame(rows)
    # A condo unit BBL is unique in a single roll; guard against accidental dupes.
    before = len(df)
    df = df.drop_duplicates(subset="bbl").reset_index(drop=True)
    if before != len(df):
        print(f"  Dropped {before - len(df):,} duplicate BBLs")
    return df


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                    help="Path to the PROPMAST .TXT roll file.")
    args = ap.parse_args()

    if not args.input.exists():
        raise SystemExit(
            f"Input not found: {args.input}\n"
            "Download the DOF Tax Class 2/3/4 master roll (.TXT) and pass --input, "
            "or place it at the default path."
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = parse(args.input)
    df.to_parquet(OUT_FILE, index=False)

    print(f"\n✅  Silver DOF condo units saved → {OUT_FILE}")
    print(f"   Rows : {len(df):,}")
    print(f"   Cols : {df.columns.tolist()}")
    print("\nNon-null rates:")
    for c in df.columns:
        if c == "bbl":
            continue
        print(f"   {c:<20} {df[c].notna().mean()*100:5.1f}%")
    print("\nSample gross_sqft quantiles (units only):")
    sq = df["condo_gross_sqft"].dropna()
    if len(sq):
        print(f"   p10={sq.quantile(.10):,.0f}  p50={sq.quantile(.50):,.0f}  "
              f"p90={sq.quantile(.90):,.0f}")


if __name__ == "__main__":
    main()
