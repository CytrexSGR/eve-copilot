"""Tests for ZKillboard RedisQ Client with ESI Killmail Caching."""

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from services.zkillboard.redisq_client import (
    ZKillRedisQClient,
    create_redisq_client,
    ESI_KILLMAIL_CACHE_TTL,
)


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis_mock = MagicMock()
    redis_mock.ping.return_value = True
    redis_mock.get.return_value = None
    redis_mock.setex.return_value = True
    return redis_mock


@pytest.fixture
def mock_session():
    """Create a mock aiohttp session."""
    session = AsyncMock()
    return session


@pytest.fixture
def sample_killmail():
    """Create a sample killmail response from ESI."""
    return {
        "killmail_id": 123456789,
        "killmail_time": "2026-01-18T12:00:00Z",
        "solar_system_id": 30000142,
        "victim": {
            "character_id": 93265215,
            "corporation_id": 98000001,
            "ship_type_id": 24690,
            "damage_taken": 50000
        },
        "attackers": [
            {
                "character_id": 93265216,
                "corporation_id": 98000002,
                "damage_done": 50000,
                "final_blow": True,
                "ship_type_id": 24690,
                "weapon_type_id": 2205
            }
        ]
    }


@pytest.fixture
def client_with_redis(mock_redis):
    """Create a RedisQ client with mocked Redis."""
    return ZKillRedisQClient(
        queue_id="test-queue",
        ttw=5,
        redis_client=mock_redis
    )


class TestZKillRedisQClientInit:
    """Test client initialization."""

    def test_init_with_redis_client(self, mock_redis):
        """Test initialization with provided Redis client."""
        client = ZKillRedisQClient(
            queue_id="test-queue",
            ttw=5,
            redis_client=mock_redis
        )

        assert client.queue_id == "test-queue"
        assert client.ttw == 5
        assert client._redis == mock_redis
        assert client._cache_hits == 0
        assert client._cache_misses == 0

    def test_init_without_redis_creates_connection(self):
        """Test initialization creates Redis connection when not provided."""
        with patch('services.zkillboard.redisq_client.redis.Redis') as mock_redis_class:
            mock_instance = MagicMock()
            mock_instance.ping.return_value = True
            mock_redis_class.return_value = mock_instance

            client = ZKillRedisQClient(queue_id="test-queue", ttw=5)

            mock_redis_class.assert_called_once()
            assert client._redis == mock_instance

    def test_init_redis_connection_failure(self):
        """Test initialization handles Redis connection failure gracefully."""
        with patch('services.zkillboard.redisq_client.redis.Redis') as mock_redis_class:
            import redis as redis_module
            mock_redis_class.return_value.ping.side_effect = redis_module.ConnectionError("Connection refused")

            client = ZKillRedisQClient(queue_id="test-queue", ttw=5)

            # Client should still be created, but without Redis
            assert client._redis is None

    def test_ttw_clamped_to_valid_range(self, mock_redis):
        """Test that ttw is clamped to 1-10 range."""
        client_low = ZKillRedisQClient(queue_id="test", ttw=0, redis_client=mock_redis)
        client_high = ZKillRedisQClient(queue_id="test", ttw=100, redis_client=mock_redis)

        assert client_low.ttw == 1
        assert client_high.ttw == 10


class TestESIKillmailCaching:
    """Test ESI killmail caching functionality."""

    def test_get_esi_cache_key(self, client_with_redis):
        """Test cache key format."""
        key = client_with_redis._get_esi_cache_key(123456789)
        assert key == "esi:killmail:123456789"

    def test_get_cached_killmail_hit(self, client_with_redis, mock_redis, sample_killmail):
        """Test cache hit returns cached data."""
        mock_redis.get.return_value = json.dumps(sample_killmail)

        result = client_with_redis._get_cached_killmail(123456789)

        assert result == sample_killmail
        assert client_with_redis._cache_hits == 1
        mock_redis.get.assert_called_once_with("esi:killmail:123456789")

    def test_get_cached_killmail_miss(self, client_with_redis, mock_redis):
        """Test cache miss returns None."""
        mock_redis.get.return_value = None

        result = client_with_redis._get_cached_killmail(123456789)

        assert result is None
        assert client_with_redis._cache_hits == 0

    def test_get_cached_killmail_redis_error(self, client_with_redis, mock_redis):
        """Test Redis error is handled gracefully."""
        import redis as redis_module
        mock_redis.get.side_effect = redis_module.RedisError("Connection lost")

        result = client_with_redis._get_cached_killmail(123456789)

        assert result is None

    def test_get_cached_killmail_json_decode_error(self, client_with_redis, mock_redis):
        """Test invalid JSON is handled gracefully."""
        mock_redis.get.return_value = "not valid json {"

        result = client_with_redis._get_cached_killmail(123456789)

        assert result is None

    def test_get_cached_killmail_no_redis(self, mock_session):
        """Test returns None when Redis is not available."""
        client = ZKillRedisQClient(queue_id="test", ttw=5, redis_client=None)
        client._redis = None  # Simulate Redis not available

        result = client._get_cached_killmail(123456789)

        assert result is None

    def test_cache_killmail_success(self, client_with_redis, mock_redis, sample_killmail):
        """Test successful caching of killmail."""
        result = client_with_redis._cache_killmail(123456789, sample_killmail)

        assert result is True
        mock_redis.setex.assert_called_once_with(
            "esi:killmail:123456789",
            ESI_KILLMAIL_CACHE_TTL,
            json.dumps(sample_killmail)
        )

    def test_cache_killmail_redis_error(self, client_with_redis, mock_redis, sample_killmail):
        """Test Redis error during caching is handled gracefully."""
        import redis as redis_module
        mock_redis.setex.side_effect = redis_module.RedisError("Connection lost")

        result = client_with_redis._cache_killmail(123456789, sample_killmail)

        assert result is False

    def test_cache_killmail_no_redis(self, mock_session, sample_killmail):
        """Test caching returns False when Redis is not available."""
        client = ZKillRedisQClient(queue_id="test", ttw=5, redis_client=None)
        client._redis = None

        result = client._cache_killmail(123456789, sample_killmail)

        assert result is False


class TestFetchKillmailFromESI:
    """Test fetch_killmail_from_esi with caching."""

    @pytest.mark.asyncio
    async def test_fetch_cache_hit(self, client_with_redis, mock_redis, sample_killmail):
        """Test that cached killmails don't hit ESI."""
        mock_redis.get.return_value = json.dumps(sample_killmail)

        with patch.object(client_with_redis, '_get_session') as mock_get_session:
            result = await client_with_redis.fetch_killmail_from_esi(123456789, "abc123hash")

            # ESI should NOT be called
            mock_get_session.assert_not_called()
            assert result == sample_killmail
            assert client_with_redis._cache_hits == 1

    @pytest.mark.asyncio
    async def test_fetch_cache_miss_calls_esi(self, client_with_redis, mock_redis, sample_killmail):
        """Test that cache miss fetches from ESI and caches result."""
        mock_redis.get.return_value = None

        # Mock the HTTP response with proper async context manager
        mock_response = MagicMock()
        mock_response.status = 200

        # json() is called with await, so make it an async method
        async def mock_json():
            return sample_killmail
        mock_response.json = mock_json

        # Create a proper async context manager for session.get()
        class MockContextManager:
            async def __aenter__(self):
                return mock_response

            async def __aexit__(self, *args):
                pass

        mock_session = MagicMock()
        mock_session.get.return_value = MockContextManager()

        # Mock _get_session as an async function returning the mock session
        async def mock_get_session():
            return mock_session

        # Mock _rate_limit as an async function
        async def mock_rate_limit():
            pass

        client_with_redis._get_session = mock_get_session
        client_with_redis._rate_limit = mock_rate_limit

        result = await client_with_redis.fetch_killmail_from_esi(123456789, "abc123hash")

        assert result == sample_killmail
        assert client_with_redis._cache_misses == 1

        # Verify caching was attempted
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_invalid_params(self, client_with_redis):
        """Test that invalid parameters return None without API call."""
        result_no_id = await client_with_redis.fetch_killmail_from_esi(0, "abc123hash")
        result_no_hash = await client_with_redis.fetch_killmail_from_esi(123456789, "")
        result_both_invalid = await client_with_redis.fetch_killmail_from_esi(None, None)

        assert result_no_id is None
        assert result_no_hash is None
        assert result_both_invalid is None

    @pytest.mark.asyncio
    async def test_fetch_esi_error(self, client_with_redis, mock_redis):
        """Test that ESI errors are handled gracefully."""
        mock_redis.get.return_value = None

        # Mock the HTTP response with error status
        mock_response = MagicMock()
        mock_response.status = 500

        # Create a proper async context manager for session.get()
        class MockContextManager:
            async def __aenter__(self):
                return mock_response

            async def __aexit__(self, *args):
                pass

        mock_session = MagicMock()
        mock_session.get.return_value = MockContextManager()

        # Mock _get_session as an async function returning the mock session
        async def mock_get_session():
            return mock_session

        # Mock _rate_limit as an async function
        async def mock_rate_limit():
            pass

        client_with_redis._get_session = mock_get_session
        client_with_redis._rate_limit = mock_rate_limit

        result = await client_with_redis.fetch_killmail_from_esi(123456789, "abc123hash")

        assert result is None
        # Should not cache error responses
        mock_redis.setex.assert_not_called()


class TestCacheStats:
    """Test cache statistics."""

    def test_get_cache_stats_initial(self, client_with_redis):
        """Test initial cache stats are zero."""
        stats = client_with_redis.get_cache_stats()

        assert stats["cache_hits"] == 0
        assert stats["cache_misses"] == 0
        assert stats["total_requests"] == 0
        assert stats["hit_rate_percent"] == 0.0

    def test_get_cache_stats_after_operations(self, client_with_redis, mock_redis, sample_killmail):
        """Test cache stats after some operations."""
        # Simulate 3 hits
        mock_redis.get.return_value = json.dumps(sample_killmail)
        for _ in range(3):
            client_with_redis._get_cached_killmail(123456789)

        # Simulate 2 misses
        mock_redis.get.return_value = None
        for _ in range(2):
            client_with_redis._get_cached_killmail(123456789)
            client_with_redis._cache_misses += 1  # Manually increment for test

        stats = client_with_redis.get_cache_stats()

        assert stats["cache_hits"] == 3
        assert stats["cache_misses"] == 2
        assert stats["total_requests"] == 5
        assert stats["hit_rate_percent"] == 60.0


class TestFactoryFunction:
    """Test create_redisq_client factory function."""

    def test_create_with_defaults(self):
        """Test factory function with default parameters."""
        with patch('services.zkillboard.redisq_client.redis.Redis') as mock_redis_class:
            mock_instance = MagicMock()
            mock_instance.ping.return_value = True
            mock_redis_class.return_value = mock_instance

            client = create_redisq_client()

            assert client.queue_id == "eve-copilot-live-v3"
            assert client.ttw == 10

    def test_create_with_custom_redis(self, mock_redis):
        """Test factory function with custom Redis client."""
        client = create_redisq_client(
            queue_id="custom-queue",
            ttw=7,
            redis_client=mock_redis
        )

        assert client.queue_id == "custom-queue"
        assert client.ttw == 7
        assert client._redis == mock_redis
