"""Tests for portfolio snapshot and history calculations.

Tests the data models and calculation logic in app/routers/portfolio.py:
  - PortfolioSnapshot model construction
  - PortfolioHistory growth calculations
  - Summary aggregation logic
  - Edge cases: empty data, single snapshot, zero values
"""

from datetime import date, timedelta

import pytest

from app.routers.portfolio import PortfolioHistory, PortfolioSnapshot


# =============================================================================
# Helpers
# =============================================================================


def _make_snapshot(
    character_id=12345,
    days_ago=0,
    wallet=1000000.0,
    sell=500000.0,
    escrow=200000.0,
):
    """Create a PortfolioSnapshot with computed total_liquid."""
    return PortfolioSnapshot(
        character_id=character_id,
        snapshot_date=date.today() - timedelta(days=days_ago),
        wallet_balance=wallet,
        sell_order_value=sell,
        buy_order_escrow=escrow,
        total_liquid=wallet + sell + escrow,
    )


def _calc_growth(snapshots):
    """Replicate the growth calculation from the router."""
    if len(snapshots) >= 2:
        first_value = snapshots[0].total_liquid
        last_value = snapshots[-1].total_liquid
        growth_absolute = last_value - first_value
        growth_percent = (growth_absolute / first_value * 100) if first_value > 0 else 0
    else:
        growth_absolute = 0
        growth_percent = 0
    return round(growth_absolute, 2), round(growth_percent, 2)


# =============================================================================
# PortfolioSnapshot model tests
# =============================================================================


class TestPortfolioSnapshot:
    """Test PortfolioSnapshot Pydantic model."""

    def test_basic_construction(self):
        """Snapshot is created with correct fields."""
        snap = _make_snapshot()
        assert snap.character_id == 12345
        assert snap.wallet_balance == 1000000.0
        assert snap.sell_order_value == 500000.0
        assert snap.buy_order_escrow == 200000.0
        assert snap.total_liquid == 1700000.0

    def test_zero_values(self):
        """Snapshot with all zero values."""
        snap = _make_snapshot(wallet=0, sell=0, escrow=0)
        assert snap.total_liquid == 0.0

    def test_date_field(self):
        """Snapshot date is a proper date object."""
        snap = _make_snapshot(days_ago=5)
        expected = date.today() - timedelta(days=5)
        assert snap.snapshot_date == expected

    def test_large_values(self):
        """Handles ISK values in the billions."""
        snap = _make_snapshot(
            wallet=50_000_000_000.0,
            sell=20_000_000_000.0,
            escrow=5_000_000_000.0,
        )
        assert snap.total_liquid == 75_000_000_000.0


# =============================================================================
# PortfolioHistory model tests
# =============================================================================


class TestPortfolioHistory:
    """Test PortfolioHistory model and growth calculation."""

    def test_construction(self):
        """PortfolioHistory is created with correct fields."""
        snapshots = [
            _make_snapshot(days_ago=7, wallet=1000000, sell=0, escrow=0),
            _make_snapshot(days_ago=0, wallet=1500000, sell=0, escrow=0),
        ]
        growth_abs, growth_pct = _calc_growth(snapshots)

        history = PortfolioHistory(
            character_id=12345,
            snapshots=snapshots,
            period_days=7,
            growth_absolute=growth_abs,
            growth_percent=growth_pct,
        )
        assert history.character_id == 12345
        assert len(history.snapshots) == 2
        assert history.period_days == 7

    def test_positive_growth(self):
        """Growth calculation with portfolio increase."""
        snapshots = [
            _make_snapshot(days_ago=30, wallet=1000000, sell=0, escrow=0),
            _make_snapshot(days_ago=0, wallet=1500000, sell=0, escrow=0),
        ]
        growth_abs, growth_pct = _calc_growth(snapshots)

        # 1500000 - 1000000 = 500000
        assert growth_abs == 500000.0
        # 500000 / 1000000 * 100 = 50%
        assert growth_pct == 50.0

    def test_negative_growth(self):
        """Growth calculation with portfolio decrease."""
        snapshots = [
            _make_snapshot(days_ago=30, wallet=2000000, sell=0, escrow=0),
            _make_snapshot(days_ago=0, wallet=1500000, sell=0, escrow=0),
        ]
        growth_abs, growth_pct = _calc_growth(snapshots)

        assert growth_abs == -500000.0
        assert growth_pct == -25.0

    def test_no_change(self):
        """Zero growth when values are unchanged."""
        snapshots = [
            _make_snapshot(days_ago=30, wallet=1000000, sell=0, escrow=0),
            _make_snapshot(days_ago=0, wallet=1000000, sell=0, escrow=0),
        ]
        growth_abs, growth_pct = _calc_growth(snapshots)

        assert growth_abs == 0.0
        assert growth_pct == 0.0

    def test_single_snapshot(self):
        """Single snapshot -> no growth calculation possible."""
        snapshots = [_make_snapshot(days_ago=0)]
        growth_abs, growth_pct = _calc_growth(snapshots)

        assert growth_abs == 0
        assert growth_pct == 0

    def test_empty_snapshots(self):
        """No snapshots -> zero growth."""
        growth_abs, growth_pct = _calc_growth([])
        assert growth_abs == 0
        assert growth_pct == 0

    def test_zero_initial_value(self):
        """Zero initial value -> no division by zero."""
        snapshots = [
            _make_snapshot(days_ago=30, wallet=0, sell=0, escrow=0),
            _make_snapshot(days_ago=0, wallet=1000000, sell=0, escrow=0),
        ]
        growth_abs, growth_pct = _calc_growth(snapshots)

        assert growth_abs == 1000000.0
        # Division by zero guard -> 0%
        assert growth_pct == 0

    def test_multiple_snapshots_uses_first_and_last(self):
        """Growth is computed between first and last snapshot only."""
        snapshots = [
            _make_snapshot(days_ago=30, wallet=1000000, sell=0, escrow=0),
            _make_snapshot(days_ago=15, wallet=500000, sell=0, escrow=0),  # dip
            _make_snapshot(days_ago=0, wallet=2000000, sell=0, escrow=0),
        ]
        growth_abs, growth_pct = _calc_growth(snapshots)

        # Uses first (1M) and last (2M), ignores the dip
        assert growth_abs == 1000000.0
        assert growth_pct == 100.0

    def test_growth_includes_all_components(self):
        """Growth calculation considers wallet + sell + escrow."""
        snapshots = [
            _make_snapshot(days_ago=30, wallet=500000, sell=300000, escrow=200000),
            _make_snapshot(days_ago=0, wallet=800000, sell=500000, escrow=300000),
        ]
        growth_abs, growth_pct = _calc_growth(snapshots)

        # first total = 1000000, last total = 1600000
        assert growth_abs == 600000.0
        assert growth_pct == 60.0


# =============================================================================
# Summary aggregation tests
# =============================================================================


class TestSummaryAggregation:
    """Test the summary/all aggregation logic."""

    def test_combined_liquid(self):
        """Combined liquid is sum of all characters' total_liquid."""
        snapshots = [
            _make_snapshot(character_id=1, wallet=1000000, sell=0, escrow=0),
            _make_snapshot(character_id=2, wallet=2000000, sell=0, escrow=0),
            _make_snapshot(character_id=3, wallet=3000000, sell=0, escrow=0),
        ]

        total_liquid = sum(s.total_liquid for s in snapshots)
        assert total_liquid == 6000000.0

    def test_empty_summary(self):
        """No snapshots -> zero combined."""
        snapshots = []
        total_liquid = sum(s.total_liquid for s in snapshots)
        assert total_liquid == 0.0

    def test_total_characters(self):
        """Character count matches snapshot count."""
        snapshots = [
            _make_snapshot(character_id=1),
            _make_snapshot(character_id=2),
        ]
        assert len(snapshots) == 2

    def test_mixed_values(self):
        """Characters with different wallet/order compositions."""
        snapshots = [
            _make_snapshot(character_id=1, wallet=5_000_000, sell=10_000_000, escrow=2_000_000),
            _make_snapshot(character_id=2, wallet=50_000_000, sell=0, escrow=0),
        ]

        total_liquid = sum(s.total_liquid for s in snapshots)
        # char1: 17M, char2: 50M = 67M
        assert total_liquid == 67_000_000.0


# =============================================================================
# Row-to-Snapshot conversion tests
# =============================================================================


class TestRowConversion:
    """Test the row-to-PortfolioSnapshot conversion logic from the router."""

    def _convert_row(self, row):
        """Replicate the conversion logic from the router."""
        return PortfolioSnapshot(
            character_id=row["character_id"],
            snapshot_date=row["snapshot_date"],
            wallet_balance=float(row["wallet_balance"]) if row["wallet_balance"] else 0,
            sell_order_value=float(row["sell_order_value"]) if row["sell_order_value"] else 0,
            buy_order_escrow=float(row["buy_order_escrow"]) if row["buy_order_escrow"] else 0,
            total_liquid=float(row["total_liquid"]) if row["total_liquid"] else 0,
        )

    def test_normal_row(self):
        """Normal row with all values present."""
        row = {
            "character_id": 12345,
            "snapshot_date": date.today(),
            "wallet_balance": 1000000.0,
            "sell_order_value": 500000.0,
            "buy_order_escrow": 200000.0,
            "total_liquid": 1700000.0,
        }
        snap = self._convert_row(row)
        assert snap.total_liquid == 1700000.0

    def test_null_values(self):
        """Null values from DB are converted to 0."""
        row = {
            "character_id": 12345,
            "snapshot_date": date.today(),
            "wallet_balance": None,
            "sell_order_value": None,
            "buy_order_escrow": None,
            "total_liquid": None,
        }
        snap = self._convert_row(row)
        assert snap.wallet_balance == 0
        assert snap.sell_order_value == 0
        assert snap.buy_order_escrow == 0
        assert snap.total_liquid == 0

    def test_decimal_values(self):
        """Decimal DB values are properly converted to float."""
        from decimal import Decimal

        row = {
            "character_id": 12345,
            "snapshot_date": date.today(),
            "wallet_balance": Decimal("1234567.89"),
            "sell_order_value": Decimal("0"),
            "buy_order_escrow": Decimal("0"),
            "total_liquid": Decimal("1234567.89"),
        }
        snap = self._convert_row(row)
        assert snap.wallet_balance == pytest.approx(1234567.89)
