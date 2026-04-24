# PropIntel AI

PropIntel AI is an end-to-end AI engineering platform for real estate investment analysis, combining a Bronze → Silver → Gold medallion data pipeline, machine learning models, a scalable backend API, and a React frontend to deliver property valuation, investment scoring, and explainable decision support.

![App Preview](docs/PropIntel_Preview.png)

### Core Stack
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![Supabase](https://img.shields.io/badge/Supabase-Backend-3ECF8E)
![React](https://img.shields.io/badge/React-19-61DAFB)
![Vite](https://img.shields.io/badge/Vite-8-646CFF)

### Data / AI Stack
![Data Engineering](https://img.shields.io/badge/Data-Engineering-darkblue)
![Machine Learning](https://img.shields.io/badge/Machine-Learning-orange)
![XGBoost](https://img.shields.io/badge/XGBoost-Model-red)
![Optuna](https://img.shields.io/badge/Optuna-HPO-blue)
![AI](https://img.shields.io/badge/AI-Artificial%20Intelligence-purple)

---

## Tech Highlights

- Full-stack platform: React 19 frontend + FastAPI backend, live and integrated
- Modular AI system architecture with clean layer separation
- Production-style FastAPI backend with Pydantic v2 validation
- PostgreSQL data layer via Supabase
- **Medallion data pipeline**: Bronze (raw) → Silver (normalised) → Gold (as-of feature views)
- **As-of / leakage contract**: every training row uses only data available before `sale_date - 1 day`
- **Time-based evaluation**: rolling-origin cross-validation (no random splits)
- Real NYC government data: Rolling Sales, PLUTO, DOF Assessment, ACRIS, J-51 Exemption
- End-to-end ML pipeline: ingestion → Silver normalisation → Gold feature build → training → inference
- XGBoost regression with log-transformed target for residential property valuation
- **Optuna hyperparameter search** on the strict time split per segment
- ModelRegistry pattern: metadata-driven, segment-routable, lazy-loading model serving
- 5 trained spine v3 models: one_family, multi_family, condo_coop, rental_walkup, rental_elevator
- Full building-class routing to dedicated segment models
- **Optional BBL + as_of_date on inference** — DOF / ACRIS / J-51 / PLUTO features loaded from Silver + Gold parquets at request time (same as-of rules as training)
- BallTree haversine subway-distance feature (MTA stations) at training and inference
- Feature importance / explainability artifact persisted after training
- Global explainability endpoint: `GET /model/feature-importance`
- `@lru_cache` on feature importance for zero disk I/O after first request
- Structured production analysis response schema with 5 grouped sections
- Deterministic investment scoring with ROI + valuation gap + risk penalty
- Deterministic `deal_label` classification: `Buy`, `Hold`, `Avoid`
- LLM-generated investment narrative via OpenAI gpt-5.4-mini (Responses API)
- Per-model-key warning system for low-confidence predictions
- **Unified authentication** on API routes: Supabase **JWT** (`Authorization: Bearer`) or legacy **`X-API-Key`** (timing-safe comparison) — same `get_current_user` dependency for prediction, properties, and auth
- **Role-based access tiers**: `user` (free, 10 AI analyses/day), `paid` (200/day), `admin` (unlimited) — enforced at the LLM service layer and surfaced via `GET /auth/quota`
- **Mapbox server-side monthly cap** — `POST /geocode/usage` returns 429 when org-wide monthly usage hits `MAPBOX_MONTHLY_FREE_REQUEST_CAP`
- Per-IP rate limiting with consistent JSON error envelope (slowapi)
- CORS locked to explicit allowed origins, methods, and headers via environment variable
- Unified error response envelope `{ error, status_code, message, detail }` for all error types
- JSON structured logging with per-request UUID tracing and `X-Request-ID` response header
- `/health` (liveness) and `/ready` (DB connectivity readiness) endpoints
- **74 backend + 112 frontend automated tests** — pytest, monkeypatch, `app.dependency_overrides`; Vitest + React Testing Library
- GitHub Actions CI pipeline running tests on push and PR to `main`
- Docker + Docker Compose for containerized local and cloud deployment

---

## Project Status

🟢 **Active — Production-Hardened Full-Stack AI Platform**

All Priority 1 bugs resolved. ML model routing complete. Frontend live and integrated. Full production hardening applied (authentication, rate limiting, CORS, error handling, structured logging). 186 total automated tests (74 backend, 112 frontend).

**Current milestone:**
- Full-stack platform live: React 19 frontend talking to FastAPI backend
- **Supabase Auth** integrated: register / login, JWT sessions, `GET`/`PATCH /auth/me` profiles, per-user saved properties; optional **admin** via `profiles.role` and/or `ADMIN_USER_IDS` in server env (full portfolio visibility for admins)
- **Paid tier feature** complete: `user` / `paid` / `admin` roles enforced on LLM quota; `GET /auth/quota` endpoint; quota pill on Analyze page; Paid badge in Navbar; tier card + quota bar + Stripe placeholder on Profile page
- **Medallion data pipeline** implemented: Bronze → Silver normalizers (DOF, ACRIS, J-51, PLUTO) → Gold as-of feature builders → spine-based training
- **Spine v3 models** trained on Gold features with strict time-based splits; Optuna HPO on 3 underperforming segments — all metrics are honest forward-time R² values
- **BBL inference enrichment**: optional `bbl` + `as_of_date` on `POST /predict-price-v2` and `POST /analyze-property-v2` triggers on-the-fly Silver/PLUTO feature loading at request time, closing the train/inference feature gap
- ModelRegistry + PredictionService + Explainer service layer fully implemented
- Feature importance persisted as ML artifact and cached at runtime
- LLM explanation layer live with structured JSON output
- All prediction endpoints operational with v2 production contract
- Property CRUD fully implemented and validated — `analysis` JSONB column stores full analysis result per property
- Portfolio page redesigned: save analysis from Analyze page, view cards with score, valuations, deal label, and expandable AI explanation
- CI pipeline passing on GitHub Actions

---

## ✅ Primary API Contract (v2)

The **official product-facing contract is the v2 API layer**.

### Recommended endpoints
These are the endpoints intended for frontend integration, product demos, and ongoing feature expansion:

```text
POST /predict-price-v2
POST /analyze-property-v2
GET  /model/feature-importance
```

### Legacy compatibility endpoints
These routes remain available for backward compatibility:

```text
POST /predict-price
POST /analyze-property
POST /predict
POST /analyze
```

New frontend work should target **v2 only**. Legacy routes are not the primary contract.

---

## 🧠 System Architecture

```text
        React Frontend (Vite + TailwindCSS)
                      │
         Supabase Auth (email/password, JWT)
                      │
                      ▼
              FastAPI REST API
                      │
                      ▼
           Request Validation Layer
              (Pydantic v2 Schemas)
                      │
                      ▼
               API Routing Layer
              (FastAPI Endpoints)
                      │
                      ▼
              Service Layer
    ┌──────────────────────────────────────┐
    │  PredictionService                   │
    │  BblFeatureBuilder (as-of lookup)    │
    │  ModelRegistry                       │
    │  Explainer (OpenAI LLM)             │
    └──────────────────────────────────────┘
                      │
              ┌───────┴────────┐
              ▼                ▼
        SQLAlchemy ORM    ML Inference
              │                │
              ▼                ▼
      PostgreSQL DB     Spine v3 Models
        (Supabase)      (XGBoost PKLs)
                               │
                               ▼
                     Silver / Gold Parquets
                     (DOF · ACRIS · J-51 · PLUTO)
```

---

## 🏅 Medallion Data Pipeline

```
Raw datasets (Bronze)
  NYC Rolling Sales (5-borough Excel, current + historical 2022–2024)
  NYC PLUTO (CSV, ~858k rows)
  DOF Property Valuation & Assessment (CSV)
  ACRIS Real Property (master + legals + parties CSVs)
  J-51 Exemption & Abatement Historical (CSV, ~4.2M rows)
  NYC Subway Stations (CSV, 496 stations)
            │
            ▼
  Silver normalizers  (ml/pipelines/silver_*.py)
  silver_dof_assessment.parquet
  silver_acris_transactions.parquet  +  silver_acris_parties.parquet
  silver_j51.parquet
            │
            ▼
  Spine builder  (ml/pipelines/spine_builder.py)
  training_spine_v1.parquet
  ─ canonical sales rows with sale_date + as_of_date (sale_date − 1 day)
  ─ BBL normalised · segment label · duplicates removed
            │
            ▼
  Gold as-of feature builders  (ml/pipelines/gold_*_asof.py)
  gold_dof_assessment_asof.parquet   — DOF roll features strictly before as_of_date
  gold_acris_features_asof.parquet   — deed / mortgage history strictly before as_of_date
  gold_j51_features_asof.parquet     — J-51 exemption status strictly before as_of_date
  gold_pluto_features.parquet        — geo / physical features (BBL-only, no date filter)
            │
            ▼
  Training  (ml/models/train_spine_models.py)
  Per-segment XGBoost pipeline (sklearn ColumnTransformer → XGBRegressor)
  Time-based split: train ≤ 2024-12-31, test ≥ 2025-01-31 (30-day gap)
            │
            ▼
  Optuna HPO  (ml/models/tune_spine_models.py)
  60 trials per underperforming segment on the same time split
            │
            ▼
  Spine v3 artifacts  (ml/artifacts/spine_models/)
  *_spine_price_model.pkl · *_spine_neighborhood_stats.json · *_spine_feature_importance.csv
```

---

## 📊 Data Sources

PropIntel uses real NYC government datasets:

| Dataset | Source | Coverage |
|---|---|---|
| NYC Rolling Sales | DOF (5 borough Excel files, current + 2022–2024 historical) | Sales transactions with price, size, building class |
| NYC PLUTO | DCP (CSV, ~858k parcels) | Lat/lon, numfloors, FAR, lot/building dimensions |
| DOF Property Valuation & Assessment | NYC Open Data | Annual tax roll — market + assessed values, year built, units |
| ACRIS Real Property | NYC Open Data (master + legals + parties) | Deed transfers, mortgages with document amounts and dates |
| J-51 Exemption & Abatement | NYC Open Data (historical, tax years ≤ 2018) | Per-BBL abatement amounts, expiry years, active flag |
| NYC Subway Stations | MTA (GTFS, 496 stations) | Lat/lon for nearest-station distance (BallTree haversine) |

### Join strategy
All datasets are joined on **BBL (Borough-Block-Lot)** — the canonical NYC property key. As-of filters prevent future data from leaking into any training row.

---

## 🔀 Model Registry & Subtype Routing

PropIntel uses a `ModelRegistry` to route each prediction request to the most appropriate trained model based on building class.

### Routing table

| Building Class | Model Key | Artifact |
|---|---|---|
| `01 ONE FAMILY DWELLINGS` | `one_family` | `one_family_spine_price_model.pkl` |
| `02 TWO FAMILY DWELLINGS`, `03 THREE FAMILY DWELLINGS` | `multi_family` | `multi_family_spine_price_model.pkl` |
| `09`–`17` COOPS / CONDOS | `condo_coop` | `condo_coop_spine_price_model.pkl` |
| `07 RENTALS - WALKUP APARTMENTS` | `rental_walkup` | `rental_walkup_spine_price_model.pkl` |
| `08 RENTALS - ELEVATOR APARTMENTS` | `rental_elevator` | `rental_elevator_spine_price_model.pkl` |
| All others | `global` | `price_model.pkl` |

### Model metadata
Each model has a JSON metadata file in `ml/artifacts/metadata/` that defines:
- `name`, `version`, `segment`
- `artifact_path` — path to the serialized `.pkl`
- `stats_path` — neighborhood stats JSON (loaded at inference for median lookups)
- `numeric_features` + `categorical_features` — exact spine v3 feature lists
- `metrics` — MAE, RMSE, R², median_ape from time-based test evaluation

### Warning system
The `warnings` field in `ProductionPredictionResponse` is populated based on model key:
- `rental_walkup` / `rental_elevator` → warning served if `total_units` is missing (falls back to global model)
- `global` → fallback model warning
- `bbl` provided without `as_of_date` (or vice versa) → warning that BBL enrichment was skipped

---

## 📈 Model Performance

### Spine v3 model results (time-based split, train ≤ 2024 / test ≥ 2025)

| Segment | Test R² | Test MAE | Test Median APE | Target | Tuned | Notes |
|---|---|---|---|---|---|---|
| `one_family` | **0.765** | $238k | 17.2% | sales_price | No | Protected — not retrained |
| `condo_coop` | **0.700** | $413k | 20.7% | sales_price | ✅ Optuna | +0.067 R² vs pre-tuning |
| `multi_family` | **0.608** | $348k | 21.0% | sales_price | No | Optuna degraded; hand-tuned retained |
| `rental_walkup` | **0.628** | $108k/unit | 24.3% | price_per_unit | ✅ Optuna | +0.135 R² vs pre-tuning |
| `rental_elevator` | **0.537** | $94k/unit | 28.6% | price_per_unit | ✅ Optuna | +0.077 R² (crossed 0.50) |

> All metrics are from a **strict time-based holdout** — no random splits. Train rows come from sales up to 2024-12-31; test rows from sales on or after 2025-01-31 (30-day reporting-lag gap). This is a more conservative and honest evaluation than the legacy random-split R² values previously reported.

Rental models predict **price per unit** ($/unit) and multiply by `total_units` at inference to recover the full building sale price.

### Feature set (all spine v3 segments)

| Group | Features |
|---|---|
| Neighbourhood stats | `neighborhood_median_price`, `dof_assess_per_unit` |
| Derived | `property_age`, `borough_name` |
| DOF roll | `dof_curmkttot`, `dof_curacttot`, `dof_curactland`, `dof_assess_per_unit`, `dof_gross_sqft`, `dof_bld_story`, `dof_units`, `dof_yrbuilt`, `dof_bldg_class`, `dof_tax_class` |
| ACRIS | `acris_prior_sale_cnt`, `acris_last_deed_amt`, `acris_days_since_last_deed`, `acris_mortgage_cnt`, `acris_last_mtge_amt` |
| J-51 | `j51_active_flag`, `j51_last_abate_amt`, `j51_total_abatement` |
| PLUTO geo | `pluto_latitude`, `pluto_longitude`, `subway_dist_km`, `pluto_numfloors`, `pluto_builtfar`, `pluto_bldg_footprint`, `pluto_bldgarea`, `pluto_lotarea`, `pluto_bldgclass` |
| Rental only | `total_units`, `residential_units` |

### Explainability
Feature importance CSVs for each segment are saved to `ml/artifacts/spine_models/` after training and are loaded at inference time to drive the LLM explanation.

---

## 🔬 v2 Prediction Request Schema

The primary v2 endpoints use the following standardized request schema:

### `POST /predict-price-v2`

```json
{
  "borough": "Brooklyn",
  "neighborhood": "Park Slope",
  "building_class": "02 TWO FAMILY DWELLINGS",
  "year_built": 1925,
  "gross_sqft": 1800,
  "land_sqft": 2000,
  "latitude": 40.6720,
  "longitude": -73.9778,
  "bbl": "3012340056",
  "as_of_date": "2025-06-15"
}
```

`bbl` and `as_of_date` are **optional**. When both are provided, the API loads DOF / ACRIS / J-51 / PLUTO features from local Silver + Gold parquets using the same as-of rules as training — closing the train/inference feature gap. Without them, the pipeline median-imputes those columns.

### `POST /analyze-property-v2`

Same as above plus:

```json
{
  "market_price": 1250000.0
}
```

---

## 🧠 ML Inference Architecture

```text
Client Request (v2 schema: borough, neighborhood, building_class,
                year_built, gross_sqft, lat, lon [, bbl, as_of_date])
          │
    FastAPI Endpoint
          │
   Pydantic Validation
          │
   PredictionService.predict()
          │
    ModelRegistry.get_model_key(building_class)
          │
    ┌─────┴──────────────────────────┐
    │  Route to segment model:       │
    │  one_family / multi_family /   │
    │  condo_coop / rental / global  │
    └─────┬──────────────────────────┘
          │
    ModelRegistry.load_model(key)
    (lazy-loaded, cached in memory)
          │
    _build_spine_row()
    ├─ neighborhood_median_price + dof_assess_per_unit
    │  (from training-time neighborhood stats JSON)
    ├─ subway_dist_km (BallTree haversine, MTA stations)
    ├─ Optional: bbl + as_of_date → BblFeatureBuilder
    │  ├─ DOF roll (Silver) — latest roll ≤ as_of_date
    │  ├─ ACRIS (Silver) — deed + mortgage aggs < as_of_date
    │  ├─ J-51 (Silver) — exemption status < as_of_date
    │  └─ PLUTO (Gold) — geo / physical by BBL
    └─ Remaining columns → pipeline median imputation
          │
    model.predict(X) → log-scale
          │
    expm1(prediction) → dollar value
    (× total_units for price_per_unit models)
          │
    Valuation interval (±1× training MAE)
          │
    Warnings + bbl_feature_status in input_summary
          │
    Return ProductionPredictionResponse
```

For analysis requests, `PredictionService.analyze()` additionally:
1. Computes valuation gap and ROI estimate
2. Scores the investment (0–100) using ROI + valuation gap + risk penalty
3. Classifies deal label: `Buy`, `Hold`, or `Avoid`
4. Loads top feature drivers (cached via `@lru_cache`)
5. Calls OpenAI gpt-5.4-mini for LLM narrative explanation
6. Returns grouped `ProductionAnalyzeResponse`

---

## 🌐 API Endpoints

### Health & Readiness
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness check — confirms process is alive |
| `GET` | `/ready` | Readiness check — confirms DB is reachable |

### Auth (JWT or API key)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/auth/me` | Current user profile (creates `profiles` row on first call) |
| `PATCH` | `/auth/me` | Update display name and marketing preferences |
| `GET` | `/auth/quota` | Daily LLM quota status — role, limit, used today, remaining, reset date |

Send `Authorization: Bearer <supabase_access_token>` from the React app after login, or `X-API-Key` for scripts and OpenAPI testing.

### Geocode usage
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/geocode/usage` | Record one Mapbox forward-geocode request. Returns 429 when org-wide monthly cap is exceeded |

### Properties
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/properties/` | Create a property listing |
| `GET` | `/properties/` | List properties with filtering and pagination |
| `GET` | `/properties/{id}` | Retrieve a specific property |
| `PATCH` | `/properties/{id}` | Partially update a property |
| `DELETE` | `/properties/{id}` | Delete a property |
| `GET` | `/housing/lookup` | Nearest `housing_data` match by lat/lng (optional borough filter) — used by Analyze autocomplete |

**Filtering and pagination:**
```
GET /properties?limit=10
GET /properties?zipcode=10001
GET /properties?min_price=500000&max_price=900000
```

### Prediction & Analysis (v2 — Primary)
All prediction routes require the same auth as above (**Bearer JWT** or **`X-API-Key`**).

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/predict-price-v2` | Property valuation with model metadata; optional `bbl`+`as_of_date` for roll-aligned features |
| `POST` | `/analyze-property-v2` | Full investment analysis with LLM explanation; optional `bbl`+`as_of_date` |
| `GET` | `/model/feature-importance` | Top global feature importances |

### Admin (admin JWT or API key)
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/admin/overview` | Aggregate counts: profiles, properties, LLM usage, Mapbox usage |
| `PATCH` | `/admin/users/{user_id}/role` | Set a user's role (`user`, `paid`, `admin`) |

### Legacy Routes (compatibility only)
| Method | Endpoint |
|---|---|
| `POST` | `/predict-price` |
| `POST` | `/analyze-property` |
| `POST` | `/predict` |
| `POST` | `/analyze` |

---

## Example `POST /analyze-property-v2` Response

```json
{
  "valuation": {
    "predicted_price": 1185000.0,
    "market_price": 1250000.0,
    "price_difference": -65000.0,
    "price_difference_pct": -5.2,
    "price_low": 946525.0,
    "price_high": 1423475.0,
    "valuation_interval_note": "Approximate range ±1× the model's training MAE for this segment (not a formal confidence interval)."
  },
  "investment_analysis": {
    "roi_estimate": -5.2,
    "investment_score": 38,
    "deal_label": "Avoid",
    "recommendation": "Approach cautiously and negotiate closer to model-estimated value.",
    "confidence": "Medium",
    "analysis_summary": "Property may be overpriced by approximately $65,000 based on model analysis."
  },
  "drivers": {
    "top_drivers": [
      "Neighborhood price level is a strong driver of property value",
      "City-assessed value per unit reflects building quality and income potential",
      "Geographic positioning influences estimated price"
    ],
    "global_context": [
      "Model is trained on NYC residential sales data",
      "Location, size, and building characteristics influence estimated value"
    ],
    "explanation_factors": [
      { "factor": "predicted_price", "value": 1185000.0, "reason": "Derived from trained ML model using property features" },
      { "factor": "market_price",    "value": 1250000.0, "reason": "User-provided listing price" }
    ]
  },
  "explanation": {
    "summary": "The property appears slightly overpriced relative to model-estimated value.",
    "opportunity": "If acquired below asking price, the valuation gap may create a better entry point.",
    "risks": "Current asking price reduces margin for upside and weakens near-term return potential.",
    "recommendation": "Avoid",
    "confidence": "Medium"
  },
  "metadata": { "model_version": "v3" }
}
```

---

## 📁 Project Structure

```
propintel-ai/
│
├── frontend/                        # React 19 + Vite + TailwindCSS 4
│   ├── src/                         # pages, components, context (Auth), services, lib/supabase.js
│   ├── public/
│   ├── package.json
│   └── .env                         # VITE_API_BASE_URL, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
│
├── backend/
│   └── app/
│       ├── api/
│       │   ├── prediction.py        # All prediction/analysis endpoints (JWT or API key)
│       │   ├── properties.py        # Property CRUD + housing lookup
│       │   ├── auth_router.py       # GET/PATCH /auth/me, GET /auth/quota
│       │   ├── admin.py             # GET /admin/overview, PATCH /admin/users/{id}/role
│       │   └── geocode_usage.py     # POST /geocode/usage (Mapbox request counter + cap gate)
│       ├── core/
│       │   ├── config.py            # Path configuration
│       │   ├── auth.py              # JWT (Supabase HS256/RS256) + API key → UserContext
│       │   ├── limiter.py           # slowapi rate limiter instance
│       │   └── error_handlers.py    # Unified error response handlers
│       ├── db/
│       │   ├── database.py          # SQLAlchemy engine + session
│       │   ├── init_db.py           # Table creation script
│       │   └── models.py            # ORM models (Property, Profile, LLMUsage, MapboxUsage, HousingData)
│       ├── schemas/
│       │   ├── prediction.py        # All prediction request/response schemas (incl. optional bbl, as_of_date)
│       │   └── property.py          # Property + auth schemas (UserProfileResponse, QuotaResponse, …)
│       ├── services/
│       │   ├── model_registry.py    # Metadata-driven model loader + routing (spine v3 aware)
│       │   ├── predictor.py         # PredictionService: spine feature row builder + predict + analyze
│       │   ├── bbl_feature_builder.py # On-the-fly as-of Silver/PLUTO feature lookup by BBL
│       │   ├── explainer.py         # OpenAI LLM explanation + per-role quota enforcement
│       │   └── mapbox_usage.py      # Mapbox daily counter + org-wide monthly cap check
│       ├── scripts/
│       │   └── load_data.py         # Bulk load housing CSV into PostgreSQL
│       └── main.py                  # FastAPI app entry point
│
├── backend/migrations/              # Supabase SQL: auth, mapbox, RLS (003–005), promote admin
│
├── ml/
│   ├── artifacts/
│   │   ├── price_model.pkl          # Global XGBoost model (legacy fallback)
│   │   ├── feature_importance.csv   # Global feature importances (legacy)
│   │   ├── metadata/                # ← COMMITTED — controls which model the API serves
│   │   │   ├── global_model.json
│   │   │   ├── one_family_model.json      # v3 — points to spine_models/
│   │   │   ├── multi_family_model.json    # v3 — points to spine_models/
│   │   │   ├── condo_coop_model.json      # v3 — points to spine_models/
│   │   │   ├── rental_walkup_model.json   # v3 — points to spine_models/
│   │   │   └── rental_elevator_model.json # v3 — points to spine_models/
│   │   └── spine_models/            # ← git-ignored (regenerate with train_spine_models.py)
│   │       ├── *_spine_price_model.pkl
│   │       ├── *_spine_neighborhood_stats.json
│   │       ├── *_spine_feature_importance.csv
│   │       └── spine_model_metrics.json
│   ├── data/
│   │   ├── nyc_raw/                 # NYC Rolling Sales Excel files — git-ignored
│   │   │   └── historical/          # 2022–2024 annualized sales
│   │   ├── pluto_raw/               # PLUTO CSV — git-ignored
│   │   ├── external/                # Raw external datasets — git-ignored
│   │   │   ├── dof_property_valuation_assessment/
│   │   │   ├── acris/ (master/ legals/ parties/)
│   │   │   ├── j51_exemption_abatement_historical/
│   │   │   └── nyc_subway_stations.csv
│   │   ├── silver/                  # Normalised parquets — git-ignored
│   │   │   ├── dof_assessment/silver_dof_assessment.parquet
│   │   │   ├── acris/silver_acris_transactions.parquet + silver_acris_parties.parquet
│   │   │   └── j51/silver_j51.parquet
│   │   ├── gold/                    # Feature-view parquets — git-ignored
│   │   │   ├── training_spine_v1.parquet
│   │   │   ├── gold_dof_assessment_asof.parquet
│   │   │   ├── gold_acris_features_asof.parquet
│   │   │   ├── gold_j51_features_asof.parquet
│   │   │   └── gold_pluto_features.parquet
│   │   ├── processed/               # Legacy merged datasets — git-ignored
│   │   └── features/                # Legacy engineered datasets — git-ignored
│   ├── features/
│   │   └── feature_engineering.py   # Legacy feature engineering
│   ├── inference/
│   │   └── predict.py               # Legacy inference + feature importance loader
│   ├── models/
│   │   ├── train_model.py           # Legacy global XGBoost training
│   │   ├── train_subtype_models.py  # Legacy subtype training
│   │   ├── train_spine_models.py    # Spine v3: Gold features + time-based split (DO NOT touch one_family artifacts)
│   │   ├── tune_spine_models.py     # Optuna HPO for multi_family/condo_coop/rental_* (one_family excluded)
│   │   └── train_catboost_model.py  # CatBoost experiment
│   └── pipelines/
│       ├── spine_builder.py             # Canonical spine: normalised BBL + as_of_date + segment
│       ├── eval_protocol.py             # Rolling-origin evaluation protocol (time-based folds)
│       ├── silver_dof_assessment.py     # Silver normalizer: DOF assessment CSV → parquet
│       ├── silver_acris.py              # Silver normalizer: ACRIS master+legals+parties → parquet
│       ├── silver_j51.py                # Silver normalizer: J-51 historical CSV → parquet
│       ├── gold_dof_assessment_asof.py  # Gold builder: as-of DOF features
│       ├── gold_acris_features_asof.py  # Gold builder: as-of ACRIS deed/mortgage features
│       ├── gold_j51_features_asof.py    # Gold builder: as-of J-51 exemption features
│       ├── gold_pluto_features.py       # Gold builder: PLUTO geo/physical + subway_dist_km
│       ├── download_j51_historical.py   # Download J-51 dataset from NYC Open Data
│       ├── download_rolling_sales_2024.py # Download 2024 annualized rolling sales
│       ├── data_ingestion.py            # Legacy: NYC Rolling Sales + PLUTO ingestion
│       ├── create_training_data.py      # Legacy training data pipeline
│       ├── create_subtype_training_data.py
│       └── profile_housing_data.py
│
├── tests/
│   ├── conftest.py
│   ├── test_prediction_api.py
│   ├── test_property_api.py
│   ├── test_llm_guardrails.py
│   ├── test_admin_api.py
│   ├── test_quota_api.py
│   ├── test_auth_me_api.py
│   └── test_geocode_usage_api.py
│
├── .github/
│   └── workflows/
│       └── tests.yml                # CI: pytest on push/PR to main
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .env.docker.example
└── README.md
```

### Module responsibilities

| Folder | Purpose |
|---|---|
| `frontend/` | React 19 UI — Home, Analyze (quota pill, save to Portfolio), Portfolio, Profile (tier + quota bar), Admin Dashboard |
| `api/` | FastAPI route handlers — prediction, properties, auth (`/me`, `/quota`), admin, geocode usage |
| `core/` | JWT + API-key auth (`auth.py`), rate limiting, error handlers, path config |
| `db/` | Database engine, session, and ORM models (`Profile`, `LLMUsage`, `MapboxUsage`, …) |
| `schemas/` | Pydantic v2 request/response validation — includes optional `bbl`, `as_of_date` on prediction requests |
| `services/` | ML prediction, investment scoring, BBL as-of feature lookup, LLM explanation (with role-based quota), Mapbox usage + cap |
| `ml/artifacts/metadata/` | Committed metadata JSONs — controls which PKL file the API loads per segment |
| `ml/data/silver/` | Normalised Silver parquets (DOF, ACRIS, J-51) — git-ignored, regenerated from pipelines |
| `ml/data/gold/` | As-of Gold feature parquets + training spine — git-ignored, regenerated from pipelines |
| `ml/models/` | Model training + Optuna tuning pipelines |
| `ml/pipelines/` | Silver normalizers, Gold builders, spine builder, eval protocol, download scripts |

---

## ⚙️ Environment Setup

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file at the project root (see also `.env.example`):

```
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE
OPENAI_API_KEY=sk-...
API_KEY=your-secret-api-key-here
CORS_ORIGINS=http://localhost:5174,http://127.0.0.1:5174
LLM_TEMPERATURE=0.3

# Supabase Auth — backend verifies access tokens (RS256 via JWKS or HS256 via secret)
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase-dashboard

# Optional: comma-separated Supabase user UUIDs treated as app admins
ADMIN_USER_IDS=00000000-0000-0000-0000-000000000000

# LLM daily quota limits per role (defaults: free=10, paid=200)
LLM_QUOTA_FREE=10
LLM_QUOTA_PAID=200

# Mapbox monthly org-wide geocoding cap (default: 100000)
MAPBOX_MONTHLY_FREE_REQUEST_CAP=100000
```

### Frontend

```bash
cd frontend
npm install
```

Create a `frontend/.env` file:

```
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_SUPABASE_URL=https://YOUR_PROJECT.supabase.co
VITE_SUPABASE_ANON_KEY=your-supabase-anon-key
```

---

## ▶️ Running the App

### Backend

```bash
uvicorn backend.app.main:app --reload
```

Available at:
- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Liveness: `http://127.0.0.1:8000/health`
- Readiness (DB check): `http://127.0.0.1:8000/ready`

### Frontend

```bash
cd frontend
npm run dev
```

Available at `http://localhost:5174`

### Initialize the database

```bash
python -m backend.app.db.init_db
```

### Rebuild the ML pipeline from scratch

```bash
# 1. Silver normalizers
python ml/pipelines/silver_dof_assessment.py
python ml/pipelines/silver_acris.py
python ml/pipelines/silver_j51.py

# 2. Spine + Gold features
python ml/pipelines/spine_builder.py
python ml/pipelines/gold_dof_assessment_asof.py
python ml/pipelines/gold_acris_features_asof.py
python ml/pipelines/gold_j51_features_asof.py
python ml/pipelines/gold_pluto_features.py

# 3. Train (one_family excluded from tuning — use train_spine_models.py for it)
python ml/models/train_spine_models.py --subtypes one_family
python ml/models/tune_spine_models.py --trials 60

# 4. Evaluate
python ml/pipelines/eval_protocol.py
```

---

## 🗄️ Database Integration

### Connection

`backend/app/db/database.py` manages:
- SQLAlchemy engine with `pool_pre_ping=True` and `pool_recycle=300`
- Session factory with `autocommit=False`, `autoflush=False`
- `get_db()` dependency injected into all route handlers via `Depends()`

### Models

| Table | Model | Description |
|---|---|---|
| `profiles` | `Profile` | One row per Supabase user: `id` (UUID), `email`, `display_name`, `role` (`user` / `paid` / `admin`), `marketing_opt_in` |
| `properties` | `Property` | Saved property analyses — `user_id` links to owner; `analysis` JSONB stores the full `POST /analyze-property-v2` response |
| `llm_usage` | `LLMUsage` | Per-user daily LLM call counter — enforces `LLM_QUOTA_FREE` / `LLM_QUOTA_PAID` limits |
| `mapbox_usage` | `MapboxUsage` | Per-user daily Mapbox geocode request counter — reported by the frontend, shown in admin dashboard |
| `housing_data` | `HousingData` | NYC training data loaded from CSV pipeline |

---

## 🔍 Testing

Automated tests live in `tests/`.

```bash
pytest
```

### Backend test coverage

| Test file | Tests | Coverage |
|---|---|---|
| `test_property_api.py` | 15 | CRUD, filters, housing lookup, `UserContext` mocks |
| `test_prediction_api.py` | 9 | All prediction/analysis endpoints, model routing, validation, mock service |
| `test_llm_guardrails.py` | 22 | Schema validation, per-user quota, quota fallback, admin/api_key exemption |
| `test_admin_api.py` | 9 | Admin overview, role PATCH (promote/demote/invalid/403/404), role enrichment |
| `test_quota_api.py` | 7 | GET /auth/quota — free/paid/admin/api_key roles, usage states, 401 |
| `test_auth_me_api.py` | 11 | GET/PATCH /auth/me — auto-creation, display-name backfill, admin promo, 400/401 |
| `test_geocode_usage_api.py` | 1 | Mapbox usage recording + monthly cap 429 |

**Total backend: 74 tests** (`pytest` from repo root)

### Frontend test coverage

| Test file | Tests | Coverage |
|---|---|---|
| `adminApi.test.js` | 4 | Auth header, 403 FORBIDDEN code, error detail, fallback message |
| `geocodeUsageApi.test.js` | 4 | POST method, 204 resolve, 429 throw, JSON body |
| `AuthContext.test.jsx` | 8 | Loading, profile/quota fetch, no-session skip, sign-out clears both |
| `Analyze.test.jsx` | 10 | Quota pill states (null/unlimited/remaining/exhausted), quota-exceeded card, form validation |
| `Register.test.jsx` | 6 | Heading, inputs, password mismatch, min-length, success screen, Supabase error |
| `Portfolio.test.jsx` | 4 | Heading, empty state, property card, sort dropdown |
| `AdminDashboard.test.jsx` | 5 | Heading, stat labels, error message, Refresh button |
| Other (Login, Profile, authApiQuota, …) | 71 | Sign-in form, tier card, quota bar, profile service calls |

**Total frontend: 112 tests** (`npm run test` from `frontend/`)

### CI Pipeline

GitHub Actions runs `pytest` automatically on push to `main` and pull requests targeting `main`.

Workflow: `.github/workflows/tests.yml`

---

## 🐳 Docker & Docker Compose

```bash
# Build
docker build -t propintel-api .

# Run with Supabase (cloud PostgreSQL)
docker run --rm -p 8000:8000 --env-file .env.docker propintel-api

# Run with Docker Compose (local PostgreSQL)
docker compose up --build
docker compose down
```

---

## ⚡ Performance Optimizations

- **Model caching** — `ModelRegistry` lazy-loads each segment PKL on first request and holds it in memory; zero disk I/O on subsequent requests for the same key.
- **Feature importance caching** — `@lru_cache` on feature importance loaders; one disk read per server process.
- **Parquet row filters** — `BblFeatureBuilder` pushes BBL equality filters into parquet reads, scanning only matching row groups.
- **BallTree subway distance** — cached at startup via `@lru_cache`; single in-memory haversine query per request.

---

## ⚠️ Model Limitations

- Trained only on **NYC residential properties** — not applicable to commercial.
- `rental_elevator` (R²=0.537) has only ~350 training rows in the time-split era; predictions should be interpreted with the provided valuation band.
- `multi_family` (R²=0.608) remains heterogeneous across price ranges and boroughs; Optuna HPO did not improve it further.
- All metrics are from a **strict time-based holdout** — forward-time generalisation, not in-sample or random-split estimates.
- PLUTO match rate is ~76%; parcels without a PLUTO row get median imputation for physical features.
- No temporal or macroeconomic cycle features.

### Future improvements
- Expand SHAP per-property explainability
- Batch prediction endpoint for portfolio analysis
- Rent-stabilisation (DHCR) feature integration for rental segments
- Additional hyperparameter trials or CatBoost for `multi_family`
- Optional admin tools (impersonation / "view as user") with audit logging
