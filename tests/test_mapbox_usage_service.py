import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.database import Base
from backend.app.db.models import MapboxUsage  # noqa: F401
from backend.app.services.mapbox_usage import increment_mapbox_geocode_requests


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session(), engine


def test_increment_mapbox_creates_first_row():
    db, engine = _session()
    try:
        increment_mapbox_geocode_requests(db, "user-1")
        row = db.query(MapboxUsage).filter_by(user_id="user-1").first()
        assert row is not None
        assert row.call_count == 1
    finally:
        db.close()
        engine.dispose()


def test_increment_mapbox_updates_existing_row():
    db, engine = _session()
    try:
        increment_mapbox_geocode_requests(db, "user-2")
        increment_mapbox_geocode_requests(db, "user-2")
        row = db.query(MapboxUsage).filter_by(user_id="user-2").first()
        assert row is not None
        assert row.call_count == 2
    finally:
        db.close()
        engine.dispose()

