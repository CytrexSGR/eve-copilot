"""Tests for in-memory TTL cache utility."""

import time
import pytest
from unittest.mock import patch
from app.utils.cache import get_cached, set_cached, clear_cache, _cache


@pytest.fixture(autouse=True)
def clean_cache():
    """Clear cache before and after each test."""
    _cache.clear()
    yield
    _cache.clear()


class TestSetAndGet:
    def test_set_then_get_returns_data(self):
        set_cached("key1", {"value": 42})
        assert get_cached("key1") == {"value": 42}

    def test_get_nonexistent_returns_none(self):
        assert get_cached("nonexistent") is None

    def test_overwrite_key(self):
        set_cached("key1", "old")
        set_cached("key1", "new")
        assert get_cached("key1") == "new"

    def test_multiple_keys_independent(self):
        set_cached("a", 1)
        set_cached("b", 2)
        assert get_cached("a") == 1
        assert get_cached("b") == 2


class TestTTL:
    def test_expired_returns_none(self):
        set_cached("key1", "data")
        # Manually set timestamp to 10 minutes ago
        _cache["key1"] = (time.time() - 600, "data")
        assert get_cached("key1", ttl_seconds=300) is None

    def test_not_expired_returns_data(self):
        set_cached("key1", "data")
        assert get_cached("key1", ttl_seconds=300) == "data"

    def test_custom_ttl_respected(self):
        set_cached("key1", "data")
        # Set timestamp to 5 seconds ago
        _cache["key1"] = (time.time() - 5, "data")
        # 10s TTL — still valid
        assert get_cached("key1", ttl_seconds=10) == "data"
        # 3s TTL — expired
        assert get_cached("key1", ttl_seconds=3) is None

    def test_expired_entry_is_deleted(self):
        set_cached("key1", "data")
        _cache["key1"] = (time.time() - 600, "data")
        get_cached("key1", ttl_seconds=300)
        assert "key1" not in _cache


class TestClearCache:
    def test_clear_all(self):
        set_cached("a:1", "data1")
        set_cached("b:1", "data2")
        clear_cache()
        assert get_cached("a:1") is None
        assert get_cached("b:1") is None

    def test_clear_with_prefix(self):
        set_cached("corp-offensive:1:30", "data1")
        set_cached("corp-offensive:2:30", "data2")
        set_cached("alliance-offensive:1:30", "data3")
        clear_cache("corp-offensive:")
        assert get_cached("corp-offensive:1:30") is None
        assert get_cached("corp-offensive:2:30") is None
        assert get_cached("alliance-offensive:1:30") == "data3"

    def test_clear_with_nonmatching_prefix(self):
        set_cached("key1", "data")
        clear_cache("nonexistent:")
        assert get_cached("key1") == "data"


class TestEdgeCases:
    def test_none_value_cached(self):
        set_cached("key1", None)
        # get_cached returns None for both expired and None-valued entries
        # This tests that a None value is actually stored
        assert "key1" in _cache

    def test_complex_data_types(self):
        data = {"list": [1, 2, 3], "nested": {"a": True}, "number": 3.14}
        set_cached("complex", data)
        assert get_cached("complex") == data

    def test_empty_string_key(self):
        set_cached("", "data")
        assert get_cached("") == "data"


class TestCacheMetrics:
    """Tests for Prometheus cache hit/miss counters."""

    def test_get_cached_hit_increments_counter(self, monkeypatch):
        """Cache hit increments Prometheus counter with result=hit."""
        from unittest.mock import MagicMock
        mock_counter = MagicMock()
        monkeypatch.setattr("app.utils.cache.cache_operations_total", mock_counter)

        set_cached("metric-hit", {"data": 1}, ttl_seconds=60)
        result = get_cached("metric-hit", ttl_seconds=60)

        assert result == {"data": 1}
        mock_counter.labels.assert_any_call(service="war-intel", operation="get", result="hit")

    def test_get_cached_miss_increments_counter(self, monkeypatch):
        """Cache miss increments Prometheus counter with result=miss."""
        from unittest.mock import MagicMock
        mock_counter = MagicMock()
        monkeypatch.setattr("app.utils.cache.cache_operations_total", mock_counter)

        result = get_cached("nonexistent-metric-key", ttl_seconds=60)

        assert result is None
        mock_counter.labels.assert_any_call(service="war-intel", operation="get", result="miss")

    def test_set_cached_increments_counter(self, monkeypatch):
        """Cache set increments Prometheus counter with result=ok."""
        from unittest.mock import MagicMock
        mock_counter = MagicMock()
        monkeypatch.setattr("app.utils.cache.cache_operations_total", mock_counter)

        set_cached("metric-set", {"data": 1}, ttl_seconds=60)

        mock_counter.labels.assert_any_call(service="war-intel", operation="set", result="ok")

    def test_expired_entry_counts_as_miss(self, monkeypatch):
        """Expired cache entries should count as miss, not hit."""
        from unittest.mock import MagicMock
        mock_counter = MagicMock()

        set_cached("metric-expired", "data")
        _cache["metric-expired"] = (time.time() - 600, "data")

        monkeypatch.setattr("app.utils.cache.cache_operations_total", mock_counter)
        result = get_cached("metric-expired", ttl_seconds=300)

        assert result is None
        mock_counter.labels.assert_any_call(service="war-intel", operation="get", result="miss")
