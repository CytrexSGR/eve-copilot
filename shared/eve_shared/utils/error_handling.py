"""Shared error handling decorators for FastAPI endpoints."""
import asyncio
import logging
from functools import wraps
from typing import Callable, Any

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def _handle_exception(func_name: str, e: Exception, default_status: int, log_errors: bool):
    """Shared exception handling logic for sync and async wrappers."""
    if isinstance(e, HTTPException):
        raise
    if isinstance(e, ValueError):
        if log_errors:
            logger.error(f"Validation error in {func_name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    if isinstance(e, KeyError):
        if log_errors:
            logger.error(f"Missing data in {func_name}: {e}")
        raise HTTPException(status_code=400, detail=f"Missing required field: {str(e)}")
    if log_errors:
        logger.exception(f"Unexpected error in {func_name}: {e}")
    raise HTTPException(status_code=default_status, detail=f"Internal server error: {str(e)}")


def handle_endpoint_errors(
    default_status: int = 500,
    log_errors: bool = True
) -> Callable:
    """Decorator to handle common endpoint errors.

    Works with both async and sync endpoint functions.

    Catches:
        HTTPException: Re-raised as-is
        ValueError: Converted to HTTP 400
        KeyError: Converted to HTTP 400
        Exception: Converted to HTTP 500 (or default_status)
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    _handle_exception(func.__name__, e, default_status, log_errors)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    _handle_exception(func.__name__, e, default_status, log_errors)
            return sync_wrapper
    return decorator


# Alias for backward compatibility with market-service
handle_errors = handle_endpoint_errors
