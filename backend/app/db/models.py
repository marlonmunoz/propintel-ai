from sqlalchemy import Column, Integer, String, Float
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
    
    