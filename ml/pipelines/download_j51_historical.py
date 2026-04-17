"""Download NYC Open Data: J-51 Exemption and Abatement (Historical).

Dataset: https://data.cityofnewyork.us/d/y7az-s7wc
Socrata id: y7az-s7wc (~4.2M rows, ~200 MB CSV via bulk export).

This table is frozen (historical before tax year 2019). For newer years use:
  - Property Exemption Detail (muvi-b6kx)
  - DOF Property Abatement Detail (rgyu-ii48)

Run from repo root:
    python ml/pipelines/download_j51_historical.py
"""

from pathlib import Path
import urllib.request

BASE = Path(__file__).resolve().parents[2]
OUT_DIR = BASE / "ml/data/external/j51_exemption_abatement_historical"
OUT_FILE = OUT_DIR / "j51_exemption_abatement_historical.csv"
BULK_URL = (
    "https://data.cityofnewyork.us/api/views/y7az-s7wc/rows.csv"
    "?accessType=DOWNLOAD"
)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading to {OUT_FILE} …")
    urllib.request.urlretrieve(BULK_URL, OUT_FILE)
    size_mb = OUT_FILE.stat().st_size / (1024 * 1024)
    print(f"Done: {size_mb:.1f} MB ({OUT_FILE})")


if __name__ == "__main__":
    main()
