from contextlib import asynccontextmanager
from typing import Any
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from backend.app.core.error_handlers import (
    http_exception_handler,
    validation_exception_handler,
    internal_error_handler,
    rate_limit_exceeded_handler,
)
from fastapi import FastAPI, Request
from backend.app.api.prediction import router as prediction_router
from backend.app.api.properties import router as properties_router
from backend.app.api.auth_router import router as auth_router
from backend.app.api.admin import router as admin_router
from backend.app.api.geocode_usage import router as geocode_usage_router
from backend.app.api.contact import router as contact_router
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from backend.app.core.limiter import limiter
from backend.app.core.client_ip import get_client_ip
import json
import logging
import os
import re
import time
import uuid

import sentry_sdk
from dotenv import load_dotenv
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

load_dotenv()

# ---------------------------------------------------------------------------
# OpenAPI docs — disabled by default in production.
# Set DOCS_ENABLED=1 to expose /docs, /redoc, and /openapi.json.
# ---------------------------------------------------------------------------
_DOCS_ENABLED = os.getenv("DOCS_ENABLED", "0").strip() == "1"

# ---------------------------------------------------------------------------
# Logging — level controlled by LOG_LEVEL env var (default: INFO).
# ---------------------------------------------------------------------------
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "time": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.basicConfig(level=getattr(logging, _LOG_LEVEL, logging.INFO), handlers=[handler])
logger = logging.getLogger("propintel")

# ---------------------------------------------------------------------------
# Sentry — error tracking. Enabled only when SENTRY_DSN is set.
# Captures unhandled exceptions with full FastAPI request context.
# PII scrubbing: strips Authorization headers and redacts DATABASE_URL from
# any exception message/extra that might contain credentials.
# ---------------------------------------------------------------------------
_SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
if _SENTRY_DSN:
    _CREDENTIAL_RE = re.compile(
        r"(postgresql\+?[a-z2]*://)[^@]+@",
        re.IGNORECASE,
    )

    def _scrub_event(event: Any, hint: Any) -> Any:
        """Strip credentials from DB URLs and Authorization headers."""
        # Scrub request headers
        request = event.get("request", {})
        headers = request.get("headers", {})
        for key in list(headers):
            if key.lower() in ("authorization", "x-api-key", "cookie"):
                headers[key] = "[Filtered]"

        # Scrub DB credentials from exception values
        for exc_entry in event.get("exception", {}).get("values", []):
            val = exc_entry.get("value", "")
            if val:
                exc_entry["value"] = _CREDENTIAL_RE.sub(r"\1[Filtered]@", val)

        # Scrub any extra/breadcrumb data that may contain DATABASE_URL
        for key in ("extra", "contexts"):
            section = event.get(key, {})
            if isinstance(section, dict):
                for k, v in section.items():
                    if isinstance(v, str):
                        section[k] = _CREDENTIAL_RE.sub(r"\1[Filtered]@", v)

        return event

    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        environment=os.getenv("SENTRY_ENVIRONMENT", "production"),
        release=os.getenv("SENTRY_RELEASE", None),
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        send_default_pii=False,
        before_send=_scrub_event,
    )
    logger.info(
        "Sentry enabled | environment=%s",
        os.getenv("SENTRY_ENVIRONMENT", "production"),
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    from backend.app.core.auth import SUPABASE_URL, SUPABASE_JWT_SECRET, API_KEY

    if not SUPABASE_URL and not SUPABASE_JWT_SECRET:
        logger.warning(
            "AUTH CONFIG WARNING: Neither SUPABASE_URL nor SUPABASE_JWT_SECRET is set. "
            "JWT authentication will fail for all users. "
            "Set at least one of these in your environment."
        )
    elif not SUPABASE_URL:
        logger.info("Auth mode: HS256 (SUPABASE_JWT_SECRET set, SUPABASE_URL not set)")
    elif not SUPABASE_JWT_SECRET:
        logger.info("Auth mode: RS256/ES256 via JWKS (SUPABASE_URL set)")
    else:
        logger.info("Auth mode: HS256 + RS256/ES256 JWKS both configured")

    if not API_KEY:
        logger.warning(
            "AUTH CONFIG WARNING: API_KEY is not set. "
            "X-API-Key authentication is disabled."
        )

    # Log accepted CORS origins so misconfiguration is immediately visible in logs.
    _cors_default = "http://localhost:5174,http://127.0.0.1:5174"
    _origins = [
        o.strip()
        for o in os.getenv("CORS_ORIGINS", _cors_default).split(",")
        if o.strip()
    ]
    logger.info("CORS allowed origins: %s", _origins)

    yield


app = FastAPI(
    title="PropIntel AI",
    description="AI-powered real estate investment analysis platform",
    version="1.0.0",
    docs_url="/docs" if _DOCS_ENABLED else None,
    redoc_url="/redoc" if _DOCS_ENABLED else None,
    openapi_url="/openapi.json" if _DOCS_ENABLED else None,
    lifespan=lifespan,
)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.time()
        response = await call_next(request)
        duration_ms = int((time.time() - start) * 1000)
        logger.info(
            "%s %s | status=%s | duration=%dms | ip=%s | request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            get_client_ip(request),
            request_id,
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        return response




app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, internal_error_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Include both localhost and 127.0.0.1 — the browser treats them as different
# origins; Vite may use either, and the API URL may use the other.
_cors_default = "http://localhost:5174,http://127.0.0.1:5174"
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", _cors_default).split(",")
    if origin.strip()
]

# CORS_ORIGIN_REGEX allows a regex pattern to match dynamic preview domains.
# Default covers all Vercel preview deployments for this project.
# Set CORS_ORIGIN_REGEX="" in production to disable if not needed.
_cors_origin_regex = os.getenv(
    "CORS_ORIGIN_REGEX",
    r"https://propintel-.*\.vercel\.app",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=_cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    # Explicit header allowlist — wildcards are forbidden when allow_credentials=True.
    # sentry-trace / baggage: W3C / Sentry distributed tracing headers sent by the
    # browser automatically when Sentry is initialised on the frontend.
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "X-API-Key",
        "X-Request-ID",
        "sentry-trace",
        "baggage",
    ],
    # Expose X-Request-ID so the browser (and Sentry) can read it for correlation.
    expose_headers=["X-Request-ID"],
    max_age=600,
)

app.include_router(prediction_router)
app.include_router(properties_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(geocode_usage_router)
app.include_router(contact_router)

@app.get("/")
def root():
    return {"message": "PropIntel AI running 🚀"}

@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


@app.get("/ready", include_in_schema=False)
def ready():
    checks: dict = {}
    failed: list[str] = []

    # ── Database ──────────────────────────────────────────────────────────────
    try:
        from backend.app.db.database import SessionLocal
        import sqlalchemy
        db = SessionLocal()
        db.execute(sqlalchemy.text("SELECT 1"))
        db.close()
        checks["database"] = "reachable"
    except Exception as exc:
        # Log full detail internally; never expose connection strings externally.
        logger.error("Readiness DB check failed: %s", exc)
        checks["database"] = "unreachable"
        failed.append("database")

    # ── ML artifacts ─────────────────────────────────────────────────────────
    try:
        from backend.app.services.model_registry import ModelRegistry
        registry = ModelRegistry()
        missing = []
        for key, meta in registry._models.items():
            p = registry._resolve_artifact_path(meta.artifact_path)
            if not p.exists():
                missing.append(key)
        if missing:
            logger.error("Readiness ML check: missing models %s", missing)
            checks["ml_artifacts"] = f"missing models: {missing}"
            failed.append("ml_artifacts")
        else:
            checks["ml_artifacts"] = f"ok ({len(registry._models)} models found)"
    except Exception as exc:
        logger.error("Readiness ML check failed: %s", exc)
        checks["ml_artifacts"] = "error loading model registry"
        failed.append("ml_artifacts")

    if failed:
        logger.warning("Readiness check failed: %s | checks=%s", failed, checks)
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail={"status": "degraded", "failed": failed, "checks": checks},
        )

    return {"status": "ok", **checks}

