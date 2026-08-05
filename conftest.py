"""
Root-level pytest configuration — loaded before any test file in the repo,
regardless of which directory or file pytest is invoked against.

Safety net: force every test onto a throwaway local SQLite file instead of
whatever DATABASE_URL is configured in .env (a real Supabase Postgres
instance for local development).

backend/app/db/database.py reads DATABASE_URL once, at import time, and
binds a module-level `engine` to it for the rest of the process. Several
individual test files also set this env var before their own imports as a
first line of defense, but that only protects a full suite run where one of
those files happens to be imported first. Running a single test file in
isolation (e.g. `pytest tests/test_billing_notifications.py` during local
development of a new test) bypasses that ordering — and once did: a test
file missing its own override wrote fake profile rows straight into
production. Setting it here, unconditionally, before collection touches any
test module anywhere in the repo, is the only place this guard is
bulletproof.
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
