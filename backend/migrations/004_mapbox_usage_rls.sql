-- ============================================================================
-- PropIntel AI — Mapbox usage RLS (migration 004)
-- Run once in Supabase SQL Editor after 003_mapbox_usage.sql.
--
-- Supabase Database Linter (0013_rls_disabled_in_public) requires RLS on
-- every public table exposed to PostgREST. This table is only accessed by
-- the FastAPI app via DATABASE_URL (table owner bypasses RLS). Enabling RLS
-- with no policies blocks anon/authenticated from reading or writing rows
-- through the Data API, which is the intended security posture.
-- ============================================================================

ALTER TABLE public.mapbox_usage ENABLE ROW LEVEL SECURITY;

-- Optional: document that no client policies are required.
COMMENT ON TABLE public.mapbox_usage IS
  'Per-user daily Mapbox geocode counters; backend-only via SQLAlchemy. RLS on, no PostgREST policies.';
