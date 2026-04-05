# tests/unit/services/test_fitting_models.py
"""Unit tests for fitting data models."""

import pytest
from src.services.fitting.models import (
    ESIFittingItem,
    ESIFitting,
    SkillRequirement,
    ModuleStats,
    FittingAnalysis,
)
from src.services.dps.models import DamageProfile


class TestESIFittingModels:
    """Test ESI fitting model structure."""

    def test_esi_fitting_item_creation(self):
        """Test ESIFittingItem model."""
        item = ESIFittingItem(
            flag="HiSlot0",
            type_id=2404,
            quantity=1
        )
        assert item.flag == "HiSlot0"
        assert item.type_id == 2404
        assert item.quantity == 1

    def test_esi_fitting_creation(self):
        """Test ESIFitting model with items."""
        fitting = ESIFitting(
            fitting_id=12345,
            name="Golem PvE",
            ship_type_id=28710,
            items=[
                ESIFittingItem(flag="HiSlot0", type_id=2404, quantity=1),
                ESIFittingItem(flag="LoSlot0", type_id=19172, quantity=1),
            ]
        )
        assert fitting.fitting_id == 12345
        assert fitting.name == "Golem PvE"
        assert len(fitting.items) == 2


class TestSkillRequirementModel:
    """Test skill requirement model."""

    def test_skill_requirement_unmet(self):
        """Test unmet skill requirement."""
        req = SkillRequirement(
            skill_id=3319,
            skill_name="Missile Launcher Operation",
            required_level=5,
            character_level=3,
            met=False
        )
        assert req.required_level == 5
        assert req.character_level == 3
        assert req.met is False

    def test_skill_requirement_met(self):
        """Test met skill requirement."""
        req = SkillRequirement(
            skill_id=3319,
            skill_name="Missile Launcher Operation",
            required_level=3,
            character_level=5,
            met=True
        )
        assert req.met is True


class TestModuleStatsModel:
    """Test module stats model."""

    def test_damage_mod_module(self):
        """Test damage modifier module stats."""
        mod = ModuleStats(
            type_id=19172,
            type_name="Caldari Navy Ballistic Control System",
            slot_type="low",
            damage_multiplier=1.10,
            rof_multiplier=0.895,
            can_use=True
        )
        assert mod.damage_multiplier == 1.10
        assert mod.rof_multiplier == 0.895
        assert mod.is_active is False

    def test_active_module(self):
        """Test active module with activation bonus."""
        mod = ModuleStats(
            type_id=33400,
            type_name="Bastion Module I",
            slot_type="high",
            is_active=True,
            activation_bonus={"missile_rof_bonus": -0.50}
        )
        assert mod.is_active is True
        assert mod.activation_bonus["missile_rof_bonus"] == -0.50


class TestFittingAnalysisModel:
    """Test fitting analysis result model."""

    def test_fitting_analysis_dps_breakdown(self):
        """Test DPS breakdown in analysis result."""
        analysis = FittingAnalysis(
            fitting=ESIFitting(
                fitting_id=1,
                name="Test",
                ship_type_id=28710,
                items=[]
            ),
            ship_name="Golem",
            character_id=1117367444,
            character_name="Cytrex",
            weapons=[],
            damage_mods=[],
            active_mods=[],
            tracking_mods=[],
            drones=[],
            weapon_dps=800.0,
            drone_dps=0.0,
            total_dps=1600.0,
            base_weapon_dps=200.0,
            skill_multiplier=1.25,
            ship_multiplier=2.0,
            module_multiplier=1.58,
            bastion_multiplier=2.0,
            damage_profile=DamageProfile(kinetic=1600.0)
        )
        assert analysis.total_dps == 1600.0
        assert analysis.bastion_multiplier == 2.0
