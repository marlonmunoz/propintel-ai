"""Train per-segment valuation models from the Gold spine + DOF/ACRIS/J-51 features.

This is the Phase E production-ready successor to train_subtype_models.py.

Differences from train_subtype_models.py
-----------------------------------------
1. Input: Gold spine parquet + three Gold feature parquets (no DB-derived CSVs).
2. Split: time-based (train ≤ 2024-12-31, test ≥ 2025-01-31) instead of random 80/20.
   This matches the rolling-origin eval protocol and eliminates temporal leakage.
3. Aggregates (neighborhood_median_price, assess_per_unit) are computed from the
   training split only and applied to the test split — same anti-leakage pattern
   as train_subtype_models.py.
4. Outputs land in ml/artifacts/spine_models/ so existing production artifacts
   are untouched until you're ready to promote.

Run from repo root:
    python ml/models/train_spine_models.py [--subtypes one_family condo_coop …]
"""

from __future__ import annotations

import argparse
import json
import warnings
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import VotingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from lightgbm import LGBMRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

BASE_DIR = Path(__file__).resolve().parents[2]

SPINE_FILE  = BASE_DIR / "ml/data/gold/training_spine_v1.parquet"
GOLD_DOF    = BASE_DIR / "ml/data/gold/gold_dof_assessment_asof.parquet"
GOLD_ACRIS  = BASE_DIR / "ml/data/gold/gold_acris_features_asof.parquet"
GOLD_J51    = BASE_DIR / "ml/data/gold/gold_j51_features_asof.parquet"
GOLD_PLUTO  = BASE_DIR / "ml/data/gold/gold_pluto_features.parquet"
# Sprint A — k-NN comparable sales and per-neighbourhood market trends.
# Both tables carry a `comp_segment` column and are joined per spine row by
# deriving each row's comp_segment from its (segment, building_class).
GOLD_COMPS        = BASE_DIR / "ml/data/gold/gold_comps_features.parquet"
GOLD_TRENDS       = BASE_DIR / "ml/data/gold/gold_market_trends.parquet"
# Sprint G: condo unit-level structural features (PROPMAST roll).
GOLD_CONDO_UNITS  = BASE_DIR / "ml/data/gold/gold_dof_condo_units.parquet"
ARTIFACTS   = BASE_DIR / "ml/artifacts/spine_models"
METRICS_FILE = ARTIFACTS / "spine_model_metrics.json"

REFERENCE_YEAR = 2024

# Time-based split boundary (matches eval_protocol.py fold design)
TRAIN_END   = date(2024, 12, 31)
TEST_START  = date(2025, 1, 31)   # 30-day reporting-lag gap


# ─── Feature definitions ──────────────────────────────────────────────────────

# Common Gold features available across all segments.
_DOF_NUMERIC = [
    "dof_curmkttot",      # DOF market value (total) — strongest single predictor
    "dof_curacttot",      # DOF actual assessed value
    "dof_curactland",     # DOF assessed land value
    "dof_assess_per_unit",# derived: dof_curacttot / dof_units
    "dof_gross_sqft",     # sqft from DOF roll (more reliable than rolling-sales)
    "dof_bld_story",      # number of storeys
    "dof_units",          # units from DOF roll
    "dof_yrbuilt",        # year built from DOF roll
]
_DOF_CAT = ["dof_bldg_class", "dof_tax_class"]

_ACRIS_NUMERIC = [
    "acris_prior_sale_cnt",
    "acris_last_deed_amt",
    "acris_days_since_last_deed",
    "acris_mortgage_cnt",
    "acris_last_mtge_amt",
]

_J51_NUMERIC = [
    "j51_active_flag",
    "j51_last_abate_amt",
    "j51_total_abatement",
]

# PLUTO geographic / physical features (joined on bbl only, no as-of filter).
# lat/lon enable the model to learn sub-neighborhood price gradients.
# Transit feature pack (v2): beyond nearest-station distance we now include
# station-density counts, a k=3 mean distance, a hub flag, and CBD distance.
# Each adds a different spatial scale: density (walkable cluster), hub (route
# diversity), CBD distance (outer-borough commute burden).
_PLUTO_NUMERIC = [
    "pluto_latitude",
    "pluto_longitude",
    # Transit pack — ordered from most to least generalizable
    "subway_dist_km",           # nearest station (original signal)
    "subway_n_500m",            # stations within 0.5 km (dense-transit flag)
    "subway_n_1km",             # stations within 1.0 km (walkable richness)
    "subway_k3_mean_dist_km",   # mean of 3-nearest (smoothed density)
    "subway_hub_flag",          # 1 = nearest station serves 2+ routes
    "subway_cbd_dist_km",       # distance to nearest CBD-flagged station
    "subway_n_lines_05mi",      # distinct route count within 0.5 statute mi
    # Physical / structural
    "pluto_numfloors",
    "pluto_builtfar",
    "pluto_bldg_footprint",
    "pluto_bldgarea",
    "pluto_lotarea",
]
_PLUTO_CAT = ["pluto_bldgclass"]

# Lat/lon excluded from rental models: geographic coordinates allow XGBoost
# to memorise specific building clusters in a small dataset (~4k rows),
# inflating the train/test gap.  All transit-pack features are retained —
# they generalise across years unlike raw coordinates.
_RENTAL_EXCL_COLS = {"pluto_latitude", "pluto_longitude"}
_RENTAL_PLUTO_NUMERIC = [c for c in _PLUTO_NUMERIC if c not in _RENTAL_EXCL_COLS]

# Multi-family override: lat/lon already encode location so density counts
# (n_500m, n_1km) are redundant and push the train/test gap over the 0.15 gate.
# We keep hub_flag (route-diversity premium), cbd_dist_km (commute burden),
# and n_lines_05mi (route diversity) — qualitatively different from density counts.
_MF_EXCL_TRANSIT = {"subway_n_500m", "subway_n_1km"}
_MF_PLUTO_NUMERIC = [c for c in _PLUTO_NUMERIC if c not in _MF_EXCL_TRANSIT]

# Sprint F: multi-family-specific enrichment features.
# - rent_stab_units: DHCR stabilized unit count — directly impacts income potential
#   and therefore investor pricing on 2-3 unit properties.
# - pluto_far_utilization: builtfar / residfar — how much of the allowed residential
#   FAR is consumed; high utilization signals a fully built-out parcel (no add-value
#   upside), while low utilization signals development opportunity and commands a
#   different investor premium. NaN for zero-residfar lots (parks, institutions).
_MF_EXTRA_NUMERIC = [
    "rent_stab_units",
    "pluto_far_utilization",
]

# Sprint G: condo unit-level structural features from the DOF PROPMAST roll.
# These exist ONLY for condo unit lots (lot 1001-6999) and cover 99.8% of the
# condo sales segment (vs ~39% from the pooled DOF CSV).
#   condo_gross_sqft   — true net interior sqft of the unit (from condo declaration)
#   condo_comint_bldg  — unit's ownership % of the building; near-direct price driver
#   condo_comint_land  — unit's land-interest % (correlated with comint_bldg but adds
#                        signal in mixed-use condos where land/bldg ratios diverge)
_CONDO_UNIT_NUMERIC = [
    "condo_gross_sqft",
    "condo_comint_bldg",
    "condo_comint_land",
]

# ── Sprint A: comp + market-trend feature packs ────────────────────────────────
# Comp features (k-NN comparable-sales aggregates, joined via comp_segment).
# Capture local market level: "what did similar nearby properties just sell for?"
#
# Curated lean set chosen empirically: full 7-feature pack widened the
# train/test gap because comp_p25/p75 are near-collinear with comp_median.
# Five features capture all the unique signal:
#   comp_median_price   — main signal: typical price of similar nearby sales
#   comp_median_ppsqft  — size-normalised price (helps when sqft varies)
#   comp_count          — how many comps were available (sparsity flag)
#   comp_search_dist_km — distance to K-th comp (tight cluster vs sparse area)
#   comp_recency_days   — days since most recent comp (data freshness)
_COMP_NUMERIC = [
    "comp_count",
    "comp_median_price",
    "comp_median_ppsqft",
    "comp_search_dist_km",
    "comp_recency_days",
]

# Market-trend features (per-neighbourhood/borough rolling medians and YoY).
# Capture market direction: "is this neighbourhood hot or cooling?"
#
# Lean set: dropping borough_median_l365 (highly collinear with neighbourhood
# median) and nbhd_sale_count_l365 (weak signal that adds tree-split variance).
# Three features remain:
#   nbhd_median_l365    — recent neighbourhood price level (rolling 12-month)
#   nbhd_yoy_growth     — neighbourhood-level direction (1-year ratio)
#   borough_yoy_growth  — borough-level smoothed direction (stable signal)
_TREND_NUMERIC = [
    "nbhd_median_l365",
    "nbhd_yoy_growth",
    "borough_yoy_growth",
]

# Sprint D: derived ratio features computed in _engineer().
# Added to all residential segments to capture zoning density and prior
# financing patterns that XGBoost's axis-aligned splits miss on raw columns.
#   far                 — floor area ratio (bldgarea / lotarea): density signal
#   prior_mortgage_ratio — last recorded LTV proxy: financing pattern signal
_DERIVED_NUMERIC = [
    "far",
    "prior_mortgage_ratio",
]

SEGMENT_FEATURES: dict[str, dict[str, Any]] = {
    "one_family": {
        "target": "sales_price",
        # Sprint B: filter non-arms-length transactions (estate sales, foreclosures,
        # intra-family transfers) that add noise the model otherwise memorises.
        "sales_hygiene": {
            "min_price":   150_000,
            "max_price": 5_000_000,
            "min_ppsqft":     50.0,
        },
        # Sprint C: comp features removed. comp_median_price is a "near-target"
        # signal that perfectly explains 2024 training comps but creates temporal
        # overfit — comp prices in 2024 don't transfer cleanly to 2025 test
        # market. Adding comps widened the R² gap from 0.12 → 0.17 with no
        # meaningful MAE improvement. Trend features retained (96% coverage,
        # market-direction signal generalises well across years).
        "numeric": [
            "neighborhood_median_price", "property_age",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC, *_PLUTO_NUMERIC,
            *_TREND_NUMERIC, *_DERIVED_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT, *_PLUTO_CAT],
        "min_train": 500,
        "min_test":  100,
    },
    # ── Two-family dwellings (building class 02) ──────────────────────────────
    # Splitting the old "multi_family" segment by unit count separates two
    # fundamentally different buyer markets:
    #   two_family — owner-occupiers buying a home with one rental unit.
    #                Pricing logic resembles single-family: location + quality.
    #   three_family — investor buyers pricing off cap rates and rental yield.
    #                  Noisier signal, different feature importance ordering.
    # Combined, they suppressed R² to 0.60.  Split, two_family should reach
    # 0.68–0.73 (similar data density to one_family) and three_family 0.60–0.65.
    "two_family": {
        "target": "sales_price",
        "spine_segment": "multi_family",  # pull rows where segment='multi_family'...
        "building_class_prefix": "02",    # ...then further filter to class 02
        # Sprint A.1 — drop nominal/non-arms-length sales.
        # Cutoffs chosen from observed distribution:
        #   p1.0 = $35k, p5.0 = $400k → anything < $100k is non-arms-length.
        #   p99.9 = $9.3M → cap at $9.5M to suppress data-entry mansions.
        #   ppsqft p1.0 = $17 → require at least $50/sqft when sqft is known.
        "sales_hygiene": {
            "min_price":   100_000,
            "max_price": 9_500_000,
            "min_ppsqft":      50.0,
        },
        # Comp + trend pack lifts comp-aware models on residential 1–4 unit
        # properties.  We keep them off the legacy multi_family for now —
        # the split models are the production path.
        "comp_segment_key": "two_family",
        "numeric": [
            "neighborhood_median_price", "property_age",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC, *_MF_PLUTO_NUMERIC,
            *_COMP_NUMERIC, *_TREND_NUMERIC, *_DERIVED_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT, *_PLUTO_CAT],
        "min_train": 500,
        "min_test":  100,
    },
    # ── Three-family dwellings (building class 03) ─────────────────────────────
    "three_family": {
        "target": "sales_price",
        "spine_segment": "multi_family",
        "building_class_prefix": "03",
        # Sprint C: add sales hygiene (same logic as two_family).
        # Three-family has more non-arms-length noise (estate/inter-family
        # transfers at nominal prices) that inflate training variance.
        "sales_hygiene": {
            "min_price":   100_000,
            "max_price": 9_500_000,
            "min_ppsqft":      40.0,
        },
        # Sprint C: add comp features.  Investor pricing for 3-fam homes is
        # comp-anchored (buyers compare against similar recent nearby sales),
        # making comp_median_price a strong market-pricing signal — same logic
        # that lifted two_family.
        "comp_segment_key": "three_family",
        "numeric": [
            "neighborhood_median_price", "property_age",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC, *_MF_PLUTO_NUMERIC,
            *_COMP_NUMERIC, *_TREND_NUMERIC, *_DERIVED_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT, *_PLUTO_CAT],
        "min_train": 300,
        "min_test":  60,
    },
    # ── Merged multi_family (two-family + three-family pooled) ────────────────
    # Sprint E: three_family was data-starved (5.5k → 11.5k rows after 2019–2021
    # extension, still insufficient).  Pooling with two_family gives ~60k training
    # rows, exposing the model to the full 2-/3-unit market cycle.
    #
    # Differentiating 2-fam vs 3-fam is left to the model via residential_units
    # (and total_units) rather than a hard split.  Both are bought by similar
    # owner-occupier / small-investor profiles in the same neighbourhoods.
    #
    # No building_class_prefix filter — takes ALL multi_family spine rows.
    "multi_family": {
        "target": "sales_price",
        "sales_hygiene": {
            "min_price":   100_000,
            "max_price": 9_500_000,
            "min_ppsqft":      40.0,  # slightly looser than two_family to keep 3-fam rows
        },
        "comp_segment_key": "two_family",  # comp pool is two_family (larger, same geography)
        "numeric": [
            "neighborhood_median_price", "property_age",
            "residential_units", "total_units",  # key differentiator: 2 vs 3 units
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC, *_MF_PLUTO_NUMERIC,
            *_MF_EXTRA_NUMERIC,  # rent_stab_units, pluto_far_utilization
            *_COMP_NUMERIC, *_TREND_NUMERIC, *_DERIVED_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT, *_PLUTO_CAT],
        "min_train": 500,
        "min_test":  100,
    },
    "condo_coop": {
        "target": "sales_price",
        "numeric": [
            "neighborhood_median_price", "property_age",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC, *_PLUTO_NUMERIC,
            # Sprint F: development-pressure signal (far_utilization) is meaningful
            # for condos — a fully built-out site has no add-value upside, which
            # affects pricing differently than a under-utilized parcel.
            # rent_stab_units has real coverage here: co-ops and large condo
            # buildings are exactly the 32k BBLs matched in the DHCR snapshot.
            "pluto_far_utilization",
            "rent_stab_units",
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT, *_PLUTO_CAT],
        "min_train": 500,
        "min_test":  100,
    },
    # ── Condo / co-op split (Sprint G) ─────────────────────────────────────────
    # Condos get the full DOF unit-level feature pack (condo_gross_sqft,
    # condo_comint_bldg, condo_comint_land) sourced from the PROPMAST roll,
    # which covers 99.8% of the condo segment (vs ~39% from the pooled CSV).
    # Co-ops intentionally do NOT get these — they share one building-level BBL
    # and have no public unit-level data; adding condo_* features there would
    # produce near-100% NaN columns.
    "condo": {
        "target": "sales_price",
        "numeric": [
            "neighborhood_median_price", "property_age",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC, *_PLUTO_NUMERIC,
            "pluto_far_utilization",
            "rent_stab_units",
            *_CONDO_UNIT_NUMERIC,  # Sprint G: true unit sqft + common-interest %
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT, *_PLUTO_CAT],
        "min_train": 500,
        "min_test":  100,
    },
    "coop": {
        "target": "sales_price",
        "numeric": [
            "neighborhood_median_price", "property_age",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC, *_PLUTO_NUMERIC,
            "pluto_far_utilization",
            "rent_stab_units",
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT, *_PLUTO_CAT],
        "min_train": 500,
        "min_test":  100,
    },
    # ── Pooled rental model ────────────────────────────────────────────────────
    # rental_walkup + rental_elevator are pooled into one model to eliminate
    # the ~350-row starvation problem for elevator rentals.
    # is_elevator (0/1) is added as a feature so the model can learn the price
    # premium for elevator buildings without splitting into two data-starved models.
    # Lat/lon are excluded to prevent geographic over-memorisation.
    "rentals_all": {
        "target": "price_per_unit",
        "numeric": [
            "neighborhood_median_price", "property_age",
            "total_units", "residential_units",
            "is_elevator",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC, *_RENTAL_PLUTO_NUMERIC,
            # Sprint F: rent_stab_units is the right segment for this feature.
            # Large rental buildings (7+ units, pre-1974) are heavily represented
            # in the DHCR stabilization snapshot. Stabilization rate directly caps
            # income potential and therefore building sale price.
            # subway_n_lines_05mi already flows through _RENTAL_PLUTO_NUMERIC.
            "rent_stab_units",
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT, *_PLUTO_CAT],
        "min_train": 300,
        "min_test":  60,
    },
    # ── Legacy individual rental segments (kept for backward compat) ───────────
    # These are NOT trained by default when rentals_all is used.
    "rental_walkup": {
        "target": "price_per_unit",
        "numeric": [
            "neighborhood_median_price", "property_age",
            "total_units", "residential_units",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC, *_RENTAL_PLUTO_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT, *_PLUTO_CAT],
        "min_train": 200,
        "min_test":  50,
    },
    "rental_elevator": {
        "target": "price_per_unit",
        "numeric": [
            "neighborhood_median_price", "property_age",
            "total_units", "residential_units",
            *_DOF_NUMERIC, *_ACRIS_NUMERIC, *_J51_NUMERIC, *_RENTAL_PLUTO_NUMERIC,
        ],
        "categorical": ["borough_name", "neighborhood", *_DOF_CAT, *_PLUTO_CAT],
        "min_train": 100,
        "min_test":  20,
    },
}

# ─── LightGBM params (Sprint D) ──────────────────────────────────────────────
# Segments listed here use LGBMRegressor instead of XGBRegressor.
# LightGBM's leaf-wise tree growth consistently outperforms XGBoost's
# level-wise growth on tabular data of this size (20k-30k rows), typically
# by 2-5 pp R².  The VotingRegressor + early stopping infrastructure is
# unchanged.  n_estimators here is an upper bound — early stopping calibrates
# the actual tree count per run.
LGBM_SEGMENTS = {"one_family", "two_family", "three_family", "multi_family"}

SEGMENT_LGBM_PARAMS: dict[str, dict[str, Any]] = {
    # one_family: 31k rows, SFH owner-occupier.  Leaf-wise allows deeper
    # focus on the high-value NYC micro-markets without global depth limit.
    "one_family": {
        "n_estimators": 1500, "learning_rate": 0.04, "num_leaves": 63,
        "min_child_samples": 20, "subsample": 0.75, "colsample_bytree": 0.70,
        "reg_alpha": 0.5, "reg_lambda": 2.0,
        "subsample_freq": 1,
    },
    # two_family: 23k rows, comp + trend features — moderate regularisation.
    "two_family": {
        "n_estimators": 1500, "learning_rate": 0.035, "num_leaves": 47,
        "min_child_samples": 30, "subsample": 0.75, "colsample_bytree": 0.65,
        "reg_alpha": 1.0, "reg_lambda": 3.5,
        "subsample_freq": 1,
    },
    # three_family: 5.7k rows — smaller leaves + stronger L1/L2 to prevent
    # memorisation of sparse investor markets.
    "three_family": {
        "n_estimators": 1500, "learning_rate": 0.025, "num_leaves": 15,
        "min_child_samples": 25, "subsample": 0.60, "colsample_bytree": 0.55,
        "reg_alpha": 2.0, "reg_lambda": 5.0,
        "subsample_freq": 1,
    },
    # multi_family (merged): ~60k rows — between two_family and one_family density.
    # num_leaves=47 matches two_family; residential_units + total_units carry the
    # 2-vs-3 signal so no depth reduction needed.
    "multi_family": {
        "n_estimators": 1500, "learning_rate": 0.035, "num_leaves": 47,
        "min_child_samples": 30, "subsample": 0.75, "colsample_bytree": 0.65,
        "reg_alpha": 1.0, "reg_lambda": 3.5,
        "subsample_freq": 1,
    },
}

SEGMENT_XGB_PARAMS: dict[str, dict[str, Any]] = {
    # Sprint B+: comp + trend features added; depth restored to 6 so the model
    # can learn comp×location interactions.  Regularisation kept tighter than
    # Sprint A (colsample 0.80→0.70, reg_alpha 0.1→0.5, reg_lambda 1.0→2.0)
    # to prevent the comp signal from creating overfit on noisy comps.
    # min_child_weight 3→5: balanced between Sprint A (3) and Sprint B (7).
    "one_family": {
        "n_estimators": 600, "learning_rate": 0.04, "max_depth": 6,
        "min_child_weight": 5, "subsample": 0.75, "colsample_bytree": 0.70,
        "gamma": 0.15, "reg_alpha": 0.5, "reg_lambda": 2.0,
    },
    # two_family: 24k rows, owner-occupier pricing.  Sprint-A-tuned:
    # adding comp + trend features pushed the gap toward 0.15; we tighten
    # min_child_weight + L1/L2 to keep splits conservative on the new
    # near-target signals (comp_median_price, nbhd_median_l365).
    "two_family": {
        "n_estimators": 600, "learning_rate": 0.035, "max_depth": 5,
        "min_child_weight": 10, "subsample": 0.75, "colsample_bytree": 0.65,
        "gamma": 0.25, "reg_alpha": 1.0, "reg_lambda": 3.5,
    },
    # three_family: ~6k rows, investor/cap-rate pricing — very noisy signal.
    # Depth-3 trees + very aggressive L1/L2; pushing min_child_weight to 35
    # and colsample to 0.45 forces the model to rely on the strongest signals
    # (DOF assessment, neighborhood median) rather than memorising rare blocks.
    "three_family": {
        "n_estimators": 400, "learning_rate": 0.025, "max_depth": 3,
        "min_child_weight": 35, "subsample": 0.60, "colsample_bytree": 0.45,
        "gamma": 0.40, "reg_alpha": 4.0, "reg_lambda": 10.0,
    },
    # Legacy combined — not trained by default.
    "multi_family": {
        "n_estimators": 700, "learning_rate": 0.035, "max_depth": 5,
        "min_child_weight": 7, "subsample": 0.75, "colsample_bytree": 0.65,
        "gamma": 0.2, "reg_alpha": 0.8, "reg_lambda": 3.0,
    },
    "condo_coop": {
        "n_estimators": 800, "learning_rate": 0.05, "max_depth": 5,
        "min_child_weight": 4, "subsample": 0.8, "colsample_bytree": 0.8,
        "gamma": 0.1, "reg_alpha": 0.3, "reg_lambda": 1.0,
    },
    # Sprint G split — start from condo_coop params; tune per-segment later.
    "condo": {
        "n_estimators": 800, "learning_rate": 0.05, "max_depth": 5,
        "min_child_weight": 4, "subsample": 0.8, "colsample_bytree": 0.8,
        "gamma": 0.1, "reg_alpha": 0.3, "reg_lambda": 1.0,
    },
    "coop": {
        "n_estimators": 800, "learning_rate": 0.05, "max_depth": 5,
        "min_child_weight": 4, "subsample": 0.8, "colsample_bytree": 0.8,
        "gamma": 0.1, "reg_alpha": 0.3, "reg_lambda": 1.0,
    },
    # Pooled rental model (walkup + elevator).
    # Very aggressive regularisation closes the train/test gap from ~0.19 → 0.13.
    # No lat/lon to prevent geographic memorisation in a small dataset.
    "rentals_all": {
        "n_estimators": 350, "learning_rate": 0.03, "max_depth": 3,
        "min_child_weight": 15, "subsample": 0.65, "colsample_bytree": 0.50,
        "gamma": 0.30, "reg_alpha": 2.5, "reg_lambda": 6.0,
    },
    # Legacy individual rental params (only used if explicitly requested).
    "rental_walkup": {
        "n_estimators": 500, "learning_rate": 0.04, "max_depth": 3,
        "min_child_weight": 6, "subsample": 0.75, "colsample_bytree": 0.6,
        "gamma": 0.2, "reg_alpha": 1.0, "reg_lambda": 3.0,
    },
    "rental_elevator": {
        "n_estimators": 150, "learning_rate": 0.04, "max_depth": 3,
        "min_child_weight": 10, "subsample": 0.7, "colsample_bytree": 0.6,
        "gamma": 0.3, "reg_alpha": 2.0, "reg_lambda": 5.0,
    },
}

# Segments that use a 5-seed VotingRegressor to reduce variance.
# one_family added Sprint B: 32k rows are sufficient to support ensemble
# voting; eliminates single-seed variance that inflated the R² gap to 0.11.
ENSEMBLE_SEGMENTS = {"one_family", "multi_family", "rentals_all"}

# Segments where rare (< RARE_N training rows) neighbourhoods are collapsed
# to "Other_<Borough>" before OHE, preventing thin-slice memorisation.
# one_family intentionally excluded: SFH pricing is highly location-specific
# and collapsing 73 micro-neighbourhoods cost ~7pp of test R² in Sprint B.
# The building-subclass OHE dominance seen before is addressed instead by
# comp + trend features that provide a market-level anchor.
RARE_NBHD_SEGMENTS = {"multi_family"}
RARE_N = 30  # neighbourhoods with fewer train rows are collapsed

# Default segments trained when no --subtypes flag is given.
# Sprint E: multi_family (merged) replaces the split two_family + three_family.
DEFAULT_SEGMENTS = {"one_family", "multi_family", "condo_coop", "rentals_all"}

# Number of seeds for VotingRegressor ensemble.
N_ENSEMBLE_SEEDS = 5

BOROUGH_NAMES = {1: "Manhattan", 2: "Bronx", 3: "Brooklyn", 4: "Queens", 5: "Staten Island"}

# ─── Condo / co-op split (building-class category) ───────────────────────────
# The legacy `condo_coop` segment pools two fundamentally different asset types:
#   * Condos (categories 12/13/15): each unit is its own real-property tax lot
#     (lot 1001-6999), so DOF unit-level assessment data EXISTS and can be
#     enriched further.
#   * Co-ops (categories 09/10/17): the corporation owns the whole building as a
#     single tax lot; a "sale" is shares, not real property. NO public unit-level
#     data exists anywhere for co-op units — their pricing ceiling is structural.
# Pooling them caps both. We split at load time so each can be trained, tuned,
# and (eventually) data-enriched independently without a full spine rebuild.
_COOP_CATEGORIES  = ("09", "10", "17")
_CONDO_CATEGORIES = ("12", "13", "15")


def _split_condo_coop(spine: pd.DataFrame) -> pd.DataFrame:
    """Re-derive `segment` so condo_coop rows become `condo` or `coop`.

    Driven by the 2-digit DOF building-class category prefix. Rows already
    labelled something other than condo_coop are untouched.
    """
    if "building_class" not in spine.columns:
        return spine
    is_cc = spine["segment"] == "condo_coop"
    if not is_cc.any():
        return spine
    cat = spine["building_class"].astype(str).str.strip().str[:2]
    new_seg = spine["segment"].copy()
    new_seg = new_seg.mask(is_cc & cat.isin(_COOP_CATEGORIES),  "coop")
    new_seg = new_seg.mask(is_cc & cat.isin(_CONDO_CATEGORIES), "condo")
    spine["segment"] = new_seg
    n_condo = int((spine["segment"] == "condo").sum())
    n_coop  = int((spine["segment"] == "coop").sum())
    n_left  = int((spine["segment"] == "condo_coop").sum())
    print(f"  Split condo_coop → condo={n_condo:,}, coop={n_coop:,}, "
          f"unclassified(left as condo_coop)={n_left:,}")
    return spine


# ─── Data loading ─────────────────────────────────────────────────────────────

def load_enriched_spine() -> pd.DataFrame:
    """Load spine and left-join all three Gold feature files."""
    print("Loading spine …")
    spine = pd.read_parquet(SPINE_FILE)
    spine["sale_date"]  = pd.to_datetime(spine["sale_date"]).dt.date
    spine["as_of_date"] = pd.to_datetime(spine["as_of_date"]).dt.date.astype(str)
    spine = _split_condo_coop(spine)
    print(f"  Spine rows: {len(spine):,}")

    join_keys = ["bbl", "as_of_date"]

    def _dedup(df: pd.DataFrame, label: str) -> pd.DataFrame:
        """Drop duplicate (bbl, as_of_date) rows, keeping the first.
        The spine itself can have two sales on the same day for the same BBL;
        without deduplication a left join would explode row counts."""
        before = len(df)
        df = df.drop_duplicates(subset=join_keys).reset_index(drop=True)
        if before != len(df):
            print(f"    [{label}] deduped {before - len(df):,} duplicate join keys")
        return df

    # ── DOF ──────────────────────────────────────────────────────────────────
    print("  Joining Gold DOF …")
    dof = pd.read_parquet(GOLD_DOF)
    dof["as_of_date"] = pd.to_datetime(dof["as_of_date"]).dt.date.astype(str)
    dof_rename = {
        "curacttot": "dof_curacttot", "curactland": "dof_curactland",
        "curmkttot": "dof_curmkttot", "curmktland": "dof_curmktland",
        "gross_sqft": "dof_gross_sqft", "units": "dof_units",
        "yrbuilt": "dof_yrbuilt", "bld_story": "dof_bld_story",
    }
    dof_keep = join_keys + [c for c in dof_rename if c in dof.columns] + \
               ["dof_bldg_class", "dof_tax_class"]
    dof_keep = list(dict.fromkeys(c for c in dof_keep if c in dof.columns))
    dof_sub  = _dedup(dof[dof_keep].rename(columns=dof_rename), "DOF")  # type: ignore[arg-type]
    spine = spine.merge(dof_sub, on=join_keys, how="left")

    # ── ACRIS ─────────────────────────────────────────────────────────────────
    print("  Joining Gold ACRIS …")
    acris = pd.read_parquet(GOLD_ACRIS)
    acris["as_of_date"] = pd.to_datetime(acris["as_of_date"]).dt.date.astype(str)
    acris_cols = join_keys + [c for c in acris.columns if c.startswith("acris_")]
    acris_sub  = _dedup(acris[[c for c in acris_cols if c in acris.columns]], "ACRIS")  # type: ignore[arg-type]
    spine = spine.merge(acris_sub, on=join_keys, how="left")

    # ── J-51 ─────────────────────────────────────────────────────────────────
    print("  Joining Gold J-51 …")
    j51 = pd.read_parquet(GOLD_J51)
    j51["as_of_date"] = pd.to_datetime(j51["as_of_date"]).dt.date.astype(str)
    j51_cols = join_keys + [c for c in j51.columns if c.startswith("j51_")]
    j51_sub  = _dedup(j51[[c for c in j51_cols if c in j51.columns]], "J51")  # type: ignore[arg-type]
    spine = spine.merge(j51_sub, on=join_keys, how="left")

    # ── PLUTO ────────────────────────────────────────────────────────────────
    # Joined on bbl only (no as_of_date) — physical/geo attributes are stable.
    print("  Joining Gold PLUTO …")
    pluto = pd.read_parquet(GOLD_PLUTO)
    # Pull all pluto_* and subway_* columns plus any named extras that don't
    # carry those prefixes (e.g. rent_stab_units from the DHCR rentstab join).
    _PLUTO_NAMED_EXTRAS = ["rent_stab_units"]
    pluto_geo = [
        c for c in pluto.columns
        if c.startswith("pluto_") or c.startswith("subway_")
        or c in _PLUTO_NAMED_EXTRAS
    ]
    pluto_sub = pluto[["bbl"] + pluto_geo].drop_duplicates(subset=["bbl"]).reset_index(drop=True)  # type: ignore[arg-type]
    spine = spine.merge(pluto_sub, on="bbl", how="left")
    print(f"    PLUTO match rate: {spine['pluto_latitude'].notna().mean():.1%}")

    # ── Condo unit structural features (Sprint G) ─────────────────────────────
    # BBL-only join: one row per condo unit lot in the roll snapshot.
    # Non-condo rows (co-ops, multifamily, etc.) get NaN for all condo_* cols,
    # which sklearn handles cleanly via the SimpleImputer in the pipeline.
    if GOLD_CONDO_UNITS.exists():
        print("  Joining Gold condo unit features …")
        cuf = pd.read_parquet(GOLD_CONDO_UNITS)
        cuf["bbl"] = cuf["bbl"].astype(str).str.strip()
        cuf_cols = ["bbl"] + [c for c in cuf.columns if c.startswith("condo_")]
        cuf_sub  = cuf[cuf_cols].drop_duplicates(subset=["bbl"]).reset_index(drop=True)  # type: ignore[arg-type]
        before = len(spine)
        spine = spine.merge(cuf_sub, on="bbl", how="left")
        assert len(spine) == before, "condo units join changed row count"
        cov = spine["condo_gross_sqft"].notna().mean()
        print(f"    condo_gross_sqft coverage: {cov:.1%}")
    else:
        print("  [warn] gold_dof_condo_units.parquet missing — condo unit features unavailable")
        for col in _CONDO_UNIT_NUMERIC:
            spine[col] = float("nan")

    # Ensure integer/mixed columns arrive as float for sklearn compatibility.
    for c in ["acris_prior_sale_cnt", "acris_mortgage_cnt", "j51_active_flag",
              *_PLUTO_NUMERIC, *_PLUTO_NAMED_EXTRAS, *_CONDO_UNIT_NUMERIC]:
        if c in spine.columns:
            spine[c] = pd.to_numeric(spine[c], errors="coerce").astype(float)  # type: ignore[union-attr]

    # ── Comp + Trend joins (Sprint A) ────────────────────────────────────────
    # Derive each spine row's comp_segment key from (segment, building_class).
    # The split is: 1-fam → one_family, multi_fam class 02 → two_family,
    # multi_fam class 03 → three_family, condo_coop → condo_coop.  Any other
    # combination gets NaN, meaning no comp/trend join (those segments either
    # don't have comp tables built or aren't part of Sprint A).
    # condo / coop / condo_coop all map to the pooled "condo_coop" comp + trend
    # tables — the gold comp/trend builders key on the pooled segment, and the
    # neighbourhood-level market anchor is shared across condo and co-op.
    bc_str = spine["building_class"].astype(str)
    seg    = spine["segment"]
    spine["comp_segment"] = np.where(
        seg == "one_family", "one_family",
        np.where(
            (seg == "multi_family") & bc_str.str.startswith("02"), "two_family",
            np.where(
                (seg == "multi_family") & bc_str.str.startswith("03"), "three_family",
                np.where(
                    seg.isin(["condo", "coop", "condo_coop"]), "condo_coop", None,  # type: ignore[arg-type]
                ),
            ),
        ),
    )

    if GOLD_COMPS.exists():
        print("  Joining Gold comps …")
        comps = pd.read_parquet(GOLD_COMPS)
        comps["as_of_date"] = comps["as_of_date"].astype(str)
        # Multiple sale events on the same day for the same BBL produce
        # duplicate (bbl, as_of_date, comp_segment) rows.  Comps are computed
        # off as_of_date so all duplicates carry the same values — keep first.
        comp_keys = ["bbl", "as_of_date", "comp_segment"]
        before_dedup = len(comps)
        comps = comps.drop_duplicates(subset=comp_keys).reset_index(drop=True)
        if before_dedup != len(comps):
            print(f"    [comps] deduped {before_dedup - len(comps):,} duplicate keys")
        before = len(spine)
        spine = spine.merge(comps, on=comp_keys, how="left")
        assert len(spine) == before, "comps join changed row count"
        cov = spine["comp_median_price"].notna().mean()
        print(f"    comp coverage: {cov:.1%}")
    else:
        print("  [warn] gold_comps_features.parquet missing — comp features unavailable")

    if GOLD_TRENDS.exists():
        print("  Joining Gold market trends …")
        trends = pd.read_parquet(GOLD_TRENDS)
        trends["as_of_date"] = trends["as_of_date"].astype(str)
        # Trend table is keyed on (as_of_date, borough, neighborhood, comp_segment).
        # Spine `borough` is int and `neighborhood` is str — match dtypes.
        spine["borough"] = spine["borough"].astype("int64")
        trends["borough"] = trends["borough"].astype("int64")
        trend_keys = ["as_of_date", "borough", "neighborhood", "comp_segment"]
        before_dedup = len(trends)
        trends = trends.drop_duplicates(subset=trend_keys).reset_index(drop=True)
        if before_dedup != len(trends):
            print(f"    [trends] deduped {before_dedup - len(trends):,} duplicate keys")
        before = len(spine)
        spine = spine.merge(trends, on=trend_keys, how="left")
        assert len(spine) == before, "trends join changed row count"
        cov = spine["nbhd_median_l365"].notna().mean()
        print(f"    trend coverage: {cov:.1%}")
    else:
        print("  [warn] gold_market_trends.parquet missing — trend features unavailable")

    print(f"  Enriched rows: {len(spine):,}  cols: {len(spine.columns)}")
    return spine


# ─── Sales hygiene (Sprint A.1) ───────────────────────────────────────────────
# NYC rolling sales records include $1 family transfers, foreclosure deeds at
# nominal prices, estate transfers, and bulk-portfolio prices.  Keeping these
# rows pollutes the regression target and inflates train/test variance.  The
# filter below is opt-in per segment via SEGMENT_FEATURES["sales_hygiene"]
# so existing gate-passing models are unaffected.
#
# Why each filter exists:
#   min_price   — drops $1/$10/$5k transfers (clear non-arms-length).
#                 For 2-family the 5th percentile of real arms-length sales
#                 is ~$400k; anything below $100k is almost certainly a
#                 nominal transfer or foreclosure pricing.
#   max_price   — drops likely data-entry errors (extreme outliers above the
#                 99.9th percentile that can pull the model toward memorising
#                 single mansion sales).
#   min_ppsqft  — drops sales whose price-per-sqft is implausibly low,
#                 which usually means gross_sqft is wrong (data error).
#                 Only applied when gross_sqft is known and reasonable.

def _apply_sales_hygiene(
    df: pd.DataFrame, segment: str, hygiene: dict[str, Any]
) -> pd.DataFrame:
    """Drop non-arms-length and obvious data-error rows.  Returns filtered copy."""
    if df.empty:
        return df

    n0 = len(df)
    out = df.copy()
    out["sales_price"] = pd.to_numeric(out["sales_price"], errors="coerce")

    min_price = hygiene.get("min_price")
    max_price = hygiene.get("max_price")
    if min_price is not None:
        out = out[out["sales_price"] >= float(min_price)]
    if max_price is not None:
        out = out[out["sales_price"] <= float(max_price)]

    min_ppsqft = hygiene.get("min_ppsqft")
    if min_ppsqft is not None and "gross_sqft" in out.columns:  # type: ignore[union-attr]
        sqft = pd.to_numeric(out["gross_sqft"], errors="coerce")
        ppsqft = out["sales_price"] / sqft.where(sqft > 100, np.nan)  # type: ignore[union-attr]
        # Only drop when gross_sqft is known and ppsqft is implausibly low.
        # Rows with unknown sqft are kept (no signal to filter on).
        keep_mask = ppsqft.isna() | (ppsqft >= float(min_ppsqft))  # type: ignore[union-attr]
        out = out[keep_mask]

    n1 = len(out)
    if n1 < n0:
        pct = (n0 - n1) / n0 * 100
        print(f"    [{segment}] sales hygiene: dropped {n0 - n1:,} rows ({pct:.1f}%)")
    return out  # type: ignore[return-value]


# ─── Feature engineering ──────────────────────────────────────────────────────

def _engineer(df: pd.DataFrame) -> pd.DataFrame:
    """Add derived columns that don't use target values."""
    df = df.copy()
    # Borough name for the categorical encoder.
    if "borough" in df.columns:
        df["borough_name"] = df["borough"].map(BOROUGH_NAMES.get).fillna("Unknown")

    # Property age from DOF year-built (fall back to spine year_built).
    yr = df.get("dof_yrbuilt", df.get("year_built"))
    if yr is not None:
        df["property_age"] = REFERENCE_YEAR - pd.to_numeric(yr, errors="coerce")  # type: ignore[operator]
        df["property_age"] = df["property_age"].clip(0, 200)

    # Assessed value per unit (the PLUTO assess_per_unit equivalent).
    if "dof_curacttot" in df.columns and "dof_units" in df.columns:
        units = pd.to_numeric(df["dof_units"], errors="coerce").clip(lower=1)  # type: ignore[union-attr]
        df["dof_assess_per_unit"] = (
            pd.to_numeric(df["dof_curacttot"], errors="coerce") / units
        )

    # Floor Area Ratio (FAR): built square footage divided by lot area.
    # A key NYC zoning signal — higher FAR → denser area → typically higher value.
    # NaN when either component is missing (imputed by median in the pipeline).
    if "pluto_bldgarea" in df.columns and "pluto_lotarea" in df.columns:
        bldg = pd.to_numeric(df["pluto_bldgarea"], errors="coerce")
        lot  = pd.to_numeric(df["pluto_lotarea"],  errors="coerce")
        df["far"] = bldg / lot.where(lot > 0, np.nan)  # type: ignore[union-attr]

    # Prior mortgage LTV proxy: last recorded mortgage divided by last deed price.
    # Properties bought with high leverage tend to be priced closer to market;
    # cash or low-LTV buyers sometimes acquire at discount.
    if "acris_last_mtge_amt" in df.columns and "acris_last_deed_amt" in df.columns:
        mtge = pd.to_numeric(df["acris_last_mtge_amt"], errors="coerce")
        deed = pd.to_numeric(df["acris_last_deed_amt"],  errors="coerce")
        df["prior_mortgage_ratio"] = mtge / deed.where(deed > 10_000, np.nan)  # type: ignore[union-attr]
        # Cap at 1.5 (over-mortgaged is noise above that level).
        df["prior_mortgage_ratio"] = df["prior_mortgage_ratio"].clip(upper=1.5)

    # sales_price must be positive.
    df = df[pd.to_numeric(df["sales_price"], errors="coerce").gt(0)]  # type: ignore[assignment, union-attr]
    df["sales_price"] = pd.to_numeric(df["sales_price"], errors="coerce")

    return df


# ─── Neighbourhood aggregates (train rows only) ───────────────────────────────

def _fit_neighborhood_stats(train: pd.DataFrame, target: str) -> dict:
    """Compute neighbourhood stats from training rows only — no leakage."""
    price_col = "sales_price" if target == "sales_price" else "price_per_unit"
    medians = train.groupby("neighborhood")[price_col].median()
    global_med_raw = train[price_col].median()
    global_med = float(global_med_raw) if pd.notna(global_med_raw) else float("nan")  # type: ignore[arg-type]
    stats: dict[str, Any] = {
        "neighborhoods": medians.to_dict(),
        "global_median": global_med,
    }
    # DOF assess_per_unit neighbourhood medians (for imputation).
    if "dof_assess_per_unit" in train.columns:
        # Robust to nullable dtypes (pd.NA) in some folds.
        apu = pd.to_numeric(train["dof_assess_per_unit"], errors="coerce").groupby(train["neighborhood"]).median()  # type: ignore[union-attr]
        stats["dof_assess_per_unit_neighborhoods"] = apu.to_dict()
        apu_global_raw = pd.to_numeric(train["dof_assess_per_unit"], errors="coerce").median()  # type: ignore[union-attr]
        stats["dof_assess_per_unit_global"] = (
            float(apu_global_raw) if pd.notna(apu_global_raw) else float("nan")
        )
    return stats


def _apply_neighborhood_stats(df: pd.DataFrame, stats: dict, target: str) -> pd.DataFrame:
    """Apply pre-fitted stats to any split without touching its target values."""
    df = df.copy()
    df["neighborhood_median_price"] = (
        df["neighborhood"].map(stats["neighborhoods"]).fillna(stats["global_median"])
    )
    if "dof_assess_per_unit" in df.columns and "dof_assess_per_unit_neighborhoods" in stats:
        global_fill = stats.get("dof_assess_per_unit_global", float("nan"))
        df["dof_assess_per_unit"] = pd.to_numeric(df["dof_assess_per_unit"], errors="coerce").fillna(  # type: ignore[union-attr]
            df["neighborhood"].map(stats["dof_assess_per_unit_neighborhoods"]).fillna(global_fill)
        )
    if target == "price_per_unit":
        df = df[df["total_units"].notna() & (df["total_units"] > 0)].copy()  # type: ignore[assignment]
        df["price_per_unit"] = df["sales_price"] / df["total_units"]
    return df


# ─── Neighbourhood collapse ───────────────────────────────────────────────────

def _collapse_rare_neighborhoods(train: pd.DataFrame, test: pd.DataFrame,
                                  rare_n: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Replace thin neighbourhood labels with 'Other_<BoroughName>'.

    Thresholds are computed from train only (no look-ahead into test).
    """
    boro_name_map = BOROUGH_NAMES
    counts = train["neighborhood"].value_counts()
    rare = set(counts[counts < rare_n].index)  # type: ignore[index]
    if not rare:
        return train, test

    def _boro_label(df: pd.DataFrame) -> pd.Series:
        return df["borough"].map(boro_name_map.get).fillna("Unknown")  # type: ignore[return-value]

    def _replace(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        mask = df["neighborhood"].isin(list(rare))
        df.loc[mask, "neighborhood"] = ("Other_" + _boro_label(df).loc[df.index[mask]]).values  # type: ignore[index]
        return df

    n_collapsed = len(rare)
    print(f"    Collapsed {n_collapsed:,} rare neighbourhoods (< {rare_n} train rows) → Other_<Borough>")
    return _replace(train), _replace(test)


# ─── Early stopping (Sprint C/D) ─────────────────────────────────────────────
# Segments where we use a chronological validation holdout to determine the
# optimal n_estimators, then re-fit on all training data with that fixed value.
EARLY_STOPPING_SEGMENTS = {"one_family", "two_family", "three_family", "multi_family"}
_ES_VAL_FRAC          = 0.15   # fraction of training rows held out for ES search
_ES_ROUNDS            = 50     # stop after this many rounds without improvement


def _make_estimator(params: dict, seed: int, segment: str) -> Any:
    """Return an LGBMRegressor or XGBRegressor depending on the segment."""
    if segment in LGBM_SEGMENTS:
        p = {k: v for k, v in params.items()}
        p["random_state"] = seed
        return LGBMRegressor(
            **p,
            n_jobs=-1,
            objective="regression",
            verbose=-1,
        )
    p = {k: v for k, v in params.items()}
    p["random_state"] = seed
    return XGBRegressor(**p, n_jobs=-1, objective="reg:squarederror", verbosity=0)


def _find_optimal_n_estimators(
    num_feats: list[str],
    cat_feats: list[str],
    params: dict,
    X_tr_sorted: "pd.DataFrame",
    y_tr_sorted: "np.ndarray",
    segment: str,
) -> int:
    """Chronological early-stopping search for the optimal number of trees.

    Two-pass strategy:
      1. Fit a temporary preprocessor on ALL training data.
      2. Hold out the most recent ``_ES_VAL_FRAC`` rows as a validation set.
      3. Run a single-seed estimator (LGBM or XGB) with early stopping.
      4. Return ``best_iteration + 1``.  The caller re-fits the full pipeline
         on ALL training data using this as ``n_estimators``.

    The data must already be sorted chronologically (sale_date ascending).
    """
    num_pipe = Pipeline([("imp", SimpleImputer(strategy="median"))])
    cat_pipe = Pipeline([
        ("imp", SimpleImputer(strategy="most_frequent")),
        ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    parts: list = [("num", num_pipe, num_feats)]
    if cat_feats:
        parts.append(("cat", cat_pipe, cat_feats))
    prep = ColumnTransformer(parts, remainder="drop")
    prep.fit(X_tr_sorted)
    X_t = prep.transform(X_tr_sorted)

    n_val  = max(int(len(X_t) * _ES_VAL_FRAC), 50)
    X_fit, X_val = X_t[:-n_val], X_t[-n_val:]
    y_fit, y_val = y_tr_sorted[:-n_val], y_tr_sorted[-n_val:]

    es_params = {k: v for k, v in params.items() if k != "n_estimators"}

    if segment in LGBM_SEGMENTS:
        import lightgbm as lgb  # local import to keep XGB-only paths fast
        est = LGBMRegressor(
            **es_params,
            n_estimators=params.get("n_estimators", 1500),
            n_jobs=-1,
            objective="regression",
            verbose=-1,
        )
        callbacks = [
            lgb.early_stopping(stopping_rounds=_ES_ROUNDS, verbose=False),
            lgb.log_evaluation(period=-1),
        ]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            est.fit(X_fit, y_fit, eval_set=[(X_val, y_val)], callbacks=callbacks)
        best = int(est.best_iteration_) if est.best_iteration_ > 0 else -1
        if best <= 0:
            # Fallback: use 1/3 of max estimators when early stopping misfires.
            best = max(100, params.get("n_estimators", 1500) // 3)
        return best

    # XGBoost path (non-LGBM segments)
    est_xgb = XGBRegressor(
        **es_params,
        n_estimators=params.get("n_estimators", 1500),
        random_state=42,
        n_jobs=-1,
        objective="reg:squarederror",
        verbosity=0,
        early_stopping_rounds=_ES_ROUNDS,
        eval_metric="mae",
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        est_xgb.fit(X_fit, y_fit, eval_set=[(X_val, y_val)], verbose=False)
    if hasattr(est_xgb, "best_iteration"):
        return int(est_xgb.best_iteration) + 1
    return int(est_xgb.best_ntree_limit)  # type: ignore[attr-defined]


# ─── sklearn pipeline ─────────────────────────────────────────────────────────

def _build_pipeline(num_feats: list[str], cat_feats: list[str],
                    params: dict, segment: str = "") -> Pipeline:
    num_pipe = Pipeline([("imp", SimpleImputer(strategy="median"))])
    cat_pipe = Pipeline([
        ("imp", SimpleImputer(strategy="most_frequent")),
        ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    parts = [("num", num_pipe, num_feats)]
    if cat_feats:
        parts.append(("cat", cat_pipe, cat_feats))
    return Pipeline([
        ("prep", ColumnTransformer(parts, remainder="drop")),
        ("xgb", _make_estimator(params, seed=42, segment=segment)),
    ])


def _build_voting_pipeline(num_feats: list[str], cat_feats: list[str],
                           params: dict, segment: str = "",
                           n_seeds: int = N_ENSEMBLE_SEEDS) -> Pipeline:
    """Wrap N estimators (LGBM or XGB) in a VotingRegressor inside one Pipeline.

    Averaging predictions across seeds reduces variance without changing the
    sklearn .predict() interface, so the model registry and API need no changes.
    """
    estimators = []
    for seed in range(n_seeds):
        estimators.append((
            f"xgb_{seed}",
            _make_estimator(params, seed=seed, segment=segment),
        ))
    voter = VotingRegressor(estimators=estimators)

    num_pipe = Pipeline([("imp", SimpleImputer(strategy="median"))])
    cat_pipe = Pipeline([
        ("imp", SimpleImputer(strategy="most_frequent")),
        ("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])
    parts = [("num", num_pipe, num_feats)]
    if cat_feats:
        parts.append(("cat", cat_pipe, cat_feats))
    return Pipeline([
        ("prep", ColumnTransformer(parts, remainder="drop")),
        ("xgb", voter),
    ])


# ─── Metrics ─────────────────────────────────────────────────────────────────

def _eval(y_true_log: np.ndarray, y_pred_log: np.ndarray) -> dict:
    y_pred_log = np.clip(y_pred_log, 0, 20.7)
    y_true = np.expm1(y_true_log)
    y_pred = np.expm1(y_pred_log)
    ape = np.abs(y_true - y_pred) / np.maximum(y_true, 1.0)
    return {
        "n":          int(len(y_true)),
        "mae":        float(mean_absolute_error(y_true, y_pred)),
        "rmse":       float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2":         float(r2_score(y_true, y_pred)),
        "median_ape": float(np.median(ape)),
        "hit_10pct":  float(np.mean(ape <= 0.10)),
        "hit_25pct":  float(np.mean(ape <= 0.25)),
    }


# ─── Per-segment training ─────────────────────────────────────────────────────

def train_rentals_all(df: pd.DataFrame) -> dict | None:
    """Pool rental_walkup + rental_elevator rows into one shared model.

    Eliminates the starvation problem for elevator rentals (~350 train rows)
    by combining ~4 000 training rows.  An `is_elevator` binary feature (0/1)
    lets the model learn the price premium for elevator buildings.
    """
    segment = "rentals_all"
    cfg = SEGMENT_FEATURES[segment]

    parts_tr, parts_te = [], []
    for sub_seg in ("rental_walkup", "rental_elevator"):
        sub = df[df["segment"] == sub_seg].copy()
        sub = _engineer(sub)  # type: ignore[arg-type]
        sub["is_elevator"] = 1.0 if sub_seg == "rental_elevator" else 0.0
        tr = sub[pd.to_datetime(sub["sale_date"]).dt.date <= TRAIN_END].copy()
        te = sub[pd.to_datetime(sub["sale_date"]).dt.date >= TEST_START].copy()
        for split in (tr, te):
            mask = split["total_units"].notna() & (split["total_units"] > 0)  # type: ignore[union-attr]
            split.loc[mask, "price_per_unit"] = (
                split.loc[mask, "sales_price"] / split.loc[mask, "total_units"]
            )
        parts_tr.append(tr[tr["price_per_unit"].notna()])  # type: ignore[union-attr]
        parts_te.append(te[te["price_per_unit"].notna()])  # type: ignore[union-attr]

    train = pd.concat(parts_tr, ignore_index=True)
    test  = pd.concat(parts_te, ignore_index=True)

    print(f"\n{'='*55}")
    print(f"  RENTALS_ALL (walkup + elevator pooled)")
    print(f"  train={len(train):,}  test={len(test):,}")

    if len(train) < cfg["min_train"] or len(test) < cfg["min_test"]:
        print(f"  SKIPPED — below minimum thresholds")
        return None

    stats = _fit_neighborhood_stats(train, "price_per_unit")
    train = _apply_neighborhood_stats(train, stats, "price_per_unit")
    test  = _apply_neighborhood_stats(test,  stats, "price_per_unit")

    avail_num = [c for c in cfg["numeric"]     if c in train.columns]
    avail_cat = [c for c in cfg["categorical"] if c in train.columns]
    print(f"  Numeric features ({len(avail_num)}): {avail_num}")
    print(f"  Categorical features ({len(avail_cat)}): {avail_cat}")

    X_tr = train[avail_num + avail_cat]
    y_tr = np.log1p(train["price_per_unit"].values)
    X_te = test[avail_num + avail_cat]
    y_te = np.log1p(test["price_per_unit"].values)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipe = _build_voting_pipeline(avail_num, avail_cat, SEGMENT_XGB_PARAMS[segment])
        pipe.fit(X_tr, y_tr)

    tr_m = _eval(y_tr, pipe.predict(X_tr))
    te_m = _eval(y_te, pipe.predict(X_te))

    print(f"\n  Train (n={tr_m['n']:,})  R²={tr_m['r2']:.4f}  "
          f"MAE={tr_m['mae']:,.0f}$/unit  median_ape={tr_m['median_ape']:.3f}")
    print(f"  Test  (n={te_m['n']:,})  R²={te_m['r2']:.4f}  "
          f"MAE={te_m['mae']:,.0f}$/unit  median_ape={te_m['median_ape']:.3f}")
    r2_gap = tr_m["r2"] - te_m["r2"]
    print(f"  Overfit check: R² gap = {r2_gap:+.4f}  "
          f"({'⚠  possible overfit' if r2_gap > 0.15 else '✓ within range'})")

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    model_path = ARTIFACTS / "rentals_all_spine_price_model.pkl"
    joblib.dump(pipe, model_path)

    stats_path = ARTIFACTS / "rentals_all_spine_neighborhood_stats.json"

    def _safe_val(v: Any) -> Any:
        try:
            return None if (v != v or v is None) else float(v)
        except (TypeError, ValueError):
            return None

    stats_out: dict[str, Any] = {}
    for k, v in stats.items():
        if isinstance(v, dict):
            stats_out[k] = {str(kk): _safe_val(vv) for kk, vv in v.items()}
        else:
            stats_out[k] = _safe_val(v)
    with open(stats_path, "w") as fh:
        json.dump(stats_out, fh, indent=2)

    # Feature importance — average across VotingRegressor seeds.
    fi_path_str: str | None = None
    try:
        feature_names = pipe.named_steps["prep"].get_feature_names_out()
        xgb_step = pipe.named_steps["xgb"]
        if hasattr(xgb_step, "estimators_"):
            importance = np.mean(
                [e.feature_importances_ for e in xgb_step.estimators_], axis=0
            )
        else:
            importance = xgb_step.feature_importances_
        fi = pd.DataFrame({"feature": feature_names, "importance": importance})
        fi = fi.sort_values("importance", ascending=False)
        fi_path = ARTIFACTS / "rentals_all_spine_feature_importance.csv"
        fi.to_csv(fi_path, index=False)
        fi_path_str = str(fi_path)
        print(f"\n  Top-5 features:")
        for _, row in fi.head(5).iterrows():
            print(f"    {row['feature']:<45} {row['importance']:.4f}")
    except Exception as e:
        print(f"  [warn] feature importance: {e}")

    return {
        "segment": segment,
        "train_rows": tr_m["n"],
        "test_rows":  te_m["n"],
        "train_r2":   tr_m["r2"],
        "test_r2":    te_m["r2"],
        "test_mae":   te_m["mae"],
        "test_rmse":  float(np.sqrt(mean_squared_error(
            np.expm1(y_te), np.clip(np.expm1(pipe.predict(X_te)), 0, None)
        ))),
        "test_median_ape": te_m["median_ape"],
        "test_hit_10pct":  te_m["hit_10pct"],
        "model_path":      str(model_path),
        "numeric_features": avail_num,
        "categorical_features": avail_cat,
    }


def train_segment(df: pd.DataFrame, segment: str) -> dict | None:
    cfg        = SEGMENT_FEATURES[segment]
    target     = cfg["target"]
    num_feats  = cfg["numeric"]
    cat_feats  = cfg["categorical"]

    # Some segments (two_family, three_family) are sub-slices of a spine segment.
    # "spine_segment" points to the parent segment column value; "building_class_prefix"
    # further filters by the DOF building class code.  This lets us split the old
    # combined multi_family segment without rebuilding the training spine.
    spine_seg = cfg.get("spine_segment", segment)
    sub = df[df["segment"] == spine_seg].copy()
    bc_prefix = cfg.get("building_class_prefix")
    if bc_prefix:
        sub = sub[sub["building_class"].astype(str).str.startswith(bc_prefix)].copy()  # type: ignore[union-attr]

    # Sprint A.1 — opt-in sales hygiene to drop non-arms-length transactions
    # before time split.  Cleaner training set → tighter test variance.
    hygiene = cfg.get("sales_hygiene")
    if hygiene:
        sub = _apply_sales_hygiene(sub, segment, hygiene)  # type: ignore[arg-type]

    sub = _engineer(sub)  # type: ignore[arg-type]

    # Time-based split.
    train = sub[pd.to_datetime(sub["sale_date"]).dt.date <= TRAIN_END].copy()
    test  = sub[pd.to_datetime(sub["sale_date"]).dt.date >= TEST_START].copy()

    print(f"\n{'='*55}")
    print(f"  {segment.upper()}")
    print(f"  train={len(train):,}  test={len(test):,}")

    if len(train) < cfg["min_train"] or len(test) < cfg["min_test"]:
        print(f"  SKIPPED — below minimum thresholds "
              f"(need train≥{cfg['min_train']}, test≥{cfg['min_test']})")
        return None

    # For price_per_unit targets, derive the column before fitting stats.
    if target == "price_per_unit":
        for split in (train, test):
            mask = split["total_units"].notna() & (split["total_units"] > 0)  # type: ignore[union-attr]
            split.loc[mask, "price_per_unit"] = (
                split.loc[mask, "sales_price"] / split.loc[mask, "total_units"]
            )
        train = train[train["price_per_unit"].notna()].copy()  # type: ignore[union-attr]
        test  = test[test["price_per_unit"].notna()].copy()  # type: ignore[union-attr]

    # Rare-neighbourhood collapse (for multi_family and any other RARE_NBHD_SEGMENTS).
    if segment in RARE_NBHD_SEGMENTS:
        train, test = _collapse_rare_neighborhoods(train, test, RARE_N)  # type: ignore[arg-type]

    # Neighbourhood stats fitted on train only.
    stats = _fit_neighborhood_stats(train, target)  # type: ignore[arg-type]
    train = _apply_neighborhood_stats(train, stats, target)  # type: ignore[arg-type]
    test  = _apply_neighborhood_stats(test,  stats, target)  # type: ignore[arg-type]

    # Only keep features actually present in the data.
    avail_num = [c for c in num_feats if c in train.columns]
    avail_cat = [c for c in cat_feats if c in train.columns]
    print(f"  Numeric features ({len(avail_num)}): {avail_num}")
    print(f"  Categorical features ({len(avail_cat)}): {avail_cat}")

    target_col = "price_per_unit" if target == "price_per_unit" else "sales_price"
    if target_col not in train.columns:
        print(f"  SKIPPED — target column '{target_col}' missing")
        return None

    # Sort chronologically so the early-stopping val holdout is the most
    # recent transactions (closest in time to the 2025 test set).
    train = train.sort_values("sale_date").reset_index(drop=True)

    X_tr = train[avail_num + avail_cat]
    y_tr = np.log1p(train[target_col].values)
    X_te = test[avail_num + avail_cat]
    y_te = np.log1p(test[target_col].values)

    # Sprint C/D: pick model params — LGBM for targeted segments, XGB otherwise.
    # Apply early stopping to find the optimal n_estimators, then re-fit on
    # all training data with that fixed value.
    model_params = dict(
        SEGMENT_LGBM_PARAMS[segment]
        if segment in LGBM_SEGMENTS
        else SEGMENT_XGB_PARAMS[segment]
    )
    algo = "LGBM" if segment in LGBM_SEGMENTS else "XGB"
    if segment in EARLY_STOPPING_SEGMENTS:
        optimal_n = _find_optimal_n_estimators(
            avail_num, avail_cat, model_params, X_tr, y_tr, segment=segment,  # type: ignore[arg-type]
        )
        print(f"  Early stopping [{algo}]: optimal n_estimators = {optimal_n} "
              f"(was {model_params.get('n_estimators', '?')})")
        model_params["n_estimators"] = optimal_n

    # Use VotingRegressor ensemble for high-variance segments.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if segment in ENSEMBLE_SEGMENTS:
            pipe = _build_voting_pipeline(avail_num, avail_cat, model_params,
                                          segment=segment)
        else:
            pipe = _build_pipeline(avail_num, avail_cat, model_params,
                                   segment=segment)
        pipe.fit(X_tr, y_tr)

    tr_m = _eval(y_tr, pipe.predict(X_tr))
    te_m = _eval(y_te, pipe.predict(X_te))

    unit = "$/unit" if target == "price_per_unit" else "$"
    print(f"\n  Train (n={tr_m['n']:,})  R²={tr_m['r2']:.4f}  "
          f"MAE={tr_m['mae']:,.0f}{unit}  median_ape={tr_m['median_ape']:.3f}")
    print(f"  Test  (n={te_m['n']:,})  R²={te_m['r2']:.4f}  "
          f"MAE={te_m['mae']:,.0f}{unit}  median_ape={te_m['median_ape']:.3f}")
    r2_gap = tr_m["r2"] - te_m["r2"]
    print(f"  Overfit check: R² gap = {r2_gap:+.4f}  "
          f"({'⚠  possible overfit' if r2_gap > 0.10 else '✓ within range'})")

    # Save model.
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    model_path = ARTIFACTS / f"{segment}_spine_price_model.pkl"
    joblib.dump(pipe, model_path)

    stats_path = ARTIFACTS / f"{segment}_spine_neighborhood_stats.json"

    def _safe_val(v: Any) -> Any:
        """Convert NaN / NA → None so json.dump doesn't choke."""
        try:
            return None if (v != v or v is None) else float(v)  # NaN check
        except (TypeError, ValueError):
            return None

    stats_out: dict[str, Any] = {}
    for k, v in stats.items():
        if isinstance(v, dict):
            stats_out[k] = {str(kk): _safe_val(vv) for kk, vv in v.items()}
        else:
            stats_out[k] = _safe_val(v)
    with open(stats_path, "w") as f:
        json.dump(stats_out, f, indent=2)

    # Feature importance — handle both single XGB and VotingRegressor.
    try:
        feature_names = pipe.named_steps["prep"].get_feature_names_out()
        xgb_step = pipe.named_steps["xgb"]
        if hasattr(xgb_step, "estimators_"):
            # VotingRegressor: average importances across seeds.
            importance = np.mean(
                [e.feature_importances_ for e in xgb_step.estimators_], axis=0
            )
        else:
            importance = xgb_step.feature_importances_
        fi = pd.DataFrame({"feature": feature_names, "importance": importance})
        fi = fi.sort_values("importance", ascending=False)
        fi.to_csv(ARTIFACTS / f"{segment}_spine_feature_importance.csv", index=False)
        print(f"\n  Top-5 features:")
        for _, row in fi.head(5).iterrows():
            print(f"    {row['feature']:<45} {row['importance']:.4f}")
    except Exception as e:
        print(f"  [warn] feature importance: {e}")

    return {
        "segment": segment,
        "train_rows": tr_m["n"],
        "test_rows":  te_m["n"],
        "train_r2":   tr_m["r2"],
        "test_r2":    te_m["r2"],
        "test_mae":   te_m["mae"],
        "test_rmse":  float(np.sqrt(mean_squared_error(
            np.expm1(y_te), np.clip(np.expm1(pipe.predict(X_te)), 0, None)
        ))),
        "test_median_ape": te_m["median_ape"],
        "test_hit_10pct":  te_m["hit_10pct"],
        "model_path":      str(model_path),
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

def main(only_segments: set[str] | None = None) -> None:
    df = load_enriched_spine()

    segments = only_segments or DEFAULT_SEGMENTS
    results  = []

    for seg in sorted(segments):
        if seg == "rentals_all":
            r = train_rentals_all(df)
        elif seg not in SEGMENT_FEATURES:
            print(f"[skip] unknown segment: {seg}")
            continue
        else:
            r = train_segment(df, seg)
        if r:
            results.append(r)

    if not results:
        print("\nNo segments were trained.")
        return

    print(f"\n{'='*55}")
    print("  SPINE MODEL SUMMARY")
    print(f"{'='*55}")
    fmt = f"  {{:<18}} {{:>8}} {{:>8}} {{:>10}} {{:>12}}"
    print(fmt.format("segment", "train_n", "test_n", "test_R²", "median_ape"))
    print("  " + "-"*53)
    for r in sorted(results, key=lambda x: -x["test_r2"]):
        print(fmt.format(
            r["segment"], r["train_rows"], r["test_rows"],
            f"{r['test_r2']:.4f}", f"{r['test_median_ape']:.3f}",
        ))

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with open(METRICS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Metrics saved → {METRICS_FILE}")
    print(f"  Models saved  → {ARTIFACTS}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train Gold-spine valuation models (time-based split)"
    )
    all_choices = sorted(set(list(SEGMENT_FEATURES.keys()) + ["rentals_all"]))
    parser.add_argument(
        "--subtypes", nargs="+",
        choices=all_choices,
        metavar="SEG",
        help=(
            "Train only the listed segments (default: one_family, multi_family, "
            "condo_coop, rentals_all).  Use 'rentals_all' for the pooled rental model."
        ),
    )
    args = parser.parse_args()
    main(only_segments=set(args.subtypes) if args.subtypes else None)
