"""Tests for Dogma Engine models - computed fields and pure calculations."""

import pytest
from app.services.dogma.models import (
    ResistProfile,
    ShipBaseStats,
    FittedModule,
    TankResult,
    TankType,
    ModuleSlot,
    KillmailAnalysis,
    AttackerDPSResult,
)


# ============================================================================
# ResistProfile
# ============================================================================

class TestResistProfilePercent:
    """Test resistance percentage computed fields."""

    def test_no_resists(self):
        """1.0 multiplier = 0% resist."""
        rp = ResistProfile(em=1.0, thermal=1.0, kinetic=1.0, explosive=1.0)
        assert rp.em_percent == 0.0
        assert rp.thermal_percent == 0.0

    def test_full_resist(self):
        """0.0 multiplier = 100% resist."""
        rp = ResistProfile(em=0.0, thermal=0.0, kinetic=0.0, explosive=0.0)
        assert rp.em_percent == 100.0
        assert rp.thermal_percent == 100.0

    def test_half_resist(self):
        """0.5 multiplier = 50% resist."""
        rp = ResistProfile(em=0.5, thermal=0.5, kinetic=0.5, explosive=0.5)
        assert rp.em_percent == pytest.approx(50.0)
        assert rp.kinetic_percent == pytest.approx(50.0)

    @pytest.mark.parametrize("mult,expected_pct", [
        (0.0, 100.0),
        (0.25, 75.0),
        (0.5, 50.0),
        (0.75, 25.0),
        (1.0, 0.0),
    ])
    def test_resist_percent_formula(self, mult, expected_pct):
        rp = ResistProfile(em=mult, thermal=0.5, kinetic=0.5, explosive=0.5)
        assert rp.em_percent == pytest.approx(expected_pct)


class TestResistProfileAverage:
    def test_uniform_resists(self):
        rp = ResistProfile(em=0.5, thermal=0.5, kinetic=0.5, explosive=0.5)
        assert rp.average == pytest.approx(0.5)

    def test_mixed_resists(self):
        rp = ResistProfile(em=0.2, thermal=0.4, kinetic=0.6, explosive=0.8)
        assert rp.average == pytest.approx(0.5)

    def test_zero_resists(self):
        rp = ResistProfile(em=0.0, thermal=0.0, kinetic=0.0, explosive=0.0)
        assert rp.average == pytest.approx(0.0)

    def test_full_vulnerability(self):
        rp = ResistProfile(em=1.0, thermal=1.0, kinetic=1.0, explosive=1.0)
        assert rp.average == pytest.approx(1.0)


class TestResistProfileLowest:
    def test_uniform(self):
        rp = ResistProfile(em=0.5, thermal=0.5, kinetic=0.5, explosive=0.5)
        assert rp.lowest == pytest.approx(0.5)

    def test_em_hole(self):
        rp = ResistProfile(em=0.8, thermal=0.3, kinetic=0.3, explosive=0.3)
        assert rp.lowest == pytest.approx(0.3)

    def test_explosive_hole(self):
        rp = ResistProfile(em=0.2, thermal=0.2, kinetic=0.2, explosive=0.9)
        assert rp.lowest == pytest.approx(0.2)


# ============================================================================
# ShipBaseStats
# ============================================================================

class TestShipBaseStats:
    def test_total_raw_hp(self):
        ship = ShipBaseStats(
            ship_type_id=24698,
            ship_name="Drake",
            shield_hp=5500,
            armor_hp=3250,
            hull_hp=3750,
        )
        assert ship.total_raw_hp == 12500

    def test_total_raw_hp_zero(self):
        ship = ShipBaseStats(ship_type_id=1, ship_name="Empty")
        assert ship.total_raw_hp == 0

    def test_default_resists(self):
        ship = ShipBaseStats(ship_type_id=1, ship_name="Test")
        assert ship.shield_resists.em == 1.0
        assert ship.armor_resists.em == 1.0


# ============================================================================
# FittedModule slot detection
# ============================================================================

class TestFittedModuleSlot:
    @pytest.mark.parametrize("flag,expected_slot", [
        (11, ModuleSlot.LOW),
        (15, ModuleSlot.LOW),
        (18, ModuleSlot.LOW),
        (19, ModuleSlot.MID),
        (23, ModuleSlot.MID),
        (26, ModuleSlot.MID),
        (27, ModuleSlot.HIGH),
        (30, ModuleSlot.HIGH),
        (34, ModuleSlot.HIGH),
        (92, ModuleSlot.RIG),
        (95, ModuleSlot.RIG),
        (99, ModuleSlot.RIG),
        (125, ModuleSlot.SUBSYSTEM),
        (130, ModuleSlot.SUBSYSTEM),
        (132, ModuleSlot.SUBSYSTEM),
    ])
    def test_flag_to_slot(self, flag, expected_slot):
        m = FittedModule(type_id=1234, flag=flag)
        assert m.slot == expected_slot

    @pytest.mark.parametrize("flag", [0, 5, 10, 35, 50, 91, 100, 133, 200])
    def test_unknown_flags_become_cargo(self, flag):
        m = FittedModule(type_id=1234, flag=flag)
        assert m.slot == ModuleSlot.CARGO


# ============================================================================
# TankResult
# ============================================================================

class TestTankResult:
    def test_total_ehp(self):
        tr = TankResult(
            ship_type_id=1, ship_name="Test",
            shield_hp=5000, armor_hp=3000, hull_hp=2000,
            shield_resists=ResistProfile(), armor_resists=ResistProfile(), hull_resists=ResistProfile(),
            shield_ehp=10000, armor_ehp=6000, hull_ehp=2000,
        )
        assert tr.total_ehp == 18000

    def test_total_ehp_zero(self):
        tr = TankResult(
            ship_type_id=1, ship_name="Test",
            shield_hp=0, armor_hp=0, hull_hp=0,
            shield_resists=ResistProfile(), armor_resists=ResistProfile(), hull_resists=ResistProfile(),
            shield_ehp=0, armor_ehp=0, hull_ehp=0,
        )
        assert tr.total_ehp == 0


# ============================================================================
# KillmailAnalysis computed fields
# ============================================================================

class TestKillmailAnalysis:
    def _make_analysis(self, total_ehp: float, fleet_dps: float) -> KillmailAnalysis:
        return KillmailAnalysis(
            killmail_id=1,
            victim_ship_type_id=1,
            victim_ship_name="Test Ship",
            victim_tank=TankResult(
                ship_type_id=1, ship_name="Test Ship",
                shield_hp=1000, armor_hp=1000, hull_hp=1000,
                shield_resists=ResistProfile(), armor_resists=ResistProfile(), hull_resists=ResistProfile(),
                shield_ehp=total_ehp / 3, armor_ehp=total_ehp / 3, hull_ehp=total_ehp / 3,
            ),
            attacker_analysis=AttackerDPSResult(
                total_attackers=5,
                estimated_fleet_dps=fleet_dps,
            ),
        )

    def test_time_to_kill(self):
        km = self._make_analysis(total_ehp=30000, fleet_dps=10000)
        assert km.time_to_kill_seconds == pytest.approx(3.0)

    def test_time_to_kill_zero_dps(self):
        km = self._make_analysis(total_ehp=30000, fleet_dps=0)
        assert km.time_to_kill_seconds == 0

    def test_overkill_ratio(self):
        km = self._make_analysis(total_ehp=10000, fleet_dps=50000)
        assert km.overkill_ratio == pytest.approx(5.0)

    def test_overkill_ratio_zero_ehp(self):
        km = self._make_analysis(total_ehp=0, fleet_dps=50000)
        assert km.overkill_ratio == 0
