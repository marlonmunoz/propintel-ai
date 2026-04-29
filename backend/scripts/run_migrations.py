"""
PropIntel AI — SQL migration runner.

Applies numbered SQL migration files in order against the Postgres database
configured via DATABASE_URL. Already-applied migrations are skipped; the
`schema_migrations` table (created on first run) acts as the audit log.

Usage
-----
    # Apply all pending migrations:
    python -m backend.scripts.run_migrations

    # Preview what would run without touching the database:
    python -m backend.scripts.run_migrations --dry-run

    # Point at a specific DB (overrides DATABASE_URL env var):
    DATABASE_URL="postgresql+psycopg://..." python -m backend.scripts.run_migrations

How migrations are discovered
------------------------------
All *.sql files under backend/migrations/ are sorted lexicographically by
filename. The convention is a numeric prefix:
    001_add_auth.sql
    002_promote_admin.sql
    ...
    006_add_paid_role.sql

Each file is executed as a single psycopg transaction (autocommit=False).
If execution fails the transaction is rolled back and the runner exits with a
non-zero code so CI/CD pipelines can catch it.

Notes
------
- The runner is Postgres-only. The CI SQLite environment initialises the schema
  via `python -m backend.app.db.init_db` (SQLAlchemy CREATE TABLE IF NOT EXISTS)
  and does not need migrations.
- Files are safe to re-run in Supabase's SQL Editor as well — every migration
  uses IF NOT EXISTS / IF EXISTS / ON CONFLICT guards where appropriate.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "backend" / "migrations"

# DDL run once to bootstrap the tracking table (Postgres-safe; idempotent).
_BOOTSTRAP_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    id           SERIAL PRIMARY KEY,
    filename     TEXT NOT NULL UNIQUE,
    applied_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        sys.exit(
            "ERROR: DATABASE_URL is not set. "
            "Export it or add it to your .env file before running migrations."
        )
    # psycopg (v3) uses postgresql+psycopg://; psycopg2 uses postgresql://.
    # Strip the SQLAlchemy dialect prefix so we can pass the raw DSN to psycopg.
    for prefix in ("postgresql+psycopg://", "postgresql+psycopg2://"):
        if url.startswith(prefix):
            return "postgresql://" + url[len(prefix):]
    return url


def _sorted_migration_files() -> list[Path]:
    """Return all *.sql files in MIGRATIONS_DIR sorted by filename."""
    files = sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda p: p.name)
    return files


def _already_applied(cur, filename: str) -> bool:
    cur.execute(
        "SELECT 1 FROM schema_migrations WHERE filename = %s",
        (filename,),
    )
    return cur.fetchone() is not None


def _mark_applied(cur, filename: str) -> None:
    cur.execute(
        "INSERT INTO schema_migrations (filename) VALUES (%s) ON CONFLICT DO NOTHING",
        (filename,),
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def run(dry_run: bool = False) -> None:
    try:
        import psycopg  # type: ignore[import]
    except ImportError:
        sys.exit(
            "ERROR: psycopg (v3) is not installed. "
            "Run `pip install psycopg` or `pip install -r requirements.txt`."
        )

    dsn = _get_database_url()
    migration_files = _sorted_migration_files()

    if not migration_files:
        print(f"No migration files found in {MIGRATIONS_DIR}")
        return

    print(f"Connecting to database …")
    if dry_run:
        print("DRY RUN — no changes will be written.\n")

    with psycopg.connect(dsn) as conn:
        conn.autocommit = False

        # Bootstrap tracking table (safe to run every time).
        with conn.cursor() as cur:
            if not dry_run:
                cur.execute(_BOOTSTRAP_DDL)
                conn.commit()

        pending: list[Path] = []
        applied_count = 0

        with conn.cursor() as cur:
            for path in migration_files:
                if dry_run:
                    # In dry-run mode we can't read the tracking table reliably
                    # (it might not exist yet), so just list files.
                    pending.append(path)
                    continue
                if _already_applied(cur, path.name):
                    print(f"  [skip]    {path.name}")
                    applied_count += 1
                else:
                    pending.append(path)

        if not pending:
            print(f"\nAll {applied_count} migration(s) already applied. Database is up to date.")
            return

        print(f"\n{len(pending)} pending migration(s):")
        for p in pending:
            print(f"  {p.name}")

        if dry_run:
            print("\nDry run complete. Run without --dry-run to apply.")
            return

        print()
        for path in pending:
            sql = path.read_text(encoding="utf-8")
            print(f"  Applying {path.name} …", end=" ", flush=True)
            try:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    _mark_applied(cur, path.name)
                conn.commit()
                print("OK")
            except Exception as exc:
                conn.rollback()
                print(f"FAILED\n\nERROR applying {path.name}:\n{exc}")
                sys.exit(1)

        print(f"\n{len(pending)} migration(s) applied successfully.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply pending PropIntel SQL migrations to the configured database.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List pending migrations without applying them.",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
