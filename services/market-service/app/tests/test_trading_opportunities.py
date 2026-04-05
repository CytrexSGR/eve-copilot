"""Tests for trading opportunities service."""

import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager

from app.routers.trading_opportunities import TradingOpportunitiesService


# ---------------------------------------------------------------------------
# Mock DB helpers
# ---------------------------------------------------------------------------

class MockCursor:
    """Mock psycopg2 RealDictCursor."""

    def __init__(self, rows=None):
        self._rows = rows or []

    def execute(self, query, params=None):
        pass

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class MockDB:
    """Mock DatabasePool that supports cursor() context manager."""

    def __init__(self, cursor=None):
        self._cursor = cursor or MockCursor()

    def cursor(self):
        return self._cursor


# ---------------------------------------------------------------------------
# get_region_name
# ---------------------------------------------------------------------------

class TestGetRegionName:
    """Tests for TradingOpportunitiesService.get_region_name()."""

    def test_known_hub_the_forge(self):
        """The Forge (Jita) is returned from the hardcoded dict."""
        svc = TradingOpportunitiesService(db=MockDB(), redis=None)
        assert svc.get_region_name(10000002) == "The Forge"

    def test_known_hub_domain(self):
        """Domain (Amarr) is returned from the hardcoded dict."""
        svc = TradingOpportunitiesService(db=MockDB(), redis=None)
        assert svc.get_region_name(10000043) == "Domain"

    def test_known_hub_heimatar(self):
        """Heimatar (Rens) is returned from the hardcoded dict."""
        svc = TradingOpportunitiesService(db=MockDB(), redis=None)
        assert svc.get_region_name(10000030) == "Heimatar"

    def test_known_hub_sinq_laison(self):
        """Sinq Laison (Dodixie) is returned from the hardcoded dict."""
        svc = TradingOpportunitiesService(db=MockDB(), redis=None)
        assert svc.get_region_name(10000032) == "Sinq Laison"

    def test_known_hub_metropolis(self):
        """Metropolis (Hek) is returned from the hardcoded dict."""
        svc = TradingOpportunitiesService(db=MockDB(), redis=None)
        assert svc.get_region_name(10000042) == "Metropolis"

    def test_non_hub_region_from_db(self):
        """Non-hub region ID queries the DB and returns the name."""
        cursor = MockCursor(rows=[{"regionName": "Tribute"}])
        db = MockDB(cursor=cursor)
        svc = TradingOpportunitiesService(db=db, redis=None)
        result = svc.get_region_name(10000010)
        assert result == "Tribute"

    def test_non_hub_region_not_found_in_db(self):
        """Non-hub region with no DB row returns fallback string."""
        cursor = MockCursor(rows=[])
        db = MockDB(cursor=cursor)
        svc = TradingOpportunitiesService(db=db, redis=None)
        result = svc.get_region_name(99999999)
        assert result == "Region 99999999"

    def test_non_hub_region_db_exception(self):
        """DB exception returns fallback string without crashing."""
        db = MagicMock()
        db.cursor.side_effect = Exception("connection refused")
        svc = TradingOpportunitiesService(db=db, redis=None)
        result = svc.get_region_name(10000010)
        assert result == "Region 10000010"

    def test_non_hub_does_not_crash_with_attribute_error(self):
        """Regression: old code called db.fetchrow() which doesn't exist on psycopg2 pools.
        This test verifies the fix works without AttributeError."""
        cursor = MockCursor(rows=[{"regionName": "Catch"}])
        db = MockDB(cursor=cursor)
        svc = TradingOpportunitiesService(db=db, redis=None)
        # This would raise AttributeError with the old asyncpg-style code
        result = svc.get_region_name(10000014)
        assert result == "Catch"


# ---------------------------------------------------------------------------
# get_tradeable_items
# ---------------------------------------------------------------------------

class TestGetTradeableItems:
    """Tests for TradingOpportunitiesService.get_tradeable_items()."""

    def test_returns_items(self):
        """Returns list of dicts with typeID and typeName."""
        rows = [
            {"typeID": 2488, "typeName": "Small Armor Repairer I", "volume": 5.0},
            {"typeID": 3170, "typeName": "Drone Damage Amplifier I", "volume": 5.0},
        ]
        cursor = MockCursor(rows=rows)
        db = MockDB(cursor=cursor)
        svc = TradingOpportunitiesService(db=db, redis=None)
        result = svc.get_tradeable_items(limit=100)
        assert len(result) == 2
        assert result[0] == {"typeID": 2488, "typeName": "Small Armor Repairer I"}
        assert result[1] == {"typeID": 3170, "typeName": "Drone Damage Amplifier I"}

    def test_empty_result(self):
        """Returns empty list when no items match."""
        cursor = MockCursor(rows=[])
        db = MockDB(cursor=cursor)
        svc = TradingOpportunitiesService(db=db, redis=None)
        result = svc.get_tradeable_items()
        assert result == []

    def test_db_exception_returns_empty(self):
        """DB exception returns empty list without crashing."""
        db = MagicMock()
        db.cursor.side_effect = Exception("timeout")
        svc = TradingOpportunitiesService(db=db, redis=None)
        result = svc.get_tradeable_items()
        assert result == []


# ---------------------------------------------------------------------------
# calculate_recommendation
# ---------------------------------------------------------------------------

class TestCalculateRecommendation:
    """Tests for TradingOpportunitiesService.calculate_recommendation()."""

    def test_excellent_high_margin_high_volume_low_comp(self):
        """High margin + high volume + low competition = excellent."""
        svc = TradingOpportunitiesService(db=None, redis=None)
        rec, reason = svc.calculate_recommendation(margin=20, volume=1500, competition='low')
        assert rec == 'excellent'
        assert 'High margin' in reason
        assert 'high volume' in reason
        assert 'low competition' in reason

    def test_good_moderate_values(self):
        """Good margin + decent volume + moderate competition = good."""
        svc = TradingOpportunitiesService(db=None, redis=None)
        rec, reason = svc.calculate_recommendation(margin=12, volume=700, competition='medium')
        assert rec == 'good'

    def test_moderate_low_margin_decent_volume(self):
        """Moderate margin + decent volume + high competition = moderate."""
        svc = TradingOpportunitiesService(db=None, redis=None)
        rec, reason = svc.calculate_recommendation(margin=7, volume=600, competition='high')
        assert rec == 'moderate'

    def test_risky_low_everything(self):
        """Low margin + low volume + high competition = risky."""
        svc = TradingOpportunitiesService(db=None, redis=None)
        rec, reason = svc.calculate_recommendation(margin=3, volume=50, competition='high')
        assert rec == 'risky'

    def test_score_boundary_7_is_excellent(self):
        """Score exactly 7 should be excellent."""
        svc = TradingOpportunitiesService(db=None, redis=None)
        # margin >= 15 (+3), volume >= 500 (+2), competition low (+2) = 7
        rec, _ = svc.calculate_recommendation(margin=15, volume=500, competition='low')
        assert rec == 'excellent'

    def test_score_boundary_5_is_good(self):
        """Score exactly 5 should be good."""
        svc = TradingOpportunitiesService(db=None, redis=None)
        # margin >= 15 (+3), volume >= 500 (+2), competition high (+0) = 5
        rec, _ = svc.calculate_recommendation(margin=15, volume=500, competition='high')
        assert rec == 'good'

    def test_score_boundary_3_is_moderate(self):
        """Score exactly 3 should be moderate."""
        svc = TradingOpportunitiesService(db=None, redis=None)
        # margin >= 10 (+2), volume >= 100 (+1), competition high (+0) = 3
        rec, _ = svc.calculate_recommendation(margin=10, volume=100, competition='high')
        assert rec == 'moderate'

    def test_zero_margin_zero_volume(self):
        """Zero margin and volume = risky with high competition reason."""
        svc = TradingOpportunitiesService(db=None, redis=None)
        rec, reason = svc.calculate_recommendation(margin=0, volume=0, competition='high')
        assert rec == 'risky'
        assert 'high competition' in reason
