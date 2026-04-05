"""Shared fixtures for shopping-service tests."""

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
    def rowcount(self):
        return len(self._rows)


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
def sample_route():
    """A typical freight route dict (as returned by _row_to_route)."""
    return {
        "id": 1,
        "name": "Jita to K-6K16",
        "start_system_id": 30000142,
        "start_system_name": "Jita",
        "end_system_id": 30003729,
        "end_system_name": "K-6K16",
        "route_type": "jf",
        "base_price": 10_000_000.0,
        "rate_per_m3": 500.0,
        "collateral_pct": 1.0,
        "max_volume": 360_000.0,
        "max_collateral": 3_000_000_000.0,
        "is_active": True,
        "notes": "Standard JF route",
    }


@pytest.fixture
def sample_db_row():
    """A raw database row dict for freight_routes (before _row_to_route)."""
    from decimal import Decimal
    return {
        "id": 1,
        "name": "Jita to K-6K16",
        "start_system_id": 30000142,
        "end_system_id": 30003729,
        "route_type": "jf",
        "base_price": Decimal("10000000"),
        "rate_per_m3": Decimal("500"),
        "collateral_pct": Decimal("1.0"),
        "max_volume": Decimal("360000"),
        "max_collateral": Decimal("3000000000"),
        "is_active": True,
        "notes": "Standard JF route",
        "start_name": "Jita",
        "end_name": "K-6K16",
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00",
    }
