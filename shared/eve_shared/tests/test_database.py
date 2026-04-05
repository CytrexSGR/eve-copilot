"""Tests for DatabasePool with optional Prometheus metrics."""

import time
from unittest.mock import MagicMock, patch, PropertyMock
from contextlib import contextmanager

import pytest


# ---------------------------------------------------------------------------
# Helpers: A lightweight mock pool that behaves like ThreadedConnectionPool
# ---------------------------------------------------------------------------

class MockCursor:
    """Minimal cursor mock supporting context manager."""

    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchall(self):
        return []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockConnection:
    """Minimal connection mock."""

    def __init__(self):
        self.committed = False
        self.rolled_back = False

    def cursor(self, cursor_factory=None):
        return MockCursor()

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class MockPool:
    """Minimal ThreadedConnectionPool mock."""

    def __init__(self):
        self._conn = MockConnection()

    def getconn(self):
        return self._conn

    def putconn(self, conn):
        pass

    def closeall(self):
        pass


# ---------------------------------------------------------------------------
# Fixture: fresh DatabasePool per test (reset singleton)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_database_pool():
    """Reset the DatabasePool singleton between tests."""
    from eve_shared.database import DatabasePool
    # Save and clear singleton state
    original_instance = DatabasePool._instance
    original_pool = DatabasePool._pool
    DatabasePool._instance = None
    DatabasePool._pool = None

    yield

    # Restore
    DatabasePool._instance = original_instance
    DatabasePool._pool = original_pool


def _make_pool(service_name=None):
    """Create a DatabasePool wired to a MockPool, bypassing real DB init."""
    from eve_shared.database import DatabasePool
    pool = DatabasePool()
    pool._pool = MockPool()
    pool._service_name = service_name
    return pool


# ---------------------------------------------------------------------------
# Tests: cursor() basic behaviour (no metrics dependency)
# ---------------------------------------------------------------------------

class TestCursorBasic:
    """cursor() works correctly regardless of prometheus_client presence."""

    def test_cursor_yields_cursor_object(self):
        pool = _make_pool()
        with pool.cursor() as cur:
            assert hasattr(cur, 'execute')

    def test_cursor_commits_on_success(self):
        pool = _make_pool()
        conn = pool._pool._conn
        with pool.cursor() as cur:
            cur.execute("SELECT 1")
        assert conn.committed is True
        assert conn.rolled_back is False

    def test_cursor_rolls_back_on_exception(self):
        pool = _make_pool()
        conn = pool._pool._conn
        with pytest.raises(ValueError):
            with pool.cursor() as cur:
                raise ValueError("boom")
        assert conn.rolled_back is True

    def test_cursor_accepts_operation_param(self):
        """operation parameter accepted without error (even if no metrics)."""
        pool = _make_pool()
        with pool.cursor(operation="insert") as cur:
            cur.execute("INSERT INTO t VALUES (1)")

    def test_cursor_without_service_name_no_crash(self):
        """When service_name is not set, metrics are silently skipped."""
        pool = _make_pool(service_name=None)
        with pool.cursor() as cur:
            cur.execute("SELECT 1")


# ---------------------------------------------------------------------------
# Tests: cursor() without prometheus_client installed (soft dependency)
# ---------------------------------------------------------------------------

class TestCursorWithoutPrometheus:
    """When prometheus_client is NOT importable, cursor still works."""

    def test_cursor_works_when_prometheus_unavailable(self):
        """Simulate prometheus_client not installed by patching the flag."""
        import eve_shared.database as db_mod
        original = db_mod._PROMETHEUS_AVAILABLE
        db_mod._PROMETHEUS_AVAILABLE = False
        try:
            pool = _make_pool(service_name="test-service")
            with pool.cursor(operation="select") as cur:
                cur.execute("SELECT 1")
            # No crash = success
        finally:
            db_mod._PROMETHEUS_AVAILABLE = original

    def test_record_metrics_noop_when_unavailable(self):
        """_record_metrics does nothing when prometheus is unavailable."""
        import eve_shared.database as db_mod
        original = db_mod._PROMETHEUS_AVAILABLE
        db_mod._PROMETHEUS_AVAILABLE = False
        try:
            pool = _make_pool(service_name="test-service")
            # Should not raise
            pool._record_metrics("query", "success", 0.05)
        finally:
            db_mod._PROMETHEUS_AVAILABLE = original


# ---------------------------------------------------------------------------
# Tests: Prometheus metrics are recorded when available
# ---------------------------------------------------------------------------

class TestCursorWithPrometheus:
    """When prometheus_client IS installed, metrics are recorded correctly."""

    def test_prometheus_is_available(self):
        """Verify prometheus_client is importable in the test environment."""
        import eve_shared.database as db_mod
        assert db_mod._PROMETHEUS_AVAILABLE is True

    def test_metrics_recorded_on_success(self):
        """Histogram and Counter are called on successful cursor usage."""
        import eve_shared.database as db_mod

        mock_histogram = MagicMock()
        mock_counter = MagicMock()
        orig_hist = db_mod._db_query_duration_seconds
        orig_counter = db_mod._db_queries_total
        db_mod._db_query_duration_seconds = mock_histogram
        db_mod._db_queries_total = mock_counter

        try:
            pool = _make_pool(service_name="test-svc")
            with pool.cursor(operation="select") as cur:
                cur.execute("SELECT 1")

            # Histogram: .labels(service=..., operation=...).observe(duration)
            mock_histogram.labels.assert_called_once_with(service="test-svc", operation="select")
            mock_histogram.labels.return_value.observe.assert_called_once()
            duration = mock_histogram.labels.return_value.observe.call_args[0][0]
            assert isinstance(duration, float)
            assert duration >= 0

            # Counter: .labels(service=..., operation=..., status="success").inc()
            mock_counter.labels.assert_called_once_with(
                service="test-svc", operation="select", status="success"
            )
            mock_counter.labels.return_value.inc.assert_called_once()
        finally:
            db_mod._db_query_duration_seconds = orig_hist
            db_mod._db_queries_total = orig_counter

    def test_metrics_recorded_on_error(self):
        """Counter records status='error' when cursor raises."""
        import eve_shared.database as db_mod

        mock_histogram = MagicMock()
        mock_counter = MagicMock()
        orig_hist = db_mod._db_query_duration_seconds
        orig_counter = db_mod._db_queries_total
        db_mod._db_query_duration_seconds = mock_histogram
        db_mod._db_queries_total = mock_counter

        try:
            pool = _make_pool(service_name="test-svc")
            with pytest.raises(RuntimeError):
                with pool.cursor(operation="insert") as cur:
                    raise RuntimeError("db error")

            mock_counter.labels.assert_called_once_with(
                service="test-svc", operation="insert", status="error"
            )
            mock_counter.labels.return_value.inc.assert_called_once()
        finally:
            db_mod._db_query_duration_seconds = orig_hist
            db_mod._db_queries_total = orig_counter

    def test_metrics_skipped_without_service_name(self):
        """When service_name is None, metrics are not recorded."""
        import eve_shared.database as db_mod

        mock_histogram = MagicMock()
        mock_counter = MagicMock()
        orig_hist = db_mod._db_query_duration_seconds
        orig_counter = db_mod._db_queries_total
        db_mod._db_query_duration_seconds = mock_histogram
        db_mod._db_queries_total = mock_counter

        try:
            pool = _make_pool(service_name=None)
            with pool.cursor() as cur:
                cur.execute("SELECT 1")

            mock_histogram.labels.assert_not_called()
            mock_counter.labels.assert_not_called()
        finally:
            db_mod._db_query_duration_seconds = orig_hist
            db_mod._db_queries_total = orig_counter

    def test_default_operation_is_query(self):
        """When operation is not specified, it defaults to 'query'."""
        import eve_shared.database as db_mod

        mock_histogram = MagicMock()
        mock_counter = MagicMock()
        orig_hist = db_mod._db_query_duration_seconds
        orig_counter = db_mod._db_queries_total
        db_mod._db_query_duration_seconds = mock_histogram
        db_mod._db_queries_total = mock_counter

        try:
            pool = _make_pool(service_name="test-svc")
            with pool.cursor() as cur:
                cur.execute("SELECT 1")

            mock_histogram.labels.assert_called_once_with(service="test-svc", operation="query")
            mock_counter.labels.assert_called_once_with(
                service="test-svc", operation="query", status="success"
            )
        finally:
            db_mod._db_query_duration_seconds = orig_hist
            db_mod._db_queries_total = orig_counter

    def test_duration_reflects_actual_time(self):
        """Observed duration should reflect time spent inside cursor block."""
        import eve_shared.database as db_mod

        mock_histogram = MagicMock()
        mock_counter = MagicMock()
        orig_hist = db_mod._db_query_duration_seconds
        orig_counter = db_mod._db_queries_total
        db_mod._db_query_duration_seconds = mock_histogram
        db_mod._db_queries_total = mock_counter

        try:
            pool = _make_pool(service_name="test-svc")
            with pool.cursor() as cur:
                time.sleep(0.05)  # 50ms

            duration = mock_histogram.labels.return_value.observe.call_args[0][0]
            assert duration >= 0.04  # Allow small timing variance
        finally:
            db_mod._db_query_duration_seconds = orig_hist
            db_mod._db_queries_total = orig_counter


# ---------------------------------------------------------------------------
# Tests: metric name compatibility with war-intel's database.py
# ---------------------------------------------------------------------------

class TestMetricCompatibility:
    """Verify metric names match war-intel's database.py for drop-in replacement."""

    def test_histogram_metric_name(self):
        """Histogram metric name matches war-intel's db_query_duration_seconds."""
        import eve_shared.database as db_mod
        assert db_mod._PROMETHEUS_AVAILABLE is True
        assert db_mod._db_query_duration_seconds._name == 'db_query_duration_seconds'

    def test_counter_metric_name(self):
        """Counter metric name matches war-intel's db_queries_total."""
        import eve_shared.database as db_mod
        assert db_mod._PROMETHEUS_AVAILABLE is True
        # prometheus_client stores counters with _name='db_queries' but exposes
        # 'db_queries_total' as the full metric name (_total suffix is automatic).
        assert db_mod._db_queries_total._name == 'db_queries'

    def test_histogram_labels(self):
        """Histogram has 'service' and 'operation' labels."""
        import eve_shared.database as db_mod
        assert 'service' in db_mod._db_query_duration_seconds._labelnames
        assert 'operation' in db_mod._db_query_duration_seconds._labelnames

    def test_counter_labels(self):
        """Counter has 'service', 'operation', and 'status' labels."""
        import eve_shared.database as db_mod
        labels = db_mod._db_queries_total._labelnames
        assert 'service' in labels
        assert 'operation' in labels
        assert 'status' in labels
