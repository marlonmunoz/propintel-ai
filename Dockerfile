FROM python:3.11-slim

WORKDIR /app

# Install git + git-lfs to resolve LFS pointer files (*.pkl, *.parquet) that
# are baked into the build context by Railway's repo checkout.  Both packages
# are removed after the pull step so the production image stays lean.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git git-lfs \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-api.txt .

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements-api.txt

COPY . .

# Resolve LFS pointer files → real binary content, then strip git metadata
# and tooling from the final image.
RUN git lfs install --local \
    && git lfs pull \
    && rm -rf .git \
    && apt-get purge -y --auto-remove git git-lfs \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONPATH=/app

EXPOSE 8000

# The API uses SQL migrations for Postgres environments (Supabase/Railway).
# They are idempotent (tracked in schema_migrations). Set RUN_MIGRATIONS=0 to skip.
# Use && so migration failure does not start uvicorn; exec for clean signals.
CMD ["sh", "-c", "if [ \"${RUN_MIGRATIONS:-1}\" = \"1\" ]; then python -m backend.scripts.run_migrations; fi && exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

