# tests/integration/test_fitting_repository.py
"""Integration tests for FittingRepository against SDE database."""

import pytest
from src.services.fitting.repository import FittingRepository


@pytest.mark.integration
class TestFittingRepository:
    """Integration tests against real SDE database."""

    def test_get_module_damage_stats_bcu(self):
        """Test getting damage stats for Caldari Navy BCU."""
        repo = FittingRepository()
        stats = repo.get_module_damage_stats(15681)  # CN BCU (correct type ID)
        assert stats is not None
        assert stats.type_name == "Caldari Navy Ballistic Control System"
        assert stats.slot_type == "low"
        # Attribute 213 stores 1.12 for +12% damage
        assert stats.damage_multiplier == pytest.approx(1.12, abs=0.01)
        # Attribute 204 stores 0.89 for -11% RoF (faster firing)
        assert stats.rof_multiplier == pytest.approx(0.89, abs=0.01)

    def test_get_module_damage_stats_weapon(self):
        """Test getting stats for Cruise Missile Launcher II."""
        repo = FittingRepository()
        stats = repo.get_module_damage_stats(19739)  # Cruise Missile Launcher II
        assert stats is not None
        assert "Cruise Missile" in stats.type_name
        assert stats.slot_type == "high"

    def test_get_module_skill_requirements(self):
        """Test getting skill requirements for a module."""
        repo = FittingRepository()
        reqs = repo.get_module_skill_requirements(19739)  # Cruise Missile Launcher II
        assert len(reqs) > 0
        skill_ids = [r.skill_id for r in reqs]
        assert 3319 in skill_ids  # Missile Launcher Operation

    def test_get_bastion_bonus(self):
        """Test getting Bastion Module active bonuses."""
        repo = FittingRepository()
        bonus = repo.get_bastion_bonus(33400)  # Bastion Module I
        assert bonus is not None
        assert "missile_rof_bonus" in bonus
        assert bonus["missile_rof_bonus"] == pytest.approx(-0.50, abs=0.01)

    def test_categorize_module_weapon(self):
        """Test categorizing a weapon."""
        repo = FittingRepository()
        category = repo.categorize_module(19739)  # Cruise Missile Launcher II
        assert category == "weapon"

    def test_categorize_module_damage_mod(self):
        """Test categorizing a damage mod."""
        repo = FittingRepository()
        category = repo.categorize_module(15681)  # CN BCU (correct type ID)
        assert category == "damage_mod"

    def test_categorize_module_bastion(self):
        """Test categorizing Bastion as active mod."""
        repo = FittingRepository()
        category = repo.categorize_module(33400)  # Bastion Module I
        assert category == "active_mod"

    def test_get_ship_name(self):
        """Test getting ship name by type ID."""
        repo = FittingRepository()
        name = repo.get_ship_name(28710)  # Golem
        assert name == "Golem"

    def test_get_module_damage_stats_heat_sink(self):
        """Test getting damage stats for Heat Sink II (turret damage mod)."""
        repo = FittingRepository()
        stats = repo.get_module_damage_stats(2364)  # Heat Sink II (correct type ID)
        assert stats is not None
        assert "Heat Sink" in stats.type_name
        assert stats.slot_type == "low"
        # Heat Sink has damage multiplier > 1.0
        assert stats.damage_multiplier > 1.0

    def test_get_module_damage_stats_gyrostabilizer(self):
        """Test getting damage stats for Gyrostabilizer II."""
        repo = FittingRepository()
        stats = repo.get_module_damage_stats(519)  # Gyrostabilizer II
        assert stats is not None
        assert "Gyrostabilizer" in stats.type_name
        assert stats.slot_type == "low"
        assert stats.damage_multiplier > 1.0

    def test_get_module_damage_stats_nonexistent(self):
        """Test getting stats for non-existent module returns None."""
        repo = FittingRepository()
        stats = repo.get_module_damage_stats(999999999)
        assert stats is None

    def test_get_ship_name_nonexistent(self):
        """Test getting ship name for non-existent ship returns None."""
        repo = FittingRepository()
        name = repo.get_ship_name(999999999)
        assert name is None

    def test_categorize_module_unknown(self):
        """Test categorizing an unknown module type returns 'other'."""
        repo = FittingRepository()
        # Test with a random non-weapon/non-damage-mod module
        category = repo.categorize_module(999999999)
        assert category == "other"
