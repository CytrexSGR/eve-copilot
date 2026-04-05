"""Shared fixtures for finance-service tests."""

import os

# Set required env vars BEFORE any app imports trigger pydantic validation.
# These are needed by eve_shared.ServiceConfig (inherited by FinanceConfig).
os.environ.setdefault("EVE_CLIENT_ID", "test_client_id")
os.environ.setdefault("EVE_CLIENT_SECRET", "test_client_secret")
os.environ.setdefault("EVE_CALLBACK_URL", "http://localhost/callback")

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
        self.rowcount = 0

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


# ──────────────────────── Sample Data Fixtures ──────────────────────────


@pytest.fixture
def sample_killmail_items_high_slots():
    """Killmail items with high-slot modules (flags 27-34)."""
    return [
        {"flag": 27, "item_type_id": 3170, "quantity_destroyed": 1, "quantity_dropped": 0},
        {"flag": 28, "item_type_id": 3170, "quantity_destroyed": 0, "quantity_dropped": 1},
        {"flag": 29, "item_type_id": 2929, "quantity_destroyed": 1, "quantity_dropped": 0},
    ]


@pytest.fixture
def sample_killmail_items_all_slots():
    """Killmail items covering all slot types."""
    return [
        # High slots (27-34)
        {"flag": 27, "item_type_id": 3170, "quantity_destroyed": 1, "quantity_dropped": 0},
        # Med slots (19-26)
        {"flag": 19, "item_type_id": 3841, "quantity_destroyed": 1, "quantity_dropped": 0},
        # Low slots (11-18)
        {"flag": 11, "item_type_id": 2048, "quantity_destroyed": 1, "quantity_dropped": 0},
        # Rig slots (92-99)
        {"flag": 92, "item_type_id": 26082, "quantity_destroyed": 1, "quantity_dropped": 0},
        # Drone bay (87)
        {"flag": 87, "item_type_id": 2488, "quantity_destroyed": 3, "quantity_dropped": 2},
    ]


@pytest.fixture
def sample_fitting():
    """A sample doctrine fitting structure."""
    return {
        "high": [
            {"type_id": 3170, "type_name": "Heavy Missile Launcher II", "quantity": 2},
        ],
        "med": [
            {"type_id": 3841, "type_name": "Large Shield Extender II", "quantity": 1},
        ],
        "low": [
            {"type_id": 2048, "type_name": "Damage Control II", "quantity": 1},
        ],
        "rig": [
            {"type_id": 26082, "type_name": "Medium Core Defense Field Extender I", "quantity": 1},
        ],
        "drones": [
            {"type_id": 2488, "type_name": "Hammerhead II", "quantity": 5},
        ],
    }


@pytest.fixture
def sample_eft_text():
    """Valid EFT fitting text."""
    return """[Drake, PvP Shield Drake]

Ballistic Control System II
Ballistic Control System II
Damage Control II

Large Shield Extender II
Large Shield Extender II
Adaptive Invulnerability Field II
Adaptive Invulnerability Field II

Heavy Missile Launcher II, Scourge Fury Heavy Missile
Heavy Missile Launcher II, Scourge Fury Heavy Missile
Heavy Missile Launcher II, Scourge Fury Heavy Missile

Medium Core Defense Field Extender I
Medium Core Defense Field Extender I
Medium Core Defense Field Extender I

Hammerhead II x5
Hobgoblin II x5"""
