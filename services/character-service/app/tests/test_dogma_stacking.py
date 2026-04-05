import pytest
from app.services.dogma.stacking import stacking_penalty, apply_stacking_penalized_multipliers

class TestStackingPenalty:
    def test_first_module_full_effect(self):
        assert stacking_penalty(0) == pytest.approx(1.0, abs=0.001)

    def test_second_module_diminished(self):
        assert stacking_penalty(1) == pytest.approx(0.8691, abs=0.001)

    def test_third_module_heavily_diminished(self):
        assert stacking_penalty(2) == pytest.approx(0.5706, abs=0.001)

    def test_fourth_module_minimal(self):
        assert stacking_penalty(3) == pytest.approx(0.2830, abs=0.001)

    def test_fifth_module_negligible(self):
        assert stacking_penalty(4) == pytest.approx(0.1059, abs=0.001)


class TestApplyStackingMultipliers:
    def test_single_multiplier(self):
        """One 10% bonus = 1.1x"""
        result = apply_stacking_penalized_multipliers([1.1])
        assert result == pytest.approx(1.1, abs=0.001)

    def test_two_identical_multipliers(self):
        """Two 10% bonuses, second penalized"""
        result = apply_stacking_penalized_multipliers([1.1, 1.1])
        # First: 1.1, Second: 1 + (0.1 * 0.869) = 1.0869
        assert result == pytest.approx(1.1 * 1.0869, abs=0.001)

    def test_sorted_by_effectiveness(self):
        """Best bonus applied first (highest benefit)"""
        result_ordered = apply_stacking_penalized_multipliers([1.15, 1.10])
        result_reversed = apply_stacking_penalized_multipliers([1.10, 1.15])
        assert result_ordered == pytest.approx(result_reversed, abs=0.001)

    def test_empty_list(self):
        assert apply_stacking_penalized_multipliers([]) == pytest.approx(1.0)

    def test_resist_multipliers_below_one(self):
        """Resist mods: 0.7 means 30% resist bonus. Best (lowest) applied first."""
        result = apply_stacking_penalized_multipliers([0.7, 0.8])
        # Sorted by distance from 1.0: [0.7, 0.8]
        # First: 0.7, Second: 1 + (0.8-1) * 0.869 = 1 - 0.1738 = 0.8262
        assert result == pytest.approx(0.7 * 0.8262, abs=0.001)

    def test_three_damage_mods(self):
        """Three Gyrostabilizer II (1.1x each)"""
        result = apply_stacking_penalized_multipliers([1.1, 1.1, 1.1])
        # 1.1 * (1+0.1*0.869) * (1+0.1*0.571)
        expected = 1.1 * 1.0869 * 1.0571
        assert result == pytest.approx(expected, abs=0.001)
