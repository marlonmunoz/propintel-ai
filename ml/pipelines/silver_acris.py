"""Silver normalizer: ACRIS Real Property (master + legals + parties).

Inputs
------
  ml/data/external/acris/master/real_property_master.csv
  ml/data/external/acris/legals/real_property_legals.csv
  ml/data/external/acris/parties/real_property_parties.csv

Outputs
-------
  ml/data/silver/acris/silver_acris_transactions.parquet
      One row per (document_id, bbl) — deed / mortgage / other transfers
      joined with the BBL and filtered to relevant document types.

  ml/data/silver/acris/silver_acris_parties.parquet
      Grantor / grantee names per document_id (for buyer/seller enrichment).

What this script does
---------------------
1. Reads master, legals, and parties CSVs.
2. Filters master to relevant doc_type groups (deeds, mortgages, assignments,
   satisfactions).
3. Parses document_date, recorded_datetime.
4. Joins master ← legals on document_id to attach BBL.
5. Builds 10-digit BBL from legals borough / block / lot.
6. Joins in buyer (party_type=1) and seller (party_type=2) names from parties.
7. Drops rows that cannot form a valid BBL.
8. Writes two compact Parquet files.

Run from repo root:
    python ml/pipelines/silver_acris.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
ACRIS_DIR = BASE / "ml/data/external/acris"
OUT_DIR   = BASE / "ml/data/silver/acris"

MASTER_FILE  = ACRIS_DIR / "master"  / "real_property_master.csv"
LEGALS_FILE  = ACRIS_DIR / "legals"  / "real_property_legals.csv"
PARTIES_FILE = ACRIS_DIR / "parties" / "real_property_parties.csv"

OUT_TXN     = OUT_DIR / "silver_acris_transactions.parquet"
OUT_PARTIES = OUT_DIR / "silver_acris_parties.parquet"

# Document type groups we care about.
DEED_TYPES = {
    "DEED", "DEEDO", "DEED, BARGAIN AND SALE", "DEED IN LIEU OF FORECLOSURE",
    "DEED, CORPORATION", "DEED, EXECUTOR", "DEED, GUARDIAN",
    "DEED, PERSONAL REPRESENTATIVE", "DEED, TRUSTEE",
    "CONVEYANCE BY REFEREE", "EXECUTOR DEED",
}
MORTGAGE_TYPES = {
    "MTGE",   # mortgage
    "AGMT",   # agreement
    "SAT",    # satisfaction of mortgage
    "ASST",   # assignment of mortgage
    "RPTT",   # real property transfer tax
}
RELEVANT_TYPES = DEED_TYPES | MORTGAGE_TYPES


def _to_int64(s: pd.Series) -> pd.Series:
    """Safely convert a numeric-ish series (may contain NaN) to nullable Int64."""
    s = pd.to_numeric(s, errors="coerce")
    mask = s.isna()
    out = s.fillna(0).round(0).astype(int).astype("Int64")
    out[mask] = pd.NA
    return out


def _build_bbl(boro: pd.Series, block: pd.Series, lot: pd.Series) -> pd.Series:
    return (
        _to_int64(boro) * 1_000_000_000
        + _to_int64(block) * 10_000
        + _to_int64(lot)
    ).astype("Int64")


def _parse_dt(series: pd.Series) -> pd.Series:
    """Parse ISO-ish timestamps like '2003-01-06T00:00:00.000' → datetime."""
    return pd.to_datetime(series, errors="coerce", utc=False)


# ── loaders ────────────────────────────────────────────────────────────────

def load_master() -> pd.DataFrame:
    print(f"Reading master …")
    df = pd.read_csv(
        MASTER_FILE,
        low_memory=False,
        usecols=[
            "document_id", "doc_type", "document_amt",
            "document_date", "recorded_datetime",
            "percent_trans", "recorded_borough",
        ],
    )
    print(f"  master raw rows: {len(df):,}")

    df["doc_type"] = df["doc_type"].astype(str).str.strip().str.upper()

    # Filter to relevant document types for efficiency.
    df = df[df["doc_type"].isin(RELEVANT_TYPES)].copy()
    print(f"  master after doc_type filter: {len(df):,}")

    df["document_amt"]       = pd.to_numeric(df["document_amt"], errors="coerce")
    df["percent_trans"]      = pd.to_numeric(df["percent_trans"], errors="coerce")
    df["document_date"]      = _parse_dt(df["document_date"])
    df["recorded_datetime"]  = _parse_dt(df["recorded_datetime"])

    return df


def load_legals() -> pd.DataFrame:
    print(f"Reading legals …")
    df = pd.read_csv(
        LEGALS_FILE,
        low_memory=False,
        usecols=["document_id", "borough", "block", "lot", "property_type"],
    )
    print(f"  legals raw rows: {len(df):,}")

    for c in ["borough", "block", "lot"]:
        df[c] = _to_int64(df[c])

    df["bbl"] = _build_bbl(df["borough"], df["block"], df["lot"])
    df = df.dropna(subset=["bbl"])
    df = df.rename(columns={"borough": "legal_borough"})
    print(f"  legals after BBL filter: {len(df):,}")
    return df


def load_parties() -> pd.DataFrame:
    print(f"Reading parties …")
    df = pd.read_csv(
        PARTIES_FILE,
        low_memory=False,
        usecols=["document_id", "party_type", "name"],
    )
    print(f"  parties raw rows: {len(df):,}")

    df["party_type"] = pd.to_numeric(df["party_type"], errors="coerce").astype("Int64")
    df["name"] = df["name"].astype(str).str.strip().str.upper()
    df["name"] = df["name"].replace("NAN", np.nan)
    return df


# ── assembly ───────────────────────────────────────────────────────────────

def build_transactions(master: pd.DataFrame, legals: pd.DataFrame) -> pd.DataFrame:
    """Join master to legals on document_id → one row per (document_id, bbl)."""
    df = master.merge(
        legals[["document_id", "bbl", "legal_borough", "block", "lot", "property_type"]],
        on="document_id",
        how="inner",
    )
    print(f"  transactions after join: {len(df):,} rows, {df['bbl'].nunique():,} unique BBLs")
    return df


def build_parties_wide(parties: pd.DataFrame, txn_ids: pd.Index) -> pd.DataFrame:
    """Pivot parties to wide: buyer_name, seller_name per document_id."""
    # Restrict to document_ids that survived the master filter.
    sub = parties[parties["document_id"].isin(txn_ids)].copy()

    buyers  = (
        sub[sub["party_type"] == 1]
        .groupby("document_id")["name"]
        .first()
        .rename("buyer_name")
    )
    sellers = (
        sub[sub["party_type"] == 2]
        .groupby("document_id")["name"]
        .first()
        .rename("seller_name")
    )
    wide = pd.concat([buyers, sellers], axis=1).reset_index()
    print(f"  parties wide: {len(wide):,} document_ids")
    return wide


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    master  = load_master()
    legals  = load_legals()
    parties = load_parties()

    txn = build_transactions(master, legals)

    # Attach buyer / seller names.
    parties_wide = build_parties_wide(parties, set(txn["document_id"]))
    txn = txn.merge(parties_wide, on="document_id", how="left")

    # Ordered output columns.
    txn_cols = [
        "document_id", "bbl", "legal_borough", "block", "lot",
        "doc_type", "document_date", "recorded_datetime",
        "document_amt", "percent_trans",
        "property_type", "recorded_borough",
        "buyer_name", "seller_name",
    ]
    txn = txn[[c for c in txn_cols if c in txn.columns]]

    # Parties silver (all party_type rows for the filtered documents).
    parties_silver = parties[parties["document_id"].isin(set(txn["document_id"]))].copy()

    # ── write ──────────────────────────────────────────────────────────────
    txn.to_parquet(OUT_TXN, index=False)
    parties_silver.to_parquet(OUT_PARTIES, index=False)

    print(f"\n✅  Silver ACRIS transactions → {OUT_TXN}")
    print(f"   Rows   : {len(txn):,}")
    print(f"   BBLs   : {txn['bbl'].nunique():,} unique")
    print(f"   Date range: "
          f"{txn['document_date'].min().date()} → "
          f"{txn['document_date'].max().date()}")

    print(f"\n✅  Silver ACRIS parties      → {OUT_PARTIES}")
    print(f"   Rows   : {len(parties_silver):,}")


if __name__ == "__main__":
    main()
