# PropIntel AI

PropIntel AI is an end-to-end AI engineering platform for real estate investment analysis, combining data pipelines, machine learning models, a scalable backend API, and a React frontend to deliver property valuation, investment scoring, and explainable decision support.

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
![AI](https://img.shields.io/badge/AI-Artificial%20Intelligence-purple)

---

## Tech Highlights

- Full-stack platform: React 19 frontend + FastAPI backend, live and integrated
- Modular AI system architecture with clean layer separation
- Production-style FastAPI backend with Pydantic v2 validation
- PostgreSQL data layer via Supabase
- Real NYC government data ingestion pipeline (Rolling Sales + PLUTO, BBL join)
- End-to-end ML pipeline: ingestion → feature engineering → training → inference
- XGBoost regression with log-transformed target for residential property valuation
- ModelRegistry pattern: metadata-driven, segment-routable, lazy-loading model serving
- 5 trained subtype models: one_family, multi_family, condo_coop, rental_walkup, rental_elevator
- Full building-class routing to dedicated segment models
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

All Priority 1 bugs resolved. ML model routing complete. Frontend live and integrated. Full production hardening applied (authentication, rate limiting, CORS, error handling, structured logging). Paid tier feature implemented end-to-end. 186 total automated tests (74 backend, 112 frontend).

**Current milestone:**
- Full-stack platform live: React 19 frontend talking to FastAPI backend
- **Supabase Auth** integrated: register / login, JWT sessions, `GET`/`PATCH /auth/me` profiles, per-user saved properties; optional **admin** via `profiles.role` and/or `ADMIN_USER_IDS` in server env (full portfolio visibility for admins)
- **Paid tier feature** complete: `user` / `paid` / `admin` roles enforced on LLM quota; `GET /auth/quota` endpoint; quota pill on Analyze page; Paid badge in Navbar; tier card + quota bar + Stripe placeholder on Profile page
- Real NYC Rolling Sales + PLUTO ingestion pipeline implemented
- Residential-only feature engineering pipeline implemented
- XGBoost pricing model trained on real NYC residential sales data
- 5 subtype models trained and fully routed via ModelRegistry:
  - `one_family` — R²=0.736 ✅ production grade
  - `multi_family` — R²=0.747 ✅ production grade
  - `condo_coop` — R²=0.801 (parent BBL fix + condo unit transactions + `numfloors` / `lot_coverage`)
  - `rental_walkup` — R²=0.594 MVP (walkup class 07, **price/unit**; density + subway features)
  - `rental_elevator` — R²=0.592 MVP (elevator class 08, **price/unit**)
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
    ┌──────────────────────────────┐
    │  PredictionService           │
    │  ModelRegistry               │
    │  Explainer (OpenAI LLM)      │
    └──────────────────────────────┘
                      │
              ┌───────┴────────┐
              ▼                ▼
        SQLAlchemy ORM    ML Inference
              │                │
              ▼                ▼
      PostgreSQL DB     Subtype Models
        (Supabase)      (XGBoost PKLs)
              │
              ▼
         Data Pipelines
              │
              ▼
       Feature Engineering
              │
              ▼
      Model Training Pipeline
```

---

## Data & ML Pipeline

```
NYC Rolling Sales (5 borough Excel files)
                    +
NYC PLUTO (CSV)
                    │
                    ▼
          Data Ingestion Pipeline
      (`ml/pipelines/data_ingestion.py`)
                    │
                    ▼
          BBL-based dataset merge
                    │
                    ▼
         Processed training dataset
  (`ml/data/processed/nyc_training_data.csv`)
                    │
                    ▼
        Training Data Preparation
    (`ml/pipelines/create_training_data.py`)
    (`ml/pipelines/create_subtype_training_data.py`)
                    │
                    ▼
         Feature Engineering Pipeline
     (`ml/features/feature_engineering.py`)
                    │
                    ▼
     Residential-only feature dataset
      (`ml/data/features/nyc_features.csv`)
                    │
                    ▼
       Global + Subtype Training Pipelines
    (`ml/models/train_model.py`)
    (`ml/models/train_subtype_models.py`)
                    │
                    ▼
      XGBoost models serialized to artifacts
  (`ml/artifacts/price_model.pkl`)
  (`ml/artifacts/subtype_models/*.pkl`)
                    │
                    ▼
      Feature importance / explainability
  (`ml/artifacts/feature_importance.csv`)
                    │
                    ▼
    ModelRegistry routes requests to segment models
                    │
                    ▼
         v2 FastAPI prediction endpoints
                    │
                    ▼
        Structured analysis responses
       with LLM explanation narrative
```

---

## 📊 Data Sources

PropIntel uses real NYC government datasets:

### NYC Rolling Sales Data
- Historical property sales records for all 5 boroughs
- Includes sale price, building size, building class, and property type

### NYC PLUTO Dataset
- Property-level geographic and structural data
- Includes zoning, building class, lot size, and geographic coordinates

### Join Strategy
- Datasets merged using **BBL (Borough-Block-Lot)** as the property key

---

## 🔀 Model Registry & Subtype Routing

PropIntel uses a `ModelRegistry` to route each prediction request to the most appropriate trained model based on building class.

### Routing table

| Building Class | Model Key | Artifact |
|---|---|---|
| `01 ONE FAMILY DWELLINGS` | `one_family` | `one_family_price_model.pkl` |
| `02 TWO FAMILY DWELLINGS`, `03 THREE FAMILY DWELLINGS` | `multi_family` | `multi_family_price_model.pkl` |
| `09`–`17` COOPS / CONDOS | `condo_coop` | `condo_coop_price_model.pkl` |
| `07 RENTALS - WALKUP APARTMENTS` | `rental_walkup` | `rental_walkup_price_model.pkl` |
| `08 RENTALS - ELEVATOR APARTMENTS` | `rental_elevator` | `rental_elevator_price_model.pkl` |
| All others | `global` | `price_model.pkl` |

### Model metadata
Each model has a JSON metadata file in `ml/artifacts/metadata/` that defines:
- `name`, `version`, `segment`
- `artifact_path` — path to the serialized `.pkl`
- `feature_columns` — exact columns the model expects
- `metrics` — MAE, RMSE, R² from training evaluation

### Warning system
The `warnings` field in `ProductionPredictionResponse` is populated based on model key:
- `rental_walkup` / `rental_elevator` → warning served if `total_units` is missing (falls back to global model)
- `global` → fallback model warning

---

## 📈 Model Performance

### Subtype model results

| Model | Segment | R² | MAE | RMSE | RMSE/MAE | Target | Ver |
|---|---|---|---|---|---|---|---|
| `condo_coop` | Condos & co-ops | **0.801** | $289k | $493k | 1.70 | sales_price | v4 |
| `one_family` | One family dwellings | **0.736** | **$140k** | **$203k** | 1.45 | sales_price | v2 |
| `multi_family` | Two & three family | **0.747** | **$205k** | **$321k** | 1.56 | sales_price | v4 |
| `rental_elevator` | Elevator rental buildings (08) | **0.592** | $78k/unit | $150k/unit | 1.92 | price_per_unit | v2 |
| `rental_walkup` | Walkup rental buildings (07) | **0.594** | $107k/unit | $170k/unit | 1.59 | price_per_unit | v4 |
| `global` | All residential fallback | **0.610** | $350k | $842k | 2.40 | sales_price | v1 |

Rental models predict **price per unit** ($/unit) and multiply by `total_units` at inference to recover the full building sale price. MAE/RMSE are therefore in $/unit, not $.

**v4 improvements (Phase 3 — feature engineering):**
- `condo_coop` **R² 0.55 → 0.801** (biggest single-session jump): root cause was a BBL mismatch — NYC condo unit lots (1001+) were not matching PLUTO's building lots (0001). Fixed by deriving the parent lot before the join, unlocking 4,599 individual condo elevator transaction records that were previously dropped. Training dataset grew from 12k → 18k rows. Added `numfloors` (floor count = prestige signal) and `lot_coverage` (FAR proxy = density signal) from PLUTO. Higher MAE/RMSE reflects the expanded price range now including condos up to $7.5M (vs co-op-only $4.5M cap before).
- `rental_walkup` **v4** R² 0.58 → 0.594: deduplicated 56 genuinely new class 07 rows from rolling sales (P5–P95 ppu filter + PLUTO inner join) appended to the housing_data base; further augmentation limited by the fact that `housing_data` was already built from the same rolling sales source. Reaching 0.65+ requires multi-year rolling sales or external data beyond public NYC sources.
- `multi_family` **v4** R² 0.641 → **0.747** (+16.5%): three-year dataset (2022 + 2023 + current, 26,931 rows vs 8,266), direct PLUTO BBL join adds `assess_per_unit`, `bldg_footprint` (front×depth), `numfloors`, `builtfar`, `lotdepth`. Per-borough×class P97 price caps preserve Manhattan transactions (260 rows vs 106). Hyperparameters: n_estimators=800, lr=0.04, max_depth=6. MAE $214k→$205k (−4%).

**v2/v3 improvements (Phase 2 + outlier hardening):**
- `one_family` + `multi_family`: per-class 97th-pct price cap + price/sqft P2–P98 anomaly filter — MAE reduced by 43% / 31%, RMSE by 67% / 49%.
- `condo_coop` (v3): per-class 95th-pct cap + `assess_per_unit` (PLUTO BBL join) added as building quality proxy.
- Rental models: `stabilization_ratio` (DHCR rent-stabilized units / total_units) added as a regulatory cash-flow signal.

### Explainability
Each subtype model is trained on its own feature set. Top features vary by segment:

| Model | Key features |
|---|---|
| `global` | `gross_sqft`, `land_sqft`, `year_built`, `property_age`, `latitude`, `longitude`, `borough`, `building_class`, `neighborhood` |
| `one_family` | same as global + `neighborhood_median_price` |
| `multi_family` | same as global + `neighborhood_median_price`, `neighborhood_median_ppsf`, `assess_per_unit`, `bldg_footprint`, `numfloors`, `builtfar`, `lotdepth` |
| `condo_coop` | `assess_per_unit`, `numfloors`, `lot_coverage`, `neighborhood_median_price`, `year_built`, `property_age`, `latitude`, `longitude`, `borough`, `building_class`, `neighborhood` |
| `rental_walkup` | same as one_family + `total_units`, `residential_units`, `sqft_per_unit`, `numfloors`, `units_per_floor`, `lot_coverage`, `subway_dist_km`, `stabilization_ratio` |
| `rental_elevator` | same as rental_walkup minus density/subway features (separate model, stronger regularization for smaller dataset) |

Feature importance CSVs for each segment are saved to `ml/artifacts/` after training and are loaded at inference time to drive the LLM explanation.

---

## 📊 Feature Engineering

The feature engineering pipeline transforms the merged NYC dataset into a model-ready residential valuation dataset.

**Core modeling features (current model contract):**

| Feature | Type | Description |
|---|---|---|
| `gross_sqft` | numeric | Gross building square footage |
| `land_sqft` | numeric | Land square footage |
| `year_built` | numeric | Year the property was built |
| `property_age` | numeric | Derived: `current_year - year_built` |
| `latitude` | numeric | Property latitude |
| `longitude` | numeric | Property longitude |
| `borough` | categorical | NYC borough |
| `building_class` | categorical | NYC building class label |
| `neighborhood` | categorical | NYC neighborhood name |

> Note: `condo_coop` model does not use `gross_sqft` / `land_sqft` (not recorded for NYC co-op share sales). Instead it uses `assess_per_unit` (PLUTO tax assessment ÷ units), `numfloors` (building height), and `lot_coverage` (FAR proxy) from PLUTO via BBL join — covering 98%+ of rows. `rental_walkup` adds `numfloors`, `units_per_floor`, `lot_coverage` (PLUTO spatial join) and `subway_dist_km` (MTA haversine BallTree) alongside `stabilization_ratio` (DHCR). The ModelRegistry handles per-model feature columns automatically.

---

## 🔬 v2 Prediction Request Schema

The primary v2 endpoints use the following standardized request schema:

### `POST /predict-price-v2`

```json
{
  "borough": "Brooklyn",
  "neighborhood": "Park Slope",
  "building_class": "01 ONE FAMILY DWELLINGS",
  "year_built": 1925,
  "gross_sqft": 1800,
  "land_sqft": 2000,
  "latitude": 40.6720,
  "longitude": -73.9778
}
```

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
Client Request (v2 schema)
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
    Build input DataFrame from
    metadata.feature_columns
          │
    model.predict(X) → log-scale
          │
    expm1(prediction) → dollar value
          │
    Warnings generated by model_key
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
| `POST` | `/predict-price-v2` | Property valuation with model metadata |
| `POST` | `/analyze-property-v2` | Full investment analysis with LLM explanation |
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
    "price_low": 980000.0,
    "price_high": 1390000.0,
    "valuation_interval_note": "Typical error band from training MAE (not a formal confidence interval)."
  },
  "investment_analysis": {
    "roi_estimate": -5.2,
    "investment_score": 38,
    "deal_label": "Avoid",
    "recommendation": "Approach cautiously and negotiate closer to model-estimated value.",
    "confidence": "medium",
    "analysis_summary": "Property may be overpriced by approximately $65,000 based on model analysis."
  },
  "drivers": {
    "top_drivers": [
      "Neighborhood demand strongly influences pricing",
      "Building size significantly impacts property value",
      "Location (borough) plays a key role in valuation"
    ],
    "global_context": [
      "Model is trained on NYC residential sales data",
      "Location, size, and building characteristics influence estimated value"
    ],
    "explanation_factors": [
      {
        "factor": "predicted_price",
        "value": 1185000.0,
        "reason": "Derived from trained ML model using property features"
      },
      {
        "factor": "market_price",
        "value": 1250000.0,
        "reason": "User-provided listing price"
      }
    ]
  },
  "explanation": {
    "summary": "The property appears slightly overpriced relative to model-estimated value.",
    "opportunity": "If acquired below asking price, the valuation gap may create a better entry point.",
    "risks": "Current asking price reduces margin for upside and weakens near-term return potential.",
    "recommendation": "Avoid",
    "confidence": "medium"
  },
  "metadata": {
    "model_version": "v1"
  }
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
│   └── .env                         # VITE_API_BASE_URL, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY; optional VITE_API_KEY for non-session API calls
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
│       │   ├── prediction.py        # All prediction request/response schemas
│       │   └── property.py          # Property + auth schemas (UserProfileResponse, QuotaResponse, …)
│       ├── services/
│       │   ├── model_registry.py    # Metadata-driven model loader + routing
│       │   ├── predictor.py         # PredictionService: predict + analyze
│       │   ├── explainer.py         # OpenAI LLM explanation + per-role quota enforcement
│       │   └── mapbox_usage.py      # Mapbox daily counter + org-wide monthly cap check
│       ├── scripts/
│       │   └── load_data.py         # Bulk load housing CSV into PostgreSQL
│       └── main.py                  # FastAPI app entry point
│
├── backend/migrations/              # SQL for Supabase (profiles, user_id on properties, RLS notes)
│
├── ml/
│   ├── artifacts/
│   │   ├── price_model.pkl          # Global XGBoost model
│   │   ├── catboost_model.joblib    # CatBoost experiment artifact
│   │   ├── feature_importance.csv   # Persisted global feature importances
│   │   ├── metadata/
│   │   │   ├── global_model.json
│   │   │   ├── one_family_model.json
│   │   │   ├── multi_family_model.json
│   │   │   ├── condo_coop_model.json
│   │   │   ├── rental_walkup_model.json
│   │   │   └── rental_elevator_model.json
│   │   └── subtype_models/
│   │       ├── one_family_price_model.pkl
│   │       ├── multi_family_price_model.pkl
│   │       ├── condo_coop_price_model.pkl
│   │       ├── rental_walkup_price_model.pkl
│   │       ├── rental_elevator_price_model.pkl
│   │       └── subtype_model_metrics.csv
│   ├── data/
│   │   ├── nyc_raw/                 # NYC Rolling Sales Excel files (git-ignored)
│   │   ├── pluto_raw/               # PLUTO CSV (git-ignored)
│   │   ├── processed/               # Merged + cleaned datasets (git-ignored)
│   │   └── features/                # Engineered feature datasets (git-ignored)
│   ├── features/
│   │   └── feature_engineering.py
│   ├── inference/
│   │   └── predict.py               # Legacy inference + feature importance loader
│   ├── models/
│   │   ├── train_model.py           # Global XGBoost training pipeline
│   │   ├── train_subtype_models.py  # Subtype XGBoost training pipeline
│   │   └── train_catboost_model.py  # CatBoost experiment
│   └── pipelines/
│       ├── data_ingestion.py        # NYC Rolling Sales + PLUTO ingestion
│       ├── create_training_data.py  # Clean + filter training data from DB
│       ├── create_subtype_training_data.py
│       └── profile_housing_data.py  # Dataset profiling utility
│
├── tests/
│   ├── conftest.py
│   ├── test_prediction_api.py       # Prediction v1/v2, feature importance; overrides get_current_user
│   ├── test_property_api.py         # Property CRUD, housing lookup, filters; UserContext mocks
│   ├── test_llm_guardrails.py       # LLM schema validation, per-user quota, admin/api_key exemption
│   ├── test_admin_api.py            # Admin overview, role PATCH, role enrichment logic
│   ├── test_quota_api.py            # GET /auth/quota — all role/usage combinations
│   ├── test_auth_me_api.py          # GET/PATCH /auth/me — profile creation, backfill, admin promo
│   └── test_geocode_usage_api.py    # Mapbox usage recording + monthly cap 429
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
| `schemas/` | Pydantic v2 request/response validation — includes `QuotaResponse`, `UserProfileResponse` |
| `services/` | ML prediction, investment scoring, LLM explanation (with role-based quota), Mapbox usage + cap |
| `ml/artifacts/` | Serialized model PKLs, metadata JSONs, feature importance |
| `ml/data/` | Dataset ingestion and processing |
| `ml/features/` | Feature engineering logic |
| `ml/inference/` | Legacy prediction utilities and feature importance loader |
| `ml/models/` | Model training pipelines |
| `ml/pipelines/` | End-to-end ML pipeline orchestration |

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

# Optional: comma-separated Supabase user UUIDs treated as app admins (full portfolio + role in /auth/me)
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

Optional: `VITE_API_KEY` — same value as backend `API_KEY` — only needed for calling the API **without** a logged-in session (e.g. local scripts). The logged-in app uses the Supabase **Bearer** token for all protected routes.

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

### Patterns used
- `monkeypatch` for mocking legacy inference functions
- `app.dependency_overrides` for mocking `PredictionService` and `get_current_user` (returns a stub `UserContext`)
- Targeted `dependency_overrides.pop()` to isolate service mocks across tests
- SQLite test database for full test isolation
- Validation error tests for coordinate and year bounds
- Auth exercised via dependency overrides; API key path still available for integration tests outside pytest overrides
- Vitest + React Testing Library for all frontend tests
- `vi.mock()` + `vi.hoisted()` for module mocking without initialization order issues
- Mapbox `PropertyLocationMap` mocked in Analyze tests to prevent WebGL errors in jsdom

### CI Pipeline

GitHub Actions runs `pytest` automatically on:
- push to `main`
- pull requests targeting `main`

Workflow: `.github/workflows/tests.yml`

The CI pipeline:
1. Checks out the repo
2. Sets up Python 3.11
3. Installs dependencies
4. Initializes the SQLite test database
5. Runs `pytest` with `DATABASE_URL=sqlite:///./test.db`

---

## 🐳 Docker & Docker Compose

### Build the API image

```bash
docker build -t propintel-api .
```

### Run with Supabase (cloud PostgreSQL)

```bash
docker run --rm -p 8000:8000 --env-file .env.docker propintel-api
```

### Run with Docker Compose (local PostgreSQL)

```bash
docker compose up --build
```

Stop:

```bash
docker compose down
```

### Environment files

| File | Purpose |
|---|---|
| `.env` | Local development |
| `.env.docker` | Docker with Supabase (git-ignored) |
| `.env.docker.example` | Template for `.env.docker` |
| `.env.example` | Template for `.env` |

---

## ⚡ Performance Optimizations

### Model caching
Models are lazy-loaded on first request and cached in memory by the `ModelRegistry`. Subsequent requests for the same model key return the cached pipeline with zero disk I/O.

### Feature importance caching
`load_feature_importance()` and `get_top_global_features()` in `ml/inference/predict.py` are decorated with `@lru_cache(maxsize=None)`. The feature importance CSV is read from disk once per server process and cached for all subsequent analysis requests.

---

## ✅ Current Progress

### Frontend
- React 19 + Vite 8 + TailwindCSS 4 + React Router 7
- Live and integrated with FastAPI backend
- **Supabase Auth** — `Login` / `Register`, `ProtectedRoute` for Analyze, Portfolio, and Profile
- **Home page** — hero section with feature highlights
- **Analyze page** — property form, Mapbox address autocomplete, v2 analysis, MAE-based valuation band (`price_low` / `price_high`), color-coded deal label badge, "Save to Portfolio"; quota pill shows remaining AI analyses with color-coded urgency states; quota-exceeded card with upgrade CTA replaces explanation panels when limit hit
- **Portfolio page** — saved analyses with deal labels, valuation range, sort and filter controls
- **Profile page** — tier card (Free / Paid / Admin), visual quota usage bar, Stripe upgrade placeholder for free users, display name and marketing preferences (`PATCH /auth/me`)
- **Navbar** — theme toggle, account menu, **Admin** badge when `profile.role === 'admin'`; **Paid** badge when `profile.role === 'paid'`
- **AuthContext** — `quota` state and `refreshQuota` hook globally available; auto-refreshed on session change and after each analysis

### Backend and Database
- FastAPI backend with modular architecture
- Supabase PostgreSQL integration
- SQLAlchemy ORM with `Property` and `HousingData` models
- Full property CRUD:
  - `POST /properties/`
  - `GET /properties/` (filtering + pagination)
  - `GET /properties/{property_id}`
  - `PATCH /properties/{property_id}`
  - `DELETE /properties/{property_id}`
- Pydantic v2 validation on all create and update schemas
- Swagger API documentation auto-generated

### Service Layer
- `ModelRegistry` — metadata-driven model loader with segment routing
- `PredictionService` — prediction + investment analysis orchestration
- `Explainer` — OpenAI gpt-5.4-mini LLM narrative generation
- Per-model-key warning system for low-confidence predictions

### Machine Learning
- NYC Rolling Sales ingestion pipeline (5 boroughs)
- PLUTO dataset ingestion pipeline
- BBL-based dataset merge
- Feature engineering pipeline
- Residential-only dataset filtering
- Log-transformed target training (`log1p` / `expm1`)
- Global XGBoost residential valuation model
- 5 trained subtype XGBoost models (v2–v4 — outlier-hardened / enriched where noted):
  - `one_family` (R²=0.736, MAE=$140k) — per-class price cap + price/sqft filter (v2)
  - `multi_family` (R²=0.747, MAE=$205k) — per-borough×class caps + PLUTO building dimensions (v4)
  - `condo_coop` (R²=0.801, MAE=$289k) — parent BBL fix, condo unit transactions, numfloors + lot_coverage (v4)
  - `rental_walkup` (R²=0.594, MAE=$107k/unit) — density features + subway proximity (v4)
  - `rental_elevator` (R²=0.592, MAE=$78k/unit) — stabilization_ratio (v2)
- Full building-class routing via `ModelRegistry.get_model_key()`
- Feature importance artifact persisted and cached at runtime
- All 6 models registered with version metadata JSONs
- ML inference endpoints:
  - `POST /predict-price-v2` (primary)
  - `POST /analyze-property-v2` (primary)
  - `GET /model/feature-importance`
  - Legacy routes maintained for compatibility
- Grouped investment analysis response schema
- Deterministic investment scoring (ROI + valuation gap + risk penalty)
- Deterministic `deal_label` classification
- LLM-based investment narrative generation

### Engineering and Reliability
- **Authentication** — `Authorization: Bearer` (Supabase JWT) or `X-API-Key` on protected routes; shared `get_current_user` dependency
- **Per-IP rate limiting** — 10–60 req/min per endpoint via slowapi
- **CORS hardening** — allowed origins from `CORS_ORIGINS` env var, explicit methods and headers
- **Unified error envelope** — `{ error, status_code, message, detail }` for all error types (401, 422, 429, 500)
- **JSON structured logging** — every request logged with method, path, status, duration, IP, and request UUID
- **Request ID tracing** — `X-Request-ID` header returned on every response for log correlation
- **Liveness + readiness endpoints** — `/health` (instant) and `/ready` (DB connectivity check)
- **186 automated tests** (74 backend + 112 frontend) — property CRUD, housing lookup, prediction v1/v2, LLM guardrails, admin role management, auth/me profile lifecycle, quota API, AuthContext, Analyze page quota UI, Register, Portfolio, AdminDashboard
- GitHub Actions CI workflow passing on push/PR to `main`
- Test isolation: SQLite `test.db`, `DATABASE_URL` set before app import
- Dockerfile for containerized API deployment
- Docker Compose with `env_file` for full environment variable passthrough
- Secure environment variable management via `.env` files

---

## ⚠️ Model Limitations

Current constraints of the valuation models:

- Trained only on **NYC residential properties** — not applicable to commercial
 - `condo_coop` (R²=0.801) is the strongest subtype model after the parent BBL fix unlocked individual condo unit transactions
 - `rental_walkup` (R²=0.594) and `rental_elevator` (R²=0.592) predict **price per unit** and require `total_units` — falls back to the global model when not provided
- All models are trained on the filtered (non-luxury) price range; very-high-end properties (above 95th–97th pct per class) should use the global model or be interpreted as directional estimates
- No temporal features — does not capture market cycles or seasonality
- No macroeconomic indicators
- Sensitive to data quality in source NYC datasets

### Future improvements
- Add time-series features for market trend awareness
- Add macroeconomic indicators
- Expand SHAP per-property explainability
- Batch prediction endpoint for portfolio analysis
- Optional admin tools (e.g. impersonation / “view as user”) with audit logging
