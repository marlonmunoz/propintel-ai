import os
from sqlalchemy import create_engine

from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in the environment")

# Pool settings — tunable via env vars without redeploy.
# Defaults (pool_size=5, max_overflow=10) are fine for low-concurrency; raise
# DB_POOL_SIZE / DB_MAX_OVERFLOW for heavier traffic on Railway paid plans.
_pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
_max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_size=_pool_size,
    max_overflow=_max_overflow,
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

# Base class for models
Base = declarative_base()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        


