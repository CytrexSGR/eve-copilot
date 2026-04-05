"""Redis-based tier-aware rate limiting middleware."""
import logging
from typing import Optional, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.middleware.redis_pool import get_redis
from app.middleware.gate_helpers import _decode_jwt

logger = logging.getLogger(__name__)

TIER_RATE_LIMITS = {
    "public": 30,
    "free": 60,
    "pilot": 200,
    "corporation": 500,
    "alliance": 1000,
    "coalition": 2000,
}

WINDOW_SECONDS = 60
SKIP_PATHS = {"/health", "/health/services", "/metrics", "/docs", "/redoc", "/openapi.json"}


def get_rate_limit_for_tier(tier: Optional[str]) -> int:
    """Get requests-per-minute limit for a tier."""
    if tier is None:
        return TIER_RATE_LIMITS["public"]
    return TIER_RATE_LIMITS.get(tier, TIER_RATE_LIMITS["public"])


def make_rate_limit_key(character_id: Optional[int], client_ip: Optional[str]) -> str:
    """Build Redis key for rate limiting. Auth users keyed by character, anon by IP."""
    if character_id:
        return f"rl:char:{character_id}"
    return f"rl:ip:{client_ip or 'unknown'}"


def check_rate_limit_pure(current_count: int, limit: int) -> Tuple[bool, int]:
    """Pure check: is request allowed? Returns (allowed, remaining)."""
    if current_count >= limit:
        return False, 0
    remaining = max(0, limit - current_count - 1)
    return True, remaining


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Redis-backed, tier-aware rate limiting."""

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    async def dispatch(self, request: Request, call_next):
        if not self.enabled or request.url.path in SKIP_PATHS:
            return await call_next(request)

        client_ip = self._get_client_ip(request)

        # Resolve tier from JWT — never trust client headers for tier
        session_token = request.cookies.get("session")
        char_id_int, jwt_tier = _decode_jwt(session_token) if session_token else (None, None)
        tier = jwt_tier or "public"
        limit = get_rate_limit_for_tier(tier)
        key = make_rate_limit_key(char_id_int, client_ip)

        r = get_redis()
        if r:
            try:
                current = r.incr(key)
                if current == 1:
                    r.expire(key, WINDOW_SECONDS)
                allowed, remaining = check_rate_limit_pure(current - 1, limit)
            except Exception:
                allowed, remaining = True, limit
        else:
            allowed, remaining = True, limit

        if not allowed:
            return Response(
                content='{"error":"rate_limit_exceeded","retry_after":60}',
                status_code=429,
                media_type="application/json",
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "Retry-After": str(WINDOW_SECONDS),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
