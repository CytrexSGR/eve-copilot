"""Redis client with connection pooling."""

import threading
from typing import Optional, Any
import redis
from redis import ConnectionPool

from eve_shared.config import get_config


class RedisClient:
    """Redis client singleton with connection pooling."""

    _instance: Optional["RedisClient"] = None
    _pool: Optional[ConnectionPool] = None
    _client: Optional[redis.Redis] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def initialize(self, url: Optional[str] = None):
        """Initialize the Redis connection pool."""
        if self._pool is not None:  # Fast path
            return

        with self._lock:
            if self._pool is not None:  # Double-check after acquiring lock
                return

            config = get_config()
            url = url or config.redis_url

            self._pool = ConnectionPool.from_url(url, decode_responses=True)
            self._client = redis.Redis(connection_pool=self._pool)

    @property
    def client(self) -> redis.Redis:
        """Get the Redis client."""
        if self._client is None:
            self.initialize()
        return self._client

    def get(self, key: str) -> Optional[str]:
        """Get a value from Redis."""
        return self.client.get(key)

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set a value in Redis with optional expiration."""
        return self.client.set(key, value, ex=ex)

    def delete(self, key: str) -> int:
        """Delete a key from Redis."""
        return self.client.delete(key)

    def publish(self, channel: str, message: str) -> int:
        """Publish message to channel."""
        return self.client.publish(channel, message)

    def close(self):
        """Close the connection pool."""
        if self._pool:
            self._pool.disconnect()
            self._pool = None
            self._client = None


def get_redis() -> RedisClient:
    """Get the Redis client singleton."""
    return RedisClient()
