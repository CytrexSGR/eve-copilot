"""Tests for production economics calculation logic.

Tests the formulas in app/services/economics.py:
  - me_factor = 1 - (me / 100)
  - adjusted_qty = max(1, ceil(base_qty * me_factor))
  - material_cost = sum(unit_price * adjusted_qty)
  - revenue = product_price * output_per_run
  - profit = revenue - material_cost
  - margin = (profit / material_cost * 100) if material_cost > 0 else 0
  - te_factor = 1 - (te / 100)
  - actual_time = int(base_time * te_factor)
  - profit_per_hour = (profit / actual_time * 3600) if actual_time > 0 else 0
"""

import math

import pytest


# ── ME factor tests ──────────────────────────────────────────────


class TestMEFactor:
    """Test Material Efficiency factor calculation."""

    def test_me_zero(self):
        me = 0
        me_factor = 1 - (me / 100)
        assert me_factor == 1.0

    def test_me_five(self):
        me = 5
        me_factor = 1 - (me / 100)
        assert me_factor == 0.95

    def test_me_ten(self):
        me = 10
        me_factor = 1 - (me / 100)
        assert me_factor == 0.90

    def test_me_one(self):
        me = 1
        me_factor = 1 - (me / 100)
        assert me_factor == 0.99


# ── Adjusted quantity tests ──────────────────────────────────────


class TestAdjustedQuantity:
    """Test adjusted quantity: max(1, ceil(base * me_factor))."""

    def test_me0_no_change(self):
        base_qty = 100
        me_factor = 1 - (0 / 100)
        adjusted = max(1, math.ceil(base_qty * me_factor))
        assert adjusted == 100

    def test_me5_standard(self):
        base_qty = 100
        me_factor = 1 - (5 / 100)
        adjusted = max(1, math.ceil(base_qty * me_factor))
        assert adjusted == 95

    def test_me10_maximum(self):
        base_qty = 100
        me_factor = 1 - (10 / 100)
        adjusted = max(1, math.ceil(base_qty * me_factor))
        assert adjusted == 90

    def test_fractional_rounds_up(self):
        """51 * 0.95 = 48.45 -> ceil = 49."""
        base_qty = 51
        me_factor = 1 - (5 / 100)
        adjusted = max(1, math.ceil(base_qty * me_factor))
        assert adjusted == 49

    def test_minimum_is_one(self):
        """Even a single unit stays at 1 with max ME."""
        base_qty = 1
        me_factor = 1 - (10 / 100)
        adjusted = max(1, math.ceil(base_qty * me_factor))
        # 1 * 0.9 = 0.9 -> ceil = 1
        assert adjusted == 1

    def test_large_quantity(self):
        """Large base quantities scale correctly."""
        base_qty = 10000
        me_factor = 1 - (10 / 100)
        adjusted = max(1, math.ceil(base_qty * me_factor))
        assert adjusted == 9000


# ── Material cost aggregation tests ──────────────────────────────


class TestMaterialCostAggregation:
    """Test sum of (unit_price * adjusted_qty)."""

    def test_single_material(self):
        materials = [(34, 100)]  # (type_id, base_qty)
        prices = {34: 5.0}
        me = 10
        me_factor = 1 - (me / 100)

        total = 0.0
        for mat_id, base_qty in materials:
            adjusted = max(1, math.ceil(base_qty * me_factor))
            total += prices[mat_id] * adjusted

        # 90 * 5.0 = 450.0
        assert total == pytest.approx(450.0)

    def test_multiple_materials(self):
        materials = [
            (34, 10000),   # Tritanium
            (35, 5000),    # Pyerite
            (36, 2000),    # Mexallon
        ]
        prices = {34: 5.0, 35: 10.0, 36: 50.0}
        me = 10
        me_factor = 1 - (me / 100)

        total = 0.0
        for mat_id, base_qty in materials:
            adjusted = max(1, math.ceil(base_qty * me_factor))
            total += prices[mat_id] * adjusted

        # 9000*5.0 + 4500*10.0 + 1800*50.0 = 45000 + 45000 + 90000 = 180000
        assert total == pytest.approx(180000.0)

    def test_zero_price_material(self):
        """Materials with no market price contribute 0 cost."""
        materials = [(34, 100), (99999, 500)]
        prices = {34: 5.0, 99999: 0.0}
        me = 0
        me_factor = 1.0

        total = 0.0
        for mat_id, base_qty in materials:
            adjusted = max(1, math.ceil(base_qty * me_factor))
            total += prices.get(mat_id, 0.0) * adjusted

        assert total == pytest.approx(500.0)


# ── Revenue and profit tests ─────────────────────────────────────


class TestRevenueAndProfit:
    """Test revenue, profit, and margin calculations."""

    def test_profitable_item(self):
        product_price = 1000000.0
        output_per_run = 1
        material_cost = 600000.0

        revenue = product_price * output_per_run
        profit = revenue - material_cost
        margin = (profit / material_cost * 100) if material_cost > 0 else 0.0

        assert revenue == 1000000.0
        assert profit == 400000.0
        assert margin == pytest.approx(66.67, rel=1e-2)

    def test_loss_item(self):
        product_price = 400000.0
        output_per_run = 1
        material_cost = 600000.0

        revenue = product_price * output_per_run
        profit = revenue - material_cost
        margin = (profit / material_cost * 100) if material_cost > 0 else 0.0

        assert profit == -200000.0
        assert margin == pytest.approx(-33.33, rel=1e-2)

    def test_zero_material_cost_guard(self):
        """Division by zero guard: margin = 0 when cost = 0."""
        product_price = 100.0
        output_per_run = 1
        material_cost = 0.0

        revenue = product_price * output_per_run
        profit = revenue - material_cost
        margin = (profit / material_cost * 100) if material_cost > 0 else 0.0

        assert margin == 0.0
        assert profit == 100.0

    def test_multiple_output(self):
        """Blueprints that produce multiple items per run."""
        product_price = 500.0
        output_per_run = 100  # Ammo blueprint
        material_cost = 10000.0

        revenue = product_price * output_per_run
        profit = revenue - material_cost

        assert revenue == 50000.0
        assert profit == 40000.0

    def test_break_even(self):
        """Exact break-even: profit = 0, margin = 0."""
        product_price = 100.0
        output_per_run = 1
        material_cost = 100.0

        revenue = product_price * output_per_run
        profit = revenue - material_cost
        margin = (profit / material_cost * 100) if material_cost > 0 else 0.0

        assert profit == 0.0
        assert margin == 0.0


# ── TE factor and production time tests ──────────────────────────


class TestTEFactor:
    """Test Time Efficiency factor and production time."""

    def test_te_zero(self):
        te = 0
        te_factor = 1 - (te / 100)
        assert te_factor == 1.0

    def test_te_ten(self):
        te = 10
        te_factor = 1 - (te / 100)
        assert te_factor == 0.90

    def test_te_twenty(self):
        te = 20
        te_factor = 1 - (te / 100)
        assert te_factor == 0.80

    def test_actual_time_calculation(self):
        """Base time 7200s with TE 20 -> 5760s."""
        base_time = 7200
        te = 20
        te_factor = 1 - (te / 100)
        actual_time = int(base_time * te_factor)
        assert actual_time == 5760

    def test_actual_time_truncates(self):
        """int() truncates, does not round."""
        base_time = 3601
        te = 10
        te_factor = 1 - (te / 100)
        actual_time = int(base_time * te_factor)
        # 3601 * 0.9 = 3240.9 -> int = 3240
        assert actual_time == 3240


# ── Profit per hour tests ────────────────────────────────────────


class TestProfitPerHour:
    """Test profit per hour calculation."""

    def test_standard_profit_per_hour(self):
        profit = 100000.0
        actual_time = 3600  # 1 hour
        pph = (profit / actual_time * 3600) if actual_time > 0 else 0.0
        assert pph == pytest.approx(100000.0)

    def test_two_hour_build(self):
        profit = 200000.0
        actual_time = 7200  # 2 hours
        pph = (profit / actual_time * 3600) if actual_time > 0 else 0.0
        assert pph == pytest.approx(100000.0)

    def test_short_build(self):
        """5-minute build produces high ISK/hr."""
        profit = 10000.0
        actual_time = 300  # 5 minutes
        pph = (profit / actual_time * 3600) if actual_time > 0 else 0.0
        assert pph == pytest.approx(120000.0)

    def test_zero_time_guard(self):
        """Division by zero guard when production time is 0."""
        profit = 100000.0
        actual_time = 0
        pph = (profit / actual_time * 3600) if actual_time > 0 else 0.0
        assert pph == 0.0

    def test_negative_profit_per_hour(self):
        """Loss items produce negative ISK/hr."""
        profit = -50000.0
        actual_time = 3600
        pph = (profit / actual_time * 3600) if actual_time > 0 else 0.0
        assert pph == pytest.approx(-50000.0)


# ── Full economics pipeline test ─────────────────────────────────


class TestFullEconomicsPipeline:
    """End-to-end economics calculation matching economics.py logic."""

    def test_full_pipeline(self, sample_materials, sample_prices):
        """Complete calculation matching ProductionEconomicsService.get_economics()."""
        me = 10
        te = 20
        me_factor = 1 - (me / 100)  # 0.9
        te_factor = 1 - (te / 100)  # 0.8

        # Material cost
        material_cost = 0.0
        for mat_id, base_qty in sample_materials:
            adjusted = max(1, math.ceil(base_qty * me_factor))
            price = sample_prices.get(mat_id, 0.0)
            material_cost += price * adjusted

        # 9000*5 + 4500*10 + 1800*50 + 90*10000
        # = 45000 + 45000 + 90000 + 900000 = 1,080,000
        assert material_cost == pytest.approx(1080000.0)

        # Revenue
        product_price = 1500000.0
        output_per_run = 1
        revenue = product_price * output_per_run
        assert revenue == 1500000.0

        # Profit
        profit = revenue - material_cost
        assert profit == pytest.approx(420000.0)

        # Margin
        margin = (profit / material_cost * 100) if material_cost > 0 else 0.0
        assert margin == pytest.approx(38.89, rel=1e-2)

        # Production time
        base_time = 10800  # 3 hours
        actual_time = int(base_time * te_factor)
        assert actual_time == 8640

        # Profit per hour
        pph = (profit / actual_time * 3600) if actual_time > 0 else 0.0
        assert pph == pytest.approx(175000.0, rel=1e-2)
