"""Database compatibility layer for migrated code.

Provides the same interface as the monolith's database module
but uses the eve_shared library under the hood.
"""

from contextlib import contextmanager
from typing import Generator
from eve_shared import get_db
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """Get a database connection from the pool.

    Returns a connection that should be used with a context manager
    or manually closed.
    """
    db = get_db()
    if db._pool is None:
        db.initialize()
    return db._pool.getconn()


def release_db_connection(conn):
    """Release a connection back to the pool."""
    db = get_db()
    if db._pool and conn:
        db._pool.putconn(conn)


@contextmanager
def db_cursor(cursor_factory=RealDictCursor) -> Generator:
    """Get a cursor with automatic connection management.

    Compatible with the monolith's cursor pattern.
    """
    db = get_db()
    with db.cursor(cursor_factory=cursor_factory) as cur:
        yield cur
