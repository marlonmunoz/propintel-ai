# PropIntel AI

PropIntel AI is an end-to-end AI engineering system for real estate investment analysis, combining data pipelines, machine learning models, and scalable backend APIs.
### Core Stack:
![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![Supabase](https://img.shields.io/badge/Supabase-Backend-3ECF8E)

### Data/ AI Stack:
![Data Engineering](https://img.shields.io/badge/Data-Engineering-darkblue)
![Machine Learning](https://img.shields.io/badge/Machine-Learning-orange)
![XGBoost](https://img.shields.io/badge/XGBoost-Model-red)
![AI](https://img.shields.io/badge/AI-Artificial%20Intelligence-purple)


AI-powered real estate investment analysis platform built with data pipelines, machine learning models, FastAPI backend services, and PostgreSQL infrastructure.

---
## Tech Highlights

- Modular AI system architecture
- Production-style FastAPI backend
- PostgreSQL data layer with Supabase
- Real NYC government data ingestion pipeline
- End-to-end ML pipeline (ingestion → feature engineering → training → inference)
- Residential-only pricing model for MVP scope
- XGBoost regression for residential property valuation
- Feature importance / explainability output after model training
- Public and internal prediction/analysis API contracts
- In-memory model caching for faster predictions

---
## 🆕 Recent Milestone
PropIntel AI has now transitioned from placeholder housing data to a real NYC residential valuation pipeline using official NYC government datasets.

Recent work completed:
- downloaded and organized **NYC Rolling Sales** files for all 5 boroughs
- downloaded and integrated the **NYC PLUTO** dataset
- implemented a real ingestion pipeline in `ml/pipelines/data_ingestion.py`
- merged datasets using **BBL** as the property join key
- built a feature engineering pipeline in `ml/features/feature_engineering.py`
- scoped the MVP model to **residential-only** sales
- retrained the model using a **log-transformed target**
- upgraded the pricing model from a linear baseline to **XGBoost**
- generated a serialized pricing model artifact for inference

This milestone turns PropIntel into a real end-to-end AI pricing prototype built on NYC property data.

---

## Project Status
🚧 Active MVP / Production-Style AI Pipeline

Current milestone:
- Real NYC Rolling Sales + PLUTO ingestion pipeline implemented
- Residential-only feature engineering pipeline implemented
- XGBoost pricing model trained on real NYC residential sales data
- Feature importance / explainability added to training output
- Internal prediction endpoints implemented:
  - `POST /predict-price`
  - `POST /analyze-property`
- Public simplified endpoints implemented:
  - `POST /predict`
  - `POST /analyze`
- Property CRUD expanded to include:
  - `GET /properties/{property_id}`
- Model artifact generated for inference (`ml/artifacts/price_model.pkl`)

---

## Key Features

- FastAPI backend for scalable REST APIs
- PostgreSQL database integration (Supabase)
- Data engineering pipelines for housing datasets
- Machine learning models for property price prediction
- Feature engineering for market analysis
- ML inference endpoints for investment scoring
- Model serialization for inference-ready deployment
- Planned investment-analysis API outputs

PropIntel AI is designed as a production-minded AI engineering system for real estate analysis. The platform combines backend APIs, database integration, data pipelines, and machine learning workflows to evaluate property investment opportunities and generate data-driven insights.

---
## 🧠 System Architecture

```text
        Client / User
              │
              ▼
        FastAPI REST API
              │
              ▼
     Request Validation Layer
        (Pydantic Schemas)
              │
              ▼
          API Routing Layer
         (FastAPI Endpoints)
              │
              ▼
     ML / DB Integration Layer
   (route handlers + inference logic)
              │
      ┌────────────────────┐
      │   Planned Service  │
      │       Layer        │
      └────────────────────┘
              │
              ▼
        SQLAlchemy ORM
              │
              ▼
      PostgreSQL Database
         (Supabase)
              │
              ▼
         Data Pipelines
              │
              ▼
       Feature Engineering
              │
              ▼
     Machine Learning Models
              │
              ▼
   Prediction + Analysis APIs
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
         Feature Engineering Pipeline
     (`ml/features/feature_engineering.py`)
                    │
                    ▼
     Residential-only feature dataset
      (`ml/data/features/nyc_features.csv`)
                    │
                    ▼
          Model Training Pipeline
        (`ml/models/train_model.py`)
                    │
                    ▼
      XGBoost residential price model
                    │
                    ▼
      Feature importance / explainability
                    │
                    ▼
         Serialized model artifact
      (`ml/artifacts/price_model.pkl`)
                    │
                    ▼
      Internal + public FastAPI endpoints

```
---
## Example Workflow

A typical PropIntel AI workflow:

1. NYC Rolling Sales files are ingested from all 5 boroughs.
2. The PLUTO dataset is loaded and joined using **BBL** as the property key.
3. The merged dataset is transformed through the feature engineering pipeline.
4. The model is trained on residential-only sales using a log-transformed target.
5. XGBoost is used to train the residential pricing model.
6. Feature importances are printed to explain the model’s strongest global drivers.
7. The trained model is serialized to `ml/artifacts/price_model.pkl`.
8. A client can call either:
   - internal ML endpoints (`/predict-price`, `/analyze-property`)
   - public simplified endpoints (`/predict`, `/analyze`)
9. The API loads the cached model artifact and returns a valuation or analysis response.

---

## 🚀 Overview

The goal of PropIntel AI is to build a scalable AI-powered platform capable of supporting:

- automated property valuation
- real estate investment scoring
- data-driven market analysis
- ML-powered property insights
- backend APIs for prediction and analysis

The system is structured like a modern production application, separating:

- backend services
- database architecture
- machine learning modules
- inference pipelines
- API delivery

---


## 📁 Project Structure
The repository was organized using a modular backend architecture.

```
propintel-ai
│
├── backend
│   └── app
│       ├── api
│       │   ├── prediction.py
│       │   └── properties.py
│       ├── core
│       ├── db
│       │   ├── database.py
│       │   └── init_db.py
│       ├── main.py
│       ├── models
│       │   └── property.py
│       ├── schemas
│       │   ├── prediction.py
│       │   └── property.py
│       └── services        # planned / currently minimal
│
├── ml
│   ├── artifacts
│   │   └── price_model.pkl
│   ├── data
│   │   ├── nyc_raw         # ignored in git
│   │   ├── pluto_raw       # ignored in git
│   │   ├── processed       # ignored in git
│   │   └── features        # ignored in git
│   ├── features
│   │   └── feature_engineering.py
│   ├── inference
│   │   └── predict.py
│   ├── models
│   │   └── train_model.py
│   └── pipelines
│       └── data_ingestion.py
│
├── tests
│   ├── test_prediction_api.py
│   └── test_property_api.py
├── requirements.txt
├── README.md
└── LICENSE
```

This structure separates responsibilities across different modules:

| Folder | Purpose |
|------|------|
| `api/` | API endpoints |
| `core/` | application configuration |
| `db/` | database setup |
| `models/` | database models |
| `schemas/` | request/response validation |
| `services/` | planned business/ service layer |
| `ml/artifacts/` | saved models and serialized ML artifacts |
| `ml/data/` | dataset ingestion and processing |
| `ml/features/` | feature engineering logic |
| `ml/inference/` | prediction and scoring logic |
| `ml/models/` | model training and evaluation |
| `ml/pipelines/` | end-to-end ML pipeline orchestration |

---

## ⚙️ Environment Setup

A Python virtual environment was created to isolate project dependencies.

```
python3 -m venv .venv
source .venv/bin/activate
```

Dependencies installed:

```
pip install fastapi uvicorn sqlalchemy python-dotenv "psycopg[binary]" pandas numpy scikit-learn xgboost joblib
```

Then dependencies were saved:

```
pip freeze > requirements.txt
```

---

## 🔧 FastAPI Server

A FastAPI application was created in:

```
backend/app/main.py
```

Example:

```python
from fastapi import FastAPI

app = FastAPI(
    title="PropIntel AI",
    description="AI-powered real estate investment analysis platform",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"message": "PropIntel AI running 🚀"}

@app.get("/health")
def health():
    return {"status": "ok"}
```

---

## ▶️ Running the API

The development server is started with:

```
uvicorn backend.app.main:app --reload
```

Once running, the API is available at:

```
http://127.0.0.1:8000
```

Interactive API documentation (Swagger UI):

```
http://127.0.0.1:8000/docs
```

---

## ✅ Outcome

At the end of Day 1 the project now includes:

- production-grade backend architecture
- FastAPI server running locally
- dependency management with `requirements.txt`
- automatic API documentation
- repository ready for data engineering and ML development
---

## 🗄️ Database Integration (Supabase + SQLAlchemy)

After the FastAPI server was initialized, the next step was connecting the backend to a **cloud PostgreSQL database** using Supabase.

This layer enables the platform to store:
- property listings
- pricing data
- structured housing features
- records used for machine learning workflows

---

## 🔗 Database Connection

A `.env` file was created to store the database connection string securely.

```
.env
```

Example:

```
DATABASE_URL=postgresql+psycopg://postgres:<PASSWORD>@db.<project>.supabase.co:5432/postgres
```

Environment variables are loaded using:

```
python-dotenv
```

This keeps sensitive credentials out of the Git repository.

---

## 🧠 SQLAlchemy Database Setup

Database connectivity and session management were implemented in:

```
backend/app/db/database.py
```

Example:

```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

This module provides:

- database engine configuration
- session creation
- dependency injection for API routes

---

## 🏠 Property Model

A SQLAlchemy ORM model was created to represent real estate listings.

```
backend/app/models/property.py
```

Example:

```python
from sqlalchemy import Column, Integer, String, Float
from backend.app.db.database import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, index=True)
    zipcode = Column(String, index=True)
    bedrooms = Column(Integer)
    bathrooms = Column(Integer)
    sqft = Column(Integer)
    listing_price = Column(Float)
```

---

## 🛠 Database Initialization

Database tables are created using a small initialization script:

```
backend/app/db/init_db.py
```

Run with:

```
python -m backend.app.db.init_db
```

This automatically generates the required tables inside Supabase.

---

## 🌐 Property API Endpoints

REST API routes were implemented to interact with the database.

```
backend/app/api/properties.py
```
Current CRUD support includes:

### Create Property


`POST /properties`

Stores a new property listing in PostgreSQL.

Example request:

```json
{
  "address": "45 W 34th St",
  "zipcode": "10001",
  "bedrooms": 2,
  "bathrooms": 1,
  "sqft": 950,
  "listing_price": 750000
}
```

The API stores the record in PostgreSQL and returns the saved object.

---

### Retrieve Properties

`GET /properties`

Returns all stored properties.

The endpoint supports pagination and filtering.

Example queries:

```python
GET /properties?limit=10
GET /properties?zipcode=10001
GET /properties?min_price=500000
GET /properties?max_price=900000
```
---

### Retrieve Property by ID
`GET /properties/{property_id}`

---
### Update Property
`PATCH /properties/{property_id}`

---
### DELETE Property
`DELETE /properties/{property_id}`

> **Note:** some README-described routes are still being aligned with the latest codebase implementation.

---
<!-- ### API Validation & Error Handling
The API uses Pydantic schemas to validate incoming requests and ensure consistent data structures.

Error handling is implemented to return clear responses when:

- invalid data is submitted
- a property record does not exist
- database operations fail

Example error response:
```json
{
  "detail": "Property not found"
}
``` -->
---

## 🔍 Testing & Reliability (pytest + FastAPI TestClient + GitHub Actions)

Automated tests are stored in:

```
tests/
```
Current coverage includes:

- prediction API endpoint contract test
- property API endpoint test
- test database initialization to create required tables before DB-dependent tests run

Run tests locally from the project root:

```
pytest 
```

### FastAPI TestClient

The test suite uses FastAPI’s built-in `TestClient` to validate endpoints without running a live server.

Example pattern:
```python
from fastapi.testclient import TestClient
from backend.app.main import app
import backend.app.api.prediction as prediction_api

client = TestClient(app)

def test_predict_price_endpoint(monkeypatch):
    payload = {
        "gross_square_feet": 1497,
        "land_square_feet": 1668,
        "residential_units": 1,
        "commercial_units": 0,
        "total_units": 1,
        "numfloors": 2,
        "unitsres": 1,
        "unitstotal": 1,
        "lotarea": 1668,
        "bldgarea": 1497,
        "latitude": 40.8538937,
        "longitude": -73.8962879,
        "pluto_year_built": 1899,
        "building_age": 127,
        "borough": 2,
        "building_class_category": "01 ONE FAMILY DWELLINGS",
        "neighborhood": "BATHGATE",
        "zip_code": 10457,
    }

    def mock_predict_price(_payload: dict):
        return {
            "predicted_price": 611081.6875,
            "model_version": "xgboost_residential_nyc_v1",
        }

    monkeypatch.setattr(prediction_api, "predict_price", mock_predict_price)

    response = client.post("/predict-price", json=payload)

    assert response.status_code == 200
```

### CI Pipeline (GitHub Actions)

A GitHub Actions workflow runs tests automatically on:
- push to `main`
- pull requests targeting `main`

Workflow location:
```
.github/workflows/tests.yml
```
The CI pipeline performs:
1. checkout repo
2. setup Python 3.11
3. install dependencies
4. run `pytest`
---

## 🐳 Docker & Docker Compose

The project is containerized to run in a production-style environment.

### Build the API image

From the project root:
```
docker build -t propintel-api .
```

### Run the container (Supabase mode)

Using an env file:
```
docker run --rm -p 8000:8000 --env-file .env.docker propintel-api
```
Then open:
- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Docker environment files
Local Docker environment variables live in:
```
.env.docker
```
This file is ignored by Git for security. Use the example file as a template:
```
.env.docker.example
```
### Run with Docker Compose
Build and run:
```
docker compose up --build
```
Stop:
```
docker compose down
```

---

<!-- ## 🧱 Current System Architecture

The backend now follows a typical production architecture:

```
Client Request
      │
FastAPI REST API
      │
Pydantic Validation
      │
Service Layer
      │
SQLAlchemy ORM
      │
Supabase PostgreSQL
```

This architecture supports scalable backend services and future AI-powered endpoints. -->

---
## 🤖 Machine Learning Implementation

PropIntel AI now includes a real data → model → prediction pipeline built on NYC government property datasets.

This stage transforms PropIntel AI from a traditional backend system into an AI-powered analytics platform.

---

## ✅ Current Progress

**Backend and Database**
- FastAPI backend server
- modular backend architecture
- Supabase PostgreSQL integration
- SQLAlchemy ORM models
- CRUD API for property management
- Pydantic validation schemas
- structured error handling
- Swagger API documentation

**Machine Learning**
- NYC Rolling Sales ingestion pipeline
- PLUTO dataset ingestion pipeline
- BBL-based dataset merge
- feature engineering pipeline
- residential-only dataset filtering
- log-transformed target training
- Linear Regression baseline model
- XGBoost residential valuation model
- model serialization
- ML inference layer structure
- prediction API architecture

**Engineering & Reliability**
- automated tests with pytest + FastAPI TestClient
- GitHub Actions CI workflow running tests on push/PR
- Dockerfile for containerized API deployment
- Docker Compose for local container orchestration
- secure environment management 

---

## 🧠 Machine Learning Stack

The PropIntel AI platform integrates a machine learning layer designed to estimate property 
values and support future investment analysis.

The ML environment includes:

- **pandas** — data manipulation and preprocessing
- **numpy** — numerical computing
- **scikit-learn** — feature engineering and baseline models
- **XGBoost** — gradient boosting model for price prediction
- **joblib** — model serialization for production inference
- **openpyxl** — Excel ingestion support for NYC Rolling Sales files

All dependencies (backend + ML) are consolidated in the root:

```
requirements.txt
```

<!-- ```
fastapi
uvicorn
sqlalchemy
python-dotenv
psycopg[binary]

pandas
numpy
scikit-learn
xgboost
joblib
``` -->

---

## 📂 ML Module Structure

The machine learning layer is organized into focused submodules:

```
ml/
├── artifacts/     # saved models and serialized ML artifacts
├── data/          # dataset ingestion and raw data
├── features/      # feature engineering logic
├── inference/     # prediction utilities
├── models/        # model training pipelines
└── pipelines/     # end-to-end ML orchestration
```

Each module represents a stage in the machine learning lifecycle.

---
## 📊 Feature Engineering
The feature engineering pipeline transforms the merged NYC Rolling Sales + PLUTO dataset into a model-ready residential valuation dataset.

Implemented transformations include:

- column normalization and renaming to snake_case
- numeric conversion for square footage, units, coordinates, and year-built fields
- residential-only filtering for MVP scope
- invalid sale filtering (`sale_price > 10000`)
- building age calculation
- target-aware analysis feature generation (`price_per_sqft`)
- selection of modeling-ready numeric and categorical features

Current core modeling features include:

- `gross_square_feet`
- `land_square_feet`
- `residential_units`
- `commercial_units`
- `total_units`
- `numfloors`
- `unitsres`
- `unitstotal`
- `lotarea`
- `bldgarea`
- `latitude`
- `longitude`
- `pluto_year_built`
- `building_age`
- `borough`
- `building_class_category`
- `neighborhood`
- `zip_code`

Generated datasets:
- `ml/data/processed/nyc_training_data.csv`
- `ml/data/features/nyc_features.csv`

> Note: `price_per_sqft` is generated for analysis purposes but excluded from model training inputs to avoid target leakage.

---
## 🧠 Model Training
Model training is implemented in:
```
ml/models/train_model.py
```
The training pipeline performs the following steps:

1. Load engineered residential NYC feature dataset
2. Select numeric and categorical training features
3. Apply preprocessing:
- median imputation for numeric columns
- most-frequent imputation for categorical columns
- one-hot encoding for categorical features
4. Train a regression model on a log-transformed target:
- `log1p(sale_price)`
5. Evaluate predictions on the original dollar scale
6. Print top global feature importances for explainability
7. Serialize the trained model for inference

Current model progression:

- Linear Regression baseline
- **XGBoost regressor** for improved non-linear residential price prediction

Run training from project root:
```
python ml/models/train_model.py
```
---

## 📈 Model Evaluation

Recent residential NYC training results:

### Linear Regression baseline
- MAE: `903,670.77`
- RMSE: `4,338,505.69`
- R²: `0.1110`

### XGBoost model
- MAE: `550,494.73`
- RMSE: `3,004,114.04`
- R²: `0.5738`

### Explainability milestone
Top global feature importances now include:
- neighborhood
- building area (`bldgarea`)
- borough
- total units
- number of floors
- zip code
- building class category
- gross square feet
- longitude

Interpretation:
- residential filtering improved modeling consistency
- log-transforming the target stabilized training across a wide price range
- XGBoost significantly outperformed the linear baseline
- the model is learning plausible NYC-specific drivers like location, building size, and property class

---

## 💾 Model Serialization

The trained model is serialized using joblib.

Saved model location:
```
ml/artifacts/price_model.pkl
```
This allows the backend API to reuse the trained model for real-time predictions without retraining.

---
## 🚀 ML Inference Layer

The inference layer loads the trained model and generates predictions from property features.

Implemented in:
```
ml/inference/predict.py
```

Responsibilities include:
- loading the trained model
- mapping public request payloads into the internal model feature contract
- transforming feature inputs
- generating predictions
- converting log-scale predictions back to original dollar values
- rreturning structured results to the API layer

Implemented inference surface:
- internal prediction: `POST /predict-price`
- internal analysis: `POST /analyze-property`
- public prediction: `POST /predict`
- public analysis: `POST /analyze`
---
## ⚡ Performance Optimization (Model Caching)

To improve performance, the model is loaded once into memory and reused for all future requests.

Without optimization:
```
Request
   │
Load model from disk
   │
Predict
```

Optimized approach:
```
First Prediction Request
        │
Load model once into memory
        │
Cache model in RAM
        │
Reuse for all future predictions
```
Benefits:
- faster response times
- reduced disk I/O
- improved scalability

---
## 🌐 ML Prediction APIs

PropIntel AI now exposes both internal and public-facing ML endpoints.

### Internal endpoints
These use the full engineered model contract:

```
POST /predict-price  
POST /analyze-property   
```

### Public endpoints
These expose a simpler product-facing request contract:

```
POST /predict
POST /analyze
```

### Example public prediction request
```json
{
 "gross_square_feet": 1497,
  "land_square_feet": 1668,
  "residential_units": 1,
  "commercial_units": 0,
  "total_units": 1,
  "numfloors": 2,
  "latitude": 40.8538937,
  "longitude": -73.8962879,
  "year_built": 1899,
  "borough": 2,
  "building_class_category": "01 ONE FAMILY DWELLINGS",
  "neighborhood": "BATHGATE",
  "zip_code": 10457
}
```

### Example public prediction response
```json
{
  "predicted_price": 611081.6875,
  "model_version": "xgboost_residential_nyc_v1"
}
```

### Example public analysis request
```json
{
  "gross_square_feet": 1497,
  "land_square_feet": 1668,
  "residential_units": 1,
  "commercial_units": 0,
  "total_units": 1,
  "numfloors": 2,
  "latitude": 40.8538937,
  "longitude": -73.8962879,
  "year_built": 1899,
  "borough": 2,
  "building_class_category": "01 ONE FAMILY DWELLINGS",
  "neighborhood": "BATHGATE",
  "zip_code": 10457,
  "market_price": 550000
}
```

### Example public analysis response
```json
{
  "predicted_price": 611081.6875,
  "market_price": 550000.0,
  "price_difference": 61081.6875,
  "roi_estimate": 11.105761363636365,
  "investment_score": 77.7644034090909,
  "model_version": "xgboost_residential_nyc_v1"
}
```

### Notes
- The current model is trained only on residential NYC sales for the MVP scope.
- Predictions are generated from engineered features derived from the NYC Rolling Sales and PLUTO datasets.
- The latest XGBoost model artifact is implemented in the ML pipeline, and full production wiring into all API routes is still being finalized.

> **Note:** endpoint structure exists, but the latest XGBoost model wiring and final request/response contract are still being aligned with the current ML pipeline.

---
## 🧾 Prediction Request Schema

The current MVP prediction model expects a residential NYC property payload with the following fields:

| Field | Type | Description |
|------|------|------|
| `gross_square_feet` | number | building square footage from sales data |
| `land_square_feet` | number | lot square footage from sales data |
| `residential_units` | number | residential unit count |
| `commercial_units` | number | commercial unit count |
| `total_units` | number | total unit count |
| `numfloors` | number | number of floors |
| `unitsres` | number | residential units from PLUTO |
| `unitstotal` | number | total units from PLUTO |
| `lotarea` | number | lot area from PLUTO |
| `bldgarea` | number | building area from PLUTO |
| `latitude` | number | latitude |
| `longitude` | number | longitude |
| `pluto_year_built` | number | year built from PLUTO |
| `building_age` | number | derived feature: current year - year built |
| `borough` | number | NYC borough code |
| `building_class_category` | string | building category label |
| `neighborhood` | string | NYC neighborhood |
| `zip_code` | number | property ZIP code |

---
## 🧠 ML Inference Architecture

The prediction system now operates as follows:
```text
Client Request
      │
FastAPI Endpoint
      │
Pydantic Validation
      │
Public Payload Mapping
      │
Internal Model Feature Contract
      │
Cached XGBoost Model
      │
Prediction / Analysis
      │
JSON Response
```

The inference layer is responsible for:
- validating incoming residential property features
- mapping request fields into the model input contract
- loading the serialized model artifact
- generating predictions
- returning a structured API response

---
## 🔬 ML Pipeline
The machine learning workflow follows a standard production pattern:

```
Dataset Ingestion
        │
Data Cleaning
        │
Feature Engineering
        │
Model Training
        │
Model Evaluation
        │
Model Serialization
        │
API Inference
```
This pipeline is intended to support:
- property price prediction
- investment scoring
- ROI estimation
- future market analysis features

---

## 📊 Preparing Data for Machine Learning

Once data is stored in PostgreSQL, it can be extracted and transformed for training machine learning models.

Examples of features that can be used for investment analysis include:
- square footage
- lot and building area
- building age
- neighborhood and borough
- zip code
- residential unit counts
- geographic coordinates
- building class category

These features feed the PropIntel AI valuation model.

---

## 📈 Planned AI Output

A future prediction endpoint will expose investment-analysis outputs through the API:
```
POST /analyze-property
```

Example response:

```json
{
  "predicted_price": 812000,
  "investment_score": 84,
  "roi_estimate": 10.7
}
```
This endpoint is part of the planned PropIntel investment analysis layer and is not yet fully implemented.
---

## ✅ Current Progress

### Backend and Database
- FastAPI backend server
- modular backend architecture
- Supabase PostgreSQL integration
- SQLAlchemy ORM models
- full property CRUD:
  - `POST /properties/`
  - `GET /properties/`
  - `GET /properties/{property_id}`
  - `PATCH /properties/{property_id}`
  - `DELETE /properties/{property_id}`
- Pydantic validation schemas
- structured error handling
- Swagger API documentation

### Machine Learning
- NYC Rolling Sales ingestion pipeline
- PLUTO dataset ingestion pipeline
- BBL-based dataset merge
- feature engineering pipeline
- residential-only dataset filtering
- log-transformed target training
- Linear Regression baseline model
- XGBoost residential valuation model
- feature importance / explainability output
- model serialization
- ML inference layer structure
- internal ML endpoints:
  - `POST /predict-price`
  - `POST /analyze-property`
- simplified public ML endpoints:
  - `POST /predict`
  - `POST /analyze`

### Engineering and Reliability
- automated tests with pytest + FastAPI TestClient
- GitHub Actions CI workflow running tests on push/PR
- Dockerfile for containerized API deployment
- Docker Compose for local container orchestration
- secure environment management
---

