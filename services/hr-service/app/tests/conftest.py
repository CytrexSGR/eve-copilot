"""Shared fixtures for hr-service tests."""

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

    @property
    def call_count(self):
        return len(self._executed)


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


class MockRedisClient:
    """Mock Redis client for Bloom filter testing."""

    def __init__(self):
        self._bits = {}
        self._keys = {}

    def setbit(self, key, offset, value):
        if key not in self._bits:
            self._bits[key] = {}
        self._bits[key][offset] = value

    def getbit(self, key, offset):
        if key not in self._bits:
            return 0
        return self._bits[key].get(offset, 0)

    def delete(self, key):
        self._bits.pop(key, None)

    def pipeline(self):
        return MockPipeline(self)


class MockPipeline:
    """Mock Redis pipeline for batched operations."""

    def __init__(self, redis_client):
        self._client = redis_client
        self._commands = []

    def setbit(self, key, offset, value):
        self._commands.append(("setbit", key, offset, value))
        return self

    def getbit(self, key, offset):
        self._commands.append(("getbit", key, offset))
        return self

    def execute(self):
        results = []
        for cmd in self._commands:
            if cmd[0] == "setbit":
                self._client.setbit(cmd[1], cmd[2], cmd[3])
                results.append(0)
            elif cmd[0] == "getbit":
                results.append(self._client.getbit(cmd[1], cmd[2]))
        self._commands = []
        return results


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
def mock_redis():
    """Create a MockRedisClient instance."""
    return MockRedisClient()
