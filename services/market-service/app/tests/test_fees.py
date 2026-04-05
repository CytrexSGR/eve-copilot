"""Tests for EVE Online trading fee calculations."""

import pytest

from app.services.fees import (
    BASE_BROKER_FEE_PCT,
    BASE_SALES_TAX_PCT,
    MIN_BROKER_FEE_PCT,
    broker_fee_rate,
    calculate_trade_fees,
    net_profit_per_unit,
    sales_tax_rate,
)


# ---------------------------------------------------------------------------
# broker_fee_rate
# ---------------------------------------------------------------------------


class TestBrokerFeeRate:
    def test_level_0_no_standings(self):
        """No skills, no standings -> base 3.0%."""
        assert broker_fee_rate(broker_relations=0) == BASE_BROKER_FEE_PCT

    def test_level_3_no_standings(self):
        """Level 3 -> 3.0 - 0.3*3 = 2.1%."""
        assert broker_fee_rate(broker_relations=3) == pytest.approx(2.1)

    def test_level_5_no_standings(self):
        """Level 5 -> 3.0 - 0.3*5 = 1.5%."""
        assert broker_fee_rate(broker_relations=5) == pytest.approx(1.5)

    def test_level_5_with_faction_standing(self):
        """Level 5 + faction 7.0 -> 1.5 - 0.03*7 = 1.29%."""
        result = broker_fee_rate(broker_relations=5, faction_standing=7.0)
        assert result == pytest.approx(1.29)

    def test_level_5_with_corp_standing(self):
        """Level 5 + corp 5.0 -> 1.5 - 0.02*5 = 1.40%."""
        result = broker_fee_rate(broker_relations=5, corp_standing=5.0)
        assert result == pytest.approx(1.40)

    def test_level_5_with_both_standings(self):
        """Level 5 + faction 7 + corp 5 -> 1.5 - 0.21 - 0.10 = 1.19%."""
        result = broker_fee_rate(broker_relations=5, faction_standing=7.0, corp_standing=5.0)
        assert result == pytest.approx(1.19)

    def test_min_floor_enforced(self):
        """Even with maximum standings the fee cannot drop below 1.0%."""
        result = broker_fee_rate(broker_relations=5, faction_standing=10.0, corp_standing=10.0)
        assert result == MIN_BROKER_FEE_PCT

    def test_defaults_level_5(self):
        """Default call uses level 5 broker relations."""
        assert broker_fee_rate() == pytest.approx(1.5)


# ---------------------------------------------------------------------------
# sales_tax_rate
# ---------------------------------------------------------------------------


class TestSalesTaxRate:
    def test_level_0(self):
        """No Accounting skill -> full 8.0% tax."""
        assert sales_tax_rate(accounting=0) == BASE_SALES_TAX_PCT

    def test_level_3(self):
        """Level 3 -> 8.0 * (1 - 0.33) = 5.36%."""
        assert sales_tax_rate(accounting=3) == pytest.approx(5.36)

    def test_level_5(self):
        """Level 5 -> 8.0 * (1 - 0.55) = 3.6%."""
        assert sales_tax_rate(accounting=5) == pytest.approx(3.6)

    def test_defaults_level_5(self):
        """Default call uses level 5 accounting."""
        assert sales_tax_rate() == pytest.approx(3.6)


# ---------------------------------------------------------------------------
# calculate_trade_fees
# ---------------------------------------------------------------------------


class TestCalculateTradeFees:
    def test_basic_trade(self):
        """Buy 100, sell 120 with default skills (BR 5, Acc 5)."""
        fees = calculate_trade_fees(buy_price=100.0, sell_price=120.0)

        assert fees["broker_fee_pct"] == pytest.approx(1.5)
        assert fees["sales_tax_pct"] == pytest.approx(3.6)
        assert fees["broker_fee_buy"] == pytest.approx(1.5)       # 100 * 1.5%
        assert fees["broker_fee_sell"] == pytest.approx(1.8)      # 120 * 1.5%
        assert fees["sales_tax"] == pytest.approx(4.32)           # 120 * 3.6%
        assert fees["total_fees"] == pytest.approx(1.5 + 1.8 + 4.32)

    def test_no_skills_trade(self):
        """Buy 100, sell 120 with zero skills."""
        fees = calculate_trade_fees(
            buy_price=100.0, sell_price=120.0, broker_relations=0, accounting=0
        )

        assert fees["broker_fee_pct"] == pytest.approx(3.0)
        assert fees["sales_tax_pct"] == pytest.approx(8.0)
        assert fees["broker_fee_buy"] == pytest.approx(3.0)       # 100 * 3%
        assert fees["broker_fee_sell"] == pytest.approx(3.6)      # 120 * 3%
        assert fees["sales_tax"] == pytest.approx(9.6)            # 120 * 8%
        assert fees["total_fees"] == pytest.approx(3.0 + 3.6 + 9.6)

    def test_zero_prices(self):
        """Both prices zero -> all fees zero."""
        fees = calculate_trade_fees(buy_price=0.0, sell_price=0.0)
        assert fees["total_fees"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# net_profit_per_unit
# ---------------------------------------------------------------------------


class TestNetProfitPerUnit:
    def test_profitable_trade(self):
        """Buy 100, sell 150 with default skills -> profitable."""
        result = net_profit_per_unit(buy_price=100.0, sell_price=150.0)

        assert result["gross_profit"] == pytest.approx(50.0)
        # broker buy = 1.5, broker sell = 2.25, sales tax = 5.4
        expected_fees = 1.5 + 2.25 + 5.4
        assert result["total_fees"] == pytest.approx(expected_fees)
        assert result["net_profit"] == pytest.approx(50.0 - expected_fees)
        assert result["is_profitable"] is True
        assert result["gross_margin_pct"] == pytest.approx(50.0 / 150.0 * 100)
        assert result["net_margin_pct"] == pytest.approx((50.0 - expected_fees) / 150.0 * 100)

    def test_unprofitable_after_fees(self):
        """Small margin wiped out by fees."""
        result = net_profit_per_unit(
            buy_price=100.0, sell_price=103.0, broker_relations=0, accounting=0
        )

        # gross = 3.0, but fees = 100*3% + 103*3% + 103*8% = 3.0 + 3.09 + 8.24 = 14.33
        assert result["gross_profit"] == pytest.approx(3.0)
        assert result["is_profitable"] is False
        assert result["net_profit"] < 0

    def test_zero_buy_price(self):
        """Buy at zero (e.g. loot) -> only sell-side fees."""
        result = net_profit_per_unit(buy_price=0.0, sell_price=1000.0)

        assert result["gross_profit"] == pytest.approx(1000.0)
        # broker buy = 0, broker sell = 15, sales tax = 36
        expected_fees = 0.0 + 15.0 + 36.0
        assert result["total_fees"] == pytest.approx(expected_fees)
        assert result["net_profit"] == pytest.approx(1000.0 - expected_fees)
        assert result["is_profitable"] is True

    def test_zero_sell_price(self):
        """Sell at zero -> margins are 0%, not profitable."""
        result = net_profit_per_unit(buy_price=100.0, sell_price=0.0)

        assert result["gross_margin_pct"] == pytest.approx(0.0)
        assert result["net_margin_pct"] == pytest.approx(0.0)
        assert result["is_profitable"] is False
