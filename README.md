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
- End-to-end ML pipeline (ingestion → feature engineering → training → inference)
- Scalable feature engineering workflow
- Model deployment via API endpoints
- In-memory model caching for faster predictions

--- 

## Project Status
🧪 Experimental AI System

---

## Key Features

- FastAPI backend for scalable REST APIs
- PostgreSQL database integration (Supabase)
- Data engineering pipelines for housing datasets
- Machine learning models for property price prediction
- Feature engineering for market analysis
- ML inference endpoints for investment scoring

PropIntel AI is designed to simulate a production-style AI engineering system for real estate analysis. The platform combines backend APIs, database integration, data pipelines, and machine learning workflows to evaluate property investment opportunities and generate data-driven insights.

---
## 🧠 System Architecture
```
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
      ┌────────────────────┐
      │   Business Logic   │
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
        Prediction API
```
---
## Data & ML Pipeline
```
Real Estate Dataset
        │
        ▼
Data Ingestion
        │
        ▼
Data Cleaning & Validation
        │
        ▼
Feature Engineering
        │
        ▼
Model Training
        │
        ▼
Model Serialization
        │
        ▼
Inference Layer
        │
        ▼
FastAPI Prediction Endpoint
        │
        ▼
Investment Analysis Response
```

---
## Example Workflow

A typical workflow for PropIntel AI:

1. A user submits property information through the API.
2. The backend validates the request using Pydantic schemas.
3. Property data is stored in the PostgreSQL database (Supabase).
4. Data pipelines ingest and prepare housing data.
5. Feature engineering transforms the raw dataset into ML-ready inputs.
6. The machine learning model is trained and serialized for inference.
7. The FastAPI prediction endpoint loads the trained model from memory and returns a predicted property value.

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
│       ├── core
│       ├── db
│       ├── main.py
│       ├── models
│       ├── schemas
│       └── services
│
├── data
├── ml
│   ├── artifacts
│   ├── data
│   ├── features
│   ├── inference
│   ├── models
│   └── pipelines
├── notebooks
├── tests
│
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
| `services/` | business logic |
| `ml/artifacts/` | saved models and serialized ML artifacts |
| `ml/data/` | dataset ingestion and processing |
| `ml/features/` | feature engineering logic |
| `ml/inference/` | prediction and scoring logic |
| `ml/models/` | model training and evaluation |
| `ml/pipelines/` | end-to-end ML pipeline orchestration |
| `data/` | raw and processed data storage |

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

Supabase provides a managed PostgreSQL instance that integrates well with Python applications and supports scalable production deployments.

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

The `.env` file is ignored in `.gitignore`.

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
The API now supports a full CRUD workflow for managing property records.

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
```
GET /properties?limit=10
GET /properties?zipcode=10001
GET /properties?min_price=500000
GET /properties?max_price=900000
```
---

### Retrieve Property by ID
`GET /properties/{property_id}`

Returns a specific property record.

---
### Update Property
`PATCH /properties/{property_id}`

Allows partial updates to property records using Pydantic validation schemas.

Example request:

```json
{
  "listing_price": 820000
}
```
---
### DELETE Property
`DELETE /properties/{property_id}`

Removes a property record from the database.

---
### API Validation & Error Handling
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
```
---

## 🔍 Testing & Reliability (pytest + FastAPI TestClient + GitHub Actions)

Automated tests are stored in:

```
tests/
```
Current coverage includes:

- Prediction API endpoint test (POST /predict-price)
- Property API endpoint test (POST /properties)
- Test database initialization to create required tables before DB-dependent tests run

Run tests locally from the project root:

```
pytest 
```
Example successful output:

```
2 passed in 2.23s
```

### FastAPI TestClient

The test suite uses FastAPI’s built-in `TestClient` to validate endpoints without running a live server.

Example pattern:
```
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_predict_price_endpoint():
    payload = {"sqft": 1000, "bedrooms": 2, "bathrooms": 1}
    response = client.post("/predict-price", json=payload)
    assert response.status_code == 200
    assert "predicted_price" in response.json()
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
The repo includes docker-compose.yml for running the API using Docker Compose.

Build and run:
```
docker compose up --build
```
Stop:
```
docker compose down
```

---

## 🧱 Current System Architecture

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

This architecture supports scalable backend services and future AI-powered endpoints.

---
🤖 Machine Learning Implementation

Introduced the machine learning layer of PropIntel AI. The platform now includes a complete data → model → prediction pipeline integrated with the FastAPI backend.

This stage transforms PropIntel AI from a traditional backend system into an AI-powered analytics platform.

---

## ✅ Current Progress

Backend and Database
- FastAPI backend server
- modular backend architecture
- Supabase PostgreSQL integration
- SQLAlchemy ORM models
- CRUD API for property management
- Pydantic validation schemas
- structured error handling
- Swagger API documentation

Machine Learning
- data ingestion pipeline
- feature engineering pipeline
- machine learning training pipeline
- model serialization
- ML inference layer
- prediction API endpoint (`POST /predict-price`)
- in memory model caching optimization

Engineering & Reliability
- automated tests with pytest + FastAPI TestClient
- GitHub Actions CI workflow running tests on push/PR
- Dockerfile for containerized API deployment
- Docker Compose for local container orchestration
- secure environment management (`.env.docker` ignored, `.env.docker.example` provided)

---

## 🧠 Machine Learning Stack

The PropIntel AI platform integrates a machine learning layer designed to estimate property values and analyze investment potential.

The ML environment includes:

- **pandas** — data manipulation and preprocessing
- **numpy** — numerical computing
- **scikit-learn** — feature engineering and baseline models
- **XGBoost** — gradient boosting model for price prediction
- **joblib** — model serialization for production inference

All dependencies (backend + ML) are consolidated in the root:

```
requirements.txt
```

```
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
```

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
Feature engineering transforms raw housing data into structured numerical inputs suitable for machine learning models.

Implemented features include:

- square footage (sqft)
- number of bedrooms
- number of bathrooms
- price per square foot
- bedroom density
- bathroom ratio

These engineered features allow the model to capture patterns in real estate valuation.

Example feature vector:

```
[sqft, bedrooms, bathrooms, price_per_sqft, bedroom_density, bathroom_ratio]
```
Example:

```
[1000, 2, 1, 800, 0.002, 0.5]
```
---
## 🧠 Model Training
A machine learning training pipeline was implemented in:
```
ml/models/train_model.py
```
The training pipeline performs the following steps:

1. Load engineered feature dataset
2. Split dataset into training and testing sets
3. Train a regression model
4. Evaluate model performance
5. Serialize the trained model

Running the training pipeline:
```
python -m ml.models.train_model
```
Example console output:
```
Loading feature data...
Training model...
Model R² Score: 0.87
Model saved to ml/artifacts/price_model.pkl
```
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

- Responsibilities:
- load trained model
- transform feature inputs
- generate predictions
- return results to the API layer

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
- significantly faster response times
- reduced disk I/O
- improved scalability

---
## 🌐 ML Prediction API
The trained model is exposed through a FastAPI endpoint.
```
POST /predict-price     
```
This endpoint allows external clients to send property features and receive predicted property prices.

Example Request
```
{
  "sqft": 1000,
  "bedrooms": 2,
  "bathrooms": 1
}
```

Example Response
```
{
  "predicted_price": 852682
}
```
The prediction is generated by the trained machine learning model.

---

## 🧠 ML Inference Architecture

The prediction system now operates as follows:
```
Client Request
      │
FastAPI Endpoint
      │
Pydantic Validation
      │
Prediction Router
      │
Cached ML Model (Memory)
      │
Prediction
      │
JSON Response
```


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
- price per square foot
- bedroom and bathroom ratios
- geographic pricing patterns
- neighborhood trends
- historical price comparisons
- market-based valuation signals

These features will later feed the PropIntel AI valuation and investment models.

---

## 📈 Example AI Output

A future prediction endpoint will expose machine learning outputs through the API:
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
This endpoint will power the PropIntel AI real estate investment analysis engine.

---

## ✅ Current Progress

So far the project includes:
- FastAPI backend server
- modular backend architecture
- Supabase PostgreSQL integration
- SQLAlchemy ORM models
- property database table
- CRUD API for property management
- Pydantic validation schemas
- API pagination and filtering
- structured error handling
- interactive API documentation (Swagger)
- data ingestion pipeline
- feature engineering pipeline
- machine learning training pipeline
- model serialization
- ML inference layer
- prediction API endpoint
- model caching optimization
- Git version control workflow
---
























