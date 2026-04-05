"""Stub database module wrapping monolith src.database for compatibility.

Various monolith modules import DatabasePool and related functions from
src.core.database, but the original module was deleted during monolith
decommission. This shim wraps the existing src.database.get_db_connection
to provide the interface expected by consumers.
"""

from contextlib import contextmanager
from src.database import get_db_connection


class DatabasePool:
    """Compatibility shim wrapping get_db_connection.

    The original DatabasePool accepted settings and managed a connection pool.
    This shim ignores settings and delegates to get_db_connection(), which
    creates a new connection per call (sufficient for batch job scripts).
    """

    def __init__(self, settings=None, *args, **kwargs):
        """Accept and ignore settings for compatibility."""
        pass

    @contextmanager
    def get_connection(self):
        """Get a database connection via the monolith's get_db_connection."""
        with get_db_connection() as conn:
            yield conn


def get_database_pool():
    """Factory function returning a DatabasePool instance."""
    return DatabasePool()


def get_db_pool():
    """Alias for get_database_pool (used by market_hot_items_refresher)."""
    return DatabasePool()
