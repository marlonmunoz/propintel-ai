from fastapi import FastAPI

app = FastAPI(
    title="PropIntel AI",
    description="An AI-powered real state investment analysis platform",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"message": "PropIntel AI running 🚀"}

@app.get("/health")
def health():
    return {"status": "OK ✅"}