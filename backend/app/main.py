from fastapi import FastAPI
from backend.app.api import properties

app = FastAPI(
    title="PropIntel AI",
    description="An AI-powered real state investment analysis platform",
    version="1.0.0"
)

app.include_router(properties.router)

@app.get("/")
def root():
    return {"message": "PropIntel AI running 🚀"}

@app.get("/health")
def health():
    return {"status": "OK ✅"}