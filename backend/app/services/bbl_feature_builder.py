"""As-of spine features for a single BBL (inference-time parity with training).

Gold parquet rows exist only for (bbl, as_of_date) pairs that appear in the
training spine.  For live API calls with an arbitrary ``as_of_date``, we
recompute DOF / ACRIS / J-51 features from Silver tables using the same rules
as ``ml/pipelines/gold_*_asof.py``.  PLUTO rows are read from
``gold_pluto_features.parquet`` (BBL-only snapshot).

If Silver / PLUTO files are missing (e.g. fresh clone without data), callers
get an empty dict and should fall back to median imputation.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger("propintel")

BASE_DIR = Path(__file__).resolve().parents[3]

SILVER_DOF   = BASE_DIR / "ml/data/silver/dof_assessment/silver_dof_assessment.parquet"
SILVER_ACRIS = BASE_DIR / "ml/data/silver/acris/silver_acris_transactions.parquet"
SILVER_J51   = BASE_DIR / "ml/data/silver/j51/silver_j51.parquet"
GOLD_PLUTO   = BASE_DIR / "ml/data/gold/gold_pluto_features.parquet"

# Must match gold_acris_features_asof.py
DEED_TYPES = {
    "DEED", "DEEDO", "DEED, BARGAIN AND SALE", "DEED IN LIEU OF FORECLOSURE",
    "DEED, CORPORATION", "DEED, EXECUTOR", "DEED, GUARDIAN",
    "DEED, PERSONAL REPRESENTATIVE", "DEED, TRUSTEE",
    "CONVEYANCE BY REFEREE", "EXECUTOR DEED",
}
MORTGAGE_TYPES = {"MTGE", "AGMT"}


def normalize_bbl(bbl: str | int | None) -> str | None:
    """Return canonical string BBL (digits only), or None if invalid."""
    if bbl is None:
        return None
    digits = "".join(ch for ch in str(bbl).strip() if ch.isdigit())
    if not digits:
        return None
    return str(int(digits))


def parse_as_of_date(value: date | datetime | str | None) -> date | None:
    """Parse ``as_of_date`` to a ``datetime.date``."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return pd.to_datetime(value, errors="coerce").date()
    return None


def _parquet_read_bbl(path: Path, bbl: str, columns: list[str] | None = None) -> pd.DataFrame:
    """Read rows for a single BBL with pushdown when supported."""
    if not path.exists():
        return pd.DataFrame()
    keys: list[Any] = [bbl]
    if bbl.isdigit():
        keys.append(int(bbl))
    for key in keys:
        try:
            df = pd.read_parquet(path, columns=columns, filters=[("bbl", "==", key)])
            if not df.empty:
                return df
        except Exception:
            continue
    try:
        df = pd.read_parquet(path, columns=columns)
        mask = df["bbl"].astype(str).str.replace(r"\.0$", "", regex=True) == bbl
        return df.loc[mask].copy()
    except Exception as e2:
        logger.warning("Could not read %s: %s", path, e2)
        return pd.DataFrame()


def _norm_series_bbl(s: pd.Series) -> pd.Series:
    out = s.astype("Int64").astype(str)
    return out.where(out != "<NA>", other=pd.NA)


def _dof_features(bbl: str, as_of: date) -> dict[str, Any]:
    """Latest DOF roll available on or before ``as_of`` (same contract as gold_dof)."""
    out: dict[str, Any] = {}
    df = _parquet_read_bbl(SILVER_DOF, bbl)
    if df.empty:
        return out
    if "bbl" in df.columns:
        df["bbl"] = _norm_series_bbl(df["bbl"])
    df = df[df["bbl"] == bbl]
    if df.empty:
        return out

    df = df.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["roll_available_date"] = pd.to_datetime(
        df["year"].astype("Int64").astype(str) + "-01-01", errors="coerce"
    ).dt.date
    df = df[df["roll_available_date"].notna() & (df["roll_available_date"] <= as_of)]
    if df.empty:
        return out
    row = df.sort_values("year", ascending=False).iloc[0]

    rename = {
        "curacttot": "dof_curacttot",
        "curactland": "dof_curactland",
        "curmkttot": "dof_curmkttot",
        "curmktland": "dof_curmktland",
        "gross_sqft": "dof_gross_sqft",
        "units": "dof_units",
        "yrbuilt": "dof_yrbuilt",
        "bld_story": "dof_bld_story",
    }
    for raw, new in rename.items():
        if raw in row.index and pd.notna(row[raw]):
            out[new] = float(row[raw])
    if "bldg_class" in row.index and pd.notna(row["bldg_class"]):
        out["dof_bldg_class"] = str(row["bldg_class"])
    if "curtaxclass" in row.index and pd.notna(row["curtaxclass"]):
        out["dof_tax_class"] = str(row["curtaxclass"])

    u = out.get("dof_units")
    t = out.get("dof_curacttot")
    if u is not None and t is not None and float(u) > 0:
        out["dof_assess_per_unit"] = float(t) / float(u)
    return out


def _acris_features(bbl: str, as_of: date) -> dict[str, Any]:
    out: dict[str, Any] = {
        "acris_prior_sale_cnt":       0.0,
        "acris_last_deed_amt":        np.nan,
        "acris_days_since_last_deed": np.nan,
        "acris_mortgage_cnt":         0.0,
        "acris_last_mtge_amt":        np.nan,
    }
    df = _parquet_read_bbl(SILVER_ACRIS, bbl)
    if df.empty or "doc_type" not in df.columns:
        return out
    df = df.copy()
    df["bbl"] = _norm_series_bbl(df["bbl"])
    df = df[df["bbl"] == bbl]
    if df.empty:
        return out

    df["document_date"] = pd.to_datetime(df["document_date"], errors="coerce")
    df = df[
        df["document_date"].notna()
        & (df["document_date"].dt.year >= 1900)
        & (df["document_date"].dt.year <= 2030)
    ]
    as_ts = pd.Timestamp(as_of)
    df_pre = df[df["document_date"].dt.date < as_of]

    deeds = df_pre[df_pre["doc_type"].isin(DEED_TYPES)]
    if not deeds.empty:
        out["acris_prior_sale_cnt"] = float(len(deeds))
        last_d = deeds.sort_values("document_date", ascending=False).iloc[0]
        out["acris_last_deed_amt"] = float(last_d["document_amt"]) if pd.notna(last_d.get("document_amt")) else np.nan
        delta = (as_ts - pd.Timestamp(last_d["document_date"])).days
        out["acris_days_since_last_deed"] = float(delta)

    mtge = df_pre[df_pre["doc_type"].isin(MORTGAGE_TYPES)]
    if not mtge.empty:
        out["acris_mortgage_cnt"] = float(len(mtge))
        last_m = mtge.sort_values("document_date", ascending=False).iloc[0]
        out["acris_last_mtge_amt"] = float(last_m["document_amt"]) if pd.notna(last_m.get("document_amt")) else np.nan

    return out


def _j51_features(bbl: str, as_of: date) -> dict[str, Any]:
    out: dict[str, Any] = {}
    df = _parquet_read_bbl(SILVER_J51, bbl)
    if df.empty:
        return out
    df = df.copy()
    df["bbl"] = _norm_series_bbl(df["bbl"])
    df = df[df["bbl"] == bbl]
    if df.empty:
        return out

    for c in ("tax_year", "init_year", "expiry_year"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    as_of_year = as_of.year
    df = df[df["tax_year"].notna() & (df["tax_year"] < as_of_year)]
    if df.empty:
        out["j51_active_flag"] = 0.0
        out["j51_last_abate_amt"] = np.nan
        out["j51_total_abatement"] = np.nan
        return out

    latest = df.sort_values("tax_year", ascending=False).iloc[0]
    if "abatement" in latest.index and pd.notna(latest["abatement"]):
        out["j51_last_abate_amt"] = float(latest["abatement"])
    if "abatement" in df.columns:
        out["j51_total_abatement"] = float(df["abatement"].sum())

    exp = latest.get("expiry_year")
    if pd.notna(exp):
        out["j51_active_flag"] = 1.0 if float(exp) >= as_of_year else 0.0
    else:
        out["j51_active_flag"] = 0.0
    return out


def _pluto_features(bbl: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not GOLD_PLUTO.exists():
        return out
    df = _parquet_read_bbl(GOLD_PLUTO, bbl)
    if df.empty:
        return out
    row = df.iloc[0]
    for c in (
        "pluto_latitude", "pluto_longitude", "subway_dist_km",
        "pluto_numfloors", "pluto_builtfar", "pluto_bldg_footprint",
        "pluto_bldgarea", "pluto_lotarea", "pluto_bldgclass",
    ):
        if c in row.index and pd.notna(row[c]):
            if c == "pluto_bldgclass":
                out[c] = str(row[c])
            else:
                out[c] = float(row[c])
    return out


def build_spine_gold_features_from_bbl(bbl: str, as_of_date: date) -> tuple[dict[str, Any], str]:
    """Return (feature_dict, status) for merging into the spine feature row.

    status
    ------
    ``"ok"``           — at least DOF or PLUTO returned data
    ``"partial"``     — only ACRIS/J-51 style signals (counts), no DOF roll
    ``"no_data"``     — nothing found for this BBL in local Silver/PLUTO files
    """
    merged: dict[str, Any] = {}
    dof = _dof_features(bbl, as_of_date)
    merged.update(dof)
    merged.update(_acris_features(bbl, as_of_date))
    merged.update(_j51_features(bbl, as_of_date))
    merged.update(_pluto_features(bbl))

    if dof:
        status = "ok"
    elif merged.get("pluto_latitude") is not None or merged.get("acris_prior_sale_cnt", 0) > 0:
        status = "partial"
    else:
        status = "no_data"
    return merged, status
