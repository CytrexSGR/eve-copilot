"""Database compatibility layer for DOTLAN service.

Uses eve_shared library for connection pooling.
"""

from contextlib import contextmanager
from typing import Generator
from eve_shared import get_db, DatabasePool
from psycopg2.extras import RealDictCursor


@contextmanager
def db_cursor(cursor_factory=RealDictCursor) -> Generator:
    """Get a cursor with automatic connection management."""
    db = get_db()
    with db.cursor(cursor_factory=cursor_factory) as cur:
        yield cur
