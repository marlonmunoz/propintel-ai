from contextlib import asynccontextmanager
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
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from backend.app.core.limiter import limiter
from backend.app.core.client_ip import get_client_ip
import json
import os
import time
import uuid
import logging
from dotenv import load_dotenv

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
# ---------------------------------------------------------------------------
_SENTRY_DSN = os.getenv("SENTRY_DSN", "").strip()
if _SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration
    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        send_default_pii=False,
    )
    logger.info("Sentry enabled (DSN configured)")


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
)

app.include_router(prediction_router)
app.include_router(properties_router)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(geocode_usage_router)

@app.get("/")
def root():
    return {"message": "PropIntel AI running 🚀"}

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
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
        checks["database"] = f"unreachable: {exc}"
        failed.append("database")

    # ── ML artifacts ─────────────────────────────────────────────────────────
    try:
        from backend.app.services.model_registry import ModelRegistry
        registry = ModelRegistry()
        metadata_dir = registry.metadata_dir
        artifact_root = registry.artifact_root
        missing = []
        for key, meta in registry._models.items():
            p = registry._resolve_artifact_path(meta.artifact_path)
            if not p.exists():
                missing.append(key)
        if missing:
            checks["ml_artifacts"] = f"missing models: {missing}"
            failed.append("ml_artifacts")
        else:
            checks["ml_artifacts"] = f"ok ({len(registry._models)} models found)"
    except Exception as exc:
        checks["ml_artifacts"] = f"error: {exc}"
        failed.append("ml_artifacts")

    if failed:
        logger.warning("Readiness check failed: %s | checks=%s", failed, checks)
        from fastapi import HTTPException
        raise HTTPException(
            status_code=503,
            detail={"status": "degraded", "failed": failed, "checks": checks},
        )

    return {"status": "ok", **checks}

