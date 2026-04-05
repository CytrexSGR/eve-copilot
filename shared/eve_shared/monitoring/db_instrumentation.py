"""Database query and connection pool instrumentation for Prometheus metrics."""

import time
import functools
from contextlib import contextmanager
from typing import Generator, Callable, Any
from psycopg2.extras import RealDictCursor

from eve_shared.metrics import (
    db_queries_total,
    db_query_duration_seconds,
    db_connections
)
from eve_shared.database import DatabasePool


def track_query(operation: str, service: str):
    """Decorator to track database query metrics.

    Usage:
        @track_query(operation="select_battles", service="war-intel")
        def get_active_battles(conn):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            status = "success"

            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.time() - start_time

                # Track query count
                db_queries_total.labels(
                    service=service,
                    operation=operation,
                    status=status
                ).inc()

                # Track query duration
                db_query_duration_seconds.labels(
                    service=service,
                    operation=operation
                ).observe(duration)

        return wrapper
    return decorator


@contextmanager
def tracked_cursor(
    db_pool: DatabasePool,
    operation: str,
    service: str,
    cursor_factory=RealDictCursor
) -> Generator:
    """Context manager for database cursors with automatic metrics tracking.

    Usage:
        with tracked_cursor(get_db(), "select_alliances", "war-intel") as cur:
            cur.execute("SELECT * FROM alliances")
    """
    start_time = time.time()
    status = "success"

    try:
        with db_pool.cursor(cursor_factory=cursor_factory) as cur:
            yield cur
    except Exception:
        status = "error"
        raise
    finally:
        duration = time.time() - start_time

        # Track query count
        db_queries_total.labels(
            service=service,
            operation=operation,
            status=status
        ).inc()

        # Track query duration
        db_query_duration_seconds.labels(
            service=service,
            operation=operation
        ).observe(duration)


def monitor_connection_pool(db_pool: DatabasePool, service: str):
    """Update connection pool metrics.

    Should be called periodically (e.g., every 30 seconds) to track pool status.

    Usage:
        # In background task or scheduled job
        monitor_connection_pool(get_db(), "war-intel")
    """
    if db_pool._pool is None:
        # Pool not initialized yet
        db_connections.labels(service=service, state="active").set(0)
        db_connections.labels(service=service, state="idle").set(0)
        return

    # psycopg2 ThreadedConnectionPool doesn't expose detailed stats
    # We can only track what we know from initialization
    pool = db_pool._pool

    # Get pool configuration
    minconn = pool.minconn if hasattr(pool, 'minconn') else 2
    maxconn = pool.maxconn if hasattr(pool, 'maxconn') else 10

    # Approximate active/idle based on pool usage
    # Note: ThreadedConnectionPool doesn't expose detailed metrics,
    # so we set conservative estimates

    # Access the internal pool state (this is somewhat fragile but works)
    # _used is a set of connections currently in use
    # _pool is a list of available connections
    try:
        active = len(pool._used) if hasattr(pool, '_used') else 0
        idle = len(pool._pool) if hasattr(pool, '_pool') else 0

        db_connections.labels(service=service, state="active").set(active)
        db_connections.labels(service=service, state="idle").set(idle)

        # Calculate waiting (connections that want a connection but can't get one)
        # This would require tracking but ThreadedConnectionPool doesn't expose it
        # For now we set to 0, but in production you'd want a custom pool wrapper
        db_connections.labels(service=service, state="waiting").set(0)

    except AttributeError:
        # Fallback if internal structure changes
        db_connections.labels(service=service, state="active").set(0)
        db_connections.labels(service=service, state="idle").set(minconn)
        db_connections.labels(service=service, state="waiting").set(0)
