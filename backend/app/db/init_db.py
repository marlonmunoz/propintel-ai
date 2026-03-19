from backend.app.db.database import engine, Base
from backend.app.db.models import Property, HousingData

# Create tables
Base.metadata.create_all(bind=engine)
print("Database tables created successfully!")