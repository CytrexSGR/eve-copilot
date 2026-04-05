"""Redis cache layer for market prices (L1 Cache)."""
import json
import logging
from json import JSONDecodeError
from datetime import datetime
from typing import Dict, List, Optional

from app.models import MarketPrice, PriceSource

logger = logging.getLogger(__name__)


class MarketCache:
    """Redis-based cache for market prices (L1 Cache)."""

    KEY_PREFIX = "market:price"
    DEFAULT_TTL = 300  # 5 minutes

    def __init__(self, redis_client):
        """
        Initialize cache with Redis client.

        Args:
            redis_client: Redis client instance
        """
        self.redis = redis_client

    def _make_key(self, type_id: int, region_id: int) -> str:
        """Generate cache key for price."""
        return f"{self.KEY_PREFIX}:{region_id}:{type_id}"

    def get_price(self, type_id: int, region_id: int) -> Optional[MarketPrice]:
        """
        Get price from cache.

        Args:
            type_id: Item type ID
            region_id: Region ID

        Returns:
            MarketPrice if cached, None otherwise
        """
        key = self._make_key(type_id, region_id)
        try:
            data = self.redis.get(key)
            if data is None:
                return None

            parsed = json.loads(data)
            # Parse datetime
            if "last_updated" in parsed and isinstance(parsed["last_updated"], str):
                parsed["last_updated"] = datetime.fromisoformat(parsed["last_updated"])

            price = MarketPrice(**parsed)
            price.source = PriceSource.REDIS
            return price

        except (JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"Cache get error for {key}: {e}")
            return None

    def set_price(self, price: MarketPrice, ttl: int = DEFAULT_TTL) -> bool:
        """
        Set price in cache.

        Args:
            price: MarketPrice to cache
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        key = self._make_key(price.type_id, price.region_id)
        try:
            data = price.model_dump()
            # Serialize datetime
            if isinstance(data.get("last_updated"), datetime):
                data["last_updated"] = data["last_updated"].isoformat()

            self.redis.setex(key, ttl, json.dumps(data))
            return True

        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")
            return False

    def get_prices(self, type_ids: List[int], region_id: int) -> Dict[int, MarketPrice]:
        """
        Get multiple prices in single round-trip.

        Args:
            type_ids: List of type IDs
            region_id: Region ID

        Returns:
            Dict mapping type_id to MarketPrice (only cached items)
        """
        if not type_ids:
            return {}

        keys = [self._make_key(tid, region_id) for tid in type_ids]
        result = {}

        try:
            with self.redis.pipeline() as pipe:
                for key in keys:
                    pipe.get(key)
                values = pipe.execute()

            for type_id, data in zip(type_ids, values):
                if data is not None:
                    try:
                        parsed = json.loads(data)
                        if "last_updated" in parsed and isinstance(parsed["last_updated"], str):
                            parsed["last_updated"] = datetime.fromisoformat(parsed["last_updated"])
                        price = MarketPrice(**parsed)
                        price.source = PriceSource.REDIS
                        result[type_id] = price
                    except (JSONDecodeError, ValueError, TypeError) as e:
                        logger.warning(f"Parse error for type {type_id}: {e}")

        except Exception as e:
            logger.error(f"Batch cache get error: {e}")

        return result

    def set_prices(self, prices: List[MarketPrice], ttl: int = DEFAULT_TTL) -> int:
        """
        Set multiple prices in single round-trip.

        Args:
            prices: List of MarketPrice objects
            ttl: Time-to-live in seconds

        Returns:
            Number of prices cached
        """
        if not prices:
            return 0

        count = 0
        try:
            with self.redis.pipeline() as pipe:
                for price in prices:
                    key = self._make_key(price.type_id, price.region_id)
                    data = price.model_dump()
                    if isinstance(data.get("last_updated"), datetime):
                        data["last_updated"] = data["last_updated"].isoformat()
                    pipe.setex(key, ttl, json.dumps(data))
                pipe.execute()
                count = len(prices)

        except Exception as e:
            logger.error(f"Batch cache set error: {e}")

        return count

    def invalidate_price(self, type_id: int, region_id: int) -> bool:
        """Invalidate cached price."""
        key = self._make_key(type_id, region_id)
        try:
            self.redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache invalidate error for {key}: {e}")
            return False
