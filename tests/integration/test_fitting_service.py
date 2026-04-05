# tests/integration/test_fitting_service.py
"""Integration tests for FittingService."""

import pytest
from src.services.fitting.service import FittingService
from src.services.fitting.models import ESIFitting, ESIFittingItem


@pytest.mark.integration
class TestFittingService:
    """Integration tests for fitting analysis."""

    def test_analyze_golem_fitting_basic(self):
        """Test basic Golem fitting analysis."""
        service = FittingService()

        # Golem with 4x Cruise Missile Launcher II, 3x CN BCU
        fitting = ESIFitting(
            fitting_id=1,
            name="Golem Test",
            ship_type_id=28710,  # Golem
            items=[
                # 4x Cruise Missile Launcher II
                ESIFittingItem(flag="HiSlot0", type_id=19739, quantity=1),
                ESIFittingItem(flag="HiSlot1", type_id=19739, quantity=1),
                ESIFittingItem(flag="HiSlot2", type_id=19739, quantity=1),
                ESIFittingItem(flag="HiSlot3", type_id=19739, quantity=1),
                # 3x Caldari Navy BCU
                ESIFittingItem(flag="LoSlot0", type_id=15681, quantity=1),
                ESIFittingItem(flag="LoSlot1", type_id=15681, quantity=1),
                ESIFittingItem(flag="LoSlot2", type_id=15681, quantity=1),
            ]
        )

        result = service.analyze_fitting(
            fitting=fitting,
            character_id=1117367444,  # Cytrex
            ammo_type_id=27353,  # Fury Cruise Missile
        )

        assert result is not None
        assert result.ship_name == "Golem"
        assert len(result.weapons) == 4
        assert len(result.damage_mods) == 3
        assert result.module_multiplier > 1.0  # BCUs increase damage
        assert result.total_dps > 0

    def test_analyze_fitting_with_bastion(self):
        """Test Golem with Bastion active."""
        service = FittingService()

        fitting = ESIFitting(
            fitting_id=2,
            name="Golem Bastion",
            ship_type_id=28710,
            items=[
                ESIFittingItem(flag="HiSlot0", type_id=19739, quantity=1),
                ESIFittingItem(flag="HiSlot4", type_id=33400, quantity=1),  # Bastion
                ESIFittingItem(flag="LoSlot0", type_id=15681, quantity=1),
            ]
        )

        # Without Bastion active
        result_inactive = service.analyze_fitting(
            fitting=fitting,
            character_id=1117367444,
            ammo_type_id=27353,
            active_modules=[]
        )

        # With Bastion active
        result_active = service.analyze_fitting(
            fitting=fitting,
            character_id=1117367444,
            ammo_type_id=27353,
            active_modules=[33400]
        )

        assert result_inactive.bastion_multiplier == 1.0
        assert result_active.bastion_multiplier == pytest.approx(2.0, abs=0.1)
        assert result_active.total_dps > result_inactive.total_dps

    def test_module_stacking_penalty_applied(self):
        """Test that stacking penalty is applied correctly."""
        service = FittingService()

        # Single BCU
        fitting_1 = ESIFitting(
            fitting_id=3,
            name="1 BCU",
            ship_type_id=28710,
            items=[
                ESIFittingItem(flag="HiSlot0", type_id=19739, quantity=1),
                ESIFittingItem(flag="LoSlot0", type_id=15681, quantity=1),
            ]
        )

        # Three BCUs
        fitting_3 = ESIFitting(
            fitting_id=4,
            name="3 BCU",
            ship_type_id=28710,
            items=[
                ESIFittingItem(flag="HiSlot0", type_id=19739, quantity=1),
                ESIFittingItem(flag="LoSlot0", type_id=15681, quantity=1),
                ESIFittingItem(flag="LoSlot1", type_id=15681, quantity=1),
                ESIFittingItem(flag="LoSlot2", type_id=15681, quantity=1),
            ]
        )

        result_1 = service.analyze_fitting(fitting_1, 1117367444, 27353)
        result_3 = service.analyze_fitting(fitting_3, 1117367444, 27353)

        # 3 BCUs should not give 3x the bonus due to stacking
        bonus_1 = result_1.module_multiplier - 1.0
        bonus_3 = result_3.module_multiplier - 1.0
        assert bonus_3 < bonus_1 * 3  # Less than triple
        assert bonus_3 > bonus_1 * 2  # More than double
