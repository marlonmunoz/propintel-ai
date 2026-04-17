-- ============================================================================
-- PropIntel AI — Enable RLS on all application tables (migration 005)
-- Run once in Supabase SQL Editor (Dashboard → SQL).
--
-- Satisfies Supabase Database Linter 0013 (rls_disabled_in_public) for every
-- PropIntel-managed table in public.
--
-- Security model:
--   - The React app does NOT use supabase-js against these tables; it calls
--     FastAPI only. PostgREST therefore must not expose rows to anon/auth.
--   - RLS ON with zero policies denies anon/authenticated via the Data API.
--   - FastAPI + SQLAlchemy uses your DATABASE_URL role (typically the table
--     owner, e.g. postgres), which bypasses RLS in PostgreSQL unless the table
--     uses FORCE ROW LEVEL SECURITY (we do not).
--
-- Safe to re-run: ENABLE ROW LEVEL SECURITY is idempotent.
-- ============================================================================

DO $$
DECLARE
  r RECORD;
BEGIN
  FOR r IN
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
      AND tablename IN (
        'profiles',
        'properties',
        'housing_data',
        'llm_usage',
        'mapbox_usage'
      )
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', r.tablename);
    RAISE NOTICE 'RLS enabled on public.%', r.tablename;
  END LOOP;
END $$;
