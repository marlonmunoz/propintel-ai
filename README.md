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
| `ml/` | machine learning pipelines |
| `data/` | dataset ingestion and processing |

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
    version="0.1.0"
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

- production-style backend architecture
- FastAPI server running locally
- dependency management with `requirements.txt`
- automatic API documentation
- repository ready for data engineering and ML development

---

## 🔜 Next Steps

Day 2 will focus on the **data pipeline**, including:

- loading housing datasets
- cleaning and preparing features
- building an ML-ready dataset for property price prediction

This dataset will be used to train the **property valuation model** that powers the PropIntel AI analysis engine.