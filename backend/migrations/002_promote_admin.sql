-- MANUAL_SUPABASE: edit YOUR_SUPABASE_USER_UUID then run in Dashboard → SQL Editor (do not rely on migration runner for promotion)
-- ============================================================================
-- Promote your account to admin
-- ============================================================================
-- Admins see every row in `properties` (including legacy saves with user_id NULL).
-- Replace YOUR_SUPABASE_USER_UUID with your id from:
--   Supabase → Authentication → Users → User UID
--   or  public.profiles → id
--
-- Run in Supabase → SQL Editor.

UPDATE public.profiles
SET role = 'admin'
WHERE id = 'YOUR_SUPABASE_USER_UUID';

-- If admin still does not apply in the API, check:
-- 1) The id above must match JWT `sub` (see jwt.io / browser devtools → access token payload).
-- 2) Row Level Security: the FastAPI server uses a direct Postgres connection that
--    normally bypasses RLS. If you added strict policies, ensure SELECT on public.profiles
--    is allowed for that connection, or temporarily disable RLS on `profiles` for debugging.
