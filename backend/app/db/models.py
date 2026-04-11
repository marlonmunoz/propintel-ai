from sqlalchemy import Boolean, Column, Integer, JSON, String, Float, DateTime, Text, UniqueConstraint
from sqlalchemy.sql import func
from backend.app.db.database import Base


class Profile(Base):
    """
    Application profile linked to a Supabase Auth user.

    Created automatically on first authenticated API call (GET /auth/me).
    `id` is the Supabase Auth UUID (auth.users.id), stored as TEXT so SQLite
    (used in tests) and Postgres are both happy.
    """
    __tablename__ = "profiles"

    id = Column(Text, primary_key=True, index=True)        # Supabase auth UUID
    email = Column(String, nullable=False, default="")
    display_name = Column(String, nullable=True)
    role = Column(String, nullable=False, default="user")  # "user" | "admin"
    marketing_opt_in = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)


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
    # Run: ALTER TABLE properties ADD COLUMN user_id TEXT;
    # Links each row to a Supabase Auth user. NULL = legacy / service-created row.
    user_id = Column(Text, nullable=True, index=True)
    
    
class LLMUsage(Base):
    """
    Per-user daily LLM explanation call counter.

    One row per (user_id, period_date).  call_count is incremented before each
    OpenAI call so quota is enforced without race conditions at low scale.

    user_id  — Supabase Auth UUID for JWT callers; "api_key:service" for
               X-API-Key callers (they are exempt from quota checks).
    period_date — ISO-8601 date string (YYYY-MM-DD); resets daily naturally.

    Postgres migration (run once on existing deployments):
        CREATE TABLE IF NOT EXISTS llm_usage (
            id          SERIAL PRIMARY KEY,
            user_id     TEXT NOT NULL,
            period_date VARCHAR(10) NOT NULL,
            call_count  INTEGER NOT NULL DEFAULT 0,
            CONSTRAINT  uq_llm_usage_user_date UNIQUE (user_id, period_date)
        );
    """
    __tablename__ = "llm_usage"
    __table_args__ = (
        UniqueConstraint("user_id", "period_date", name="uq_llm_usage_user_date"),
    )

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Text, nullable=False, index=True)
    period_date = Column(String(10), nullable=False)   # YYYY-MM-DD
    call_count  = Column(Integer, nullable=False, default=0)


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
    
    