"""Shared ESI rate limit state via Redis for cross-service coordination."""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

REDIS_KEY_ERROR_REMAIN = "esi:error_limit_remain"
REDIS_KEY_ERROR_RESET = "esi:error_limit_reset"
REDIS_KEY_GLOBAL_BAN = "esi:global_ban"

ERROR_LIMIT_THRESHOLD = 30  # Throttle below this
HARD_STOP_THRESHOLD = 10    # Block ALL requests below this


class SharedRateState:
    """Cross-service ESI error budget tracking via Redis."""

    def __init__(self):
        self._redis = None
        self._local_error_remain = 100

    @property
    def redis(self):
        if self._redis is None:
            try:
                from eve_shared import get_redis
                self._redis = get_redis().client
            except Exception:
                logger.debug("Redis unavailable for shared rate state")
        return self._redis

    def update_from_headers(self, headers: dict) -> None:
        """Update shared state from ESI response headers."""
        error_remain = headers.get("X-ESI-Error-Limit-Remain")
        error_reset = headers.get("X-ESI-Error-Limit-Reset")

        if error_remain is not None:
            self._local_error_remain = int(error_remain)
            if self.redis:
                try:
                    self.redis.set(REDIS_KEY_ERROR_REMAIN, error_remain, ex=120)
                    if error_reset:
                        self.redis.set(REDIS_KEY_ERROR_RESET, error_reset, ex=120)
                except Exception:
                    pass

    def get_error_remaining(self) -> int:
        """Get current error budget remaining."""
        if self.redis:
            try:
                val = self.redis.get(REDIS_KEY_ERROR_REMAIN)
                if val:
                    return int(val)
            except Exception:
                pass
        return self._local_error_remain

    def set_global_ban(self, duration_seconds: int = 120) -> None:
        """Set global ban flag (420 received)."""
        logger.critical("ESI GLOBAL BAN SET — all services paused")
        if self.redis:
            try:
                self.redis.setex(REDIS_KEY_GLOBAL_BAN, duration_seconds, "1")
            except Exception:
                pass

    def is_globally_banned(self) -> bool:
        """Check if global ban is active."""
        if self.redis:
            try:
                return self.redis.get(REDIS_KEY_GLOBAL_BAN) == "1"
            except Exception:
                pass
        return False

    def should_hard_stop(self) -> bool:
        """Check if error budget is critically low."""
        return self.get_error_remaining() < HARD_STOP_THRESHOLD

    def should_throttle(self) -> bool:
        """Check if we should slow down."""
        return self.get_error_remaining() < ERROR_LIMIT_THRESHOLD


# Singleton
shared_rate_state = SharedRateState()
