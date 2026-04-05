"""Test ETag caching via Redis."""
import pytest
import json
from unittest.mock import MagicMock


class TestETagCache:
    @pytest.fixture
    def mock_redis(self):
        r = MagicMock()
        r.get.return_value = None
        return r

    @pytest.fixture
    def cache(self, mock_redis):
        from src.integrations.esi.etag_cache import ETagCache
        c = ETagCache()
        c._redis = mock_redis
        return c

    def test_get_etag_none_when_not_cached(self, cache, mock_redis):
        mock_redis.get.return_value = None
        assert cache.get_etag("/characters/123/wallet/") is None

    def test_get_etag_returns_cached(self, cache, mock_redis):
        mock_redis.get.return_value = '"abc123"'
        assert cache.get_etag("/characters/123/wallet/") == '"abc123"'

    def test_store_saves_etag_and_data(self, cache, mock_redis):
        cache.store("/characters/123/wallet/", '"abc123"', {"balance": 1000})
        mock_redis.setex.assert_any_call(
            "esi:etag:/characters/123/wallet/", 1800, '"abc123"'
        )
        mock_redis.setex.assert_any_call(
            "esi:data:/characters/123/wallet/", 1800,
            json.dumps({"balance": 1000})
        )

    def test_get_cached_data(self, cache, mock_redis):
        mock_redis.get.return_value = json.dumps({"balance": 1000})
        assert cache.get_cached_data("/characters/123/wallet/") == {"balance": 1000}

    def test_get_cached_data_none_when_empty(self, cache, mock_redis):
        mock_redis.get.return_value = None
        assert cache.get_cached_data("/characters/123/wallet/") is None

    def test_works_without_redis(self):
        from src.integrations.esi.etag_cache import ETagCache
        c = ETagCache()
        c._redis = None
        assert c.get_etag("/test") is None
        assert c.get_cached_data("/test") is None
        c.store("/test", '"tag"', {"data": 1})  # Should not raise
