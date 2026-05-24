"""As-of spine features for a single BBL (inference-time parity with training).

Production data path (Option A fix for ML-CRIT-1):
  DOF / ACRIS / J-51 features are read from pre-computed Gold parquet files
  (``ml/data/gold/gold_*_asof.parquet``).  These files are included in the
  Docker image (~24 MB combined) and contain snapshots up to the latest
  training run.  At inference time we pick the most recent snapshot whose
  ``as_of_date`` is <= the requested inference date.

Silver fallback (local dev only):
  If a Gold file is missing but the corresponding Silver file exists, the
  original Silver-based computation is used.  Silver files are ~1.8 GB and
  are excluded from the Docker image, so this path is never hit in production.

PLUTO features are read from ``gold_pluto_features.parquet`` (BBL snapshot,
always in the Docker image).

If neither Gold nor Silver data is found for a BBL, callers get an empty dict
and the model falls back to neighbourhood median imputation.
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

# Gold pre-computed feature tables — included in Docker image (~24 MB combined).
# Production inference reads from these; Silver is the local-dev fallback.
GOLD_DOF_FEATURES   = BASE_DIR / "ml/data/gold/gold_dof_assessment_asof.parquet"
GOLD_ACRIS_FEATURES = BASE_DIR / "ml/data/gold/gold_acris_features_asof.parquet"
GOLD_J51_FEATURES   = BASE_DIR / "ml/data/gold/gold_j51_features_asof.parquet"
GOLD_PLUTO          = BASE_DIR / "ml/data/gold/gold_pluto_features.parquet"
# Sprint A — comp + trend features for inference parity.
# Both tables carry a `comp_segment` column derived from (segment, building_class):
#   one_family / two_family (multi-fam class 02) / three_family (class 03) / condo_coop
GOLD_COMPS   = BASE_DIR / "ml/data/gold/gold_comps_features.parquet"
GOLD_TRENDS  = BASE_DIR / "ml/data/gold/gold_market_trends.parquet"

# Must match gold_acris_features_asof.py
DEED_TYPES = {
    "DEED", "DEEDO", "DEED, BARGAIN AND SALE", "DEED IN LIEU OF FORECLOSURE",
    "DEED, CORPORATION", "DEED, EXECUTOR", "DEED, GUARDIAN",
    "DEED, PERSONAL REPRESENTATIVE", "DEED, TRUSTEE",
    "CONVEYANCE BY REFEREE", "EXECUTOR DEED",
}
MORTGAGE_TYPES = {"MTGE", "AGMT"}


def gold_data_available() -> bool:
    """Return True when all three Gold feature parquets are present on disk.

    Used by PredictionService to surface an operational warning when a deploy
    is missing the Gold files (ML-CRIT-1 regression guard).
    """
    return GOLD_DOF_FEATURES.exists() and GOLD_ACRIS_FEATURES.exists() and GOLD_J51_FEATURES.exists()


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
    """Read rows for a single BBL using predicate pushdown only.

    Tries both the canonical string form and the integer form of the BBL to
    handle parquet files that store BBLs as different dtypes.  Returns an empty
    DataFrame when the path does not exist, the BBL is absent, or pushdown
    raises an unexpected error.

    The previous full-file-scan fallback (read entire parquet, filter in Python)
    has been removed.  That path was never reached in production (Gold files
    always support pushdown) and posed an OOM risk for large Silver files in
    local dev (~600 MB+ per table).
    """
    if not path.exists():
        return pd.DataFrame()
    # Cover three common BBL storage formats: plain string, int64, and float64.
    # float64 is the most common in older parquet exports (e.g. 5016460069.0).
    keys: list[Any] = [bbl]
    if bbl.isdigit():
        keys.append(int(bbl))
        keys.append(float(bbl))
    for key in keys:
        try:
            df = pd.read_parquet(path, columns=columns, filters=[("bbl", "==", key)])
            if not df.empty:
                return df
        except Exception:
            continue
    return pd.DataFrame()


def _norm_series_bbl(s: pd.Series) -> pd.Series:
    out = s.astype("Int64").astype(str)
    return out.where(out != "<NA>", other=pd.NA)


# ── Gold-based feature readers (production path) ──────────────────────────────

def _latest_gold_row(path: Path, bbl: str, as_of: date,
                     columns: list[str] | None = None) -> pd.Series | None:
    """Return the most recent Gold row for ``bbl`` whose ``as_of_date`` <= ``as_of``.

    Returns None when the file is missing, the BBL is not in the table, or
    no snapshot is available on or before the requested date.
    """
    df = _parquet_read_bbl(path, bbl, columns=columns)
    if df.empty:
        return None
    df = df.copy()
    df["as_of_date"] = pd.to_datetime(df["as_of_date"], errors="coerce").dt.date  # type: ignore[union-attr]
    df = df[df["as_of_date"].notna() & (df["as_of_date"] <= as_of)]  # type: ignore[union-attr]
    if df.empty:  # type: ignore[union-attr]
        return None
    return df.sort_values("as_of_date", ascending=False).iloc[0]  # type: ignore[call-overload, union-attr]


def _dof_features_gold(bbl: str, as_of: date) -> dict[str, Any]:
    """DOF assessment features from the pre-computed Gold table (production path)."""
    out: dict[str, Any] = {}
    row = _latest_gold_row(
        GOLD_DOF_FEATURES, bbl, as_of,
        columns=["bbl", "as_of_date", "curacttot", "curactland", "curmkttot",
                 "curmktland", "gross_sqft", "units", "yrbuilt", "bld_story",
                 "dof_bldg_class", "dof_tax_class"],
    )
    if row is None:
        return out
    rename = {
        "curacttot":  "dof_curacttot",
        "curactland": "dof_curactland",
        "curmkttot":  "dof_curmkttot",
        "curmktland": "dof_curmktland",
        "gross_sqft": "dof_gross_sqft",
        "units":      "dof_units",
        "yrbuilt":    "dof_yrbuilt",
        "bld_story":  "dof_bld_story",
    }
    for raw, new in rename.items():
        if raw in row.index and pd.notna(row[raw]):  # type: ignore[truthy-function]
            out[new] = float(row[raw])  # type: ignore[arg-type]
    for cat in ("dof_bldg_class", "dof_tax_class"):
        if cat in row.index and pd.notna(row[cat]):  # type: ignore[truthy-function]
            out[cat] = str(row[cat])
    u = out.get("dof_units")
    t = out.get("dof_curacttot")
    if u is not None and t is not None and float(u) > 0:
        out["dof_assess_per_unit"] = float(t) / float(u)
    return out


def _acris_features_gold(bbl: str, as_of: date) -> dict[str, Any]:
    """ACRIS deed/mortgage features from the pre-computed Gold table (production path)."""
    out: dict[str, Any] = {
        "acris_prior_sale_cnt":       0.0,
        "acris_last_deed_amt":        np.nan,
        "acris_days_since_last_deed": np.nan,
        "acris_mortgage_cnt":         0.0,
        "acris_last_mtge_amt":        np.nan,
    }
    row = _latest_gold_row(
        GOLD_ACRIS_FEATURES, bbl, as_of,
        columns=["bbl", "as_of_date", "acris_prior_sale_cnt", "acris_last_deed_amt",
                 "acris_days_since_last_deed", "acris_mortgage_cnt", "acris_last_mtge_amt"],
    )
    if row is None:
        return out
    for c in ("acris_prior_sale_cnt", "acris_last_deed_amt",
              "acris_days_since_last_deed", "acris_mortgage_cnt", "acris_last_mtge_amt"):
        if c in row.index and pd.notna(row[c]):  # type: ignore[truthy-function]
            out[c] = float(row[c])  # type: ignore[arg-type]
    return out


def _j51_features_gold(bbl: str, as_of: date) -> dict[str, Any]:
    """J-51 tax abatement features from the pre-computed Gold table (production path)."""
    out: dict[str, Any] = {}
    row = _latest_gold_row(
        GOLD_J51_FEATURES, bbl, as_of,
        columns=["bbl", "as_of_date", "j51_active_flag",
                 "j51_last_abate_amt", "j51_total_abatement"],
    )
    if row is None:
        return out
    for c in ("j51_active_flag", "j51_last_abate_amt", "j51_total_abatement"):
        if c in row.index and pd.notna(row[c]):  # type: ignore[truthy-function]
            out[c] = float(row[c])  # type: ignore[arg-type]
    return out


def _dof_features(bbl: str, as_of: date) -> dict[str, Any]:
    """Latest DOF roll available on or before ``as_of``.

    Uses the pre-computed Gold table in production (file present in Docker).
    Falls back to Silver only when Gold is unavailable (local dev with raw data).
    """
    if GOLD_DOF_FEATURES.exists():
        return _dof_features_gold(bbl, as_of)
    # Silver fallback — only reachable locally; Silver excluded from Docker image.
    out: dict[str, Any] = {}
    df = _parquet_read_bbl(SILVER_DOF, bbl)
    if df.empty:
        return out
    if "bbl" in df.columns:
        df["bbl"] = _norm_series_bbl(df["bbl"])  # type: ignore[arg-type]
    df = df[df["bbl"] == bbl]
    if df.empty:
        return out

    df = df.copy()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["roll_available_date"] = pd.to_datetime(
        df["year"].astype("Int64").astype(str) + "-01-01", errors="coerce"
    ).dt.date  # type: ignore[union-attr]
    df = df[df["roll_available_date"].notna() & (df["roll_available_date"] <= as_of)]  # type: ignore[union-attr]
    if df.empty:  # type: ignore[union-attr]
        return out
    row = df.sort_values("year", ascending=False).iloc[0]  # type: ignore[call-overload, union-attr]

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
        if raw in row.index and pd.notna(row[raw]):  # type: ignore[truthy-function]
            out[new] = float(row[raw])  # type: ignore[arg-type]
    if "bldg_class" in row.index and pd.notna(row["bldg_class"]):  # type: ignore[truthy-function]
        out["dof_bldg_class"] = str(row["bldg_class"])
    if "curtaxclass" in row.index and pd.notna(row["curtaxclass"]):  # type: ignore[truthy-function]
        out["dof_tax_class"] = str(row["curtaxclass"])

    u = out.get("dof_units")
    t = out.get("dof_curacttot")
    if u is not None and t is not None and float(u) > 0:
        out["dof_assess_per_unit"] = float(t) / float(u)
    return out


def _acris_features(bbl: str, as_of: date) -> dict[str, Any]:
    """ACRIS deed/mortgage history as-of ``as_of``.

    Uses the pre-computed Gold table in production (file present in Docker).
    Falls back to Silver only when Gold is unavailable (local dev with raw data).
    """
    if GOLD_ACRIS_FEATURES.exists():
        return _acris_features_gold(bbl, as_of)
    # Silver fallback — only reachable locally; Silver excluded from Docker image.
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
    df["bbl"] = _norm_series_bbl(df["bbl"])  # type: ignore[arg-type]
    df = df[df["bbl"] == bbl]
    if df.empty:
        return out

    df["document_date"] = pd.to_datetime(df["document_date"], errors="coerce")
    df = df[
        df["document_date"].notna()  # type: ignore[union-attr]
        & (df["document_date"].dt.year >= 1900)  # type: ignore[union-attr]
        & (df["document_date"].dt.year <= 2030)  # type: ignore[union-attr]
    ]
    as_ts = pd.Timestamp(as_of)
    df_pre = df[df["document_date"].dt.date < as_of]  # type: ignore[union-attr]

    deeds = df_pre[df_pre["doc_type"].isin(DEED_TYPES)]  # type: ignore[union-attr, arg-type]
    if not deeds.empty:  # type: ignore[union-attr]
        out["acris_prior_sale_cnt"] = float(len(deeds))
        last_d = deeds.sort_values("document_date", ascending=False).iloc[0]  # type: ignore[call-overload, union-attr]
        out["acris_last_deed_amt"] = float(last_d["document_amt"]) if pd.notna(last_d.get("document_amt")) else np.nan  # type: ignore[arg-type]
        delta = (as_ts - pd.Timestamp(last_d["document_date"])).days
        out["acris_days_since_last_deed"] = float(delta)

    mtge = df_pre[df_pre["doc_type"].isin(MORTGAGE_TYPES)]  # type: ignore[union-attr, arg-type]
    if not mtge.empty:  # type: ignore[union-attr]
        out["acris_mortgage_cnt"] = float(len(mtge))
        last_m = mtge.sort_values("document_date", ascending=False).iloc[0]  # type: ignore[call-overload, union-attr]
        out["acris_last_mtge_amt"] = float(last_m["document_amt"]) if pd.notna(last_m.get("document_amt")) else np.nan  # type: ignore[arg-type]

    return out


def _j51_features(bbl: str, as_of: date) -> dict[str, Any]:
    """J-51 tax abatement features as-of ``as_of``.

    Uses the pre-computed Gold table in production (file present in Docker).
    Falls back to Silver only when Gold is unavailable (local dev with raw data).
    """
    if GOLD_J51_FEATURES.exists():
        return _j51_features_gold(bbl, as_of)
    # Silver fallback — only reachable locally; Silver excluded from Docker image.
    out: dict[str, Any] = {}
    df = _parquet_read_bbl(SILVER_J51, bbl)
    if df.empty:
        return out
    df = df.copy()
    df["bbl"] = _norm_series_bbl(df["bbl"])  # type: ignore[arg-type]
    df = df[df["bbl"] == bbl]
    if df.empty:
        return out

    for c in ("tax_year", "init_year", "expiry_year"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    as_of_year = as_of.year
    df = df[df["tax_year"].notna() & (df["tax_year"] < as_of_year)]  # type: ignore[union-attr]
    if df.empty:  # type: ignore[union-attr]
        out["j51_active_flag"] = 0.0
        out["j51_last_abate_amt"] = np.nan
        out["j51_total_abatement"] = np.nan
        return out

    latest = df.sort_values("tax_year", ascending=False).iloc[0]  # type: ignore[call-overload, union-attr]
    if "abatement" in latest.index and pd.notna(latest["abatement"]):  # type: ignore[truthy-function]
        out["j51_last_abate_amt"] = float(latest["abatement"])  # type: ignore[arg-type]
    if "abatement" in df.columns:  # type: ignore[union-attr]
        out["j51_total_abatement"] = float(df["abatement"].sum())  # type: ignore[union-attr]

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
    # Numeric columns (includes transit pack v2 features).
    # Reading directly from gold_pluto_features.parquet ensures perfect parity
    # with training — no separate computation, no drift risk.
    for c in (
        "pluto_latitude", "pluto_longitude",
        # Transit pack — all five signals
        "subway_dist_km",
        "subway_n_500m",
        "subway_n_1km",
        "subway_k3_mean_dist_km",
        "subway_hub_flag",
        "subway_cbd_dist_km",
        # Physical / structural
        "pluto_numfloors", "pluto_builtfar", "pluto_bldg_footprint",
        "pluto_bldgarea", "pluto_lotarea",
    ):
        if c in row.index and pd.notna(row[c]):
            out[c] = float(row[c])
    # Categorical
    if "pluto_bldgclass" in row.index and pd.notna(row["pluto_bldgclass"]):
        out["pluto_bldgclass"] = str(row["pluto_bldgclass"])
    return out


# ── Comp + market-trend lookup (Sprint A inference parity) ────────────────────
# Both tables are keyed on as_of_date.  At inference time we typically don't
# have an exact match (today's date isn't in the training spine), so we fall
# back to the most recent precomputed snapshot within a 365-day window for the
# same join key.  This is acceptable because:
#   * comps depend on prior 365 days of sales — yesterday's snapshot is a
#     near-perfect proxy for today's snapshot.
#   * trends are area-level and move slowly.
# If no snapshot exists we return an empty dict and XGBoost imputes via NaN
# handling — the model still produces a valid prediction without comp signal.


_COMP_FEATURE_KEYS = (
    "comp_count", "comp_median_price", "comp_median_ppsqft",
    "comp_search_dist_km", "comp_recency_days",
)
_TREND_FEATURE_KEYS = (
    "nbhd_median_l365", "nbhd_yoy_growth", "borough_yoy_growth",
)


def _comp_features(bbl: str, as_of: date, comp_segment: str | None) -> dict[str, Any]:
    """Look up comp features.  Exact (bbl, as_of, segment) match preferred,
    falling back to the most recent matching row within 365 days."""
    out: dict[str, Any] = {}
    if not comp_segment or not GOLD_COMPS.exists():
        return out
    df = _parquet_read_bbl(GOLD_COMPS, bbl)
    if df.empty:
        return out
    df = df[df["comp_segment"] == comp_segment].copy()
    if df.empty:
        return out
    # Use only snapshots strictly on/before as_of within the lookback window.
    df["as_of_date"] = pd.to_datetime(df["as_of_date"], errors="coerce").dt.date  # type: ignore[union-attr]
    as_of_d = as_of
    df = df[df["as_of_date"].notna() & (df["as_of_date"] <= as_of_d)]  # type: ignore[union-attr]
    if df.empty:  # type: ignore[union-attr]
        return out
    # Take the most recent snapshot (closest to inference date).
    row = df.sort_values("as_of_date", ascending=False).iloc[0]  # type: ignore[call-overload, union-attr]
    for c in _COMP_FEATURE_KEYS:
        if c in row.index and pd.notna(row[c]):  # type: ignore[truthy-function]
            out[c] = float(row[c])  # type: ignore[arg-type]
    return out


def _trend_features(
    borough: int | None,
    neighborhood: str | None,
    as_of: date,
    comp_segment: str | None,
) -> dict[str, Any]:
    """Look up market-trend snapshot for (as_of, borough, neighborhood, segment).
    Falls back to the most recent snapshot within 365 days when no exact match."""
    out: dict[str, Any] = {}
    if borough is None or not neighborhood or not comp_segment or not GOLD_TRENDS.exists():
        return out
    try:
        # The trend file is small per-segment when filtered by area; use partition
        # filters where supported.
        df = pd.read_parquet(
            GOLD_TRENDS,
            filters=[
                ("borough", "==", int(borough)),
                ("comp_segment", "==", comp_segment),
            ],
        )
    except Exception:
        try:
            # Fallback to full read if predicate pushdown isn't available.
            df = pd.read_parquet(GOLD_TRENDS)
            df = df[(df["borough"].astype(int) == int(borough))
                    & (df["comp_segment"] == comp_segment)]
        except Exception:
            import logging
            logging.getLogger("propintel").warning(
                "bbl_feature_builder: could not read GOLD_TRENDS (%s) — trend features skipped",
                GOLD_TRENDS,
            )
            return out
    if df.empty:
        return out
    df = df[df["neighborhood"].astype(str) == str(neighborhood)].copy()
    if df.empty:  # type: ignore[union-attr]
        return out
    df["as_of_date"] = pd.to_datetime(df["as_of_date"], errors="coerce").dt.date  # type: ignore[union-attr]
    df = df[df["as_of_date"].notna() & (df["as_of_date"] <= as_of)]  # type: ignore[union-attr]
    if df.empty:  # type: ignore[union-attr]
        return out
    row = df.sort_values("as_of_date", ascending=False).iloc[0]  # type: ignore[call-overload, union-attr]
    for c in _TREND_FEATURE_KEYS:
        if c in row.index and pd.notna(row[c]):  # type: ignore[truthy-function]
            out[c] = float(row[c])  # type: ignore[arg-type]
    return out


def derive_comp_segment(segment: str | None, building_class: str | None) -> str | None:
    """Map (segment, building_class) → comp_segment key used in Gold tables.

    Returns None when the combo isn't covered by the Sprint A comp/trend
    pipeline (e.g. rentals).  Callers should treat None as "skip the join".
    """
    if not segment:
        return None
    if segment == "one_family":
        return "one_family"
    if segment == "condo_coop":
        return "condo_coop"
    if segment == "multi_family":
        bc = (building_class or "").strip()
        if bc.startswith("02"):
            return "two_family"
        if bc.startswith("03"):
            return "three_family"
    return None


def build_spine_gold_features_from_bbl(
    bbl: str,
    as_of_date: date,
    *,
    segment: str | None = None,
    building_class: str | None = None,
    borough: int | None = None,
    neighborhood: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Return (feature_dict, status) for merging into the spine feature row.

    status
    ------
    ``"ok"``       — at least DOF or PLUTO returned data
    ``"partial"`` — only ACRIS/J-51 style signals (counts), no DOF roll
    ``"no_data"`` — nothing found for this BBL in local Silver/PLUTO files

    Sprint A: when ``segment`` (and for multi_family, ``building_class``) is
    provided we additionally attempt to load comp + trend features.  Missing
    comp/trend rows do not affect the status — XGBoost imputes.
    """
    merged: dict[str, Any] = {}
    dof = _dof_features(bbl, as_of_date)
    merged.update(dof)
    merged.update(_acris_features(bbl, as_of_date))
    merged.update(_j51_features(bbl, as_of_date))
    merged.update(_pluto_features(bbl))

    # Comp + trend features (no impact on status; opt-in via segment kwarg).
    comp_segment = derive_comp_segment(segment, building_class)
    if comp_segment:
        merged.update(_comp_features(bbl, as_of_date, comp_segment))
        merged.update(_trend_features(borough, neighborhood, as_of_date, comp_segment))

    if dof:
        status = "ok"
    elif merged.get("pluto_latitude") is not None or merged.get("acris_prior_sale_cnt", 0) > 0:
        status = "partial"
    else:
        status = "no_data"
    return merged, status
