# tests/services/test_market_repository.py
"""Tests for unified MarketRepository with hybrid caching."""
import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from src.services.market.repository import UnifiedMarketRepository
from src.services.market.models import MarketPrice, PriceSource, JITA_REGION_ID


class TestUnifiedMarketRepository:
    """Test UnifiedMarketRepository hybrid caching."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        return MagicMock()

    @pytest.fixture
    def mock_db(self):
        """Mock database pool."""
        return MagicMock()

    @pytest.fixture
    def mock_esi(self):
        """Mock ESI client."""
        return MagicMock()

    @pytest.fixture
    def repo(self, mock_redis, mock_db, mock_esi):
        """Create repository with mocked dependencies."""
        return UnifiedMarketRepository(
            redis_client=mock_redis,
            db_pool=mock_db,
            esi_client=mock_esi
        )

    def test_get_price_redis_hit(self, repo, mock_redis):
        """Test L1 cache hit (Redis)."""
        # Setup: Redis has data
        mock_redis.get.return_value = '{"type_id": 34, "sell_price": 5.5, "buy_price": 5.0, "region_id": 10000002, "source": "redis", "last_updated": "2026-01-18T10:00:00"}'

        result = repo.get_price(34)

        assert result is not None
        assert result.type_id == 34
        assert result.source == PriceSource.REDIS

    def test_get_price_postgres_hit_promotes_to_redis(self, repo, mock_redis, mock_db):
        """Test L2 cache hit (PostgreSQL) promotes to L1."""
        # Setup: Redis miss
        mock_redis.get.return_value = None

        # PostgreSQL hit
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "type_id": 34,
            "lowest_sell": 5.5,
            "highest_buy": 5.0,
            "adjusted_price": 5.25,
            "average_price": 5.30,
            "last_updated": datetime(2026, 1, 18, 10, 0, 0)
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_db.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)

        result = repo.get_price(34)

        assert result is not None
        assert result.type_id == 34
        assert result.source == PriceSource.CACHE
        # Should promote to Redis
        mock_redis.setex.assert_called()

    def test_get_price_esi_fallback(self, repo, mock_redis, mock_db, mock_esi):
        """Test L3 fallback (ESI)."""
        # Setup: Redis miss
        mock_redis.get.return_value = None

        # PostgreSQL miss
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_db.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)

        # ESI returns data
        mock_esi.get_market_orders.return_value = [
            {"price": 5.5, "is_buy_order": False},
            {"price": 5.0, "is_buy_order": True}
        ]

        result = repo.get_price(34)

        assert result is not None
        assert result.type_id == 34
        assert result.source == PriceSource.ESI

    def test_is_hot_item(self, repo):
        """Test hot item detection."""
        # Tritanium (34) should be hot
        assert repo.is_hot_item(34) is True
        # Random item should not be hot
        assert repo.is_hot_item(99999999) is False

    def test_get_price_with_region_id(self, repo, mock_redis):
        """Test get_price with specific region ID."""
        # Setup: Redis has data
        mock_redis.get.return_value = '{"type_id": 34, "sell_price": 6.0, "buy_price": 5.5, "region_id": 10000043, "source": "redis", "last_updated": "2026-01-18T10:00:00"}'

        result = repo.get_price(34, region_id=10000043)  # Amarr region

        assert result is not None
        assert result.type_id == 34
        assert result.region_id == 10000043

    def test_get_prices_batch_partial_cache_hit(self, repo, mock_redis, mock_db, mock_esi):
        """Test batch retrieval with partial cache hits."""
        # Setup: Mock pipeline for Redis
        mock_pipeline = MagicMock()
        mock_redis.pipeline.return_value.__enter__ = Mock(return_value=mock_pipeline)
        mock_redis.pipeline.return_value.__exit__ = Mock(return_value=False)

        # Type 34 cached, 35 not cached
        mock_pipeline.execute.return_value = [
            '{"type_id": 34, "sell_price": 5.5, "buy_price": 5.0, "region_id": 10000002, "last_updated": "2026-01-18T10:00:00"}',
            None
        ]

        # PostgreSQL has type 35
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {
                "type_id": 35,
                "lowest_sell": 10.0,
                "highest_buy": 9.5,
                "adjusted_price": 9.75,
                "average_price": 9.80,
                "last_updated": datetime(2026, 1, 18, 10, 0, 0)
            }
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_db.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)

        result = repo.get_prices([34, 35])

        assert len(result) == 2
        assert 34 in result
        assert 35 in result
        assert result[34].source == PriceSource.REDIS
        assert result[35].source == PriceSource.CACHE

    def test_get_price_redis_error_fallback(self, repo, mock_redis, mock_db):
        """Test fallback to PostgreSQL when Redis fails."""
        # Setup: Redis throws exception
        mock_redis.get.side_effect = Exception("Redis connection failed")

        # PostgreSQL works
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "type_id": 34,
            "lowest_sell": 5.5,
            "highest_buy": 5.0,
            "adjusted_price": 5.25,
            "average_price": 5.30,
            "last_updated": datetime(2026, 1, 18, 10, 0, 0)
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_db.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)

        result = repo.get_price(34)

        # Should still return data from PostgreSQL
        assert result is not None
        assert result.type_id == 34

    def test_esi_writes_to_both_caches(self, repo, mock_redis, mock_db, mock_esi):
        """Test ESI data is written to both L1 and L2."""
        # Setup: All caches miss
        mock_redis.get.return_value = None

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = Mock(return_value=False)
        mock_db.get_connection.return_value.__enter__ = Mock(return_value=mock_conn)
        mock_db.get_connection.return_value.__exit__ = Mock(return_value=False)

        # ESI returns data
        mock_esi.get_market_orders.return_value = [
            {"price": 5.5, "is_buy_order": False},
            {"price": 5.0, "is_buy_order": True}
        ]

        result = repo.get_price(34)

        assert result is not None
        assert result.source == PriceSource.ESI
        # Verify Redis was called to cache
        mock_redis.setex.assert_called()
        # Verify PostgreSQL insert/upsert was called
        mock_cursor.execute.assert_called()
