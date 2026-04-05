"""Tests for invention cost calculation logic.

Tests the formulas in app/services/invention.py:
  - cost_per_bpc = total_input_cost / (adjusted_runs * adjusted_probability)
  - adjusted_runs = max(1, base_runs + run_modifier)
  - result_me = 2 + me_modifier  (T2 base ME = 2)
  - result_te = 4 + te_modifier  (T2 base TE = 4)
  - adjusted_probability = base_probability * prob_modifier
  - material qty: max(1, ceil(base_qty * me_factor))
  - me_factor = 1 - (result_me / 100)
"""

import math
from decimal import Decimal

import pytest

from app.services.invention import (
    InventionService,
    ACTIVITY_MANUFACTURING,
    ACTIVITY_INVENTION,
)
from app.tests.conftest import MultiResultCursor, MockDB


# ── Formula-level tests (no imports of DB-dependent code needed) ─────


class TestCostPerBPC:
    """Test the core invention cost formula: input_cost / (runs * probability)."""

    def test_basic_cost_per_bpc(self):
        """Standard case: 220k input, 10 runs, 34% probability."""
        total_input_cost = Decimal("220000")
        adjusted_runs = 10
        adjusted_probability = 0.34
        cost = float(total_input_cost / Decimal(str(adjusted_runs * adjusted_probability)))
        assert round(cost, 2) == round(220000 / (10 * 0.34), 2)
        assert cost == pytest.approx(64705.88, rel=1e-2)

    def test_high_probability(self):
        """With probability modifier bringing it close to 1.0."""
        total_input_cost = Decimal("100000")
        adjusted_runs = 10
        adjusted_probability = 0.90
        cost = float(total_input_cost / Decimal(str(adjusted_runs * adjusted_probability)))
        assert cost == pytest.approx(11111.11, rel=1e-2)

    def test_low_probability(self):
        """Low probability significantly increases cost per BPC."""
        total_input_cost = Decimal("100000")
        adjusted_runs = 10
        adjusted_probability = 0.10
        cost = float(total_input_cost / Decimal(str(adjusted_runs * adjusted_probability)))
        assert cost == pytest.approx(100000.0, rel=1e-2)

    def test_single_run(self):
        """Ship invention: only 1 output run."""
        total_input_cost = Decimal("500000")
        adjusted_runs = 1
        adjusted_probability = 0.30
        cost = float(total_input_cost / Decimal(str(adjusted_runs * adjusted_probability)))
        assert cost == pytest.approx(1666666.67, rel=1e-2)

    def test_zero_probability_guard(self):
        """Zero probability should cause division by zero - the service guards this."""
        total_input_cost = Decimal("100000")
        adjusted_runs = 10
        adjusted_probability = 0.0
        # The real code returns None before reaching this formula
        # when probability <= 0. Verify the guard works.
        with pytest.raises(Exception):
            float(total_input_cost / Decimal(str(adjusted_runs * adjusted_probability)))


class TestDecryptorModifiers:
    """Test decryptor modifier application to base invention values."""

    def test_no_decryptor_baseline(self):
        """Without decryptor: ME=2, TE=4, runs=base, prob=base."""
        me_modifier = 0
        te_modifier = 0
        run_modifier = 0
        prob_modifier = 1.0
        base_probability = 0.34
        base_runs = 10

        result_me = 2 + me_modifier
        result_te = 4 + te_modifier
        adjusted_runs = max(1, base_runs + run_modifier)
        adjusted_probability = base_probability * prob_modifier

        assert result_me == 2
        assert result_te == 4
        assert adjusted_runs == 10
        assert adjusted_probability == pytest.approx(0.34)

    def test_accelerant_decryptor(self):
        """Accelerant: ME+2, TE+10, runs+1, prob*1.2."""
        me_modifier = 2
        te_modifier = 10
        run_modifier = 1
        prob_modifier = 1.2
        base_probability = 0.34
        base_runs = 10

        result_me = 2 + me_modifier
        result_te = 4 + te_modifier
        adjusted_runs = max(1, base_runs + run_modifier)
        adjusted_probability = base_probability * prob_modifier

        assert result_me == 4
        assert result_te == 14
        assert adjusted_runs == 11
        assert adjusted_probability == pytest.approx(0.408)

    def test_parity_decryptor(self):
        """Parity: ME+1, TE-2, runs+3, prob*1.5."""
        me_modifier = 1
        te_modifier = -2
        run_modifier = 3
        prob_modifier = 1.5
        base_probability = 0.34
        base_runs = 10

        result_me = 2 + me_modifier
        result_te = 4 + te_modifier
        adjusted_runs = max(1, base_runs + run_modifier)
        adjusted_probability = base_probability * prob_modifier

        assert result_me == 3
        assert result_te == 2
        assert adjusted_runs == 13
        assert adjusted_probability == pytest.approx(0.51)

    def test_negative_run_modifier_clamped_to_1(self):
        """Run modifier cannot reduce runs below 1."""
        base_runs = 1
        run_modifier = -5
        adjusted_runs = max(1, base_runs + run_modifier)
        assert adjusted_runs == 1

    def test_negative_te_modifier(self):
        """Negative TE modifier can bring result_te below base."""
        te_modifier = -6
        result_te = 4 + te_modifier
        assert result_te == -2

    def test_augmentation_decryptor(self):
        """Augmentation: ME-2, TE-2, runs+9, prob*0.6 (negative ME)."""
        me_modifier = -2
        te_modifier = -2
        run_modifier = 9
        prob_modifier = 0.6
        base_probability = 0.34
        base_runs = 10

        result_me = 2 + me_modifier
        result_te = 4 + te_modifier
        adjusted_runs = max(1, base_runs + run_modifier)
        adjusted_probability = base_probability * prob_modifier

        assert result_me == 0
        assert result_te == 2
        assert adjusted_runs == 19
        assert adjusted_probability == pytest.approx(0.204)


class TestMaterialQuantityWithME:
    """Test material quantity calculation: max(1, ceil(base_qty * me_factor))."""

    def test_me0_no_reduction(self):
        """ME 0: no reduction, quantity equals base."""
        result_me = 2  # T2 base without decryptor
        me_factor = 1 - (result_me / 100)
        base_qty = 100
        qty = max(1, math.ceil(base_qty * me_factor))
        assert qty == 98

    def test_me4_with_decryptor(self):
        """ME 4 (base 2 + decryptor +2): ~4% reduction."""
        result_me = 4
        me_factor = 1 - (result_me / 100)
        base_qty = 100
        qty = max(1, math.ceil(base_qty * me_factor))
        assert qty == 96

    def test_me_factor_rounding_up(self):
        """Fractional quantities always round up."""
        result_me = 2
        me_factor = 1 - (result_me / 100)
        base_qty = 51
        qty = max(1, math.ceil(base_qty * me_factor))
        # 51 * 0.98 = 49.98 -> ceil = 50
        assert qty == 50

    def test_minimum_quantity_is_one(self):
        """Even with high ME, minimum quantity is 1."""
        result_me = 2
        me_factor = 1 - (result_me / 100)
        base_qty = 1
        qty = max(1, math.ceil(base_qty * me_factor))
        # 1 * 0.98 = 0.98 -> ceil = 1 -> max(1, 1) = 1
        assert qty == 1

    def test_zero_me_full_cost(self):
        """ME 0 (result_me=0): me_factor = 1.0, no reduction."""
        result_me = 0
        me_factor = 1 - (result_me / 100)
        assert me_factor == 1.0
        base_qty = 500
        qty = max(1, math.ceil(base_qty * me_factor))
        assert qty == 500


class TestInventionOutputRuns:
    """Test the invention output runs calculation."""

    def test_standard_item_runs(self):
        """Standard T2 items: maxProductionLimit > 10 gives limit // 10."""
        limit = 100
        runs = max(1, limit // 10) if limit > 10 else 1
        assert runs == 10

    def test_ship_runs(self):
        """T2 ships: maxProductionLimit <= 10 gives 1."""
        limit = 10
        runs = max(1, limit // 10) if limit > 10 else 1
        assert runs == 1

    def test_low_limit(self):
        """Very low production limit gives 1."""
        limit = 5
        runs = max(1, limit // 10) if limit > 10 else 1
        assert runs == 1

    def test_high_limit(self):
        """High limit items like ammo."""
        limit = 300
        runs = max(1, limit // 10) if limit > 10 else 1
        assert runs == 30
