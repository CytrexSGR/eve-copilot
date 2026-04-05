"""Global exception handler for FastAPI services."""
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on a FastAPI app.

    Catches unhandled exceptions and returns structured JSON instead
    of raw 500 errors. Does NOT interfere with HTTPException (FastAPI
    handles those natively).
    """

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        logger.error(f"ValueError on {request.url.path}: {exc}")
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(KeyError)
    async def key_error_handler(request: Request, exc: KeyError):
        logger.error(f"KeyError on {request.url.path}: {exc}")
        return JSONResponse(status_code=400, content={"detail": f"Missing required field: {str(exc)}"})

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled error on {request.url.path}: {exc}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
