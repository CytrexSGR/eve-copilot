"""Tests for ESIClient.get_market_stats Redis caching behavior.

Covers: cache hit, cache miss, no redis, redis error on get, redis error on set.
"""

import json
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from app.services.esi_client import ESIClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_ORDERS = [
    {"price": 100.0, "is_buy_order": False, "volume_remain": 500, "location_id": 60003760},
    {"price": 80.0, "is_buy_order": True, "volume_remain": 300, "location_id": 60003760},
]

SAMPLE_STATS = {
    "type_id": 34,
    "region_id": 10000002,
    "total_orders": 2,
    "sell_orders": 1,
    "buy_orders": 1,
    "lowest_sell": 100.0,
    "highest_buy": 80.0,
    "sell_volume": 500,
    "buy_volume": 300,
    "spread": 20.0,
    "spread_percent": 20.0,
}


def _mock_get_market_orders(region_id, type_id):
    """Return mock orders for testing."""
    return SAMPLE_ORDERS


# ---------------------------------------------------------------------------
# test_cache_hit
# ---------------------------------------------------------------------------

class TestCacheHit:
    def test_returns_cached_data_without_esi_call(self):
        """When Redis has cached data, ESI should NOT be called."""
        redis_mock = MagicMock()
        redis_mock.get.return_value = json.dumps(SAMPLE_STATS)

        client = ESIClient(redis_client=redis_mock)
        client.get_market_orders = MagicMock()

        result = client.get_market_stats(10000002, 34)

        redis_mock.get.assert_called_once_with("market-stats:10000002:34")
        client.get_market_orders.assert_not_called()
        assert result == SAMPLE_STATS

    def test_cache_key_format(self):
        """Cache key should be market-stats:{region_id}:{type_id}."""
        redis_mock = MagicMock()
        redis_mock.get.return_value = json.dumps({"cached": True})

        client = ESIClient(redis_client=redis_mock)
        client.get_market_orders = MagicMock()

        client.get_market_stats(10000043, 587)
        redis_mock.get.assert_called_once_with("market-stats:10000043:587")


# ---------------------------------------------------------------------------
# test_cache_miss
# ---------------------------------------------------------------------------

class TestCacheMiss:
    def test_calls_esi_and_caches_result(self):
        """When Redis returns None, ESI should be called and result cached."""
        redis_mock = MagicMock()
        redis_mock.get.return_value = None

        client = ESIClient(redis_client=redis_mock)
        client.get_market_orders = MagicMock(return_value=SAMPLE_ORDERS)

        result = client.get_market_stats(10000002, 34)

        # ESI was called
        client.get_market_orders.assert_called_once_with(10000002, 34)

        # Result was cached with 60s TTL
        redis_mock.set.assert_called_once()
        call_args = redis_mock.set.call_args
        assert call_args[0][0] == "market-stats:10000002:34"
        cached_data = json.loads(call_args[0][1])
        assert cached_data["lowest_sell"] == 100.0
        assert cached_data["highest_buy"] == 80.0
        assert call_args[1]["ex"] == 60

        # Result returned correctly
        assert result["lowest_sell"] == 100.0
        assert result["highest_buy"] == 80.0

    def test_empty_orders_returns_empty_dict(self):
        """When ESI returns no orders, result should be empty dict and not cached."""
        redis_mock = MagicMock()
        redis_mock.get.return_value = None

        client = ESIClient(redis_client=redis_mock)
        client.get_market_orders = MagicMock(return_value=[])

        result = client.get_market_stats(10000002, 34)

        assert result == {}
        redis_mock.set.assert_not_called()


# ---------------------------------------------------------------------------
# test_no_redis
# ---------------------------------------------------------------------------

class TestNoRedis:
    def test_works_without_redis(self):
        """ESIClient with redis_client=None should work (ESI only, no cache)."""
        client = ESIClient(redis_client=None)
        client.get_market_orders = MagicMock(return_value=SAMPLE_ORDERS)

        result = client.get_market_stats(10000002, 34)

        assert result["lowest_sell"] == 100.0
        assert result["highest_buy"] == 80.0

    def test_no_redis_no_exception(self):
        """Should not raise any exception when Redis is None."""
        client = ESIClient(redis_client=None)
        client.get_market_orders = MagicMock(return_value=[])

        result = client.get_market_stats(10000002, 34)
        assert result == {}


# ---------------------------------------------------------------------------
# test_redis_error_on_get
# ---------------------------------------------------------------------------

class TestRedisErrorOnGet:
    def test_falls_back_to_esi(self):
        """If Redis.get raises an exception, should fallback to ESI."""
        redis_mock = MagicMock()
        redis_mock.get.side_effect = Exception("Redis connection refused")

        client = ESIClient(redis_client=redis_mock)
        client.get_market_orders = MagicMock(return_value=SAMPLE_ORDERS)

        result = client.get_market_stats(10000002, 34)

        # ESI was called despite Redis error
        client.get_market_orders.assert_called_once()
        assert result["lowest_sell"] == 100.0

    def test_still_caches_on_set(self):
        """After get fails, should still attempt to cache the ESI result."""
        redis_mock = MagicMock()
        redis_mock.get.side_effect = Exception("Redis timeout")

        client = ESIClient(redis_client=redis_mock)
        client.get_market_orders = MagicMock(return_value=SAMPLE_ORDERS)

        client.get_market_stats(10000002, 34)

        # set should still be attempted
        redis_mock.set.assert_called_once()


# ---------------------------------------------------------------------------
# test_redis_error_on_set
# ---------------------------------------------------------------------------

class TestRedisErrorOnSet:
    def test_returns_esi_result_despite_cache_failure(self):
        """If Redis.setex raises an exception, should still return ESI result."""
        redis_mock = MagicMock()
        redis_mock.get.return_value = None  # cache miss
        redis_mock.set.side_effect = Exception("Redis write error")

        client = ESIClient(redis_client=redis_mock)
        client.get_market_orders = MagicMock(return_value=SAMPLE_ORDERS)

        result = client.get_market_stats(10000002, 34)

        # Result should still be correct
        assert result["lowest_sell"] == 100.0
        assert result["highest_buy"] == 80.0
        assert result["total_orders"] == 2

    def test_no_exception_propagated(self):
        """Redis setex error should be swallowed, not propagated."""
        redis_mock = MagicMock()
        redis_mock.get.return_value = None
        redis_mock.set.side_effect = ConnectionError("Redis down")

        client = ESIClient(redis_client=redis_mock)
        client.get_market_orders = MagicMock(return_value=SAMPLE_ORDERS)

        # Should not raise
        result = client.get_market_stats(10000002, 34)
        assert "type_id" in result
