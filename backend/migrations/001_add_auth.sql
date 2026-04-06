-- ============================================================================
-- PropIntel AI — Auth migration 001
-- Run this in your Supabase project's SQL Editor (Dashboard → SQL Editor).
-- ============================================================================

-- 1. Add user_id to the properties table
--    Links each saved analysis to the Supabase Auth user who created it.
--    NULL = legacy / service-created rows (safe default).
ALTER TABLE properties
  ADD COLUMN IF NOT EXISTS user_id TEXT;

CREATE INDEX IF NOT EXISTS idx_properties_user_id
  ON properties (user_id);


-- 2. Create the profiles table
--    Our app-level user profile, linked to Supabase's auth.users by UUID.
CREATE TABLE IF NOT EXISTS profiles (
  id               TEXT PRIMARY KEY,           -- Supabase auth.users.id (UUID as text)
  email            TEXT NOT NULL DEFAULT '',
  display_name     TEXT,
  role             TEXT NOT NULL DEFAULT 'user'
                     CHECK (role IN ('user', 'admin')),
  marketing_opt_in BOOLEAN NOT NULL DEFAULT false,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- 3. Promote yourself to admin
--    Replace <YOUR_SUPABASE_USER_UUID> with your actual UUID from:
--      Supabase Dashboard → Authentication → Users → (your row) → copy User UID
--
-- INSERT INTO profiles (id, email, display_name, role)
-- VALUES (
--   '<YOUR_SUPABASE_USER_UUID>',
--   '<your-email@example.com>',
--   'Marlon',
--   'admin'
-- )
-- ON CONFLICT (id) DO UPDATE SET role = 'admin';
