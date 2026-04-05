# tests/unit/services/test_dps_models.py
"""Unit tests for DPS calculation models."""

import pytest
from src.services.dps.models import (
    DamageProfile,
    WeaponAttributes,
    AmmoAttributes,
    ShipBonus,
    SkillBonus,
    DPSResult,
)


class TestDamageProfile:
    """Test DamageProfile model."""

    def test_total_damage(self):
        """Test total damage calculation."""
        profile = DamageProfile(em=10, thermal=20, kinetic=30, explosive=40)
        assert profile.total == 100

    def test_damage_profile_defaults(self):
        """Test default values are zero."""
        profile = DamageProfile()
        assert profile.em == 0
        assert profile.thermal == 0
        assert profile.kinetic == 0
        assert profile.explosive == 0
        assert profile.total == 0


class TestWeaponAttributes:
    """Test WeaponAttributes model."""

    def test_weapon_attributes(self):
        """Test weapon attribute storage."""
        weapon = WeaponAttributes(
            type_id=2961,
            type_name="200mm Autocannon II",
            rate_of_fire_ms=3000,
            damage_modifier=3.0,
            optimal_range=1200,
            falloff=8000,
            tracking=0.35
        )
        assert weapon.type_id == 2961
        assert weapon.rate_of_fire_seconds == 3.0


class TestDPSResult:
    """Test DPSResult model."""

    def test_dps_result(self):
        """Test DPS result calculation."""
        result = DPSResult(
            weapon_name="200mm Autocannon II",
            ammo_name="Hail M",
            raw_dps=150.0,
            skill_multiplier=1.15,
            ship_multiplier=1.25,
            total_dps=215.625,
            damage_profile=DamageProfile(em=0, thermal=0, kinetic=50, explosive=100)
        )
        assert result.total_dps == 215.625
