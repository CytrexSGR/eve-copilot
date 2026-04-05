"""Tests for arbitrage models, fee calculations, route metrics, and ship recommendations."""

import pytest

from app.routers.arbitrage import (
    ArbitrageItem,
    ArbitrageRoute,
    ArbitrageRouteLogistics,
    ArbitrageRouteSummary,
    ArbitrageRoutesResponse,
)
from app.services.fees import (
    broker_fee_rate,
    calculate_trade_fees,
    net_profit_per_unit,
    sales_tax_rate,
)


# ---------------------------------------------------------------------------
# ArbitrageItem model
# ---------------------------------------------------------------------------


class TestArbitrageItemModel:
    """Test ArbitrageItem Pydantic model fields and defaults."""

    def test_required_fields(self):
        """Required fields create valid model."""
        item = ArbitrageItem(
            type_id=34,
            type_name="Tritanium",
            buy_price_source=4.50,
            sell_price_dest=5.20,
            quantity=10000,
            volume=100.0,
            profit_per_unit=0.70,
            total_profit=7000.0,
        )
        assert item.type_id == 34
        assert item.type_name == "Tritanium"
        assert item.quantity == 10000

    def test_default_optional_fields(self):
        """Optional fields have correct defaults."""
        item = ArbitrageItem(
            type_id=34,
            type_name="Tritanium",
            buy_price_source=4.50,
            sell_price_dest=5.20,
            quantity=10000,
            volume=100.0,
            profit_per_unit=0.70,
            total_profit=7000.0,
        )
        assert item.gross_margin_pct is None
        assert item.net_profit_per_unit is None
        assert item.net_margin_pct is None
        assert item.total_fees_per_unit is None
        assert item.net_total_profit is None
        assert item.avg_daily_volume is None
        assert item.days_to_sell is None
        assert item.turnover == "unknown"
        assert item.competition == "medium"

    def test_fee_adjusted_fields(self):
        """Fee-adjusted fields can be set."""
        item = ArbitrageItem(
            type_id=34,
            type_name="Tritanium",
            buy_price_source=100.0,
            sell_price_dest=120.0,
            quantity=1000,
            volume=10.0,
            profit_per_unit=20.0,
            total_profit=20000.0,
            gross_margin_pct=16.67,
            net_profit_per_unit=12.50,
            net_margin_pct=10.42,
            total_fees_per_unit=7.50,
            net_total_profit=12500.0,
        )
        assert item.gross_margin_pct == pytest.approx(16.67)
        assert item.net_profit_per_unit == pytest.approx(12.50)


# ---------------------------------------------------------------------------
# ArbitrageRouteSummary model
# ---------------------------------------------------------------------------


class TestArbitrageRouteSummary:
    """Test route summary calculations."""

    def test_basic_summary(self):
        """Basic summary without fee-adjusted fields."""
        summary = ArbitrageRouteSummary(
            total_items=5,
            total_volume=5000.0,
            total_buy_cost=10_000_000.0,
            total_sell_value=12_000_000.0,
            total_profit=2_000_000.0,
            profit_per_jump=200_000.0,
            roi_percent=20.0,
        )
        assert summary.total_items == 5
        assert summary.roi_percent == pytest.approx(20.0)
        assert summary.net_total_profit is None

    def test_fee_adjusted_summary(self):
        """Summary with net profit fields."""
        summary = ArbitrageRouteSummary(
            total_items=5,
            total_volume=5000.0,
            total_buy_cost=10_000_000.0,
            total_sell_value=12_000_000.0,
            total_profit=2_000_000.0,
            profit_per_jump=200_000.0,
            roi_percent=20.0,
            net_total_profit=1_500_000.0,
            net_roi_percent=15.0,
            net_profit_per_jump=150_000.0,
        )
        assert summary.net_total_profit == pytest.approx(1_500_000.0)
        assert summary.net_roi_percent == pytest.approx(15.0)


# ---------------------------------------------------------------------------
# Enhanced arbitrage fee calculations (inline logic from endpoint)
# ---------------------------------------------------------------------------


class TestEnhancedArbitrageFees:
    """Test the inline fee calculation logic from the enhanced arbitrage endpoint."""

    def _calculate_enhanced_fees(
        self,
        buy_price: float,
        sell_price: float,
        broker_fee_percent: float = 3.0,
        sales_tax_percent: float = 8.0,
    ) -> dict:
        """Replicate the inline fee calculation from the enhanced endpoint."""
        broker_fee_buy = buy_price * (broker_fee_percent / 100)
        broker_fee_sell = sell_price * (broker_fee_percent / 100)
        sales_tax = sell_price * (sales_tax_percent / 100)
        total_fees = broker_fee_buy + broker_fee_sell + sales_tax
        gross_profit = sell_price - buy_price
        net_profit = gross_profit - total_fees
        net_profit_percent = (
            (net_profit / buy_price * 100) if buy_price > 0 else 0
        )
        return {
            "broker_fee_buy": round(broker_fee_buy, 2),
            "broker_fee_sell": round(broker_fee_sell, 2),
            "sales_tax": round(sales_tax, 2),
            "total_fees": round(total_fees, 2),
            "net_profit_per_unit": round(net_profit, 2),
            "net_profit_percent": round(net_profit_percent, 2),
            "is_profitable_after_fees": net_profit > 0,
        }

    def test_profitable_trade(self):
        """Buy 100, sell 150 with default fees -> profitable."""
        result = self._calculate_enhanced_fees(100.0, 150.0)
        assert result["broker_fee_buy"] == pytest.approx(3.0)
        assert result["broker_fee_sell"] == pytest.approx(4.5)
        assert result["sales_tax"] == pytest.approx(12.0)
        assert result["total_fees"] == pytest.approx(19.5)
        assert result["net_profit_per_unit"] == pytest.approx(30.5)
        assert result["is_profitable_after_fees"] is True

    def test_unprofitable_after_fees(self):
        """Small spread wiped by fees."""
        result = self._calculate_enhanced_fees(100.0, 105.0)
        # gross = 5, fees = 3 + 3.15 + 8.4 = 14.55
        assert result["is_profitable_after_fees"] is False
        assert result["net_profit_per_unit"] < 0

    def test_zero_buy_price(self):
        """Buy at zero -> net_profit_percent = 0."""
        result = self._calculate_enhanced_fees(0.0, 100.0)
        assert result["net_profit_percent"] == 0
        assert result["broker_fee_buy"] == 0

    def test_custom_fee_rates(self):
        """Custom broker fee and sales tax."""
        result = self._calculate_enhanced_fees(
            100.0, 200.0, broker_fee_percent=1.5, sales_tax_percent=3.6
        )
        assert result["broker_fee_buy"] == pytest.approx(1.5)
        assert result["broker_fee_sell"] == pytest.approx(3.0)
        assert result["sales_tax"] == pytest.approx(7.2)
        assert result["total_fees"] == pytest.approx(11.7)
        assert result["net_profit_per_unit"] == pytest.approx(88.3)

    @pytest.mark.parametrize(
        "buy,sell,profitable",
        [
            (100, 200, True),
            (100, 120, True),   # 20% spread, fees ~14%
            (100, 110, False),  # 10% spread, fees ~14%
            (100, 100, False),  # No spread
            (100, 90, False),   # Negative spread
        ],
    )
    def test_profitability_thresholds(self, buy, sell, profitable):
        """Parametrized profitability threshold tests."""
        result = self._calculate_enhanced_fees(float(buy), float(sell))
        assert result["is_profitable_after_fees"] is profitable


# ---------------------------------------------------------------------------
# Ship recommendation logic (from live route endpoint)
# ---------------------------------------------------------------------------


class TestShipRecommendation:
    """Test ship recommendation based on cargo capacity."""

    @staticmethod
    def _recommend_ship(cargo_capacity: int) -> str:
        """Replicate ship recommendation logic from live route endpoint."""
        if cargo_capacity >= 500000:
            return "Freighter"
        elif cargo_capacity >= 30000:
            return "Deep Space Transport"
        elif cargo_capacity >= 10000:
            return "Blockade Runner"
        else:
            return "Industrial"

    @pytest.mark.parametrize(
        "capacity,expected",
        [
            (1000000, "Freighter"),
            (500000, "Freighter"),
            (60000, "Deep Space Transport"),
            (30000, "Deep Space Transport"),
            (20000, "Blockade Runner"),
            (10000, "Blockade Runner"),
            (5000, "Industrial"),
            (1000, "Industrial"),
        ],
    )
    def test_ship_for_capacity(self, capacity, expected):
        """Correct ship for given cargo capacity."""
        assert self._recommend_ship(capacity) == expected


# ---------------------------------------------------------------------------
# Hub distances (from live route endpoint)
# ---------------------------------------------------------------------------


class TestHubDistances:
    """Test hub distance lookup logic from the arbitrage route endpoint."""

    HUB_DISTANCES = {
        (10000002, 10000043): 9,   # Jita -> Amarr
        (10000002, 10000030): 11,  # Jita -> Rens
        (10000002, 10000032): 12,  # Jita -> Dodixie
        (10000002, 10000042): 14,  # Jita -> Hek
        (10000043, 10000030): 18,  # Amarr -> Rens
        (10000043, 10000032): 8,   # Amarr -> Dodixie
        (10000043, 10000042): 15,  # Amarr -> Hek
        (10000030, 10000032): 15,  # Rens -> Dodixie
        (10000030, 10000042): 7,   # Rens -> Hek
        (10000032, 10000042): 10,  # Dodixie -> Hek
    }

    def test_jita_amarr_distance(self):
        """Jita to Amarr is 9 jumps."""
        assert self.HUB_DISTANCES[(10000002, 10000043)] == 9

    def test_symmetric_lookup_helper(self):
        """Helper to look up distance regardless of key order."""
        def lookup(a, b):
            return self.HUB_DISTANCES.get((a, b)) or self.HUB_DISTANCES.get((b, a))
        assert lookup(10000002, 10000030) == 11
        assert lookup(10000030, 10000002) == 11

    def test_all_pairs_have_distances(self):
        """All 10 hub pairs have defined distances (5 choose 2 = 10)."""
        assert len(self.HUB_DISTANCES) == 10

    def test_rens_hek_shortest(self):
        """Rens to Hek is the shortest route (7 jumps)."""
        distances = list(self.HUB_DISTANCES.values())
        assert min(distances) == 7
        assert self.HUB_DISTANCES[(10000030, 10000042)] == 7

    def test_amarr_rens_longest(self):
        """Amarr to Rens is the longest route (18 jumps)."""
        distances = list(self.HUB_DISTANCES.values())
        assert max(distances) == 18
        assert self.HUB_DISTANCES[(10000043, 10000030)] == 18


# ---------------------------------------------------------------------------
# Route risk classification (from cached routes endpoint)
# ---------------------------------------------------------------------------


class TestRouteRiskClassification:
    """Test route risk classification logic from the cached routes endpoint."""

    @staticmethod
    def _classify_risk(valid_days: list) -> str:
        """Replicate route risk classification from cached routes endpoint."""
        max_days = max(valid_days) if valid_days else None
        if max_days and max_days < 3:
            return "low"
        elif max_days and max_days < 7:
            return "medium"
        else:
            return "high"

    @pytest.mark.parametrize(
        "days_list,expected",
        [
            ([0.5, 1.0, 2.0], "low"),
            ([1.0, 3.0, 5.0], "medium"),
            ([2.0, 5.0, 10.0], "high"),
            ([0.1], "low"),
            ([6.9], "medium"),
            ([7.0], "high"),
            ([], "high"),  # No data -> high risk
        ],
    )
    def test_risk_levels(self, days_list, expected):
        """Parametrized risk classification by days_to_sell."""
        assert self._classify_risk(days_list) == expected


# ---------------------------------------------------------------------------
# ROI and profit-per-hour calculations
# ---------------------------------------------------------------------------


class TestRouteMetrics:
    """Test route-level metric calculations."""

    def test_roi_calculation(self):
        """ROI = (profit / buy_cost) * 100."""
        total_buy = 10_000_000.0
        total_profit = 2_000_000.0
        roi = (total_profit / total_buy * 100) if total_buy > 0 else 0
        assert roi == pytest.approx(20.0)

    def test_roi_zero_buy(self):
        """ROI with zero buy cost -> 0."""
        total_buy = 0.0
        total_profit = 100.0
        roi = (total_profit / total_buy * 100) if total_buy > 0 else 0
        assert roi == 0

    def test_profit_per_jump(self):
        """Profit per jump = total_profit / jumps."""
        total_profit = 5_000_000.0
        jumps = 10
        ppj = total_profit / jumps if jumps > 0 else 0
        assert ppj == pytest.approx(500_000.0)

    def test_profit_per_hour(self):
        """Profit per hour based on round trip time."""
        total_profit = 5_000_000.0
        jumps = 10
        round_trip_minutes = jumps * 2 * 2  # 40 minutes
        pph = (total_profit / round_trip_minutes * 60) if round_trip_minutes > 0 else 0
        assert pph == pytest.approx(7_500_000.0)

    def test_cargo_packing_greedy(self):
        """Greedy cargo packing selects items until full."""
        items = [
            {"volume": 3000, "profit": 500000},
            {"volume": 2000, "profit": 300000},
            {"volume": 1500, "profit": 200000},
            {"volume": 4000, "profit": 400000},
        ]
        # Sort by profit desc
        items.sort(key=lambda x: x["profit"], reverse=True)

        cargo_capacity = 6000
        selected = []
        used_volume = 0
        for item in items:
            if used_volume + item["volume"] <= cargo_capacity:
                selected.append(item)
                used_volume += item["volume"]

        # Should pick: 500k (3000m3) + 300k (2000m3) = 5000m3, then 200k doesn't fit? 5000+1500=6500 > 6000
        # Actually 5000+1500=6500 > 6000, skip. 5000+4000=9000 > 6000, skip.
        assert len(selected) == 2
        assert used_volume == 5000
        total_profit = sum(i["profit"] for i in selected)
        assert total_profit == 800000


# ---------------------------------------------------------------------------
# ArbitrageRoutesResponse model
# ---------------------------------------------------------------------------


class TestArbitrageRoutesResponse:
    """Test the response model."""

    def test_empty_routes(self):
        """Response with no routes is valid."""
        resp = ArbitrageRoutesResponse(
            start_region="Jita",
            cargo_capacity=60000,
            routes=[],
            generated_at="2026-01-01T00:00:00Z",
        )
        assert resp.start_region == "Jita"
        assert len(resp.routes) == 0
        assert resp.fee_assumptions is None

    def test_fee_assumptions(self):
        """Fee assumptions can be attached."""
        resp = ArbitrageRoutesResponse(
            start_region="Jita",
            cargo_capacity=60000,
            routes=[],
            generated_at="2026-01-01T00:00:00Z",
            fee_assumptions={
                "broker_fee_pct": 1.5,
                "sales_tax_pct": 3.6,
                "skill_assumption": "Broker Relations V + Accounting V",
            },
        )
        assert resp.fee_assumptions["broker_fee_pct"] == 1.5
        assert resp.fee_assumptions["sales_tax_pct"] == 3.6
