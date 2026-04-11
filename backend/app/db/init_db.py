from backend.app.db.database import engine, Base
from backend.app.db.models import Property, HousingData, LLMUsage  # noqa: F401

# Create tables (including LLMUsage added for per-user quota tracking)
Base.metadata.create_all(bind=engine)
print("Database tables created successfully!")