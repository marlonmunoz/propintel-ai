from backend.app.db.database import engine, Base
from backend.app.db.models import Property, HousingData, LLMUsage, MapboxUsage  # noqa: F401

# Create tables (LLMUsage / MapboxUsage for per-user usage tracking)
Base.metadata.create_all(bind=engine)
print("Database tables created successfully!")