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
