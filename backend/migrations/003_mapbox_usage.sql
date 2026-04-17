-- ============================================================================
-- PropIntel AI — Mapbox geocode usage migration 003
-- Run once in Supabase SQL Editor (or any Postgres used by the API).
-- Table name: mapbox_usage (tracks in-app autocomplete counts, not Mapbox billing).
-- ============================================================================

CREATE TABLE IF NOT EXISTS mapbox_usage (
  id           SERIAL PRIMARY KEY,
  user_id      TEXT NOT NULL,
  period_date  VARCHAR(10) NOT NULL,
  call_count   INTEGER NOT NULL DEFAULT 0,
  CONSTRAINT uq_mapbox_usage_user_date UNIQUE (user_id, period_date)
);

CREATE INDEX IF NOT EXISTS idx_mapbox_usage_user_id
  ON mapbox_usage (user_id);

CREATE INDEX IF NOT EXISTS idx_mapbox_usage_period_date
  ON mapbox_usage (period_date);

-- Supabase linter 0013: public tables must have RLS enabled for PostgREST.
-- Backend uses the DB owner connection and bypasses RLS; no policies needed.
ALTER TABLE public.mapbox_usage ENABLE ROW LEVEL SECURITY;
