"""Shared fixtures for production-service tests."""

import pytest
from contextlib import contextmanager


class MockCursor:
    """Minimal mock cursor that returns pre-set rows via fetchall/fetchone.

    Usage:
        cur = MockCursor([(1, "foo"), (2, "bar")])
        cur.execute("SELECT ...")
        rows = cur.fetchall()  # [(1, "foo"), (2, "bar")]
    """

    def __init__(self, rows=None):
        self._rows = rows or []
        self._executed = []

    def execute(self, sql, params=None):
        self._executed.append((sql, params))

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def set_rows(self, rows):
        """Set rows for the next fetchall/fetchone call."""
        self._rows = rows

    @property
    def last_sql(self):
        return self._executed[-1][0] if self._executed else None

    @property
    def last_params(self):
        return self._executed[-1][1] if self._executed else None


class MultiResultCursor(MockCursor):
    """Mock cursor that returns different rows per execute() call.

    Usage:
        cur = MultiResultCursor([
            [(1, "A")],       # first execute
            [(2, "B")],       # second execute
        ])
    """

    def __init__(self, result_sets=None):
        super().__init__()
        self._result_sets = list(result_sets or [])
        self._call_index = 0

    def execute(self, sql, params=None):
        super().execute(sql, params)
        if self._call_index < len(self._result_sets):
            self._rows = self._result_sets[self._call_index]
        else:
            self._rows = []
        self._call_index += 1


class MockConnection:
    """Mock database connection with cursor context manager."""

    def __init__(self, cursor):
        self._cursor = cursor

    @contextmanager
    def cursor(self):
        yield self._cursor


class MockDB:
    """Mock database pool that provides connection() and cursor() context managers.

    Supports both patterns used in the production-service:
      - with self.db.connection() as conn: with conn.cursor() as cur:  (invention.py)
      - with self.db.cursor() as cur:  (structure_bonus.py)
    """

    def __init__(self, cursor):
        self._cursor = cursor
        self._conn = MockConnection(cursor)

    @contextmanager
    def connection(self):
        yield self._conn

    @contextmanager
    def cursor(self):
        yield self._cursor


@pytest.fixture
def mock_cursor():
    """Create a MockCursor instance."""
    return MockCursor()


@pytest.fixture
def multi_cursor():
    """Factory for MultiResultCursor instances."""
    def factory(result_sets):
        return MultiResultCursor(result_sets)
    return factory


@pytest.fixture
def mock_db():
    """Factory for MockDB with a given cursor."""
    def factory(cursor):
        return MockDB(cursor)
    return factory


# ── Common test data ──────────────────────────────────────────────

@pytest.fixture
def sample_materials():
    """Typical T2 manufacturing materials (type_id, base_qty)."""
    return [
        (34, 10000),    # Tritanium
        (35, 5000),     # Pyerite
        (36, 2000),     # Mexallon
        (11399, 100),   # Morphite
    ]


@pytest.fixture
def sample_invention_inputs():
    """Typical invention inputs (datacores)."""
    return [
        (20424, 2),  # Datacore - Mechanical Engineering
        (20172, 2),  # Datacore - Caldari Starship Engineering
    ]


@pytest.fixture
def sample_prices():
    """Price lookup dict for common materials."""
    return {
        34: 5.0,        # Tritanium
        35: 10.0,       # Pyerite
        36: 50.0,       # Mexallon
        11399: 10000.0, # Morphite
        20424: 50000.0, # Datacore ME
        20172: 60000.0, # Datacore CSE
    }
