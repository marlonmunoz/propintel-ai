from backend.app.db.database import engine, Base
from backend.app.models.property import Property

# Create tables
Base.metadata.create_all(bind=engine)
print("Database tables created successfully!")