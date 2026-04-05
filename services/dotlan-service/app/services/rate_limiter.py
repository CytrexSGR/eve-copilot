"""Token-bucket rate limiter for DOTLAN requests."""

import asyncio
import time
import logging

logger = logging.getLogger(__name__)


class TokenBucketRateLimiter:
    """Token-bucket rate limiter.

    Ensures we don't exceed the configured request rate to DOTLAN servers.
    Default: 1 request/second with burst of 3.
    """

    def __init__(self, rate: float = 1.0, burst: int = 3):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()
        self._total_waits = 0

    async def acquire(self):
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_refill = now

            if self.tokens < 1.0:
                wait_time = (1.0 - self.tokens) / self.rate
                self._total_waits += 1
                logger.debug(f"Rate limiter: waiting {wait_time:.2f}s (total waits: {self._total_waits})")
                await asyncio.sleep(wait_time)
                self.tokens = 0.0
                self.last_refill = time.monotonic()
            else:
                self.tokens -= 1.0

    @property
    def total_waits(self) -> int:
        """Total number of times we had to wait for a token."""
        return self._total_waits
