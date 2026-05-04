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
- **4 trained spine v4 models** with overfitting-gate guardrails: one_family, multi_family, condo_coop, rentals_all (pooled walkup + elevator)
- Full building-class routing to dedicated segment models; `07` and `08` both route to the pooled `rentals_all` model
- **Optional BBL + as_of_date on inference** — Gold parquets (committed for prod/Docker) supply PLUTO/geo and related views; **Silver** parquets (~1.8GB) remain local/git-ignored — without them, DOF/ACRIS/J-51 roll features degrade gracefully (`bbl_feature_status=no_data`) while predictions still run
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
- CORS locked to explicit allowed origins, methods, and headers via **`CORS_ORIGINS`**; startup logs the resolved origin list; preflight allowlist includes **`sentry-trace`** / **`baggage`** (Sentry browser SDK) plus **`Authorization`**, **`X-API-Key`**, **`X-Request-ID`**, **`Accept`**, **`Content-Type`**; **`X-Request-ID`** is exposed to the client via **`Access-Control-Expose-Headers`**
- Unified error response envelope `{ error, status_code, message, detail, request_id }` for HTTP errors
- JSON structured logging with `LOG_LEVEL` env control; optional **Sentry** (`SENTRY_DSN`) with **`before_send` PII scrubbing** (Authorization / API key / cookies; redacted Postgres URLs in exception text), **`SENTRY_ENVIRONMENT`**, optional **`SENTRY_RELEASE`**
- Security response headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`)
- Supabase JWT verification via **HS256 + JWKS (RS256)** with a **cached PyJWKClient**; OpenAPI `/docs` gated by **`DOCS_ENABLED`** (off by default in prod)
- Proxy-aware client IP for rate limits when **`TRUST_PROXY_HEADERS=1`**
- **`/health`** (liveness) and **`/ready`** (Postgres + **ML artifact presence** checks) — both omitted from OpenAPI; **`/ready`** returns sanitized failure messages (full errors logged server-side only)
- SQL migrations runner (`python -m backend.scripts.run_migrations`) — optional auto-run on Docker boot via **`RUN_MIGRATIONS`**
- Docker image respects **`PORT`** (Railway); **`ML_ARTIFACT_ROOT`** overrides artifact paths when using volumes
- **83 backend + 112 frontend automated tests** — pytest; Vitest + React Testing Library
- GitHub Actions CI pipeline running tests on push and PR to `main`
- **`railway.toml`** + `.dockerignore` for lean builds; Docker + Docker Compose for local/container workflows

---

## Project Status

🟢 **Active — Production-Hardened Full-Stack AI Platform**

All Priority 1 bugs resolved. ML model routing complete. Frontend live and integrated. Production hardening includes auth (JWT/JWKS), rate limiting, CORS, unified errors with `request_id`, observability hooks, Docker/Railway-oriented defaults, and interactive Analyze map (Mapbox Standard, draggable pin). **195 total automated tests** (83 backend, 112 frontend).

**Current milestone:**
- Full-stack platform live: React 19 frontend talking to FastAPI backend
- **Supabase Auth** integrated: register / login, JWT sessions, `GET`/`PATCH /auth/me` profiles, per-user saved properties; optional **admin** via `profiles.role` and/or `ADMIN_USER_IDS` in server env (full portfolio visibility for admins)
- **Paid tier feature** complete: `user` / `paid` / `admin` roles enforced on LLM quota; `GET /auth/quota` endpoint; quota pill on Analyze page; Paid badge in Navbar; tier card + quota bar + Stripe placeholder on Profile page (billing integration deferred until LLC / Stripe account)
- **Medallion data pipeline** implemented: Bronze → Silver normalizers (DOF, ACRIS, J-51, PLUTO) → Gold as-of feature builders → spine-based training
- **Spine v5/v6 models** trained on Gold features with strict time-based splits; overfitting-gate guardrails applied — all metrics are honest forward-time R² values. `multi_family` split into dedicated `two_family` (R²=0.677, Sprint A) and `three_family` models. Anti-overfitting measures: 5-seed VotingRegressor, rare-neighbourhood collapse, transit feature pack, k-NN comparable-sales pack, neighbourhood/borough trend pack
- **BBL inference enrichment**: optional `bbl` + `as_of_date` loads features from **Gold** (in repo/Docker) and **Silver** when present locally — full parity when Silver parquets exist; otherwise enriched PLUTO/geo paths still work with graceful degradation for roll-history columns
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
                     Gold Parquets (deploy) · Silver (optional local)
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
| `07 RENTALS - WALKUP APARTMENTS` | `rentals_all` | `rentals_all_spine_price_model.pkl` |
| `08 RENTALS - ELEVATOR APARTMENTS` | `rentals_all` | `rentals_all_spine_price_model.pkl` |
| All others | `global` | `price_model.pkl` |

Both rental building classes route to the shared `rentals_all` pooled model. An `is_elevator` binary feature (0 = walkup, 1 = elevator) is injected at inference to preserve the signal.

### Model metadata
Each model has a JSON metadata file in `ml/artifacts/metadata/` that defines:
- `name`, `version`, `segment`
- `artifact_path` — path to the serialized `.pkl`
- `stats_path` — neighborhood stats JSON (loaded at inference for median lookups)
- `numeric_features` + `categorical_features` — exact spine v4 feature lists
- `metrics` — MAE, RMSE, R², median_ape, ΔR² gap and worst-fold R² from time-based evaluation

### Warning system
The `warnings` field in `ProductionPredictionResponse` is populated based on model key:
- `rentals_all` → warning served if `total_units` is missing (falls back to global model)
- `global` → fallback model warning
- `bbl` provided without `as_of_date` (or vice versa) → warning that BBL enrichment was skipped

---

## 📈 Model Performance

### Current model scorecard — time-based split (train ≤ 2024-12-31 / test ≥ 2025-01-31)

| Segment | Test R² | Test MAE | Test Median APE | Target | ΔR² gap | Worst-fold R² | Notes |
|---|---|---|---|---|---|---|---|
| `one_family` | **0.768** | $237k | 17.3% | sales_price | 0.111 ✅ | 0.746 ✅ | Protected — not retrained |
| `condo_coop` | **0.637** | $419k | 21.2% | sales_price | 0.043 ✅ | 0.596 ✅ | Most stable model |
| `two_family` | **0.677** | $264k | 16.4% | sales_price | 0.131 ✅ | 0.519 ✅ | v2 (Sprint A): + sales hygiene + comp pack + market trends; +5.6% R², −16% MAE |
| `three_family` | **0.395** | $486k | 23.2% | sales_price | 0.158 ⚠️ | 0.395 ⚠️ | v1: class 03 only; limited by missing rental income data; fold-mean R²=0.470 |
| `rentals_all` | **0.458** | $110k/unit | 25.9% | price_per_unit | 0.140 ✅ | 0.458 ✅ | v5: full transit pack — `subway_cbd_dist_km` ranks #5 in importance |

> All metrics are from a **strict time-based holdout** — no random splits. Train rows: sales up to 2024-12-31. Test rows: sales on or after 2025-01-31 (30-day reporting-lag gap enforced). Gates: ΔR² ≤ 0.15 AND worst-fold R² ≥ 0.40.

> **`two_family` v2 (Sprint A):** Three layered improvements stacked on the v1 split model — (1) sales hygiene filter that drops $1/$10/$50k non-arms-length transfers (~545 rows, 1.8% of class-02 sales); (2) k-NN **comparable-sales pack** (5 features) which finds the 5 nearest 2-family sales within 1km in the prior 365 days and adds median price, $/sqft, search distance, and recency as signals; (3) **market-trend pack** which captures neighbourhood and borough YoY price growth as direction signals. Lift: R² 0.641 → 0.677, MAE $316k → $264k, median APE 20.6% → 16.4%. New features `nbhd_median_l365` (#3) and `comp_median_price` (#4) earn real importance, confirming the model is using local market context as designed.

> **`two_family` vs `multi_family`:** The old combined multi_family segment (0.604 R²) mixed two fundamentally different buyer markets — 2-family owner-occupiers and 3-family investors. Splitting them by building class gives `two_family` a dedicated model with cleaner signal — first to 0.641 (v1), then to 0.677 with Sprint A enrichments — on the 80% of multi-family traffic (30,873 transactions).

> **`three_family`:** 3-family investor pricing is driven by rental income yields not observable in our feature set. The model achieves fold-mean R²=0.470 across historical years but struggled with the 2025 test period where investor market dynamics shifted with higher rates. Wider prediction intervals are expected for this segment.

> **`rentals_all`** replaces the previous separate `rental_walkup` and `rental_elevator` models. Both building classes `07` and `08` route here via the `is_elevator` binary feature. `subway_cbd_dist_km` ranks #5 in importance, confirming outer-borough commute access drives rental building pricing.

Rental models predict **price per unit** ($/unit) and multiply by `total_units` at inference to recover the full building sale price.

### Anti-overfitting measures

| Measure | Segments |
|---|---|
| 5-seed VotingRegressor ensemble | `two_family`, `three_family`, `rentals_all` |
| Rare-neighbourhood collapse (< 30 train rows → `Other_<Borough>`) | `two_family`, `three_family` |
| lat/lon excluded (prevents geographic memorisation in small datasets) | `rentals_all` |
| Transit density counts (`n_500m`, `n_1km`) excluded to avoid lat/lon collinearity | `two_family`, `three_family` |
| Sales hygiene filter (drops nominal/non-arms-length sales below $100k) | `two_family` |
| Curated lean comp pack (5 features) — drops collinear p25/p75 to avoid gap widening | `two_family` |
| Time-based split instead of random 80/20 | All |
| Rolling-origin fold scorecard gates: ΔR² ≤ 0.15, worst-fold R² ≥ 0.40 | All |

### Model routing

| Building Class | Segment | Model |
|---|---|---|
| `01 ONE FAMILY DWELLINGS` | `one_family` | Promoted ✅ |
| `02 TWO FAMILY DWELLINGS` | `two_family` | Promoted ✅ |
| `03 THREE FAMILY DWELLINGS` | `three_family` | Active ⚠️ (wider intervals) |
| `09`, `10`, `12`, `13`, `15`, `17` (Condo/Co-op) | `condo_coop` | Promoted ✅ |
| `07 RENTALS - WALKUP`, `08 RENTALS - ELEVATOR` | `rentals_all` | Promoted ✅ |
| All others | `global` | Fallback |

### Feature set

| Group | Features | Segments |
|---|---|---|
| Neighbourhood stats | `neighborhood_median_price`, `dof_assess_per_unit` | All |
| Derived | `property_age`, `borough_name` | All |
| DOF roll | `dof_curmkttot`, `dof_curacttot`, `dof_curactland`, `dof_gross_sqft`, `dof_bld_story`, `dof_units`, `dof_yrbuilt`, `dof_bldg_class`, `dof_tax_class` | All |
| ACRIS | `acris_prior_sale_cnt`, `acris_last_deed_amt`, `acris_days_since_last_deed`, `acris_mortgage_cnt`, `acris_last_mtge_amt` | All |
| J-51 | `j51_active_flag`, `j51_last_abate_amt`, `j51_total_abatement` | All |
| PLUTO geo | `pluto_latitude`, `pluto_longitude`, `pluto_numfloors`, `pluto_builtfar`, `pluto_bldg_footprint`, `pluto_bldgarea`, `pluto_lotarea`, `pluto_bldgclass` | All except `rentals_all` (no lat/lon) |
| Transit pack | `subway_dist_km`, `subway_k3_mean_dist_km`, `subway_hub_flag`, `subway_cbd_dist_km` | `two_family`, `three_family`, `one_family`, `condo_coop` |
| Transit density | `subway_n_500m`, `subway_n_1km` | `rentals_all` only |
| **Comp pack** (Sprint A) | `comp_count`, `comp_median_price`, `comp_median_ppsqft`, `comp_search_dist_km`, `comp_recency_days` | `two_family` |
| **Market trends** (Sprint A) | `nbhd_median_l365`, `nbhd_yoy_growth`, `borough_yoy_growth` | `two_family` |
| Rental only | `total_units`, `residential_units`, `is_elevator` | `rentals_all` |

> **Sprint A — Comp + trend feature packs.** Two new Gold builders (`gold_comps_features.py`, `gold_market_trends.py`) compute as-of-safe k-NN comparable-sales aggregates and per-neighbourhood/borough rolling-window medians + YoY growth. Comps are matched per `comp_segment` so 2-family comps come from 2-family sales only. Look-back window is 365 days; spatial cap is 5 km; minimum comp price is $100k (mirrors the hygiene filter). At inference time `bbl_feature_builder.py` reads the most recent matching snapshot for the target (BBL, segment) — a yesterday-snapshot proxy for today is acceptable because the underlying signals (recent sales, neighbourhood medians, YoY rates) move slowly. Missing snapshots fall through to NaN; XGBoost imputes via the column's training median so the prediction stays valid.

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
| `GET` | `/health` | Liveness — process is alive (use for load-balancer / Railway **liveness** probes) |
| `GET` | `/ready` | Readiness — Postgres `SELECT 1` + registered ML artifacts on disk; returns **503** with `{ status, failed, checks }` if degraded; error details are **not** echoed to clients (check server logs) |

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
│   ├── .env.example                 # Template — copy to frontend/.env (never commit secrets)
│   └── .env                         # Local only: VITE_* (see Environment Setup)
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
│       └── main.py                  # FastAPI app entry point (lifespan, CORS, middleware)
│
├── backend/scripts/
│       └── run_migrations.py        # Postgres migration runner (schema_migrations)
│
├── backend/migrations/              # Numbered SQL (auth, mapbox, RLS, paid role, …)
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
│   │   └── spine_models/            # ← COMMITTED — segment .pkl + stats + feature CSVs for Docker/prod
│   │       ├── *_spine_price_model.pkl
│   │       ├── *_spine_neighborhood_stats.json
│   │       ├── *_spine_feature_importance.csv
│   │       └── spine_model_metrics.json (and Optuna JSON sidecars where present)
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
│   │   ├── gold/                    # Feature-view parquets — COMMITTED (BBL / PLUTO paths in prod)
│   │   │   ├── training_spine_v1.parquet
│   │   │   ├── gold_dof_assessment_asof.parquet
│   │   │   ├── gold_acris_features_asof.parquet
│   │   │   ├── gold_j51_features_asof.parquet
│   │   │   ├── gold_pluto_features.parquet
│   │   │   ├── gold_comps_features.parquet
│   │   │   └── gold_market_trends.parquet
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
│   ├── test_geocode_usage_api.py
│   ├── test_client_ip.py
│   └── test_mapbox_usage_service.py
│
├── .github/
│   └── workflows/
│       └── tests.yml                # CI: pytest on push/PR to main
│
├── Dockerfile
├── docker-compose.yml
├── railway.toml                     # Railway deploy hints + env checklist (comments)
├── .dockerignore                    # Keeps build context small (excludes Silver/raw/ml training code)
├── requirements.txt
├── .env.example
├── .env.docker.example
└── README.md
```

### Module responsibilities

| Folder | Purpose |
|---|---|
| `frontend/` | React 19 UI — Home, Analyze (quota pill, Mapbox Standard preview map + draggable pin, save to Portfolio), Portfolio, Profile, Admin Dashboard |
| `api/` | FastAPI route handlers — prediction, properties, auth (`/me`, `/quota`), admin, geocode usage |
| `core/` | JWT + API-key auth (`auth.py`), rate limiting, error handlers, path config |
| `db/` | Database engine, session, and ORM models (`Profile`, `LLMUsage`, `MapboxUsage`, …) |
| `schemas/` | Pydantic v2 request/response validation — includes optional `bbl`, `as_of_date` on prediction requests |
| `services/` | ML prediction, investment scoring, BBL as-of feature lookup, LLM explanation (with role-based quota), Mapbox usage + cap |
| `ml/artifacts/metadata/` | Committed metadata JSONs — controls which PKL file the API loads per segment |
| `ml/artifacts/spine_models/` | Committed trained spine artifacts (`.pkl`, stats JSON, feature CSV) — baked into Docker |
| `ml/data/silver/` | Normalised Silver parquets (DOF, ACRIS, J-51) — git-ignored (~1.8GB); regenerate locally for full BBL roll features |
| `ml/data/gold/` | Gold feature parquets + training spine — **committed** for production inference / Docker |
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

Create a `.env` file at the project root. **Start from `.env.example`** — it stays in sync with the codebase.

**Critical:** use the **`postgresql+psycopg://`** SQLAlchemy dialect (matches `psycopg` v3 in `requirements.txt`). A bare `postgresql://` URL makes SQLAlchemy look for `psycopg2`, which is not installed.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Postgres DSN, e.g. `postgresql+psycopg://…` (Supabase pooler URL works) |
| `OPENAI_API_KEY` | LLM explanations |
| `API_KEY` | `X-API-Key` for scripts / OpenAPI when not using JWT |
| `CORS_ORIGINS` | Comma-separated **exact** browser origins (`scheme://host:port`, no trailing slash). Include **both** `http://localhost:5174` and `http://127.0.0.1:5174` if you use either. Add staging/production HTTPS origins when you deploy. Mismatch causes **OPTIONS preflight 400** in the browser |
| `SUPABASE_URL` | Same host as `VITE_SUPABASE_URL` — enables JWKS for asymmetric JWTs |
| `SUPABASE_JWT_SECRET` | HS256 verification (Dashboard → API → JWT Secret) |
| `ADMIN_USER_IDS` | Optional comma-separated UUIDs with admin access before DB profile exists |
| `LLM_QUOTA_*`, `LLM_TEMPERATURE` | Daily explanation quotas per tier |
| `MAPBOX_MONTHLY_FREE_REQUEST_CAP` | Admin dashboard vs in-app geocode counter |
| `DOCS_ENABLED` | Set `1` locally for `/docs` — omit or `0` in production |
| `LOG_LEVEL` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |
| `SENTRY_DSN` | Optional — when set, unhandled exceptions go to Sentry with PII scrubbing |
| `SENTRY_ENVIRONMENT` | e.g. `local`, `staging`, `production` (defaults to `production` if unset) |
| `SENTRY_RELEASE` | Optional — app version / git SHA for release tracking |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.0`–`1.0` (default `0.1`) |
| `TRUST_PROXY_HEADERS` | Set `1` behind a trusted reverse proxy only |
| `ML_ARTIFACT_ROOT` | Optional — override repo root for `.pkl` paths (volumes / custom layout) |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | SQLAlchemy pool tuning |
| `RUN_MIGRATIONS` | Docker: `0` skips `run_migrations` on boot (default runs migrations) |

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env` from `frontend/.env.example`. **Vite bakes `VITE_*` at build time** — set `VITE_API_BASE_URL` to your deployed API origin in CI/hosting before `npm run build`.

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | FastAPI base URL (required — `apiFetch` throws if unset) |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key (public, scoped by RLS) |
| `VITE_MAPBOX_TOKEN` | Public token for geocoding + Analyze map |
| `VITE_MAPBOX_STYLE` | Optional — defaults to Mapbox **Standard** (`mapbox://styles/mapbox/standard`); override e.g. `streets-v12` if needed |
| `VITE_API_KEY` | Optional — must match server `API_KEY` for API-key auth without a session (**never treat as a secret** — it ships in the bundle) |

---

## ▶️ Running the App

### Backend

```bash
uvicorn backend.app.main:app --reload
```

Available at:
- API: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs` — only when **`DOCS_ENABLED=1`** in `.env` (disabled by default)
- Liveness: `http://127.0.0.1:8000/health`
- Readiness (DB + ML artifacts): `http://127.0.0.1:8000/ready` — use for **readiness** probes; expect **200** only when DB and on-disk models are OK

### Frontend

```bash
cd frontend
npm run dev
```

Available at `http://localhost:5174`

### Initialize the database

- **Local SQLite / CI:** `python -m backend.app.db.init_db` creates tables for pytest.
- **Postgres (Supabase / Docker / prod):** apply **`backend/migrations/*.sql`** via `python -m backend.scripts.run_migrations` (same runner the Docker image invokes on boot). Migration **`007_rls_verify_no_public_policies.sql`** is a read-only audit: asserts RLS is enabled on app tables and warns if permissive `anon` / `authenticated` policies would expose rows via PostgREST.

**Staging vs production:** keep separate Supabase projects (or at least separate DB roles + env files). Copy **`.env.example`** — the bottom **env matrix** table lists variables that typically differ per environment (`CORS_ORIGINS`, `VITE_API_BASE_URL`, `SENTRY_*`, `DOCS_ENABLED`, etc.).

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
- SQLAlchemy engine with `pool_pre_ping=True`, `pool_recycle=300`, and tunable **`DB_POOL_SIZE`** / **`DB_MAX_OVERFLOW`**
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
| `test_client_ip.py` | 7 | Proxy-aware client IP for rate limiting |
| `test_mapbox_usage_service.py` | 2 | Atomic Mapbox usage counter behaviour |

**Total backend: 83 tests** (`pytest` from repo root)

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

**Total frontend: 112 tests** (`npm run test` from `frontend/` — production build runs with **sourcemaps disabled** in `vite.config.js`)

### CI Pipeline

GitHub Actions runs `pytest` automatically on push to `main` and pull requests targeting `main`.

Workflow: `.github/workflows/tests.yml`

---

## 🐳 Docker & Docker Compose

Root **`Dockerfile`** copies the repo (respecting **`.dockerignore`**) so Silver/raw/training bulk stays **out** of the image while **`ml/artifacts/spine_models/`** and **`ml/data/gold/`** bake in for inference.

```bash
# Build (example tag)
docker build -t propintel-ai:latest .

# Run against Supabase or any Postgres — use a root .env with DATABASE_URL=postgresql+psycopg://…
# NOTE: .env is excluded from the image via .dockerignore — always pass --env-file
docker run --rm -p 8000:8000 --env-file .env propintel-ai:latest

# Compose path (local Postgres + api) — still supported
docker compose up --build
docker compose down
```

> **`docker` not found?** Docker Desktop must be running. If the CLI is still missing from your shell after launching it, add it to your PATH permanently:
> ```bash
> echo 'export PATH="$PATH:/Applications/Docker.app/Contents/Resources/bin"' >> ~/.zshrc && source ~/.zshrc
> ```

### Migrations on container boot
The image runs `python -m backend.scripts.run_migrations` **before** uvicorn unless **`RUN_MIGRATIONS=0`**. Migrations are Postgres-only and tracked in **`schema_migrations`**. See **`backend/migrations/README.md`**.

### Runtime
- **`PORT`** — injected by Railway (or map host port in `docker run`).
- **`DATABASE_URL`** — must use **`postgresql+psycopg://`** for SQLAlchemy inside the container.

---

## 🚀 Production & deployment (checklist)

Deploy steps vary by host; this is the contract the repo expects:

| Step | Notes |
|---|---|
| **Database** | Supabase Postgres or any Postgres; run migrations via Docker boot or `python -m backend.scripts.run_migrations` |
| **API env** | `DATABASE_URL` (+psycopg dialect), `SUPABASE_*`, `OPENAI_API_KEY`, `API_KEY`, **`CORS_ORIGINS` exactly matching the browser origin** (see `.env.example`), `SENTRY_DSN` + `SENTRY_ENVIRONMENT` in non-local envs |
| **Frontend build** | Set `VITE_API_BASE_URL`, `VITE_SUPABASE_*`, `VITE_MAPBOX_TOKEN` at **build** time |
| **Stripe / billing** | Not wired yet — Profile shows placeholder until LLC + Stripe account |
| **Observability** | Optional `SENTRY_DSN`; structured logs to stdout |
| **Railway** | **`railway.toml`** sets **`healthcheckPath = /health`** (liveness). Use **`/ready`** manually or via an external monitor for DB + ML readiness; Railway’s single built-in check does not replace a full readiness probe |

---


## ⚡ Performance Optimizations

- **Model caching** — `ModelRegistry` lazy-loads each segment PKL on first request and holds it in memory; zero disk I/O on subsequent requests for the same key.
- **Feature importance caching** — `@lru_cache` on feature importance loaders; one disk read per server process.
- **Parquet row filters** — `BblFeatureBuilder` pushes BBL equality filters into parquet reads, scanning only matching row groups.
- **BallTree subway distance** — cached at startup via `@lru_cache`; single in-memory haversine query per request.

---

## ⚠️ Model Limitations

- Trained only on **NYC residential properties** — not applicable to commercial.
- `rentals_all` (R²=0.456) pools walkup and elevator rentals to solve elevator's 350-row starvation. The pooled model passes both overfitting gates (ΔR² = 0.131, worst-fold = 0.456) but rental markets are inherently noisy; predictions should be interpreted with the valuation band.
- `multi_family` (R²=0.608) remains heterogeneous across price ranges and boroughs; variance is reduced by the 5-seed ensemble but the market complexity limits further improvement without more data.
- All metrics are from a **strict time-based holdout** — forward-time generalisation, not in-sample or random-split estimates.
- PLUTO match rate is ~76%; parcels without a PLUTO row get median imputation for physical features.
- No temporal or macroeconomic cycle features.

### Future improvements
- Expand SHAP per-property explainability
- Batch prediction endpoint for portfolio analysis
- Rent-stabilisation (DHCR) feature integration for rental segments
- Additional hyperparameter trials or CatBoost for `multi_family`
- Optional admin tools (impersonation / "view as user") with audit logging
