"""Tests for Dogma Tank Calculator - stacking penalty, EHP, and tank classification."""

import math
import pytest
from app.services.dogma.tank_calculator import TankCalculatorService
from app.services.dogma.models import ResistProfile, TankType


@pytest.fixture
def calc():
    """Tank calculator without repository (pure math tests only)."""
    return TankCalculatorService(repository=None)


# ============================================================================
# Stacking Penalty
# ============================================================================

class TestStackingPenalty:
    def test_first_module_full_effect(self, calc):
        assert calc._stacking_penalty(0) == pytest.approx(1.0)

    def test_second_module_reduced(self, calc):
        p = calc._stacking_penalty(1)
        assert 0.86 < p < 0.88  # ~0.8691

    def test_third_module_further_reduced(self, calc):
        p = calc._stacking_penalty(2)
        assert 0.57 < p < 0.58  # ~0.5706

    def test_fourth_module_heavily_reduced(self, calc):
        p = calc._stacking_penalty(3)
        assert 0.28 < p < 0.29  # ~0.2830

    def test_fifth_module_near_zero(self, calc):
        p = calc._stacking_penalty(4)
        assert p < 0.11

    def test_penalty_always_positive(self, calc):
        for i in range(10):
            assert calc._stacking_penalty(i) > 0

    def test_penalty_monotonically_decreasing(self, calc):
        penalties = [calc._stacking_penalty(i) for i in range(8)]
        for i in range(len(penalties) - 1):
            assert penalties[i] > penalties[i + 1]

    def test_formula_matches_eve(self, calc):
        """Verify against EVE's known stacking penalty formula."""
        for i in range(5):
            expected = math.exp(-((i / 2.67) ** 2))
            assert calc._stacking_penalty(i) == pytest.approx(expected)


# ============================================================================
# Layer EHP Calculation
# ============================================================================

class TestLayerEHP:
    def test_zero_hp(self, calc):
        r = ResistProfile(em=0.5, thermal=0.5, kinetic=0.5, explosive=0.5)
        assert calc._calculate_layer_ehp(0, r) == 0

    def test_negative_hp(self, calc):
        r = ResistProfile(em=0.5, thermal=0.5, kinetic=0.5, explosive=0.5)
        assert calc._calculate_layer_ehp(-100, r) == 0

    def test_no_resists(self, calc):
        """With 1.0 (no resist), EHP equals HP."""
        r = ResistProfile(em=1.0, thermal=1.0, kinetic=1.0, explosive=1.0)
        assert calc._calculate_layer_ehp(1000, r) == pytest.approx(1000)

    def test_50_percent_resist(self, calc):
        """With 0.5 avg resist mult, EHP = HP * 2."""
        r = ResistProfile(em=0.5, thermal=0.5, kinetic=0.5, explosive=0.5)
        assert calc._calculate_layer_ehp(1000, r) == pytest.approx(2000)

    def test_75_percent_resist(self, calc):
        """With 0.25 avg resist mult, EHP = HP * 4."""
        r = ResistProfile(em=0.25, thermal=0.25, kinetic=0.25, explosive=0.25)
        assert calc._calculate_layer_ehp(1000, r) == pytest.approx(4000)

    def test_near_immunity_capped(self, calc):
        """Very low resist multiplier caps at 100x HP."""
        r = ResistProfile(em=0.0, thermal=0.0, kinetic=0.0, explosive=0.0)
        result = calc._calculate_layer_ehp(1000, r)
        assert result == 100000  # 1000 * 100

    def test_mixed_resists(self, calc):
        """EHP based on average resist multiplier."""
        r = ResistProfile(em=0.2, thermal=0.4, kinetic=0.6, explosive=0.8)
        avg = 0.5  # (0.2+0.4+0.6+0.8)/4
        expected = 1000 / avg
        assert calc._calculate_layer_ehp(1000, r) == pytest.approx(expected)


# ============================================================================
# Tank Classification
# ============================================================================

class TestTankClassification:
    def test_shield_dominant(self, calc):
        """Shield EHP > 1.5x armor → shield buffer."""
        tank_type, primary = calc._classify_tank(8000, 3000, 16000, 6000)
        assert tank_type == TankType.SHIELD_BUFFER
        assert primary == "shield"

    def test_armor_dominant(self, calc):
        """Armor EHP > 1.5x shield → armor buffer."""
        tank_type, primary = calc._classify_tank(3000, 8000, 6000, 16000)
        assert tank_type == TankType.ARMOR_BUFFER
        assert primary == "armor"

    def test_balanced_shield_higher(self, calc):
        """Near-equal EHP, shield slightly higher → unknown with shield primary."""
        tank_type, primary = calc._classify_tank(5000, 5000, 10000, 9000)
        assert tank_type == TankType.UNKNOWN
        assert primary == "shield"

    def test_balanced_armor_higher(self, calc):
        """Near-equal EHP, armor slightly higher → unknown with armor primary."""
        tank_type, primary = calc._classify_tank(5000, 5000, 9000, 10000)
        assert tank_type == TankType.UNKNOWN
        assert primary == "armor"

    def test_equal_ehp(self, calc):
        """Exactly equal → unknown with shield primary (tie-breaker)."""
        tank_type, primary = calc._classify_tank(5000, 5000, 10000, 10000)
        assert tank_type == TankType.UNKNOWN
        assert primary == "shield"

    def test_zero_ehp(self, calc):
        """Both zero → unknown."""
        tank_type, primary = calc._classify_tank(0, 0, 0, 0)
        assert tank_type == TankType.UNKNOWN


# ============================================================================
# Apply Stacked Resists
# ============================================================================

class TestApplyStackedResists:
    def test_no_bonuses(self, calc):
        """No module bonuses → base resists unchanged."""
        base = ResistProfile(em=0.8, thermal=0.6, kinetic=0.5, explosive=0.9)
        result = calc._apply_stacked_resists(base, {})
        assert result.em == pytest.approx(0.8)
        assert result.thermal == pytest.approx(0.6)

    def test_single_bonus(self, calc):
        """Single resist module applies at full strength (penalty index 0)."""
        base = ResistProfile(em=0.8, thermal=0.6, kinetic=0.5, explosive=0.9)
        bonuses = {'em': [0.75]}  # 25% EM resist
        result = calc._apply_stacked_resists(base, bonuses)
        # 0.8 * 0.75 = 0.6
        assert result.em == pytest.approx(0.6)
        # Other resists unchanged
        assert result.thermal == pytest.approx(0.6)
        assert result.explosive == pytest.approx(0.9)

    def test_two_modules_stacking(self, calc):
        """Two resist modules apply with stacking penalty on second."""
        base = ResistProfile(em=0.8, thermal=0.8, kinetic=0.8, explosive=0.8)
        bonuses = {'em': [0.75, 0.75]}
        result = calc._apply_stacked_resists(base, bonuses)
        # Second module gets ~0.869 effectiveness
        # First: 0.8 * 0.75 = 0.6
        # Second: 0.6 * (1.0 + (0.75 - 1.0) * 0.869) = 0.6 * 0.7827 ≈ 0.4696
        assert result.em < 0.6  # Better than single module
        assert result.em > 0.4  # But not double benefit

    def test_resist_clamped_to_zero(self, calc):
        """Result can't go below 0.0."""
        base = ResistProfile(em=0.1, thermal=0.5, kinetic=0.5, explosive=0.5)
        # Extreme bonuses
        bonuses = {'em': [0.01, 0.01, 0.01, 0.01]}
        result = calc._apply_stacked_resists(base, bonuses)
        assert result.em >= 0.0

    def test_resist_clamped_to_one(self, calc):
        """Result can't go above 1.0."""
        base = ResistProfile(em=0.9, thermal=0.5, kinetic=0.5, explosive=0.5)
        # Multiplier > 1.0 would increase vulnerability
        bonuses = {'em': [1.5]}
        result = calc._apply_stacked_resists(base, bonuses)
        assert result.em <= 1.0
