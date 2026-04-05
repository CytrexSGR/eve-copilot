"""Shared fixtures for dotlan-service tests."""

import pytest


class MockCursor:
    """Minimal mock cursor that returns pre-set rows via fetchall/fetchone.

    Usage:
        cur = MockCursor([{"col": 1}, {"col": 2}])
        cur.execute("SELECT ...")
        rows = cur.fetchall()  # [{"col": 1}, {"col": 2}]
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
    """Mock cursor that returns different rows per execute() call."""

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
