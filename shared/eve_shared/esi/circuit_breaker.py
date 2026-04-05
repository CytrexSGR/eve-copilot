"""Global ESI circuit breaker using Redis.

Monitors the X-Esi-Error-Limit-Remain header across all services and blocks
requests when the error budget is critically low. Replaces the simpler
SharedRateState from eve_shared.integrations.esi.shared_rate_state.

Redis keys:
    esi:cb:error_remain   - Current error budget remaining (0-100)
    esi:cb:reset_at       - UTC timestamp when ESI error window resets
    esi:cb:blocked_until  - UTC timestamp until which all requests are blocked
    esi:cb:global_ban     - Flag set when ESI returns 420 (Enhance Your Calm)
"""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# Thresholds
BLOCK_THRESHOLD = 20       # Block all requests when remaining < 20
THROTTLE_THRESHOLD = 40    # Log warnings when remaining < 40
GLOBAL_BAN_TTL = 120       # Default ban duration for 420 responses (seconds)

# Redis key prefixes
KEY_ERROR_REMAIN = "esi:cb:error_remain"
KEY_RESET_AT = "esi:cb:reset_at"
KEY_BLOCKED_UNTIL = "esi:cb:blocked_until"
KEY_GLOBAL_BAN = "esi:cb:global_ban"


class EsiCircuitBreaker:
    """Redis-backed ESI error budget circuit breaker.

    All services share the same Redis keys, so any service detecting
    a low error budget will block requests across the entire fleet.
    """

    def __init__(self):
        self._redis = None
        self._local_remain = 100

    @property
    def redis(self):
        if self._redis is None:
            try:
                from eve_shared import get_redis
                self._redis = get_redis().client
            except Exception:
                logger.debug("Redis unavailable for circuit breaker")
        return self._redis

    def is_open(self) -> bool:
        """Return True if the circuit breaker is open (requests should be blocked)."""
        if self._is_globally_banned():
            return True
        if self._is_blocked():
            return True
        return False

    def record_response(self, headers: dict, status_code: int) -> None:
        """Update circuit breaker state from ESI response headers."""
        if status_code == 420:
            self._set_global_ban()
            return

        remain_str = headers.get("X-Esi-Error-Limit-Remain") or headers.get("x-esi-error-limit-remain")
        reset_str = headers.get("X-Esi-Error-Limit-Reset") or headers.get("x-esi-error-limit-reset")

        if remain_str is None:
            return

        remain = int(remain_str)
        self._local_remain = remain

        if not self.redis:
            return

        try:
            pipe = self.redis.pipeline()
            pipe.set(KEY_ERROR_REMAIN, remain, ex=120)

            if reset_str:
                reset_seconds = int(reset_str)
                reset_at = time.time() + reset_seconds
                pipe.set(KEY_RESET_AT, str(reset_at), ex=reset_seconds + 10)

                if remain < BLOCK_THRESHOLD:
                    blocked_until = time.time() + reset_seconds
                    pipe.set(KEY_BLOCKED_UNTIL, str(blocked_until), ex=reset_seconds + 10)
                    logger.warning(
                        f"ESI circuit breaker OPEN: {remain} errors remaining, "
                        f"blocked for {reset_seconds}s"
                    )

            if remain < THROTTLE_THRESHOLD:
                logger.warning(f"ESI error budget low: {remain} remaining")

            pipe.execute()
        except Exception as e:
            logger.warning(f"Circuit breaker Redis error: {e}")

    def get_error_remaining(self) -> int:
        """Get current error budget remaining."""
        if self.redis:
            try:
                val = self.redis.get(KEY_ERROR_REMAIN)
                if val:
                    return int(val)
            except Exception:
                pass
        return self._local_remain

    def get_blocked_seconds(self) -> float:
        """Get seconds remaining until circuit breaker closes. Returns 0 if not blocked."""
        if not self.redis:
            return 0.0
        try:
            blocked = self.redis.get(KEY_BLOCKED_UNTIL)
            if blocked:
                remaining = float(blocked) - time.time()
                return max(0.0, remaining)
            ban = self.redis.get(KEY_GLOBAL_BAN)
            if ban:
                ttl = self.redis.ttl(KEY_GLOBAL_BAN)
                return max(0.0, float(ttl))
        except Exception:
            pass
        return 0.0

    def _is_blocked(self) -> bool:
        """Check if requests are blocked due to low error budget."""
        if not self.redis:
            return self._local_remain < BLOCK_THRESHOLD
        try:
            blocked = self.redis.get(KEY_BLOCKED_UNTIL)
            if blocked and float(blocked) > time.time():
                return True
        except Exception:
            pass
        return False

    def _is_globally_banned(self) -> bool:
        """Check if ESI returned 420 and we're in global ban mode."""
        if not self.redis:
            return False
        try:
            return self.redis.get(KEY_GLOBAL_BAN) == "1"
        except Exception:
            return False

    def _set_global_ban(self, duration: int = GLOBAL_BAN_TTL) -> None:
        """Set global ban flag (ESI returned 420)."""
        logger.critical(f"ESI GLOBAL BAN (420) — all services paused for {duration}s")
        if self.redis:
            try:
                self.redis.setex(KEY_GLOBAL_BAN, duration, "1")
            except Exception:
                pass


# Singleton
esi_circuit_breaker = EsiCircuitBreaker()
