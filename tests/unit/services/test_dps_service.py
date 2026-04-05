# tests/unit/services/test_dps_service.py
"""Unit tests for DPS Calculator Service."""

import pytest
from unittest.mock import Mock, patch
from src.services.dps.service import DPSCalculatorService
from src.services.dps.models import (
    WeaponAttributes, AmmoAttributes, DamageProfile,
    ShipBonus, SkillBonus, DPSResult
)
from src.services.dps.repository import DPSRepository


class TestDPSCalculatorService:
    """Test DPS calculation logic."""

    @pytest.fixture
    def mock_repository(self):
        """Create mock repository."""
        return Mock(spec=DPSRepository)

    @pytest.fixture
    def service(self, mock_repository):
        """Create service with mock repository."""
        return DPSCalculatorService(repository=mock_repository)

    def test_calculate_raw_dps(self, service):
        """Test raw DPS calculation without modifiers."""
        weapon = WeaponAttributes(
            type_id=2961,
            type_name="200mm Autocannon II",
            rate_of_fire_ms=3000,  # 3 seconds
            damage_modifier=3.0
        )
        ammo = AmmoAttributes(
            type_id=178,
            type_name="EMP S",
            damage=DamageProfile(em=9, thermal=0, kinetic=2, explosive=0)
        )

        # Raw DPS = (9+0+2+0) * 3.0 / 3.0 = 11 DPS
        raw_dps = service.calculate_raw_dps(weapon, ammo)
        assert raw_dps == 11.0

    def test_calculate_with_skill_bonuses(self, service, mock_repository):
        """Test DPS with skill bonuses applied."""
        mock_repository.get_weapon_attributes.return_value = WeaponAttributes(
            type_id=2961,
            type_name="200mm Autocannon II",
            rate_of_fire_ms=3000,
            damage_modifier=3.0
        )
        mock_repository.get_ammo_attributes.return_value = AmmoAttributes(
            type_id=178,
            type_name="EMP S",
            damage=DamageProfile(em=9, thermal=0, kinetic=2, explosive=0)
        )

        skills = {
            3315: 5,  # Surgical Strike V (+3% per level = +15%)
        }

        result = service.calculate_dps(
            weapon_type_id=2961,
            ammo_type_id=178,
            character_skills=skills
        )

        assert result is not None
        assert result.raw_dps == 11.0
        # With Surgical Strike V: 11 * 1.15 = 12.65
        assert result.total_dps == pytest.approx(12.65, rel=0.01)

    def test_stacking_penalty(self, service):
        """Test stacking penalty calculation."""
        # EVE stacking penalty formula
        penalties = [service._stacking_penalty(i) for i in range(5)]

        assert penalties[0] == pytest.approx(1.0, rel=0.01)
        assert penalties[1] == pytest.approx(0.869, rel=0.01)
        assert penalties[2] == pytest.approx(0.571, rel=0.01)
        assert penalties[3] == pytest.approx(0.283, rel=0.01)
        assert penalties[4] == pytest.approx(0.106, rel=0.01)
