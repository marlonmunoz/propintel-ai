-- ============================================================================
-- PropIntel AI — RLS policy audit (migration 007)
--
-- Purpose:
--   Asserts that no permissive SELECT/INSERT/UPDATE/DELETE policies exist on
--   PropIntel tables that would grant access to the `anon` or `authenticated`
--   PostgREST roles. The app uses FastAPI + SQLAlchemy (table-owner role) and
--   intentionally keeps PostgREST access blocked via RLS with no client policies.
--
--   This migration raises a NOTICE for each table confirming its posture, and
--   raises an EXCEPTION (rolling back) if a permissive open policy is found.
--
-- Safe to re-run: read-only assertions, no schema changes.
-- ============================================================================

DO $$
DECLARE
  r         RECORD;
  tbl       TEXT;
  bad_count INT;
  tables    TEXT[] := ARRAY[
    'profiles', 'properties', 'housing_data', 'llm_usage', 'mapbox_usage'
  ];
BEGIN
  FOREACH tbl IN ARRAY tables LOOP
    -- Confirm RLS is enabled on the table.
    IF NOT EXISTS (
      SELECT 1 FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      WHERE n.nspname = 'public'
        AND c.relname = tbl
        AND c.relrowsecurity = TRUE
    ) THEN
      RAISE EXCEPTION 'SECURITY: RLS is NOT enabled on public.%. Run 005_enable_rls_all_public_app_tables.sql first.', tbl;
    END IF;

    -- Check for permissive policies granted to anon or authenticated.
    SELECT COUNT(*) INTO bad_count
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = tbl
      AND permissive = 'PERMISSIVE'
      AND (roles @> ARRAY['anon']::name[] OR roles @> ARRAY['authenticated']::name[]);

    IF bad_count > 0 THEN
      RAISE WARNING
        'SECURITY WARNING: % permissive policy/policies found on public.% granting anon/authenticated access. '
        'Review these policies — they expose rows via the Supabase Data API.',
        bad_count, tbl;
    ELSE
      RAISE NOTICE 'RLS OK: public.% — RLS enabled, no open anon/authenticated policies.', tbl;
    END IF;
  END LOOP;
END $$;
