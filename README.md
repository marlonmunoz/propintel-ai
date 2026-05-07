# PropIntel AI

PropIntel AI is an end-to-end AI engineering platform for NYC residential real estate investment analysis: a medallion-style data pipeline, segment-routed ML models, a production FastAPI backend, and a React frontend for valuation, scoring, explainability, and portfolio workflows.

![App Preview](docs/PropIntel_Preview.png)

### Core stack

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![Supabase](https://img.shields.io/badge/Supabase-Backend-3ECF8E)
![React](https://img.shields.io/badge/React-19-61DAFB)
![Vite](https://img.shields.io/badge/Vite-8-646CFF)

### Data / AI stack

![Data Engineering](https://img.shields.io/badge/Data-Engineering-darkblue)
![Machine Learning](https://img.shields.io/badge/Machine-Learning-orange)
![XGBoost](https://img.shields.io/badge/XGBoost-Model-red)
![Optuna](https://img.shields.io/badge/Optuna-HPO-blue)
![AI](https://img.shields.io/badge/AI-Artificial%20Intelligence-purple)

---

## Contents

- [Highlights](#highlights)
- [Product surface](#product-surface)
- [Contact form & email](#contact-form--email)
- [System architecture](#system-architecture)
- [Medallion data pipeline](#medallion-data-pipeline)
- [API endpoints](#api-endpoints)
- [v2 prediction schema](#v2-prediction-request-schema)
- [Model registry & routing](#model-registry--subtype-routing)
- [Project structure](#project-structure)
- [Environment variables](#environment-setup)
- [Running locally](#running-the-app)
- [Database](#database-integration)
- [Testing & CI](#testing)
- [Docker & Railway](#docker--docker-compose)
- [Production checklist](#production--deployment-checklist)

---

## Highlights

- **Full stack:** React 19 + Vite + Tailwind CSS 4 frontend; FastAPI + Pydantic v2 backend; PostgreSQL via Supabase.
- **Auth:** Supabase Auth (email/password). API accepts **`Authorization: Bearer`** (JWT) or **`X-API-Key`** for scripts — unified `get_current_user` dependency.
- **Roles & LLM quota:** `user` / `paid` / `admin`; daily LLM limits enforced in the explainer; **`GET /auth/quota`** exposes usage.
- **Medallion pipeline:** Bronze → Silver normalisers → Gold as-of features → spine training with **strict time splits** and rolling-origin evaluation.
- **Inference:** `ModelRegistry` routes by building class to spine segment models; optional **`bbl` + `as_of_date`** enriches from committed Gold parquets (Silver optional locally).
- **Analysis:** Deterministic investment score, `deal_label`, OpenAI narrative (quota-aware), Mapbox geocoding with org-wide monthly cap via **`POST /geocode/usage`**.
- **Contact:** Public **`POST /contact`** delivers visitor messages via **Resend** (no Supabase table required); **`/contact`** page + **`SupportLink`** component across legal/error/login flows.
- **Ops:** slowapi rate limits, CORS allowlist + optional **`CORS_ORIGIN_REGEX`** (Vercel previews), unified JSON errors with **`request_id`**, optional Sentry with PII scrubbing, **`/health`** + **`/ready`**, JSON logs, security headers, proxy-aware IP when **`TRUST_PROXY_HEADERS=1`**.
- **Quality:** **93** backend pytest tests + **145** frontend Vitest tests (**238** total); GitHub Actions runs backend pytest, frontend **lint**, tests, and production build.

---

## Product surface

### Public routes

| Path | Purpose |
|------|---------|
| `/` | Marketing home |
| `/login`, `/register`, `/forgot-password`, `/reset-password` | Supabase Auth flows |
| `/terms`, `/privacy`, `/disclaimer` | Legal & valuation disclaimer |
| **`/contact`** | Contact form (support vs partnerships topics) — submits to **`POST /contact`** |

### Protected routes (valid Supabase session)

| Path | Purpose |
|------|---------|
| `/analyze` | Property analysis (Mapbox map, quota pill, save to portfolio) |
| `/portfolio` | Saved analyses |
| `/profile` | Account, tier/quota, preferences |
| `/admin` | Admin dashboard (admin JWT or API key) |

### Support email UX

- **`SupportLink`** (`frontend/src/components/SupportLink.jsx`) centralises **`support@propintel-ai.com`** mailto links with optional subject/body — used in Footer-adjacent legal pages, error boundary, email verification banner, login (locked account), and profile (account deletion).
- **`/contact`** replaces mailto-only CTAs with a **form** so visitors without a desktop mail client can still reach you; routing is server-side by topic (see below).

---

## Contact form & email

### Behaviour

1. The browser **`POST`**s JSON to **`{VITE_API_BASE_URL}/contact`** (no auth).
2. FastAPI validates payload, applies **rate limiting** (**5 submissions / hour / IP**), and calls the **Resend** REST API.
3. Messages are delivered to Google Workspace inboxes:
   - **`topic: "support"`** → **`support@propintel-ai.com`**
   - **`topic: "partnerships"`** → **`marlon@propintel-ai.com`**
4. **`reply_to`** is set to the visitor’s email so **Reply** in Gmail goes directly to them.
5. **`CONTACT_FROM_EMAIL`** controls the visible **From** header (e.g. `PropIntel AI <noreply@propintel-ai.com>`); the address must be allowed in Resend for your verified domain.

### Backend env (Railway / local)

| Variable | Required | Purpose |
|----------|----------|---------|
| **`RESEND_API_KEY`** | Yes | Resend API key (sending scope). |
| **`CONTACT_FROM_EMAIL`** | Optional | Defaults in code to `PropIntel AI <noreply@propintel-ai.com>` if unset. |

### Related files

| Layer | Path |
|-------|------|
| API route | `backend/app/api/contact.py` |
| App wiring | `backend/app/main.py` (`contact_router`) |
| Validation JSON | `backend/app/core/error_handlers.py` (Pydantic v2 **`ctx.error`** safe for JSON) |
| Frontend page | `frontend/src/pages/Contact.jsx` |
| Frontend API | `frontend/src/services/contactApi.js` |
| Tests | `backend/tests/test_contact.py`, `frontend/src/__tests__/pages/Contact.test.jsx`, `frontend/src/__tests__/services/contactApi.test.js` |

### Dependencies

- **`httpx`** — async HTTP client to Resend (already in API requirements).
- **`email-validator`** + **`dnspython`** — required by Pydantic **`EmailStr`** on the contact schema; pinned in **`requirements.txt`** and **`requirements-api.txt`**.

---

## System architecture

```text
        React Frontend (Vite + Tailwind CSS)
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
      PostgreSQL DB     Spine segment models
        (Supabase)      (XGBoost PKLs)
                               │
                               ▼
                     Gold Parquets (deploy) · Silver (optional local)
                     (DOF · ACRIS · J-51 · PLUTO)

        Contact form ──► POST /contact ──► Resend ──► Workspace inboxes
```

---

## Medallion data pipeline

```
Raw datasets (Bronze)
  NYC Rolling Sales · PLUTO · DOF Assessment · ACRIS · J-51 · Subway stations
            │
            ▼
  Silver normalisers  (ml/pipelines/silver_*.py)
            │
            ▼
  Spine builder  (ml/pipelines/spine_builder.py)
  training_spine_v1.parquet — BBL + sale_date + as_of_date (sale_date − 1 day)
            │
            ▼
  Gold as-of feature builders  (ml/pipelines/gold_*_asof.py)
            │
            ▼
  Training / tuning  (ml/models/train_spine_models.py, tune_spine_models.py)
            │
            ▼
  ml/artifacts/spine_models/   — committed PKLs + stats + feature importances
```

---

## Data sources

| Dataset | Role |
|---------|------|
| NYC Rolling Sales | Transaction prices and attributes |
| NYC PLUTO | Parcel / geo / physical attributes |
| DOF Property Valuation & Assessment | Roll history for as-of features |
| ACRIS | Deed / mortgage history |
| J-51 | Exemption / abatement flags |
| NYC Subway Stations | Transit distance features |

Join key: **BBL**. As-of filters prevent future data from leaking into training rows.

---

## Model registry & subtype routing

`ModelRegistry` maps **building class** → segment model (see `ml/artifacts/metadata/`). Rental classes **`07`** and **`08`** share **`rentals_all`** with an **`is_elevator`** feature. Feature importances ship as CSV artifacts for explainability and LLM context.

### Performance snapshot (time-based holdout)

Train ≤ **2024-12-31**, test ≥ **2025-01-31** (gap enforced). Example segments:

| Segment | Test R² | Notes |
|---------|---------|-------|
| `one_family` | **0.768** | Strong baseline |
| `condo_coop` | **0.637** | Stable |
| `two_family` | **0.677** | Split from legacy multi_family + comp/trend packs |
| `three_family` | **0.395** | Noisier investor segment |
| `rentals_all` | **0.458** | Pooled rentals; **price per unit** target |

See the tables in version-controlled docs / prior releases for full MAE, APE, and gate metrics.

---

## API endpoints

### Health

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Liveness |
| `GET` | `/ready` | DB + ML artifacts on disk (**503** if degraded) |

### Public (no JWT)

| Method | Path | Purpose |
|--------|------|---------|
| **`POST`** | **`/contact`** | Contact form → Resend (**rate limited**) |

### Auth (JWT or `X-API-Key`)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/auth/me` | Profile (creates row on first hit) |
| `PATCH` | `/auth/me` | Update profile |
| `GET` | `/auth/quota` | LLM quota status |

### Geocode usage

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/geocode/usage` | Record Mapbox request; **429** over monthly cap |

### Properties

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/properties/` | Create |
| `GET` | `/properties/` | List / filter |
| `GET` | `/properties/{id}` | Read |
| `PATCH` | `/properties/{id}` | Update |
| `DELETE` | `/properties/{id}` | Delete |
| `GET` | `/housing/lookup` | Nearest housing row for autocomplete |

### Prediction & analysis (**v2** — primary contract)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/predict-price-v2` | Valuation |
| `POST` | `/analyze-property-v2` | Full analysis + LLM |
| `GET` | `/model/feature-importance` | Global importances |

Legacy **`/predict-price`**, **`/analyze-property`**, **`/predict`**, **`/analyze`** remain for compatibility; new work should target **v2** only.

### Admin

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/admin/overview` | Aggregate stats |
| `PATCH` | `/admin/users/{user_id}/role` | Set role |

OpenAPI **`/docs`**, **`/redoc`**, **`/openapi.json`** are gated by **`DOCS_ENABLED=1`** (keep off in production).

---

## v2 prediction request schema

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

Optional **`bbl`** + **`as_of_date`** enable roll-aligned enrichment when Gold/Silver data is available.

### `POST /analyze-property-v2`

Same fields plus optional **`market_price`** for listing comparison.

---

## Example `POST /analyze-property-v2` response

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
  "drivers": { "top_drivers": [], "global_context": [], "explanation_factors": [] },
  "explanation": {
    "summary": "…",
    "opportunity": "…",
    "risks": "…",
    "recommendation": "Avoid",
    "confidence": "Medium"
  },
  "metadata": { "model_version": "v3" }
}
```

---

## Project structure

```
propintel-ai/
├── frontend/                    # React 19 + Vite + Tailwind CSS 4
│   ├── src/
│   │   ├── pages/               # Home, Analyze, Portfolio, Profile, Auth, Legal, Contact, …
│   │   ├── components/          # Navbar, Footer, SupportLink, …
│   │   ├── services/            # authApi, contactApi, housingApi, …
│   │   └── lib/                 # apiClient, supabase
│   ├── public/
│   ├── vercel.json              # SPA rewrites for React Router
│   └── package.json
│
├── backend/app/
│   ├── api/
│   │   ├── prediction.py
│   │   ├── properties.py
│   │   ├── auth_router.py
│   │   ├── admin.py
│   │   ├── geocode_usage.py
│   │   └── contact.py           # POST /contact → Resend
│   ├── core/                    # auth, limiter, error_handlers, config
│   ├── db/
│   ├── schemas/
│   ├── services/
│   └── main.py
│
├── backend/scripts/run_migrations.py
├── backend/migrations/          # SQL migrations + schema_migrations
├── backend/tests/               # e.g. test_contact.py
│
├── tests/                       # Main pytest suite (API, auth, quota, …)
│
├── ml/                          # Pipelines, training, artifacts (see repo)
├── Dockerfile
├── docker-compose.yml
├── railway.toml
├── requirements.txt             # Full dev + ML stack
├── requirements-api.txt         # Slim API Docker image
└── .env.example
```

---

## Environment setup

### Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy **`.env.example`** → **`.env`** at the repo root. Use **`postgresql+psycopg://`** for **`DATABASE_URL`** (matches `psycopg` v3).

**Docker / API-only installs:** add any new **runtime** import used by `backend/app/` to **`requirements-api.txt`** with the same pin as **`requirements.txt`** when applicable.

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Postgres (Supabase pooler OK) |
| `OPENAI_API_KEY` | LLM explanations |
| `API_KEY` | `X-API-Key` for scripts |
| `CORS_ORIGINS` | Exact browser origins (include both `localhost` and `127.0.0.1` dev ports if needed) |
| `CORS_ORIGIN_REGEX` | Optional (e.g. Vercel previews); default in code matches `propintel-*.vercel.app` |
| `SUPABASE_URL` | JWKS host for asymmetric JWTs |
| `SUPABASE_JWT_SECRET` | HS256 verification |
| `ADMIN_USER_IDS` | Comma-separated admin UUIDs |
| **`RESEND_API_KEY`** | **Contact form + can match Supabase SMTP usage operationally** |
| **`CONTACT_FROM_EMAIL`** | **Verified sender string for `/contact`** |
| `LLM_QUOTA_*`, `LLM_TEMPERATURE` | Quotas / sampling |
| `MAPBOX_MONTHLY_FREE_REQUEST_CAP` | Geocode cap checks |
| `DOCS_ENABLED` | `1` = expose `/docs` |
| `LOG_LEVEL` | Log verbosity |
| `SENTRY_*` | Optional observability |
| `TRUST_PROXY_HEADERS` | `1` behind trusted reverse proxy only |
| `ML_ARTIFACT_ROOT` | Override artifact root |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW` | Pool tuning |
| `RUN_MIGRATIONS` | Docker: skip migrations if `0` |

### Frontend

```bash
cd frontend && npm install
```

Copy **`frontend/.env.example`** → **`frontend/.env`**. **`VITE_*`** are inlined at **build** time.

| Variable | Purpose |
|----------|---------|
| **`VITE_API_BASE_URL`** | FastAPI origin (**required** for `apiFetch` and `/contact`) |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Anon key |
| `VITE_MAPBOX_TOKEN` | Mapbox public token |
| `VITE_MAPBOX_STYLE` | Optional map style override |
| `VITE_API_KEY` | Optional; must match server `API_KEY` (ships in bundle — not a secret) |

**Staging:** `frontend/.env.staging` + **`npm run dev:staging`** (see comments in `.env.example`).

---

## Running the app

### Backend

```bash
uvicorn backend.app.main:app --reload
```

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs` when **`DOCS_ENABLED=1`**
- Health: `/health`, readiness: `/ready`

### Frontend

```bash
cd frontend && npm run dev
```

Default dev server: `http://localhost:5174` (match **`CORS_ORIGINS`**).

### Database migrations

- Local SQLite / CI: `python -m backend.app.db.init_db`
- Postgres: `python -m backend.scripts.run_migrations` (also optional on Docker boot unless **`RUN_MIGRATIONS=0`**)

---

## Database integration

| Table | Model | Role |
|-------|-------|------|
| `profiles` | `Profile` | User profile + role |
| `properties` | `Property` | Saved analyses (`analysis` JSONB) |
| `llm_usage` | `LLMUsage` | Daily LLM counts |
| `mapbox_usage` | `MapboxUsage` | Geocode usage reporting |
| `housing_data` | `HousingData` | Reference / lookup data |

Contact submissions are **not** persisted in Postgres by default.

---

## Testing

### Backend

```bash
PYTHONPATH=. pytest
```

From the repo root this discovers **`tests/`** and **`backend/tests/`** (**93** tests), including **`backend/tests/test_contact.py`**.

### Frontend

```bash
cd frontend && npm test
```

**145** tests (Vitest + Testing Library). **`npm run lint`** runs ESLint (also executed in CI).

### Totals

| Suite | Count |
|-------|------:|
| Backend (`pytest`) | 93 |
| Frontend (`npm test`) | 145 |
| **Total** | **238** |

### CI

Workflow: **`.github/workflows/tests.yml`**

- **Backend:** Python 3.11, install **`requirements.txt`**, init SQLite DB, **`PYTHONPATH=. pytest`**
- **Frontend:** **`npm ci`**, **`npm run lint`**, **`npm test`**, **`npm run build`**

---

## Docker & Docker Compose

```bash
docker build -t propintel-ai:latest .
docker run --rm -p 8000:8000 --env-file .env propintel-ai:latest
# or: docker compose up --build
```

**`.dockerignore`** keeps Silver/raw bulk out of the image; **`ml/artifacts/spine_models/`** and Gold parquets needed for inference are included per Dockerfile layout.

- **`PORT`** — Railway / container port.
- **`DATABASE_URL`** — must use **`postgresql+psycopg://`** inside the container.

---

## Production & deployment checklist

| Area | Notes |
|------|--------|
| **Database** | Run migrations (`RUN_MIGRATIONS` or manual `run_migrations`) |
| **API** | `DATABASE_URL`, `SUPABASE_*`, `OPENAI_API_KEY`, `API_KEY`, **`CORS_ORIGINS`** exact match to the live site + **`TRUST_PROXY_HEADERS=1`** behind Railway |
| **Email** | **`RESEND_API_KEY`**, **`CONTACT_FROM_EMAIL`** on the API host; domain verified in Resend |
| **Frontend** | Set all **`VITE_*`** at **build** time on Vercel |
| **SPA** | **`frontend/vercel.json`** rewrites to `index.html` |
| **Domains** | Add production origins to **`CORS_ORIGINS`** (e.g. `https://www.propintel-ai.com`) |
| **Observability** | Optional `SENTRY_DSN` |
| **Billing** | Stripe not wired yet — Profile placeholders |

---

## Performance notes

- Lazy-loaded segment PKLs cached in memory after first load.
- `@lru_cache` on feature-importance loaders.
- Parquet predicate pushdown in **`BblFeatureBuilder`** where applicable.
- Cached BallTree / subway distance helpers.

---

## Model limitations

- Trained on **NYC residential** sales — not for generic commercial use.
- Metrics come from **forward-time** evaluation — not random splits.
- Segments with thinner data (e.g. three-family) show wider intervals.
- Macro / cycle features are out of scope for the current spine.

---

## License

MIT — see repository license file.
