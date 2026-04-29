-- ============================================================================
-- PropIntel AI — Auth migration 002 (add paid role)
-- Run this in your Supabase project's SQL Editor (Dashboard → SQL Editor).
--
-- Purpose:
--   The application supports three roles: 'user', 'paid', 'admin'.
--   Migration 001 created profiles.role with a CHECK constraint allowing only
--   ('user', 'admin'). This migration expands the allowed set to include 'paid'.
--
-- Notes:
--   - Supabase/Postgres auto-names the CHECK constraint unless explicitly named.
--   - We therefore (1) drop any CHECK constraints on profiles.role, then
--     (2) add a new named constraint with the correct allowed values.
-- ============================================================================

DO $$
DECLARE
  r record;
BEGIN
  -- Drop any existing CHECK constraints that constrain profiles.role.
  FOR r IN (
    SELECT con.conname
    FROM pg_constraint con
    JOIN pg_class rel
      ON rel.oid = con.conrelid
    JOIN pg_attribute att
      ON att.attrelid = rel.oid
     AND att.attnum = ANY (con.conkey)
    WHERE rel.relname = 'profiles'
      AND con.contype = 'c'
      AND att.attname = 'role'
  )
  LOOP
    EXECUTE format('ALTER TABLE profiles DROP CONSTRAINT IF EXISTS %I', r.conname);
  END LOOP;

  -- Add the updated constraint.
  ALTER TABLE profiles
    ADD CONSTRAINT profiles_role_check
    CHECK (role IN ('user', 'paid', 'admin'));
END $$;

