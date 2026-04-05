"""Shared Redis connection singleton for api-gateway middleware.

Provides a single lazy-initialized Redis connection used by both
FeatureGateMiddleware and RateLimitMiddleware. The connection is
created on first use (not at import time) so tests that don't need
Redis are unaffected.
"""
import logging

from app.middleware.tier_config import REDIS_HOST, REDIS_PORT, REDIS_PASSWORD

logger = logging.getLogger(__name__)

_redis_instance = None
_redis_init_attempted = False


def get_redis():
    """Return a shared Redis connection, or None if unavailable.

    Lazy: connects on first call, not at import time.
    After a failed connection attempt, returns None immediately
    on subsequent calls (no retry storm).
    """
    global _redis_instance, _redis_init_attempted

    if _redis_instance is not None:
        return _redis_instance

    if _redis_init_attempted:
        return None

    _redis_init_attempted = True
    try:
        import redis

        conn = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD or None,
            decode_responses=True,
        )
        conn.ping()
        _redis_instance = conn
        logger.info(f"Redis connected: {REDIS_HOST}:{REDIS_PORT}")
    except Exception as e:
        logger.debug(f"Redis unavailable: {e}")
        _redis_instance = None

    return _redis_instance


def reset_redis():
    """Reset the singleton (for testing only)."""
    global _redis_instance, _redis_init_attempted
    _redis_instance = None
    _redis_init_attempted = False
