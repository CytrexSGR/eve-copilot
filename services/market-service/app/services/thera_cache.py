"""Redis cache layer for Thera connections."""
import json
import logging
from datetime import datetime
from typing import Optional

from app.models.thera import TheraConnection

logger = logging.getLogger(__name__)


class TheraCache:
    """Redis-based cache for Thera/Turnur connections."""

    KEY_CONNECTIONS = "thera:connections"
    KEY_LAST_FETCH = "thera:last_fetch"
    DEFAULT_TTL = 300  # 5 minutes

    def __init__(self, redis_client):
        """
        Initialize cache with Redis client.

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client

    def get_connections(self) -> Optional[list[TheraConnection]]:
        """
        Get cached Thera connections.

        Returns:
            List of TheraConnection if cached, None otherwise
        """
        try:
            data = self.redis.get(self.KEY_CONNECTIONS)
            if data is None:
                return None

            parsed = json.loads(data)
            connections = []

            for item in parsed:
                # Parse datetime fields
                if "expires_at" in item and isinstance(item["expires_at"], str):
                    item["expires_at"] = datetime.fromisoformat(item["expires_at"])
                if "created_at" in item and isinstance(item["created_at"], str):
                    item["created_at"] = datetime.fromisoformat(item["created_at"])
                if "updated_at" in item and isinstance(item["updated_at"], str):
                    item["updated_at"] = datetime.fromisoformat(item["updated_at"])

                connections.append(TheraConnection(**item))

            return connections

        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"Cache get error: {e}")
            return None

    def set_connections(
        self,
        connections: list[TheraConnection],
        ttl: int = DEFAULT_TTL
    ) -> bool:
        """
        Cache Thera connections.

        Args:
            connections: List of TheraConnection objects
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        try:
            data = []
            for conn in connections:
                item = conn.model_dump()
                # Serialize datetime fields
                if isinstance(item.get("expires_at"), datetime):
                    item["expires_at"] = item["expires_at"].isoformat()
                if isinstance(item.get("created_at"), datetime):
                    item["created_at"] = item["created_at"].isoformat()
                if isinstance(item.get("updated_at"), datetime):
                    item["updated_at"] = item["updated_at"].isoformat()
                data.append(item)

            self.redis.setex(
                self.KEY_CONNECTIONS,
                ttl,
                json.dumps(data)
            )

            # Store fetch timestamp
            self.redis.setex(
                self.KEY_LAST_FETCH,
                ttl,
                datetime.utcnow().isoformat()
            )

            return True

        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False

    def get_last_fetch(self) -> Optional[datetime]:
        """Get timestamp of last successful fetch."""
        try:
            data = self.redis.get(self.KEY_LAST_FETCH)
            if data:
                return datetime.fromisoformat(data.decode() if isinstance(data, bytes) else data)
            return None
        except Exception:
            return None

    def get_cache_age_seconds(self) -> Optional[int]:
        """Get age of cached data in seconds."""
        last_fetch = self.get_last_fetch()
        if last_fetch:
            age = (datetime.utcnow() - last_fetch).total_seconds()
            return int(age)
        return None

    def invalidate(self) -> bool:
        """Invalidate cached connections."""
        try:
            self.redis.delete(self.KEY_CONNECTIONS)
            self.redis.delete(self.KEY_LAST_FETCH)
            return True
        except Exception as e:
            logger.warning(f"Cache invalidate error: {e}")
            return False
