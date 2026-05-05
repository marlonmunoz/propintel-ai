FROM python:3.11-slim

WORKDIR /app

COPY requirements-api.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements-api.txt

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8000

# The API uses SQL migrations for Postgres environments (Supabase/Railway).
# They are idempotent (tracked in schema_migrations). Set RUN_MIGRATIONS=0 to skip.
# Use && so migration failure does not start uvicorn; exec for clean signals.
CMD ["sh", "-c", "if [ \"${RUN_MIGRATIONS:-1}\" = \"1\" ]; then python -m backend.scripts.run_migrations; fi && exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

