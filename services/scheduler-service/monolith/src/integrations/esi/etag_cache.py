"""ETag cache using Redis for ESI conditional requests."""
import json
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

ETAG_TTL = 1800  # 30 minutes


class ETagCache:
    """Redis-backed ETag storage for ESI conditional requests."""

    def __init__(self):
        self._redis = None

    @property
    def redis(self):
        if self._redis is None:
            try:
                from eve_shared import get_redis
                self._redis = get_redis().client
            except Exception:
                logger.debug("Redis unavailable for ETag cache")
        return self._redis

    def _etag_key(self, endpoint: str) -> str:
        return f"esi:etag:{endpoint}"

    def _data_key(self, endpoint: str) -> str:
        return f"esi:data:{endpoint}"

    def get_etag(self, endpoint: str) -> Optional[str]:
        """Get cached ETag for an endpoint."""
        if not self.redis:
            return None
        try:
            return self.redis.get(self._etag_key(endpoint))
        except Exception:
            return None

    def get_cached_data(self, endpoint: str) -> Optional[Any]:
        """Get cached response data for an endpoint."""
        if not self.redis:
            return None
        try:
            raw = self.redis.get(self._data_key(endpoint))
            return json.loads(raw) if raw else None
        except Exception:
            return None

    def store(self, endpoint: str, etag: str, data: Any, ttl: int = ETAG_TTL) -> None:
        """Store ETag and response data."""
        if not self.redis:
            return
        try:
            self.redis.setex(self._etag_key(endpoint), ttl, etag)
            self.redis.setex(self._data_key(endpoint), ttl, json.dumps(data))
        except Exception as e:
            logger.warning(f"Failed to cache ETag for {endpoint}: {e}")


# Singleton
etag_cache = ETagCache()
