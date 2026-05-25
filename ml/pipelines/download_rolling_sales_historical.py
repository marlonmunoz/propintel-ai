"""Download NYC DOF annualized rolling sales for one or more historical years.

Files land in ml/data/nyc_raw/historical/ following the naming convention
{year}_{borough}.xlsx so spine_builder.py picks them up automatically.

Source:
  https://www.nyc.gov/site/finance/property/property-annualized-sales-update.page

Run from repo root:
    # Download all three extension years at once
    python ml/pipelines/download_rolling_sales_historical.py --years 2019 2020 2021

    # Or a single year
    python ml/pipelines/download_rolling_sales_historical.py --years 2021
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

# NYC Finance servers sit behind Akamai CDN which blocks plain urllib requests.
# Adding a real browser User-Agent + Referer header bypasses the 403.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.nyc.gov/site/finance/property/property-annualized-sales-update.page",
}

BASE    = Path(__file__).resolve().parents[2]
OUT_DIR = BASE / "ml/data/nyc_raw/historical"

DOF_BASE = (
    "https://www.nyc.gov/assets/finance/downloads/pdf/"
    "rolling_sales/annualized-sales"
)

# Primary borough slugs; older years may use an alternative (see fallback below)
BOROUGHS = [
    "manhattan",
    "bronx",
    "brooklyn",
    "queens",
    "staten_island",
]

# Some years (e.g. 2019) publish Staten Island without the underscore
_SLUG_FALLBACKS: dict[str, str] = {
    "staten_island": "statenisland",
}


def _candidate_urls(year: int, slug: str) -> list[str]:
    """Return primary URL plus any known fallbacks for *slug*."""
    primary = f"{DOF_BASE}/{year}/{year}_{slug}.xlsx"
    alt = _SLUG_FALLBACKS.get(slug)
    if alt:
        return [primary, f"{DOF_BASE}/{year}/{year}_{alt}.xlsx"]
    return [primary]


def _files_for_year(year: int) -> dict[str, list[str]]:
    """Return {local_filename: [url, fallback_url, ...]} mapping for *year*."""
    return {
        f"{year}_{b}.xlsx": _candidate_urls(year, b)
        for b in BOROUGHS
    }


def download_year(year: int, *, force: bool = False) -> list[str]:
    """Download rolling-sales files for *year*. Returns list of filenames written."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    for filename, urls in _files_for_year(year).items():
        dest = OUT_DIR / filename
        if dest.exists() and not force:
            print(f"  [skip] already exists: {filename}")
            continue
        print(f"  Downloading {filename} …", end=" ", flush=True)
        succeeded = False
        last_exc: Exception | None = None
        for url in urls:
            try:
                req = urllib.request.Request(url, headers=_HEADERS)
                with urllib.request.urlopen(req) as resp, open(dest, "wb") as fh:
                    fh.write(resp.read())
                succeeded = True
                break
            except Exception as exc:
                last_exc = exc
                if dest.exists():
                    dest.unlink()
        if succeeded:
            size_kb = dest.stat().st_size / 1024
            print(f"✓  ({size_kb:.0f} KB)")
            written.append(filename)
        else:
            print(f"✗  FAILED — {last_exc}", file=sys.stderr)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Download NYC DOF rolling sales archives")
    parser.add_argument(
        "--years",
        nargs="+",
        type=int,
        default=[2019, 2020, 2021],
        metavar="YEAR",
        help="Calendar years to download (default: 2019 2020 2021)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if the file already exists",
    )
    args = parser.parse_args()

    total_written = 0
    for year in sorted(args.years):
        print(f"\n── {year} ──")
        written = download_year(year, force=args.force)
        total_written += len(written)

    print(f"\n✅  Done — {total_written} new file(s) saved → {OUT_DIR}")
    print("   Next: python ml/pipelines/spine_builder.py")


if __name__ == "__main__":
    main()
