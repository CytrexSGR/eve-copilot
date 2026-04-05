"""Shared fixtures for ectmap-service tests."""

import pytest
from datetime import datetime


class MockCursor:
    """Minimal mock cursor that returns pre-set rows."""

    def __init__(self, rows=None):
        self._rows = rows or []
        self._executed = []
        self.rowcount = 0

    def execute(self, sql, params=None):
        self._executed.append((sql, params))
        self.rowcount = len(self._rows)

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None


@pytest.fixture
def mock_cursor():
    return MockCursor()


@pytest.fixture
def sample_view_row():
    """Return a realistic map_views DB row dict."""
    return {
        "id": 1,
        "name": "Fraternity Sov Map",
        "description": "Daily sov snapshot",
        "map_type": "sovmap",
        "region": "Detorid",
        "width": 1920,
        "height": 1080,
        "params": {"colorMode": "sov", "showJammers": True},
        "auto_snapshot": True,
        "snapshot_schedule": "0 */6 * * *",
        "last_snapshot_at": datetime(2026, 2, 10, 12, 0, 0),
        "last_snapshot_id": "sovmap-20260210-120000-abc12345",
        "created_at": datetime(2026, 1, 15, 8, 30, 0),
    }
