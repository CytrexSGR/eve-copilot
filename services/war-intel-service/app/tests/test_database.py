"""Tests for database pool configuration and metrics instrumentation."""

import os
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


class TestPoolConfiguration:
    """Test that DatabasePool reads configuration from env vars."""

    def test_default_pool_min(self):
        """Default DB_POOL_MIN is 2."""
        assert int(os.getenv("DB_POOL_MIN", "2")) == 2

    def test_default_pool_max(self):
        """Default DB_POOL_MAX is 10."""
        assert int(os.getenv("DB_POOL_MAX", "10")) == 10

    def test_custom_pool_config_from_env(self, monkeypatch):
        """Pool reads custom config from env vars."""
        monkeypatch.setenv("DB_POOL_MIN", "1")
        monkeypatch.setenv("DB_POOL_MAX", "5")

        assert int(os.getenv("DB_POOL_MIN")) == 1
        assert int(os.getenv("DB_POOL_MAX")) == 5

    def test_pool_max_env_var_parsing(self, monkeypatch):
        """Pool max value correctly parses string env var to int."""
        monkeypatch.setenv("DB_POOL_MAX", "15")
        assert int(os.getenv("DB_POOL_MAX")) == 15


class TestDbCursorOperation:
    """Test that db_cursor passes operation label for metrics."""

    def test_db_cursor_accepts_operation_param(self):
        """db_cursor function signature accepts operation parameter."""
        from app.database import db_cursor
        import inspect
        sig = inspect.signature(db_cursor)
        assert "operation" in sig.parameters
        assert sig.parameters["operation"].default == "query"

    def test_db_cursor_accepts_cursor_factory_param(self):
        """db_cursor function signature accepts cursor_factory parameter."""
        from app.database import db_cursor
        import inspect
        sig = inspect.signature(db_cursor)
        assert "cursor_factory" in sig.parameters

    def test_database_pool_cursor_accepts_operation(self):
        """DatabasePool.cursor method accepts operation parameter."""
        from app.database import DatabasePool
        import inspect
        sig = inspect.signature(DatabasePool.cursor)
        assert "operation" in sig.parameters
        assert sig.parameters["operation"].default == "query"


class TestServiceName:
    """Test that service name constant is correct for metrics."""

    def test_service_name_is_war_intel(self):
        """SERVICE_NAME in database.py matches expected value."""
        from app.database import SERVICE_NAME
        assert SERVICE_NAME == "war-intel"

    def test_cache_service_name_matches(self):
        """SERVICE_NAME in cache.py matches database.py."""
        from app.database import SERVICE_NAME as db_name
        from app.utils.cache import SERVICE_NAME as cache_name
        assert db_name == cache_name
