"""Database connection pool management."""

import time
import threading
from contextlib import contextmanager
from typing import Optional, Generator
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

from eve_shared.config import get_config

# Optional Prometheus metrics — no-op if prometheus_client is not installed.
# Imports from eve_shared.metrics to reuse the same metric instances and avoid
# duplicate timeseries errors when both modules are loaded in the same process.
try:
    from eve_shared.metrics import db_query_duration_seconds as _db_query_duration_seconds
    from eve_shared.metrics import db_queries_total as _db_queries_total
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False
    _db_query_duration_seconds = None
    _db_queries_total = None


class DatabasePool:
    """Thread-safe PostgreSQL connection pool."""

    _instance: Optional["DatabasePool"] = None
    _pool: Optional[ThreadedConnectionPool] = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def initialize(
        self,
        dsn: Optional[str] = None,
        min_conn: int = 2,
        max_conn: int = 10,
        service_name: Optional[str] = None,
    ):
        """Initialize the connection pool.

        Args:
            dsn: PostgreSQL DSN. Defaults to config.postgres_dsn.
            min_conn: Minimum connections in the pool.
            max_conn: Maximum connections in the pool.
            service_name: Service name label for Prometheus metrics.
                          If None, metrics are not emitted.
        """
        if self._pool is not None:  # Fast path
            return

        with self._lock:
            if self._pool is not None:  # Double-check after acquiring lock
                return

            self._service_name = service_name

            config = get_config()
            dsn = dsn or config.postgres_dsn

            self._pool = ThreadedConnectionPool(
                min_conn,
                max_conn,
                dsn,
                options="-c client_min_messages=ERROR"  # Suppress warnings
            )

    @contextmanager
    def connection(self) -> Generator:
        """Get a connection from the pool."""
        if self._pool is None:
            self.initialize()

        conn = self._pool.getconn()
        try:
            yield conn
        finally:
            self._pool.putconn(conn)

    @contextmanager
    def cursor(self, cursor_factory=RealDictCursor, operation: str = "query") -> Generator:
        """Get a cursor with automatic connection management and optional metrics.

        Args:
            cursor_factory: psycopg2 cursor factory. Defaults to RealDictCursor.
            operation: Operation label for Prometheus metrics (e.g. "query", "insert").
        """
        with self.connection() as conn:
            start_time = time.time()
            status = "success"
            try:
                with conn.cursor(cursor_factory=cursor_factory) as cur:
                    yield cur
                conn.commit()
            except Exception:
                conn.rollback()
                status = "error"
                raise
            finally:
                self._record_metrics(operation, status, time.time() - start_time)

    def _record_metrics(self, operation: str, status: str, duration: float) -> None:
        """Record Prometheus metrics if available and service_name is set."""
        if not _PROMETHEUS_AVAILABLE:
            return
        service_name = getattr(self, '_service_name', None)
        if not service_name:
            return
        _db_query_duration_seconds.labels(service=service_name, operation=operation).observe(duration)
        _db_queries_total.labels(service=service_name, operation=operation, status=status).inc()

    def close(self):
        """Close all connections."""
        if self._pool:
            self._pool.closeall()
            self._pool = None


def get_db() -> DatabasePool:
    """Get the database pool singleton."""
    return DatabasePool()
