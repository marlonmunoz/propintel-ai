![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-API-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-blue)
![Supabase](https://img.shields.io/badge/Supabase-Backend-green)
![Machine Learning](https://img.shields.io/badge/ML-XGBoost-orange)
![AI](https://img.shields.io/badge/AI-Artificial%20Intelligence-purple)

# PropIntel AI

AI-powered real estate investment analysis platform using machine learning, FastAPI, PostgreSQL, and data pipelines.

PropIntel AI is designed to simulate a production-style AI engineering system for real estate analysis. The platform combines backend APIs, database integration, data pipelines, and machine learning workflows to evaluate property investment opportunities and generate data-driven insights.

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

## 🧠 System Architecture

```text
Client / Frontend
        │
        ▼
FastAPI REST API
        │
Pydantic Validation
        │
Business Logic (Services)
        │
SQLAlchemy ORM
        │
Supabase PostgreSQL
        │
Data Pipelines
        │
Feature Engineering
        │
Machine Learning Models
        │
Prediction / Analysis API
- AI-generated investment reports
``` 


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
| `ml/artifacts/` | saved model files and serialized objects |
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
pip install fastapi uvicorn sqlalchemy python-dotenv "psycopg[binary]"
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

### Create Property

```
POST /properties
```

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

```
GET /properties
```

Returns all stored properties.

---

### Retrieve Property by ID

```
GET /properties/{property_id}
```

Returns a specific property record.

---

## 🔍 API Testing

The endpoints can be tested directly using FastAPI's automatic documentation:

```
http://127.0.0.1:8000/docs
```

Swagger UI allows sending requests and viewing responses without additional tools.

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

<!-- --- -->

<!-- ## ✅ Current Progress

So far the project includes:

- FastAPI backend server
- modular backend architecture
- Supabase PostgreSQL integration
- SQLAlchemy ORM models
- property database table
- REST API endpoints
- interactive API documentation
- Git version control workflow -->

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
├── artifacts/     # saved models, scalers, and serialized objects
├── data/          # data loading, ingestion, and raw dataset helpers
├── features/      # feature engineering and transformation logic
├── inference/     # prediction pipeline and scoring utilities
├── models/        # model training, evaluation, and selection
└── pipelines/     # end-to-end orchestrated ML workflows
```

This modular structure keeps each stage of the ML lifecycle isolated and independently testable.

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
- REST API endpoints
- interactive API documentation
- machine learning module structure
- prediction pipeline design
- Git version control workflow

---

## 🎯 Why This Project Matters

PropIntel AI demonstrates skills across multiple disciplines relevant to modern AI engineering roles:
- backend development
- API integration
- PostgreSQL database design
- system architecture
- machine learning pipeline design
- model evaluation preparation
- scalable systems thinking
- production environment patterns

This makes the project a strong portfolio example for roles in:

- AI Engineering
- ML Engineering
- Data Engineering
- Backend Python Development

---

## 🔜 Next Steps

The next stage of development focuses on the AI layer and production-readiness of the platform:

- ingesting real estate datasets
- cleaning and validating housing data
- feature engineering for valuation models
- training machine learning models
- evaluating model performance
- exposing predictions through API endpoints
- adding deployment and inference workflows

As development continues, PropIntel AI will evolve from a backend + database foundation into a complete end-to-end AI-powered real estate analytics platform.

---























