import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("propintel")


def _request_id(request: Request) -> str | None:
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


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
        request_id=_request_id(request),
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return error_response(
        status_code=422,
        message="Validation error - check your request body",
        detail=exc.errors(),
        request_id=_request_id(request),
    )

async def internal_error_handler(request: Request, exc: Exception):
    rid = _request_id(request)
    logger.exception(
        "Unhandled exception on %s %s | request_id=%s",
        request.method,
        request.url.path,
        rid,
    )
    return error_response(
        status_code=500,
        message="An unexpected error occurred. Please try again later.",
        request_id=rid,
    )


async def rate_limit_exceeded_handler(request: Request, exc: Exception):
    return error_response(
        status_code=429,
        message="Too many requests. Please slow down and try again later.",
        request_id=_request_id(request),
    )
