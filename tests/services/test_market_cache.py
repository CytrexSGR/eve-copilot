"""Tests for Market Cache layer."""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from src.services.market.cache import MarketCache
from src.services.market.models import MarketPrice, PriceSource


class TestMarketCache:
    """Test Market Cache operations."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client."""
        return MagicMock()

    @pytest.fixture
    def cache(self, mock_redis):
        """Create MarketCache with mocked Redis."""
        return MarketCache(redis_client=mock_redis)

    def test_get_price_cache_hit(self, cache, mock_redis):
        """Test cache hit returns cached price."""
        # Setup: Redis has cached data
        mock_redis.get.return_value = '{"type_id": 34, "sell_price": 5.5, "buy_price": 5.0, "region_id": 10000002, "last_updated": "2026-01-18T10:00:00"}'

        result = cache.get_price(34, 10000002)

        assert result is not None
        assert result.type_id == 34
        assert result.sell_price == 5.5
        assert result.source == PriceSource.REDIS
        mock_redis.get.assert_called_once_with("market:price:10000002:34")

    def test_get_price_cache_miss(self, cache, mock_redis):
        """Test cache miss returns None."""
        mock_redis.get.return_value = None

        result = cache.get_price(34, 10000002)

        assert result is None

    def test_set_price(self, cache, mock_redis):
        """Test setting price in cache."""
        price = MarketPrice(
            type_id=34,
            sell_price=5.5,
            buy_price=5.0,
            region_id=10000002,
            source=PriceSource.ESI,
            last_updated=datetime(2026, 1, 18, 12, 0, 0)
        )

        cache.set_price(price, ttl=300)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "market:price:10000002:34"
        assert call_args[0][1] == 300  # TTL

    def test_get_prices_batch(self, cache, mock_redis):
        """Test batch price retrieval."""
        # Setup: Mock pipeline
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value.__enter__ = Mock(return_value=mock_pipeline)
        mock_redis.pipeline.return_value.__exit__ = Mock(return_value=False)
        mock_pipeline.execute.return_value = [
            '{"type_id": 34, "sell_price": 5.5, "region_id": 10000002, "last_updated": "2026-01-18T10:00:00"}',
            None,  # Cache miss for 35
            '{"type_id": 36, "sell_price": 10.0, "region_id": 10000002, "last_updated": "2026-01-18T10:00:00"}'
        ]

        result = cache.get_prices([34, 35, 36], 10000002)

        assert 34 in result
        assert 35 not in result  # Cache miss
        assert 36 in result
        assert result[34].sell_price == 5.5

    def test_invalidate_price(self, cache, mock_redis):
        """Test cache invalidation."""
        cache.invalidate_price(34, 10000002)

        mock_redis.delete.assert_called_once_with("market:price:10000002:34")
