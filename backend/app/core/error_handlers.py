import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("propintel")


def error_response(status_code: int, message: str, detail=None):
    return JSONResponse(
        status_code=status_code,
        content={
            "error": True,
            "status_code": status_code,
            "message": message,
            "detail": detail,
        },
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return error_response(
        status_code=exc.status_code,
        message=str(exc.detail),
    )

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return error_response(
        status_code=422,
        message="Validation error - check your request body",
        detail=exc.errors(),
    )

async def internal_error_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
    )
    return error_response(
        status_code=500,
        message="An unexpected error occurred. Please try again later.",
    )


async def rate_limit_exceeded_handler(request: Request, exc: Exception):
    return error_response(
        status_code=429,
        message="Too many requests. Please slow down and try again later.",
    )
    