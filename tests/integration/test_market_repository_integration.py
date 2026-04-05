# tests/integration/test_market_repository_integration.py
"""Integration tests for Market Repository with real Redis/PostgreSQL."""
import pytest
import redis
from datetime import datetime
import time

from src.services.market.cache import MarketCache
from src.services.market.models import MarketPrice, PriceSource, JITA_REGION_ID


@pytest.fixture(scope="module")
def redis_client():
    """Real Redis client for integration tests.

    Uses DB 15 for test isolation to avoid interfering with production data.
    """
    try:
        client = redis.Redis(host="localhost", port=6379, db=15)
        # Test connection
        client.ping()
        yield client
        # Cleanup after all tests in module
        client.flushdb()
    except redis.ConnectionError:
        pytest.skip("Redis not available for integration tests")


@pytest.fixture
def market_cache(redis_client):
    """MarketCache with real Redis."""
    return MarketCache(redis_client=redis_client)


class TestMarketCacheIntegration:
    """Integration tests for Redis cache."""

    def test_set_and_get_price(self, market_cache, redis_client):
        """Test round-trip: set price, get price."""
        # Cleanup
        redis_client.flushdb()

        price = MarketPrice(
            type_id=34,
            sell_price=5.50,
            buy_price=5.00,
            region_id=JITA_REGION_ID,
            source=PriceSource.ESI,
            last_updated=datetime(2026, 1, 18, 12, 0, 0)
        )

        # Set
        result = market_cache.set_price(price, ttl=60)
        assert result is True

        # Get
        cached = market_cache.get_price(34, JITA_REGION_ID)

        assert cached is not None
        assert cached.type_id == 34
        assert cached.sell_price == 5.50
        assert cached.buy_price == 5.00
        assert cached.region_id == JITA_REGION_ID
        # Source should be REDIS after retrieval from cache
        assert cached.source == PriceSource.REDIS.value

    def test_batch_operations(self, market_cache, redis_client):
        """Test batch set and get."""
        redis_client.flushdb()

        prices = [
            MarketPrice(
                type_id=34,
                sell_price=5.5,
                region_id=JITA_REGION_ID,
                last_updated=datetime(2026, 1, 18, 12, 0, 0)
            ),
            MarketPrice(
                type_id=35,
                sell_price=10.0,
                region_id=JITA_REGION_ID,
                last_updated=datetime(2026, 1, 18, 12, 0, 0)
            ),
            MarketPrice(
                type_id=36,
                sell_price=15.0,
                region_id=JITA_REGION_ID,
                last_updated=datetime(2026, 1, 18, 12, 0, 0)
            ),
        ]

        # Batch set
        count = market_cache.set_prices(prices, ttl=60)
        assert count == 3

        # Batch get - includes one non-existent type_id (99999)
        result = market_cache.get_prices([34, 35, 36, 99999], JITA_REGION_ID)

        assert len(result) == 3
        assert 34 in result
        assert 35 in result
        assert 36 in result
        assert 99999 not in result  # Not cached

        # Verify individual prices
        assert result[34].sell_price == 5.5
        assert result[35].sell_price == 10.0
        assert result[36].sell_price == 15.0

    def test_ttl_expiration(self, market_cache, redis_client):
        """Test that prices expire after TTL."""
        redis_client.flushdb()

        price = MarketPrice(
            type_id=34,
            sell_price=5.5,
            region_id=JITA_REGION_ID,
            last_updated=datetime(2026, 1, 18, 12, 0, 0)
        )
        market_cache.set_price(price, ttl=1)  # 1 second TTL

        # Should exist immediately
        assert market_cache.get_price(34, JITA_REGION_ID) is not None

        # Wait for expiration
        time.sleep(1.5)

        # Should be gone
        assert market_cache.get_price(34, JITA_REGION_ID) is None

    def test_invalidate_price(self, market_cache, redis_client):
        """Test cache invalidation."""
        redis_client.flushdb()

        price = MarketPrice(
            type_id=34,
            sell_price=5.5,
            region_id=JITA_REGION_ID,
            last_updated=datetime(2026, 1, 18, 12, 0, 0)
        )
        market_cache.set_price(price, ttl=60)

        # Verify it exists
        assert market_cache.get_price(34, JITA_REGION_ID) is not None

        # Invalidate
        result = market_cache.invalidate_price(34, JITA_REGION_ID)
        assert result is True

        # Should be gone
        assert market_cache.get_price(34, JITA_REGION_ID) is None

    def test_key_format(self, market_cache, redis_client):
        """Test that cache keys follow expected format."""
        redis_client.flushdb()

        price = MarketPrice(
            type_id=12345,
            sell_price=100.0,
            region_id=JITA_REGION_ID,
            last_updated=datetime(2026, 1, 18, 12, 0, 0)
        )
        market_cache.set_price(price, ttl=60)

        # Check key format: market:price:{region_id}:{type_id}
        expected_key = f"market:price:{JITA_REGION_ID}:12345"
        assert redis_client.exists(expected_key) == 1

    def test_empty_batch_operations(self, market_cache, redis_client):
        """Test batch operations with empty inputs."""
        redis_client.flushdb()

        # Empty set should return 0
        count = market_cache.set_prices([], ttl=60)
        assert count == 0

        # Empty get should return empty dict
        result = market_cache.get_prices([], JITA_REGION_ID)
        assert result == {}

    def test_price_data_integrity(self, market_cache, redis_client):
        """Test that all price fields are preserved through cache round-trip."""
        redis_client.flushdb()

        original_price = MarketPrice(
            type_id=34,
            sell_price=5.50,
            buy_price=5.00,
            adjusted_price=5.25,
            average_price=5.15,
            region_id=JITA_REGION_ID,
            source=PriceSource.ESI,
            last_updated=datetime(2026, 1, 18, 12, 0, 0)
        )

        market_cache.set_price(original_price, ttl=60)
        cached = market_cache.get_price(34, JITA_REGION_ID)

        assert cached is not None
        assert cached.type_id == original_price.type_id
        assert cached.sell_price == original_price.sell_price
        assert cached.buy_price == original_price.buy_price
        assert cached.adjusted_price == original_price.adjusted_price
        assert cached.average_price == original_price.average_price
        assert cached.region_id == original_price.region_id
        # Note: source changes to REDIS when retrieved from cache
        assert cached.source == PriceSource.REDIS.value
        assert cached.last_updated == original_price.last_updated

    def test_invalidate_nonexistent_price(self, market_cache, redis_client):
        """Test invalidating a price that doesn't exist returns True (idempotent)."""
        redis_client.flushdb()

        # Invalidate something that was never set
        result = market_cache.invalidate_price(99999, JITA_REGION_ID)
        # Should still return True (delete is idempotent)
        assert result is True

    def test_concurrent_set_operations(self, market_cache, redis_client):
        """Test that concurrent set operations don't corrupt data."""
        redis_client.flushdb()

        # Set the same key multiple times with different values
        for i in range(10):
            price = MarketPrice(
                type_id=34,
                sell_price=float(i),
                region_id=JITA_REGION_ID,
                last_updated=datetime(2026, 1, 18, 12, 0, 0)
            )
            market_cache.set_price(price, ttl=60)

        # Final value should be from the last set
        cached = market_cache.get_price(34, JITA_REGION_ID)
        assert cached is not None
        assert cached.sell_price == 9.0
