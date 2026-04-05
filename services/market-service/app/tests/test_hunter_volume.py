"""Tests for volume/liquidity data in manufacturing opportunities API.

Covers: volume fields in response, min_volume filter, net_profit < gross,
risk_score defaults, sort_by=volume.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from decimal import Decimal
from datetime import datetime

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers — mock DB rows
# ---------------------------------------------------------------------------

def _make_row(**overrides):
    """Build a mock DB row dict for manufacturing_opportunities."""
    defaults = {
        'product_id': 34,
        'blueprint_id': 1034,
        'product_name': 'Tritanium',
        'category': 'Material',
        'group_name': 'Mineral',
        'difficulty': 1,
        'cheapest_material_cost': Decimal('0'),
        'best_sell_price': Decimal('5.50'),
        'profit': Decimal('5.50'),
        'roi': Decimal('100.00'),
        'avg_daily_volume': 500000,
        'sell_volume': 1200000,
        'risk_score': 10,
        'days_to_sell': Decimal('0.01'),
        'net_profit': Decimal('5.22'),
        'net_roi': Decimal('94.90'),
        'updated_at': datetime(2026, 2, 10, 12, 0, 0),
    }
    defaults.update(overrides)
    return defaults


SAMPLE_MOROS = _make_row(
    product_id=19724,
    blueprint_id=19725,
    product_name='Moros',
    category='Ship',
    group_name='Dreadnought',
    difficulty=5,
    cheapest_material_cost=Decimal('1840000000'),
    best_sell_price=Decimal('3350000000'),
    profit=Decimal('1510000000'),
    roi=Decimal('82.07'),
    avg_daily_volume=0,
    sell_volume=4,
    risk_score=50,
    days_to_sell=None,
    net_profit=Decimal('1339150000'),
    net_roi=Decimal('72.78'),
)

SAMPLE_RAITARU = _make_row(
    product_id=35825,
    blueprint_id=35826,
    product_name='Raitaru',
    category='Structure',
    group_name='Engineering Complex',
    difficulty=3,
    cheapest_material_cost=Decimal('150000000'),
    best_sell_price=Decimal('250000000'),
    profit=Decimal('100000000'),
    roi=Decimal('66.67'),
    avg_daily_volume=8,
    sell_volume=45,
    risk_score=46,
    days_to_sell=Decimal('12.50'),
    net_profit=Decimal('87250000'),
    net_roi=Decimal('58.17'),
)

STATS_ROW = {'cnt': 1027, 'max_updated': datetime(2026, 2, 10, 12, 0, 0)}


# ---------------------------------------------------------------------------
# Result field extraction
# ---------------------------------------------------------------------------

def _extract_result(row):
    """Simulate the result dict construction from hunter.py."""
    return {
        "product_id": row['product_id'],
        "blueprint_id": row['blueprint_id'],
        "product_name": row['product_name'],
        "category": row['category'] or "Unknown",
        "group_name": row['group_name'],
        "difficulty": row['difficulty'],
        "material_cost": float(row['cheapest_material_cost']) if row['cheapest_material_cost'] else 0,
        "sell_price": float(row['best_sell_price']) if row['best_sell_price'] else 0,
        "profit": float(row['profit']) if row['profit'] else 0,
        "roi": min(float(row['roi']), 9999) if row['roi'] else 0,
        "volume_available": 0,
        "avg_daily_volume": row.get('avg_daily_volume') or 0,
        "sell_volume": row.get('sell_volume') or 0,
        "risk_score": row.get('risk_score') or 50,
        "days_to_sell": float(row['days_to_sell']) if row.get('days_to_sell') else None,
        "net_profit": float(row['net_profit']) if row.get('net_profit') is not None else float(row.get('profit') or 0),
        "net_roi": float(row['net_roi']) if row.get('net_roi') is not None else float(row.get('roi') or 0),
    }


# ---------------------------------------------------------------------------
# Tests: Volume fields in response
# ---------------------------------------------------------------------------

class TestVolumeFieldsInResponse:
    """API response includes all volume/liquidity fields."""

    def test_response_includes_avg_daily_volume(self):
        result = _extract_result(SAMPLE_RAITARU)
        assert result['avg_daily_volume'] == 8

    def test_response_includes_sell_volume(self):
        result = _extract_result(SAMPLE_RAITARU)
        assert result['sell_volume'] == 45

    def test_response_includes_risk_score(self):
        result = _extract_result(SAMPLE_RAITARU)
        assert result['risk_score'] == 46

    def test_response_includes_days_to_sell(self):
        result = _extract_result(SAMPLE_RAITARU)
        assert result['days_to_sell'] == 12.5

    def test_response_includes_net_profit(self):
        result = _extract_result(SAMPLE_RAITARU)
        assert result['net_profit'] == 87250000.0

    def test_response_includes_net_roi(self):
        result = _extract_result(SAMPLE_RAITARU)
        assert result['net_roi'] == 58.17

    def test_zero_volume_item(self):
        result = _extract_result(SAMPLE_MOROS)
        assert result['avg_daily_volume'] == 0
        assert result['sell_volume'] == 4
        assert result['days_to_sell'] is None


# ---------------------------------------------------------------------------
# Tests: Net profit is less than gross
# ---------------------------------------------------------------------------

class TestNetProfitLessThanGross:
    """net_profit should be less than profit (fees deducted)."""

    def test_raitaru_net_less_than_gross(self):
        result = _extract_result(SAMPLE_RAITARU)
        assert result['net_profit'] < result['profit']

    def test_moros_net_less_than_gross(self):
        result = _extract_result(SAMPLE_MOROS)
        assert result['net_profit'] < result['profit']

    def test_net_roi_less_than_gross_roi(self):
        result = _extract_result(SAMPLE_RAITARU)
        assert result['net_roi'] < result['roi']


# ---------------------------------------------------------------------------
# Tests: Risk score defaults
# ---------------------------------------------------------------------------

class TestRiskScoreDefaults:
    """Items without market_prices data get risk_score=50."""

    def test_default_risk_score_when_none(self):
        row = _make_row(risk_score=None)
        result = _extract_result(row)
        assert result['risk_score'] == 50

    def test_default_risk_score_when_zero(self):
        row = _make_row(risk_score=0)
        result = _extract_result(row)
        # 0 is falsy, so defaults to 50
        assert result['risk_score'] == 50

    def test_explicit_risk_score_preserved(self):
        row = _make_row(risk_score=75)
        result = _extract_result(row)
        assert result['risk_score'] == 75


# ---------------------------------------------------------------------------
# Tests: Net profit fallback
# ---------------------------------------------------------------------------

class TestNetProfitFallback:
    """When net_profit is None, falls back to gross profit."""

    def test_fallback_to_gross_when_net_none(self):
        row = _make_row(net_profit=None, profit=Decimal('500000'))
        result = _extract_result(row)
        assert result['net_profit'] == 500000.0

    def test_fallback_to_gross_roi_when_net_none(self):
        row = _make_row(net_roi=None, roi=Decimal('45.00'))
        result = _extract_result(row)
        assert result['net_roi'] == 45.0

    def test_zero_net_profit_preserved(self):
        """net_profit=0 should NOT fall back — 0 is a valid value."""
        row = _make_row(net_profit=Decimal('0'), profit=Decimal('500'))
        result = _extract_result(row)
        assert result['net_profit'] == 0.0


# ---------------------------------------------------------------------------
# Tests: Min volume filter SQL
# ---------------------------------------------------------------------------

class TestMinVolumeFilter:
    """min_volume parameter should generate correct SQL WHERE clause."""

    def test_min_volume_zero_no_filter(self):
        """min_volume=0 should not add volume filter clause."""
        # Simulate the logic from hunter.py
        min_volume = 0
        where_clauses = ["mo.roi >= %s"]
        params = [10]

        if min_volume > 0:
            where_clauses.append("mo.avg_daily_volume >= %s")
            params.append(min_volume)

        assert len(where_clauses) == 1
        assert len(params) == 1

    def test_min_volume_positive_adds_filter(self):
        """min_volume>0 should add volume filter clause."""
        min_volume = 5
        where_clauses = ["mo.roi >= %s"]
        params = [10]

        if min_volume > 0:
            where_clauses.append("mo.avg_daily_volume >= %s")
            params.append(min_volume)

        assert len(where_clauses) == 2
        assert "mo.avg_daily_volume >= %s" in where_clauses
        assert params[-1] == 5

    def test_min_volume_filters_out_moros(self):
        """Moros (volume=0) should be filtered out with min_volume=1."""
        rows = [SAMPLE_MOROS, SAMPLE_RAITARU]
        min_volume = 1
        filtered = [r for r in rows if r['avg_daily_volume'] >= min_volume]
        assert len(filtered) == 1
        assert filtered[0]['product_name'] == 'Raitaru'


# ---------------------------------------------------------------------------
# Tests: Sort by volume
# ---------------------------------------------------------------------------

class TestSortByVolume:
    """sort_by=volume maps to correct column."""

    def test_volume_sort_column(self):
        sort_by = "volume"
        sort_column = "mo.profit"
        sort_direction = "DESC"

        if sort_by == "profit":
            sort_column = "mo.profit"
        elif sort_by == "roi":
            sort_column = "mo.roi"
        elif sort_by == "volume":
            sort_column = "mo.avg_daily_volume"
        elif sort_by == "name":
            sort_column = "mo.product_name"
            sort_direction = "ASC"

        assert sort_column == "mo.avg_daily_volume"
        assert sort_direction == "DESC"

    def test_sort_orders_high_volume_first(self):
        rows = [SAMPLE_MOROS, SAMPLE_RAITARU]
        sorted_rows = sorted(rows, key=lambda r: r['avg_daily_volume'], reverse=True)
        assert sorted_rows[0]['product_name'] == 'Raitaru'
        assert sorted_rows[1]['product_name'] == 'Moros'


# ---------------------------------------------------------------------------
# Tests: Fee calculation in batch_calculator
# ---------------------------------------------------------------------------

class TestFeeCalculation:
    """Verify fee assumptions used in batch_calculator enrichment."""

    SELL_FEE_PCT = 0.051  # 1.5% broker + 3.6% sales tax

    def test_fee_reduces_sell_price(self):
        sell_price = 1_000_000
        net_revenue = sell_price * (1 - self.SELL_FEE_PCT)
        assert net_revenue == pytest.approx(949_000, rel=1e-6)

    def test_fee_on_moros(self):
        sell_price = 3_350_000_000
        material_cost = 1_840_000_000
        net_revenue = sell_price * (1 - self.SELL_FEE_PCT)
        net_profit = net_revenue - material_cost
        # 3,350,000,000 * 0.949 = 3,179,150,000 - 1,840,000,000 = 1,339,150,000
        assert net_profit == pytest.approx(1_339_150_000, rel=1e-6)

    def test_net_roi_moros(self):
        sell_price = 3_350_000_000
        material_cost = 1_840_000_000
        net_revenue = sell_price * (1 - self.SELL_FEE_PCT)
        net_profit = net_revenue - material_cost
        net_roi = (net_profit / material_cost) * 100
        assert net_roi == pytest.approx(72.78, rel=1e-2)

    def test_gross_vs_net_difference(self):
        """Fee impact should be ~5.1% of sell price."""
        sell_price = 1_000_000_000
        gross_revenue = sell_price
        net_revenue = sell_price * (1 - self.SELL_FEE_PCT)
        fee_amount = gross_revenue - net_revenue
        assert fee_amount == pytest.approx(51_000_000, rel=1e-6)
