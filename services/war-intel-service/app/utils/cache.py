"""TTL cache utility with pluggable backend (memory or Redis).

Backend is selected via CACHE_BACKEND env var:
  - "memory" (default): in-process dict, single-worker only
  - "redis": shared across workers via Redis SETEX
"""

import json
import logging
import os
import time
from decimal import Decimal
from typing import Any, Dict, Optional, Tuple

from eve_shared.metrics import cache_operations_total

logger = logging.getLogger(__name__)

CACHE_BACKEND = os.getenv("CACHE_BACKEND", "memory")
_REDIS_PREFIX = "war-intel:"
SERVICE_NAME = "war-intel"


class _DecimalEncoder(json.JSONEncoder):
    """Handle Decimal values from psycopg2 query results."""
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super().default(o)

# ── In-memory backend ────────────────────────────────────────────────────────

_cache: Dict[str, Tuple[float, Any]] = {}


def _mem_get(key: str, ttl_seconds: int) -> Optional[Any]:
    if key in _cache:
        ts, data = _cache[key]
        if time.time() - ts < ttl_seconds:
            return data
        del _cache[key]
    return None


def _mem_set(key: str, data: Any, ttl_seconds: int) -> None:
    _cache[key] = (time.time(), data)


def _mem_clear(prefix: Optional[str]) -> None:
    if prefix is None:
        _cache.clear()
    else:
        keys_to_delete = [k for k in _cache if k.startswith(prefix)]
        for k in keys_to_delete:
            del _cache[k]


# ── Redis backend ────────────────────────────────────────────────────────────

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        import redis
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis_client = redis.from_url(url, decode_responses=True)
        logger.info(f"Redis cache connected: {url}")
    return _redis_client


def _redis_get(key: str, ttl_seconds: int) -> Optional[Any]:
    try:
        raw = _get_redis().get(f"{_REDIS_PREFIX}{key}")
        if raw is not None:
            return json.loads(raw)
    except Exception:
        logger.warning(f"Redis GET failed for {key}, falling back to None", exc_info=True)
    return None


def _redis_set(key: str, data: Any, ttl_seconds: int) -> None:
    try:
        _get_redis().setex(f"{_REDIS_PREFIX}{key}", ttl_seconds, json.dumps(data, cls=_DecimalEncoder))
    except Exception:
        logger.warning(f"Redis SET failed for {key}", exc_info=True)


def _redis_clear(prefix: Optional[str]) -> None:
    try:
        r = _get_redis()
        if prefix is None:
            pattern = f"{_REDIS_PREFIX}*"
        else:
            pattern = f"{_REDIS_PREFIX}{prefix}*"
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor, match=pattern, count=200)
            if keys:
                r.delete(*keys)
            if cursor == 0:
                break
    except Exception:
        logger.warning(f"Redis CLEAR failed for prefix={prefix}", exc_info=True)


# ── Public API (backend-agnostic) ────────────────────────────────────────────

if CACHE_BACKEND == "redis":
    _backend_get = _redis_get
    _backend_set = _redis_set
    _backend_clear = _redis_clear
    logger.info("Cache backend: redis")
else:
    _backend_get = _mem_get
    _backend_set = _mem_set
    _backend_clear = _mem_clear


def get_cached(key: str, ttl_seconds: int = 300) -> Optional[Any]:
    """Return cached data if still valid, else None."""
    result = _backend_get(key, ttl_seconds)
    if result is not None:
        cache_operations_total.labels(service=SERVICE_NAME, operation="get", result="hit").inc()
    else:
        cache_operations_total.labels(service=SERVICE_NAME, operation="get", result="miss").inc()
    return result


def set_cached(key: str, data: Any, ttl_seconds: int = 300) -> None:
    """Cache data with TTL.

    Args:
        key: Cache key (use service-specific prefixes like 'corp-offensive:')
        data: Data to cache (must be JSON-serializable)
        ttl_seconds: Time-to-live in seconds (default: 300 = 5 minutes)
    """
    _backend_set(key, data, ttl_seconds)
    cache_operations_total.labels(service=SERVICE_NAME, operation="set", result="ok").inc()


def clear_cache(prefix: Optional[str] = None) -> None:
    """Clear cache entries, optionally filtered by key prefix."""
    _backend_clear(prefix)
