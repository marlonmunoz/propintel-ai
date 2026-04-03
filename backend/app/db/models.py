from sqlalchemy import Column, Integer, JSON, String, Float, DateTime
from sqlalchemy.sql import func
from backend.app.db.database import Base

class Property(Base):
    __tablename__ = "properties"
    
    id = Column(Integer, primary_key=True, index=True)
    address = Column(String, nullable=False)
    zipcode = Column(String, nullable=False)
    bedrooms = Column(Integer, nullable=False)
    bathrooms = Column(Integer, nullable=False)
    sqft = Column(Integer, nullable=False)
    listing_price = Column(Float, nullable=False)
    analysis = Column(JSON, nullable=True)
    # Nullable so existing rows in Supabase are unaffected until the migration runs.
    # Run: ALTER TABLE properties ADD COLUMN created_at TIMESTAMPTZ DEFAULT now();
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    
    
class HousingData(Base):
    __tablename__ = "housing_data"
    
    id = Column(Integer, primary_key=True, index=True)
    
    borough = Column(String, nullable=False)
    neighborhood = Column(String, nullable=False)
    building_class = Column(String, nullable=False)
    
    year_built = Column(Integer, nullable=True)
    sales_price = Column(Float, nullable=True)
    
    gross_sqft = Column(Float, nullable=True)
    land_sqft = Column(Float, nullable=True)
    
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    postcode = Column(String, nullable=True)
    residential_units = Column(Float, nullable=True)
    total_units = Column(Float, nullable=True)
    
    