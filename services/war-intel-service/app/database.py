"""Database compatibility layer for migrated code.

Direct database connection without shared library caching issues.
"""

import os
import time
from contextlib import contextmanager
from typing import Generator, Optional
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

from eve_shared.metrics import db_query_duration_seconds, db_queries_total

SERVICE_NAME = "war-intel"


class DatabasePool:
    """Simple database connection pool."""

    _instance: Optional['DatabasePool'] = None
    _pool: Optional[ThreadedConnectionPool] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self):
        """Initialize the connection pool."""
        if self._pool is not None:
            return

        self._pool = ThreadedConnectionPool(
            minconn=int(os.getenv("DB_POOL_MIN", "2")),
            maxconn=int(os.getenv("DB_POOL_MAX", "10")),
            host=os.getenv("POSTGRES_HOST", "eve_db"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.getenv("POSTGRES_DB", "eve_sde"),
            user=os.getenv("POSTGRES_USER", "eve"),
            password=os.getenv("POSTGRES_PASSWORD", "")
        )

    @contextmanager
    def cursor(self, cursor_factory=RealDictCursor, operation: str = "query") -> Generator:
        """Get a cursor with automatic connection management and metrics."""
        if self._pool is None:
            self.initialize()

        conn = self._pool.getconn()
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
            duration = time.time() - start_time
            db_query_duration_seconds.labels(service=SERVICE_NAME, operation=operation).observe(duration)
            db_queries_total.labels(service=SERVICE_NAME, operation=operation, status=status).inc()
            self._pool.putconn(conn)


_db = DatabasePool()


def get_db_connection():
    """Get a database connection from the pool."""
    if _db._pool is None:
        _db.initialize()
    return _db._pool.getconn()


def release_db_connection(conn):
    """Release a connection back to the pool."""
    if _db._pool and conn:
        _db._pool.putconn(conn)


@contextmanager
def db_cursor(cursor_factory=RealDictCursor, operation: str = "query") -> Generator:
    """Get a cursor with automatic connection management."""
    with _db.cursor(cursor_factory=cursor_factory, operation=operation) as cur:
        yield cur
