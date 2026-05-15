from backend.app.db.database import engine, Base
from backend.app.db.models import (  # noqa: F401
    Property,
    HousingData,
    LLMUsage,
    MapboxUsage,
    BillingCustomer,
    BillingEvent,
)

# Create tables (LLMUsage / MapboxUsage for per-user usage tracking)
Base.metadata.create_all(bind=engine)
print("Database tables created successfully!")