"""Download NYC DOF annualized rolling sales for 2024 (all 5 boroughs).

Files land in ml/data/nyc_raw/historical/ following the existing naming
convention so spine_builder.py picks them up automatically on the next run.

Source: https://www.nyc.gov/site/finance/property/property-annualized-sales-update.page

Run from repo root:
    python ml/pipelines/download_rolling_sales_2024.py
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

BASE    = Path(__file__).resolve().parents[2]
OUT_DIR = BASE / "ml/data/nyc_raw/historical"

BASE_URL = (
    "https://www.nyc.gov/assets/finance/downloads/pdf/"
    "rolling_sales/annualized-sales/2024"
)

FILES = {
    "2024_manhattan.xlsx":    f"{BASE_URL}/2024_manhattan.xlsx",
    "2024_bronx.xlsx":        f"{BASE_URL}/2024_bronx.xlsx",
    "2024_brooklyn.xlsx":     f"{BASE_URL}/2024_brooklyn.xlsx",
    "2024_queens.xlsx":       f"{BASE_URL}/2024_queens.xlsx",
    "2024_staten_island.xlsx": f"{BASE_URL}/2024_staten_island.xlsx",
}


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for filename, url in FILES.items():
        dest = OUT_DIR / filename
        if dest.exists():
            print(f"  [skip] already exists: {dest.name}")
            continue
        print(f"  Downloading {filename} …")
        urllib.request.urlretrieve(url, dest)
        size_kb = dest.stat().st_size / 1024
        print(f"  ✓ {dest.name}  ({size_kb:.0f} KB)")

    print(f"\n✅  2024 rolling sales saved → {OUT_DIR}")
    print("   Next step: python ml/pipelines/spine_builder.py")


if __name__ == "__main__":
    main()
