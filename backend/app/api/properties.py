from fastapi import APIRouter, Depends, HTTPException, Query, Request
from backend.app.core.limiter import limiter
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from backend.app.core.security import verify_api_key
from backend.app.db.database import get_db
from backend.app.db.models import Property, HousingData
from backend.app.schemas.property import (
    PropertyCreate, 
    PropertyResponse,
    PropertyUpdate
)

router = APIRouter()

# CRUD operations for Property model

# ================ POST /properties/ ================
@limiter.limit("60/minute")
@router.post("/properties/", response_model=PropertyResponse)
def create_property(
    request: Request,
    property: PropertyCreate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    db_property = Property(**property.model_dump()) # automatically maps fields

    db.add(db_property)
    

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(db_property)

    return db_property

# =============== GET /properties/ ================
@limiter.limit("60/minute")
@router.get("/properties/", response_model=List[PropertyResponse])
def get_properties(
    request: Request,
    zipcode: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    query = db.query(Property)

    if zipcode:
        query = query.filter(Property.zipcode == zipcode)

    if min_price:
        query = query.filter(Property.listing_price >= min_price)

    if max_price:
        query = query.filter(Property.listing_price <= max_price)

    properties = query.offset(skip).limit(limit).all()

    return properties

# =============== GET /properties/{property_id} ================
@limiter.limit("60/minute")
@router.get("/properties/{property_id}", response_model=PropertyResponse)
def get_property(
    request: Request,
    property_id: int, 
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    property_obj = db.query(Property).filter(Property.id == property_id).first()

    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")

    return property_obj



# ============== PATCH /properties/{property_id} ================
@limiter.limit("60/minute")
@router.patch("/properties/{property_id}", response_model=PropertyResponse)
def update_property(
    request: Request,
    property_id: int,
    property_update: PropertyUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    property_obj = db.query(Property).filter(Property.id == property_id).first()

    if not property_obj:
        raise HTTPException(status_code=404, detail="Property not found")

    update_data = property_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(property_obj, field, value)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(property_obj)

    return property_obj

# ============== DELETE /properties/{property_id} ================
@limiter.limit("60/minute")
@router.delete("/properties/{property_id}")
def delete_property(
    request: Request,
    property_id: int,
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    property_obj = db.query(Property).filter(Property.id == property_id).first()
    
    if not property_obj:
        raise HTTPException(
            status_code=404, 
            detail="Property not found",
        )
        
    db.delete(property_obj)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    
    return {"message": "Property deleted successfully"}


# ============== GET /housing/lookup ================
# Finds the nearest property in housing_data to the given coordinates.
# Called by the frontend after Mapbox resolves an address to lat/lng.
# We use Euclidean distance on lat/lng — accurate enough for within-borough
# lookups where we're comparing properties very close to each other.
# Borough filter ensures we don't accidentally match across water (e.g.,
# a Manhattan address matching a Brooklyn property across the East River).
@limiter.limit("60/minute")
@router.get("/housing/lookup")
def lookup_housing(
    request: Request,
    lat: float = Query(...),
    lng: float = Query(...),
    borough: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: str = Depends(verify_api_key),
):
    distance = func.sqrt(
        func.power(HousingData.latitude - lat, 2) +
        func.power(HousingData.longitude - lng, 2)
    )

    base_filter = [
        HousingData.latitude.isnot(None),
        HousingData.longitude.isnot(None),
    ]

    # Try with borough filter first (case-insensitive).
    # Falls back to proximity-only if no borough match is found —
    # this handles any borough format mismatch between Mapbox and our data.
    match = None
    if borough:
        match = (
            db.query(HousingData)
            .filter(*base_filter, func.lower(HousingData.borough) == borough.lower())
            .order_by(distance)
            .first()
        )

    if not match:
        match = (
            db.query(HousingData)
            .filter(*base_filter)
            .order_by(distance)
            .first()
        )

    if not match:
        raise HTTPException(status_code=404, detail="No nearby property found")

    return {
        "year_built":      match.year_built,
        "gross_sqft":      match.gross_sqft,
        "land_sqft":       match.land_sqft,
        "building_class":  match.building_class,
        "neighborhood":    match.neighborhood,
        "borough":         match.borough,
    }