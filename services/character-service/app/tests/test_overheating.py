"""Tests for overheating bonus calculations."""
import pytest
from app.services.fitting_stats.overheating import (
    calculate_overload_bonus, calculate_heat_damage,
    ATTR_OVERLOAD_ROF_BONUS, ATTR_OVERLOAD_DAMAGE_MODIFIER,
    ATTR_OVERLOAD_HARDENING_BONUS, ATTR_OVERLOAD_SPEED_BONUS,
    ATTR_OVERLOAD_ARMOR_REP, ATTR_OVERLOAD_SHIELD_BOOST,
    ATTR_HEAT_DAMAGE, SKILL_THERMODYNAMICS,
    OVERLOAD_BONUS_ATTRS,
)


class TestOverloadBonusCalculation:
    """Test overload bonus percentage application."""

    def test_positive_bonus(self):
        """E.g., +15% damage modifier."""
        assert calculate_overload_bonus(1.0, 15.0) == pytest.approx(1.15)

    def test_negative_bonus(self):
        """E.g., -15% rate of fire (fires faster)."""
        assert calculate_overload_bonus(5000.0, -15.0) == pytest.approx(4250.0)

    def test_zero_bonus(self):
        assert calculate_overload_bonus(1000.0, 0.0) == 1000.0

    def test_large_bonus(self):
        """E.g., +50% propmod speed bonus."""
        assert calculate_overload_bonus(500.0, 50.0) == pytest.approx(750.0)

    def test_zero_base(self):
        assert calculate_overload_bonus(0.0, 15.0) == 0.0


class TestHeatDamageCalculation:
    """Test heat damage with Thermodynamics skill."""

    def test_no_skill(self):
        """Without Thermodynamics, full heat damage."""
        assert calculate_heat_damage(5.6, 0) == pytest.approx(5.6)

    def test_level_1(self):
        """Level 1 -> 5% reduction."""
        assert calculate_heat_damage(5.6, 1) == pytest.approx(5.32)

    def test_level_5(self):
        """Level 5 -> 25% reduction."""
        assert calculate_heat_damage(5.6, 5) == pytest.approx(4.2)

    def test_zero_heat_damage(self):
        assert calculate_heat_damage(0, 5) == 0.0

    def test_negative_heat_damage(self):
        assert calculate_heat_damage(-1.0, 5) == 0.0


class TestOverloadConstants:
    """Test that overload constants are defined correctly."""

    def test_overload_bonus_attrs_count(self):
        assert len(OVERLOAD_BONUS_ATTRS) == 9

    def test_key_attrs_in_set(self):
        assert ATTR_OVERLOAD_DAMAGE_MODIFIER in OVERLOAD_BONUS_ATTRS
        assert ATTR_OVERLOAD_ROF_BONUS in OVERLOAD_BONUS_ATTRS
        assert ATTR_OVERLOAD_HARDENING_BONUS in OVERLOAD_BONUS_ATTRS

    def test_heat_damage_attr(self):
        assert ATTR_HEAT_DAMAGE == 1211

    def test_thermodynamics_skill_id(self):
        assert SKILL_THERMODYNAMICS == 28164


class TestOverheatedResponseFields:
    """Test that overheated fields exist on response models."""

    def test_offense_has_overheated_fields(self):
        from app.services.fitting_stats.models import OffenseStats
        stats = OffenseStats(weapon_dps=500, drone_dps=100, total_dps=600)
        assert stats.overheated_weapon_dps is None  # default
        stats.overheated_weapon_dps = 575
        stats.overheated_total_dps = 675
        assert stats.overheated_weapon_dps == 575

    def test_repairs_has_overheated_fields(self):
        from app.services.fitting_stats.models import RepairStats
        stats = RepairStats(shield_rep=100, armor_rep=50)
        assert stats.overheated_shield_rep is None
        stats.overheated_shield_rep = 120
        assert stats.overheated_shield_rep == 120
