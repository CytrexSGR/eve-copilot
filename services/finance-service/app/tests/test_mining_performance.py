"""Tests for MiningTaxService extraction status derivation and performance metrics.

Covers:
- get_extractions(): status derivation (active/ready/expired) from timestamps
- get_performance(): aggregation, isk_per_day, ore percentage calculation
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_db(cursor_rows):
    """Create a mock DB where db.cursor() context manager yields a mock cursor."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = cursor_rows
    mock_cursor.fetchone.return_value = cursor_rows[0] if cursor_rows else None
    mock_db.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_db.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_db


def _make_multi_result_db(result_sets):
    """Create a mock DB whose cursor returns different rows per cursor() call.

    Each call to db.cursor() creates a new context manager with the next result set.
    This is needed for methods like get_performance() that open multiple cursor blocks.
    """
    mock_db = MagicMock()
    call_count = [0]

    def cursor_side_effect():
        ctx = MagicMock()
        cur = MagicMock()
        idx = min(call_count[0], len(result_sets) - 1)
        cur.fetchall.return_value = result_sets[idx]
        cur.fetchone.return_value = result_sets[idx][0] if result_sets[idx] else None
        call_count[0] += 1
        ctx.__enter__ = MagicMock(return_value=cur)
        ctx.__exit__ = MagicMock(return_value=False)
        return ctx

    mock_db.cursor.side_effect = cursor_side_effect
    return mock_db


def _build_service(mock_db):
    """Instantiate MiningTaxService with a pre-built mock DB."""
    with patch("app.services.mining_tax.get_db", return_value=mock_db), \
         patch("app.services.mining_tax.EsiClient"):
        from app.services.mining_tax import MiningTaxService
        svc = MiningTaxService()
    return svc


# ---------------------------------------------------------------------------
# Extraction Status Tests
# ---------------------------------------------------------------------------


class TestExtractionStatus:
    """Test get_extractions() status derivation from chunk_arrival / natural_decay."""

    def test_active_extraction_future_arrival(self):
        """chunk_arrival_time in future -> status 'active'."""
        now = datetime.now(timezone.utc)
        row = {
            "structure_id": 1000000001,
            "moon_id": 40000001,
            "extraction_start_time": now - timedelta(days=3),
            "chunk_arrival_time": now + timedelta(hours=12),
            "natural_decay_time": now + timedelta(days=2),
        }
        mock_db = _make_mock_db([row])
        svc = _build_service(mock_db)

        results = svc.get_extractions(corp_id=98000001)

        assert len(results) == 1
        assert results[0]["status"] == "active"
        assert results[0]["structure_id"] == 1000000001
        assert results[0]["moon_id"] == 40000001

    def test_ready_extraction_arrived_not_decayed(self):
        """chunk_arrival_time passed, natural_decay_time in future -> status 'ready'."""
        now = datetime.now(timezone.utc)
        row = {
            "structure_id": 1000000002,
            "moon_id": 40000002,
            "extraction_start_time": now - timedelta(days=5),
            "chunk_arrival_time": now - timedelta(hours=6),
            "natural_decay_time": now + timedelta(hours=18),
        }
        mock_db = _make_mock_db([row])
        svc = _build_service(mock_db)

        results = svc.get_extractions(corp_id=98000001)

        assert len(results) == 1
        assert results[0]["status"] == "ready"

    def test_expired_extraction_past_decay(self):
        """natural_decay_time passed -> status 'expired'."""
        now = datetime.now(timezone.utc)
        row = {
            "structure_id": 1000000003,
            "moon_id": 40000003,
            "extraction_start_time": now - timedelta(days=7),
            "chunk_arrival_time": now - timedelta(days=2),
            "natural_decay_time": now - timedelta(hours=1),
        }
        mock_db = _make_mock_db([row])
        svc = _build_service(mock_db)

        results = svc.get_extractions(corp_id=98000001)

        assert len(results) == 1
        assert results[0]["status"] == "expired"

    def test_empty_extractions(self):
        """No rows from DB -> empty list returned."""
        mock_db = _make_mock_db([])
        svc = _build_service(mock_db)

        results = svc.get_extractions(corp_id=98000001)

        assert results == []


# ---------------------------------------------------------------------------
# Performance Metrics Tests
# ---------------------------------------------------------------------------


class TestPerformanceMetrics:
    """Test get_performance() aggregation and derived calculations."""

    def test_performance_with_structures(self):
        """Two structures with ISK data produce correct totals and per-struct percentages."""
        structure_rows = [
            {
                "observer_id": 5001,
                "total_isk": Decimal("1000000000"),  # 1B
                "unique_miners": 10,
                "active_days": 20,
            },
            {
                "observer_id": 5002,
                "total_isk": Decimal("500000000"),  # 500M
                "unique_miners": 5,
                "active_days": 15,
            },
        ]
        ore_rows = [
            {"rarity": "R64", "total_isk": Decimal("800000000")},
            {"rarity": "R32", "total_isk": Decimal("700000000")},
        ]
        mock_db = _make_multi_result_db([structure_rows, ore_rows])
        svc = _build_service(mock_db)

        result = svc.get_performance(corp_id=98000001, days=30)

        # Total ISK = 1B + 500M = 1.5B
        assert result["total_isk_mined"] == 1_500_000_000.0
        # ISK per day = 1.5B / 30
        assert result["isk_per_day"] == round(1_500_000_000.0 / 30, 2)
        assert result["period_days"] == 30
        assert result["corporation_id"] == 98000001

        # Structure performance percentages
        sp = result["structure_performance"]
        assert len(sp) == 2
        assert sp[0]["observer_id"] == 5001
        assert sp[0]["percentage"] == round(1_000_000_000.0 / 1_500_000_000.0 * 100, 1)
        assert sp[1]["observer_id"] == 5002
        assert sp[1]["unique_miners"] == 5
        assert sp[1]["active_days"] == 15

    def test_performance_empty_data(self):
        """No data produces zeros and empty lists."""
        mock_db = _make_multi_result_db([[], []])
        svc = _build_service(mock_db)

        result = svc.get_performance(corp_id=98000001, days=30)

        assert result["total_isk_mined"] == 0.0
        assert result["isk_per_day"] == 0.0
        assert result["structure_performance"] == []
        assert result["ore_breakdown"] == []

    def test_performance_zero_days_no_division_error(self):
        """days=0 must not crash with division-by-zero; isk_per_day should be 0."""
        structure_rows = [
            {
                "observer_id": 6001,
                "total_isk": Decimal("250000000"),
                "unique_miners": 3,
                "active_days": 0,
            },
        ]
        ore_rows = []
        mock_db = _make_multi_result_db([structure_rows, ore_rows])
        svc = _build_service(mock_db)

        result = svc.get_performance(corp_id=98000001, days=0)

        assert result["isk_per_day"] == 0.0
        assert result["total_isk_mined"] == 250_000_000.0

    def test_performance_ore_percentage_calculation(self):
        """Three ore rarities produce percentages summing to approximately 100%."""
        structure_rows = [
            {
                "observer_id": 7001,
                "total_isk": Decimal("3000000"),
                "unique_miners": 2,
                "active_days": 5,
            },
        ]
        ore_rows = [
            {"rarity": "R64", "total_isk": Decimal("1500000")},   # 50%
            {"rarity": "R32", "total_isk": Decimal("900000")},    # 30%
            {"rarity": "R16", "total_isk": Decimal("600000")},    # 20%
        ]
        mock_db = _make_multi_result_db([structure_rows, ore_rows])
        svc = _build_service(mock_db)

        result = svc.get_performance(corp_id=98000001, days=7)

        ob = result["ore_breakdown"]
        assert len(ob) == 3

        # Verify individual percentages
        assert ob[0]["rarity"] == "R64"
        assert ob[0]["percentage"] == 50.0
        assert ob[1]["rarity"] == "R32"
        assert ob[1]["percentage"] == 30.0
        assert ob[2]["rarity"] == "R16"
        assert ob[2]["percentage"] == 20.0

        # Sum should be 100%
        total_pct = sum(o["percentage"] for o in ob)
        assert total_pct == pytest.approx(100.0, abs=0.5)
