# PropIntel AI — SQL Migrations

All schema changes to the Postgres / Supabase database live here as numbered SQL files.

---

## File naming

```
NNN_short_description.sql
```

`NNN` is a zero-padded integer (001, 002, …). Files are applied in lexicographic order.

### When you must use the Supabase SQL Editor

If a migration (or any SQL snippet) **must** be pasted and run manually in **Supabase Dashboard → SQL Editor** — for example one-off data fixes, rollbacks, or templates where you substitute your own UUID — the file begins with a header line:

```text
-- MANUAL_SUPABASE: <short reason>
```

Migrations without that line are intended to run only via **`python -m backend.scripts.run_migrations`** (or Docker on boot) against `DATABASE_URL`. If you add a manual-only script, include the header so operators know not to rely on the runner alone.

### Current migration history

| File | Purpose |
|---|---|
| `001_add_auth.sql` | Add `user_id` to `properties`; create `profiles` table |
| `002_promote_admin.sql` | **`MANUAL_SUPABASE`** — replace `YOUR_SUPABASE_USER_UUID`, then run in SQL Editor (not applied meaningfully by the runner) |
| `003_mapbox_usage.sql` | Create `mapbox_usage` table |
| `004_mapbox_usage_rls.sql` | Enable RLS on `mapbox_usage` |
| `005_enable_rls_all_public_app_tables.sql` | Enable RLS on all app tables |
| `006_add_paid_role.sql` | Expand `profiles.role` CHECK constraint to allow `'paid'` |
| `007_rls_verify_no_public_policies.sql` | Read-only audit: RLS must be ON; warns if permissive `anon` / `authenticated` policies exist on app tables |

---

## Running migrations

### Option A — migration runner (recommended for Postgres / Supabase)

The runner tracks applied migrations in a `schema_migrations` table and skips files that have already been applied (idempotent).

```bash
# Preview what would run (safe — no DB changes):
python -m backend.scripts.run_migrations --dry-run

# Apply all pending migrations:
python -m backend.scripts.run_migrations
```

Requires `DATABASE_URL` to be set (your `.env` file is loaded automatically).

> **Note:** `002_promote_admin.sql` is marked **`MANUAL_SUPABASE`** — replace `YOUR_SUPABASE_USER_UUID` and run in the SQL Editor. For API admin access without editing SQL, set **`ADMIN_USER_IDS`** in the API environment instead.

### Option B — Supabase SQL Editor (manual)

Paste and run each file in order in **Supabase Dashboard → SQL Editor** if you are not using the migration runner. Prefer the runner when possible. Files marked **`MANUAL_SUPABASE`** in the header (e.g. `002_promote_admin.sql`) are meant for the editor after you edit placeholders — do not expect them to do anything useful via the runner until customized.

### CI / SQLite

The GitHub Actions CI workflow uses SQLite and initialises the schema via:
```bash
python -m backend.app.db.init_db
```
SQLAlchemy `CREATE TABLE IF NOT EXISTS` handles the full schema for tests. SQL migrations are Postgres-only and do **not** run in CI.

---

## Adding a new migration

1. Create the next numbered file: `008_my_change.sql` (increment from the highest existing `NNN_*.sql`)
2. Write idempotent SQL (`IF NOT EXISTS`, `IF EXISTS`, `ON CONFLICT DO NOTHING`, etc.)
3. Test locally with `--dry-run` first, then apply
4. Commit the file — the runner will pick it up on the next deploy

---

## Rolling back

There is no automated rollback. Write a companion `008_rollback_my_change.sql` if a manual rollback is needed, apply it via the SQL Editor, and then remove or skip the original file from future runs.
