from fastapi import FastAPI
from backend.app.api.prediction import router as prediction_router
from backend.app.api.properties import router as properties_router

app = FastAPI(
    title="PropIntel AI",
    description="AI-powered real estate investment analysis platform",
    version="1.0.0"
)

app.include_router(prediction_router)
app.include_router(properties_router)

@app.get("/")
def root():
    return {"message": "PropIntel AI running 🚀"}

@app.get("/health")
def health():
    return {"status": "OK ✅"}

