# tests/integration/test_dps_integration.py
"""Integration tests for DPS Calculator."""

import pytest
from src.services.dps.service import DPSCalculatorService


@pytest.mark.integration
class TestDPSIntegration:
    """Integration tests against real SDE database."""

    def test_calculate_autocannon_dps(self):
        """Test DPS calculation for 200mm Autocannon II with EMP S."""
        service = DPSCalculatorService()

        result = service.calculate_dps(
            weapon_type_id=2889,  # 200mm AutoCannon II
            ammo_type_id=185,     # EMP S
        )

        assert result is not None
        assert result.weapon_name == "200mm AutoCannon II"
        assert result.ammo_name == "EMP S"
        assert result.raw_dps > 0
        assert result.total_dps > 0

    def test_calculate_missile_dps_with_golem(self):
        """Test missile DPS with Golem ship bonuses."""
        service = DPSCalculatorService()

        # Golem (28710) has +100% missile damage role bonus
        result = service.calculate_dps(
            weapon_type_id=2404,   # Cruise Missile Launcher II
            ammo_type_id=27353,    # Fury Cruise Missile
            ship_type_id=28710,    # Golem
        )

        assert result is not None
        # Ship bonus should increase DPS
        assert result.ship_multiplier >= 2.0  # +100% = 2x

    def test_search_weapons(self):
        """Test weapon search functionality."""
        from src.services.dps.repository import DPSRepository
        repo = DPSRepository()

        results = repo.search_weapons("Autocannon")

        assert len(results) > 0
        assert any("Autocannon" in r['typeName'] for r in results)

    def test_search_ammo(self):
        """Test ammo search functionality."""
        from src.services.dps.repository import DPSRepository
        repo = DPSRepository()

        results = repo.search_ammo("Hail")

        assert len(results) > 0
        assert any("Hail" in r['typeName'] for r in results)

    def test_get_ship_damage_bonuses(self):
        """Test ship damage bonus retrieval."""
        from src.services.dps.repository import DPSRepository
        repo = DPSRepository()

        # Golem should have damage bonuses
        bonuses = repo.get_ship_damage_bonuses(28710)  # Golem

        assert len(bonuses) > 0
        # Should have at least one damage-related bonus
        assert any('damage' in b.bonus_type for b in bonuses)

    def test_compare_ammo_types(self):
        """Test ammo comparison functionality."""
        service = DPSCalculatorService()

        # Compare different projectile ammo types
        results = service.compare_ammo(
            weapon_type_id=2889,  # 200mm AutoCannon II
            ammo_type_ids=[185, 186, 187],  # EMP S, Phased Plasma S, Fusion S
        )

        assert len(results) > 0
        # Results should be sorted by DPS descending
        if len(results) > 1:
            assert results[0].total_dps >= results[1].total_dps
