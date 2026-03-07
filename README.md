# propintel-ai
AI-powered real estate investment analysis platform using machine learning, FastAPI, and data pipelines.

## 🚀 Day 1 — Backend Setup (FastAPI)

The first step in building **PropIntel AI** was setting up the backend architecture and API server.

The goal of this stage was to create a **clean, scalable backend structure** that will support:

- data pipelines
- machine learning services
- real estate analysis endpoints
- AI-generated investment reports

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

<!-- ## 🔜 Next Steps

Day 2 will focus on the **data pipeline**, including:

- loading housing datasets
- cleaning and preparing features
- building an ML-ready dataset for property price prediction

This dataset will be used to train the **property valuation model** that powers the PropIntel AI analysis engine. -->

---

## 🗄️ Database Integration (Supabase + SQLAlchemy)

After the FastAPI server was initialized, the next step was connecting the backend to a **cloud PostgreSQL database** using Supabase.

Supabase provides a managed PostgreSQL instance that integrates well with Python applications and supports scalable production deployments.

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
SQLAlchemy ORM
      │
Supabase PostgreSQL
```

This architecture supports scalable backend services and future AI-powered endpoints.

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
- Git version control workflow

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

## 🔜 Next Steps (AI Layer)

The next stage of development focuses on the **machine learning pipeline**:

- ingesting real estate datasets
- feature engineering for property valuation
- training a machine learning model
- exposing the model via a prediction API

Future endpoint:

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

This will power the **PropIntel AI real estate investment analysis engine**.