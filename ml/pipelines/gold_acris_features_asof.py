"""Gold builder: ACRIS transaction features (as-of safe).

Input  : ml/data/silver/acris/silver_acris_transactions.parquet
         ml/data/gold/training_spine_v1.parquet  (provides bbl + as_of_date)
Output : ml/data/gold/gold_acris_features_asof.parquet

As-of contract
--------------
For each spine row (bbl, as_of_date) we compute ACRIS-derived features using
only transactions whose `document_date` is STRICTLY BEFORE `as_of_date`.

Features produced (all computed relative to as_of_date)
--------------------------------------------------------
acris_prior_sale_cnt       : # deed transfers for this BBL before as_of_date
acris_last_deed_amt        : document_amt of the most recent deed before as_of_date
acris_last_deed_date       : date of the most recent deed before as_of_date
acris_days_since_last_deed : (as_of_date - acris_last_deed_date).days
acris_last_buyer           : name of buyer in most recent deed
acris_last_seller          : name of seller in most recent deed
acris_mortgage_cnt         : # mortgage records before as_of_date
acris_last_mtge_amt        : amount of most recent mortgage before as_of_date
acris_last_mtge_date       : date of most recent mortgage

Run from repo root:
    python ml/pipelines/gold_acris_features_asof.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[2]
SILVER_FILE = BASE / "ml/data/silver/acris/silver_acris_transactions.parquet"
SPINE_FILE  = BASE / "ml/data/gold/training_spine_v1.parquet"
OUT_DIR     = BASE / "ml/data/gold"
OUT_FILE    = OUT_DIR / "gold_acris_features_asof.parquet"

DEED_TYPES = {
    "DEED", "DEEDO", "DEED, BARGAIN AND SALE", "DEED IN LIEU OF FORECLOSURE",
    "DEED, CORPORATION", "DEED, EXECUTOR", "DEED, GUARDIAN",
    "DEED, PERSONAL REPRESENTATIVE", "DEED, TRUSTEE",
    "CONVEYANCE BY REFEREE", "EXECUTOR DEED",
}
MORTGAGE_TYPES = {"MTGE", "AGMT"}


def _norm_bbl(s: pd.Series) -> pd.Series:
    """Return BBL as a plain string, compatible with spine's str BBL dtype."""
    out = s.astype("Int64").astype(str)
    return out.where(out != "<NA>", other=pd.NA)


def _compute_deed_features(
    deeds: pd.DataFrame, spine: pd.DataFrame
) -> pd.DataFrame:
    """
    For each (bbl, as_of_date) in spine, aggregate deed records that precede
    as_of_date.  Returns a DataFrame indexed on (bbl, as_of_date).
    """
    print("  Computing deed features …")

    # Join spine to deed records on bbl.
    merged = spine[["bbl", "as_of_date"]].merge(
        deeds[["bbl", "document_date", "document_amt", "buyer_name", "seller_name"]],
        on="bbl",
        how="left",
    )

    # As-of filter.
    merged = merged[
        merged["document_date"].notna()
        & (merged["document_date"].dt.date < merged["as_of_date"])
    ]

    # Count of prior deeds.
    cnt = (
        merged.groupby(["bbl", "as_of_date"])
        .size()
        .rename("acris_prior_sale_cnt")
        .reset_index()
    )

    # Most recent deed.
    latest = (
        merged.sort_values("document_date", ascending=False)
        .drop_duplicates(subset=["bbl", "as_of_date"])
        [["bbl", "as_of_date", "document_date", "document_amt",
          "buyer_name", "seller_name"]]
        .rename(columns={
            "document_date": "acris_last_deed_date",
            "document_amt":  "acris_last_deed_amt",
            "buyer_name":    "acris_last_buyer",
            "seller_name":   "acris_last_seller",
        })
    )

    feats = cnt.merge(latest, on=["bbl", "as_of_date"], how="outer")
    return feats


def _compute_mortgage_features(
    mtge: pd.DataFrame, spine: pd.DataFrame
) -> pd.DataFrame:
    print("  Computing mortgage features …")

    merged = spine[["bbl", "as_of_date"]].merge(
        mtge[["bbl", "document_date", "document_amt"]],
        on="bbl",
        how="left",
    )
    merged = merged[
        merged["document_date"].notna()
        & (merged["document_date"].dt.date < merged["as_of_date"])
    ]

    cnt = (
        merged.groupby(["bbl", "as_of_date"])
        .size()
        .rename("acris_mortgage_cnt")
        .reset_index()
    )

    latest = (
        merged.sort_values("document_date", ascending=False)
        .drop_duplicates(subset=["bbl", "as_of_date"])
        [["bbl", "as_of_date", "document_date", "document_amt"]]
        .rename(columns={
            "document_date": "acris_last_mtge_date",
            "document_amt":  "acris_last_mtge_amt",
        })
    )

    feats = cnt.merge(latest, on=["bbl", "as_of_date"], how="outer")
    return feats


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── load ────────────────────────────────────────────────────────────────
    print("Loading silver ACRIS transactions …")
    txn = pd.read_parquet(SILVER_FILE)
    txn["bbl"] = _norm_bbl(txn["bbl"])
    txn = txn.dropna(subset=["bbl"])
    print(f"  {len(txn):,} rows")

    # Filter out records with implausible dates (year < 1900 or > 2030).
    txn["document_date"] = pd.to_datetime(txn["document_date"], errors="coerce")
    txn = txn[
        txn["document_date"].notna()
        & (txn["document_date"].dt.year >= 1900)
        & (txn["document_date"].dt.year <= 2030)
    ]
    print(f"  {len(txn):,} rows after date sanity filter")

    print("Loading training spine …")
    spine = pd.read_parquet(SPINE_FILE, columns=["bbl", "as_of_date", "sale_date"])
    spine["as_of_date"] = pd.to_datetime(spine["as_of_date"]).dt.date
    print(f"  {len(spine):,} spine rows")

    # Restrict ACRIS to BBLs that appear in spine (perf).
    spine_bbls = set(spine["bbl"].dropna().unique())
    txn = txn[txn["bbl"].isin(spine_bbls)].copy()
    print(f"  ACRIS rows after BBL filter: {len(txn):,}")

    deeds = txn[txn["doc_type"].isin(DEED_TYPES)].copy()
    mtge  = txn[txn["doc_type"].isin(MORTGAGE_TYPES)].copy()
    print(f"  Deed rows: {len(deeds):,}  |  Mortgage rows: {len(mtge):,}")

    # ── compute features ────────────────────────────────────────────────────
    deed_feats = _compute_deed_features(deeds, spine)
    mtge_feats = _compute_mortgage_features(mtge, spine)

    # ── assemble gold ───────────────────────────────────────────────────────
    gold = spine.copy()
    gold = gold.merge(deed_feats, on=["bbl", "as_of_date"], how="left")
    gold = gold.merge(mtge_feats, on=["bbl", "as_of_date"], how="left")

    # Derived feature: days since last deed.
    gold["acris_last_deed_date"] = pd.to_datetime(
        gold["acris_last_deed_date"], errors="coerce"
    )
    gold["acris_days_since_last_deed"] = (
        pd.to_datetime(gold["as_of_date"]) - gold["acris_last_deed_date"]
    ).dt.days

    # Fill count nulls with 0 (no records = 0 events).
    for c in ["acris_prior_sale_cnt", "acris_mortgage_cnt"]:
        gold[c] = gold[c].fillna(0).astype("Int64")

    gold.to_parquet(OUT_FILE, index=False)

    print(f"\n✅  Gold ACRIS features saved → {OUT_FILE}")
    print(f"   Rows : {len(gold):,}")
    feat_cols = [c for c in gold.columns if c.startswith("acris_")]
    print(f"   Feature columns: {feat_cols}")
    print(f"\nFeature null rates:")
    for c in feat_cols:
        pct = gold[c].isna().mean() * 100
        print(f"   {c:<35} {pct:.1f}% null")


if __name__ == "__main__":
    main()
