import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.websockets import WebSocket

logger = logging.getLogger("propintel")

# Starlette registers the same handler for HTTP and WebSocket; stubs expect
# (Request | WebSocket, Exception). We only emit JSON for HTTP Request.
RequestOrWs = Request | WebSocket


def _request_id(request: RequestOrWs) -> str | None:
    return getattr(request.state, "request_id", None)


def error_response(status_code: int, message: str, detail=None, request_id: str | None = None):
    content: dict = {
        "error": True,
        "status_code": status_code,
        "message": message,
        "detail": detail,
    }
    if request_id:
        content["request_id"] = request_id
    return JSONResponse(status_code=status_code, content=content)


async def http_exception_handler(request: RequestOrWs, exc: Exception):
    if not isinstance(request, Request):
        raise exc
    if not isinstance(exc, StarletteHTTPException):
        raise exc
    return error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        request_id=_request_id(request),
    )


def _safe_validation_errors(errors: list) -> list:
    """
    Pydantic v2 ``@field_validator`` puts the raw ``ValueError`` into
    ``ctx['error']``, which is not JSON-serialisable.  Walk the error list
    and stringify any exception values so ``JSONResponse`` can encode them.
    """
    result = []
    for error in errors:
        safe: dict = {}
        for key, val in error.items():
            if key == "url":
                continue  # strip pydantic doc URLs from API responses
            if key == "ctx" and isinstance(val, dict):
                safe["ctx"] = {
                    ck: str(cv) if isinstance(cv, Exception) else cv
                    for ck, cv in val.items()
                }
            else:
                safe[key] = val
        result.append(safe)
    return result


async def validation_exception_handler(request: RequestOrWs, exc: Exception):
    if not isinstance(request, Request):
        raise exc
    if not isinstance(exc, RequestValidationError):
        raise exc
    return error_response(
        status_code=422,
        message="Validation error - check your request body",
        detail=_safe_validation_errors(exc.errors()),
        request_id=_request_id(request),
    )


async def internal_error_handler(request: RequestOrWs, exc: Exception):
    rid = _request_id(request)
    if isinstance(request, Request):
        logger.exception(
            "Unhandled exception on %s %s | request_id=%s",
            request.method,
            request.url.path,
            rid,
        )
    else:
        logger.exception("Unhandled exception on WebSocket | request_id=%s", rid)
    return error_response(
        status_code=500,
        message="An unexpected error occurred. Please try again later.",
        request_id=rid,
    )


async def rate_limit_exceeded_handler(request: RequestOrWs, exc: Exception):
    if not isinstance(request, Request):
        raise exc
    return error_response(
        status_code=429,
        message="Too many requests. Please slow down and try again later.",
        request_id=_request_id(request),
    )
