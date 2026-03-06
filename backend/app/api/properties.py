from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.models.property import Property
from backend.app.schemas.property import PropertyCreate

router = APIRouter()

@router.post("/properties/")
def create_property(property: PropertyCreate, db: Session = Depends(get_db)):
    db_property = Property(
        address=property.address,
        zipcode=property.zipcode,
        bedrooms=property.bedrooms,
        bathrooms=property.bathrooms,
        sqft=property.sqft,
        listing_price=property.listing_price
    )
    db.add(db_property)
    db.commit()
    db.refresh(db_property)
    return db_property

@router.get("/properties/")
def get_properties(db: Session = Depends(get_db)):
    properties = db.query(Property).all()
    return properties

@router.get("/properties/{property_id}")
def get_property(property_id: int, db: Session = Depends(get_db)):
    property = db.query(Property).all()
    return property 