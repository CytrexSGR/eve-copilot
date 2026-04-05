"""Tests for _get_coalition_members() Union-Find algorithm with mock data."""

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.routers.powerbloc._shared import _get_coalition_members
from eve_shared.constants.coalition import WEIGHTED_TOGETHER_RATIO as MIN_TOGETHER_RATIO
from app.utils.cache import _cache


@pytest.fixture(autouse=True)
def clear_coalition_cache():
    """Clear cache before each test to prevent cross-test contamination."""
    _cache.clear()
    yield
    _cache.clear()


def _make_dict_cursor(call_results):
    """Create a mock cursor that returns different results per execute() call.

    Args:
        call_results: list of lists — each inner list is the fetchall() result
                      for the corresponding execute() call.
    """
    cur = MagicMock()
    call_index = {"i": 0}

    def mock_execute(sql, params=None):
        pass

    def mock_fetchall():
        idx = call_index["i"]
        call_index["i"] += 1
        if idx < len(call_results):
            return call_results[idx]
        return []

    cur.execute = mock_execute
    cur.fetchall = mock_fetchall
    return cur


class TestBasicCoalition:
    def test_single_alliance_no_partners(self):
        """Leader with no fight-together data returns just itself."""
        cur = _make_dict_cursor([
            [],  # fight_together: no pairs
            [{"alliance_id": 100, "total_kills": 500}],  # alliance_activity
            [],  # fight_against
            [{"alliance_id": 100, "alliance_name": "Test Alliance", "ticker": "TEST"}],  # name_cache
        ])
        member_ids, name, name_map, ticker_map = _get_coalition_members(100, cur)
        assert member_ids == [100]
        assert name == "Test Alliance"

    def test_two_allied_alliances(self):
        """Two alliances with high fights_together and low fights_against merge."""
        cur = _make_dict_cursor([
            # fight_together pairs
            [{"alliance_a": 100, "alliance_b": 200, "fights_together": 500, "fights_against": 0}],
            # alliance_activity
            [
                {"alliance_id": 100, "total_kills": 1000},
                {"alliance_id": 200, "total_kills": 800},
            ],
            # fight_against (no confirmed enemies)
            [],
            # name_cache
            [
                {"alliance_id": 100, "alliance_name": "Alpha Alliance", "ticker": "ALPH"},
                {"alliance_id": 200, "alliance_name": "Beta Alliance", "ticker": "BETA"},
            ],
        ])
        member_ids, name, name_map, ticker_map = _get_coalition_members(100, cur)
        assert set(member_ids) == {100, 200}
        assert "Coalition" in name
        assert name_map[100] == "Alpha Alliance"
        assert ticker_map[200] == "BETA"


class TestEnemyExclusion:
    def test_confirmed_enemies_not_merged(self):
        """Alliances with confirmed enemy status are not merged."""
        cur = _make_dict_cursor([
            # fight_together: 100-200 fight together
            [{"alliance_a": 100, "alliance_b": 200, "fights_together": 500, "fights_against": 0}],
            # alliance_activity
            [
                {"alliance_id": 100, "total_kills": 1000},
                {"alliance_id": 200, "total_kills": 800},
            ],
            # fight_against: 100 and 200 are confirmed enemies
            [{"alliance_a": 100, "alliance_b": 200}],
            # name_cache
            [{"alliance_id": 100, "alliance_name": "Alpha", "ticker": "A"}],
        ])
        member_ids, name, name_map, ticker_map = _get_coalition_members(100, cur)
        assert member_ids == [100]

    def test_high_against_ratio_excludes(self):
        """Alliances with fights_together/fights_against < MIN_TOGETHER_RATIO are excluded."""
        ratio_below = int(200 / MIN_TOGETHER_RATIO) + 1  # fights_against > together/ratio
        cur = _make_dict_cursor([
            # fight_together with too much fighting against
            [{"alliance_a": 100, "alliance_b": 200,
              "fights_together": 200, "fights_against": ratio_below}],
            # alliance_activity
            [
                {"alliance_id": 100, "total_kills": 1000},
                {"alliance_id": 200, "total_kills": 800},
            ],
            # fight_against (no confirmed enemies at 100 threshold)
            [],
            # name_cache
            [{"alliance_id": 100, "alliance_name": "Solo Alliance", "ticker": "SOLO"}],
        ])
        member_ids, name, name_map, ticker_map = _get_coalition_members(100, cur)
        assert member_ids == [100]


class TestSortingAndLimits:
    def test_members_sorted_by_activity(self):
        """Coalition members should be sorted by total_kills descending."""
        cur = _make_dict_cursor([
            # Multiple allies
            [
                {"alliance_a": 100, "alliance_b": 200, "fights_together": 500, "fights_against": 0},
                {"alliance_a": 100, "alliance_b": 300, "fights_together": 400, "fights_against": 0},
            ],
            # alliance_activity (300 is most active, 100 second, 200 least)
            [
                {"alliance_id": 300, "total_kills": 2000},
                {"alliance_id": 100, "total_kills": 1000},
                {"alliance_id": 200, "total_kills": 500},
            ],
            # No enemies
            [],
            # name_cache
            [
                {"alliance_id": 100, "alliance_name": "A100", "ticker": "100"},
                {"alliance_id": 200, "alliance_name": "A200", "ticker": "200"},
                {"alliance_id": 300, "alliance_name": "A300", "ticker": "300"},
            ],
        ])
        member_ids, name, name_map, ticker_map = _get_coalition_members(100, cur)
        assert set(member_ids) == {100, 200, 300}
        # Should be sorted by activity: 300 (2000), 100 (1000), 200 (500)
        assert member_ids[0] == 300
        assert member_ids[1] == 100
        assert member_ids[2] == 200


class TestNamingConventions:
    def test_single_member_no_coalition_suffix(self):
        """Single-member 'coalition' uses alliance name without 'Coalition' suffix."""
        cur = _make_dict_cursor([
            [],
            [{"alliance_id": 100, "total_kills": 500}],
            [],
            [{"alliance_id": 100, "alliance_name": "Solo Corp", "ticker": "SC"}],
        ])
        _, name, _, _ = _get_coalition_members(100, cur)
        assert name == "Solo Corp"
        assert "Coalition" not in name

    def test_multi_member_gets_coalition_suffix(self):
        """Multi-member coalition appends ' Coalition' to leader name."""
        cur = _make_dict_cursor([
            [{"alliance_a": 100, "alliance_b": 200, "fights_together": 500, "fights_against": 0}],
            [
                {"alliance_id": 100, "total_kills": 1000},
                {"alliance_id": 200, "total_kills": 800},
            ],
            [],
            [
                {"alliance_id": 100, "alliance_name": "Big Alliance", "ticker": "BIG"},
                {"alliance_id": 200, "alliance_name": "Ally", "ticker": "ALY"},
            ],
        ])
        _, name, _, _ = _get_coalition_members(100, cur)
        # Leader is sorted by activity, so the most active alliance name is used
        assert "Coalition" in name
