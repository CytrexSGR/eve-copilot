"""Shared fixtures for character-service tests."""

import pytest


class MockCursor:
    """Minimal mock cursor that returns pre-set rows via fetchall/fetchone.

    Supports the context manager protocol so it works with::

        with db.cursor(cursor_factory=...) as cur:
            cur.execute(...)
            rows = cur.fetchall()

    Usage:
        cur = MockCursor([{"col": 1}, {"col": 2}])
        cur.execute("SELECT ...")
        rows = cur.fetchall()  # [{"col": 1}, {"col": 2}]
    """

    def __init__(self, rows=None):
        self._rows = rows or []
        self._executed = []

    # --- context manager protocol ---
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

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
            [row1, row2],  # first execute
            [row3],        # second execute
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


class MockDB:
    """Mock database connection manager for unit tests.

    Supports three usage patterns:

    1. Pre-built cursor (for tests that inspect cursor._executed)::

        cur = MockCursor([{"id": 1}])
        db = MockDB(cursor=cur)

    2. Single result set (cursor created internally)::

        db = MockDB(rows=[{"id": 1}])

    3. Multiple result sets (MultiResultCursor created internally)::

        db = MockDB(result_sets=[[row1], [row2]])

    The cursor() method returns a MockCursor that supports the context manager
    protocol, compatible with both ``with db.cursor() as cur:`` and
    ``cur = db.cursor(); cur.execute(...)`` patterns.
    """

    def __init__(self, rows=None, result_sets=None, cursor=None):
        self._cursor = cursor
        self._rows = rows
        self._result_sets = result_sets

    def cursor(self, cursor_factory=None):
        if self._cursor is not None:
            return self._cursor
        if self._result_sets is not None:
            return MultiResultCursor(self._result_sets)
        return MockCursor(self._rows)

    def connection(self):
        """Return a context manager yielding a mock connection."""
        from contextlib import contextmanager

        @contextmanager
        def _conn():
            yield self

        return _conn()


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
    """Create a MockDB instance with no pre-set data."""
    return MockDB()


@pytest.fixture
def dogma_engine():
    """Create a DogmaEngine instance without __init__ for unit testing.

    Usage: set engine.db, engine.DEFAULT_SKILL_LEVEL, etc. as needed per test.
    """
    from app.services.dogma.engine import DogmaEngine

    engine = DogmaEngine.__new__(DogmaEngine)
    engine.db = None
    engine.DEFAULT_SKILL_LEVEL = 5
    engine.ATTR_REQUIRED_SKILL_1 = 182
    engine.ATTR_REQUIRED_SKILL_2 = 183
    engine.CHARGE_DAMAGE_ATTR_IDS = {114, 116, 117, 118}
    return engine
