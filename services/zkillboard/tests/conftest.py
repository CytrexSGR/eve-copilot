"""Shared test fixtures for zkillboard service tests."""

import sys
from unittest.mock import MagicMock
import pytest

# ---------------------------------------------------------------------------
# Stub out all src.* modules that are transitively imported by
# services/zkillboard/__init__.py before any test module is collected.
# These modules require a live database / external services and must not
# be imported in the unit-test environment.
# ---------------------------------------------------------------------------
_src_stubs = [
    "src",
    "src.database",
    "src.route_service",
    "src.telegram_service",
    "src.auth",
]
for _mod in _src_stubs:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Also stub redis so live_service / battle_tracker don't fail on import
for _mod in ["redis", "redis.asyncio"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()


@pytest.fixture
def sample_r2z2_response():
    """A sample R2Z2 killmail response matching the real API format."""
    return {
        "killmail_id": 133144542,
        "hash": "abc123def456",
        "zkb": {
            "hash": "abc123def456",
            "totalValue": 125000000.0,
            "points": 15,
            "npc": False,
            "awox": False,
            "solo": False,
        },
        "killmail": {
            "killmail_id": 133144542,
            "killmail_time": "2026-03-21T12:00:00Z",
            "solar_system_id": 30002537,
            "victim": {
                "character_id": 12345678,
                "corporation_id": 98000001,
                "alliance_id": 99000001,
                "ship_type_id": 17703,
                "items": [],
            },
            "attackers": [
                {
                    "character_id": 87654321,
                    "corporation_id": 98000002,
                    "alliance_id": 99000002,
                    "ship_type_id": 11393,
                    "weapon_type_id": 3170,
                    "damage_done": 15000,
                    "final_blow": True,
                }
            ],
        },
        "sequence_id": 96088891,
        "uploaded_at": 1711018800,
    }


@pytest.fixture
def sample_sequence_response():
    """A sample R2Z2 sequence.json response."""
    return {"sequence": 96088891}
