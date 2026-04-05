"""Tests for fitting_service.py and fitting_stats_service.py pure functions.

Covers: parse_flag, FLAG_STRING_MAP, FittingItem validator, slot usage calculation,
        Pydantic model defaults, resource usage models, capacitor simulation,
        align time calculation, and new stat categories.
"""

import pytest

from app.services.fitting_service import (
    parse_flag,
    FLAG_STRING_MAP,
    FittingItem,
)
from contextlib import contextmanager

from app.services.fitting_stats import (
    SlotUsage,
    ResourceUsage,
    DamageBreakdown,
    ResistProfile,
    OffenseStats,
    DefenseStats,
    CapacitorStats,
    NavigationStats,
    TargetingStats,
    RepairStats,
    FittingStatsService,
    FittingStatsRequest,
    calculate_capacitor,
    calculate_align_time,
    calculate_lock_time,
    calculate_shield_peak_regen,
    calculate_rep_rate,
    calculate_weapon_dps,
    calculate_drone_dps,
    ATTR_HI_SLOTS,
    ATTR_MED_SLOTS,
    ATTR_LOW_SLOTS,
    ATTR_RIG_SLOTS,
    ATTR_POWER_OUTPUT,
    ATTR_CPU_OUTPUT,
    ATTR_CALIBRATION_OUTPUT,
    ATTR_CAP_CAPACITY,
    ATTR_CAP_RECHARGE,
    ATTR_DRONE_CAPACITY,
    ATTR_DRONE_BANDWIDTH,
    ATTR_TURRET_SLOTS,
    ATTR_LAUNCHER_SLOTS,
    ATTR_MAX_TARGET_RANGE,
    ATTR_SCAN_RES,
    ATTR_MAX_LOCKED,
    ATTR_SCAN_RADAR,
    ATTR_SCAN_LADAR,
    ATTR_SCAN_MAGNETO,
    ATTR_SCAN_GRAVI,
    ATTR_WARP_SPEED_MULT,
    ATTR_MASS,
    ATTR_DAMAGE_MULT,
    ATTR_RATE_OF_FIRE,
    ATTR_EM_DAMAGE,
    ATTR_THERMAL_DAMAGE,
    ATTR_KINETIC_DAMAGE,
    ATTR_EXPLOSIVE_DAMAGE,
    ATTR_META_LEVEL,
    ATTR_CHARGE_GROUP1,
    ATTR_SHIELD_BOOST_AMOUNT,
    ATTR_ARMOR_REPAIR_AMOUNT,
    ATTR_HULL_REPAIR_AMOUNT,
    ATTR_DRONE_CONTROL_RANGE,
    ATTR_CARGO_CAPACITY,
    ATTR_DURATION,
    FLAG_DRONE_BAY,
    EFFECT_TURRET_FITTED,
    EFFECT_LAUNCHER_FITTED,
    ATTR_CPU_NEED,
    ATTR_POWER_NEED,
)


# ---------------------------------------------------------------------------
# parse_flag
# ---------------------------------------------------------------------------

class TestParseFlag:
    """Test ESI flag string → integer conversion."""

    @pytest.mark.parametrize("flag_str,expected", [
        ("LoSlot0", 11),
        ("LoSlot7", 18),
        ("MedSlot0", 19),
        ("MedSlot7", 26),
        ("HiSlot0", 27),
        ("HiSlot7", 34),
        ("RigSlot0", 92),
        ("RigSlot2", 94),
        ("DroneBay", 87),
        ("Cargo", 5),
        ("SubSystemSlot0", 125),
        ("ServiceSlot0", 164),
    ])
    def test_known_string_flags(self, flag_str, expected):
        assert parse_flag(flag_str) == expected

    def test_integer_passthrough(self):
        """Integer flags pass through unchanged."""
        assert parse_flag(11) == 11
        assert parse_flag(27) == 27
        assert parse_flag(0) == 0

    def test_numeric_string(self):
        """String that is a number gets parsed to int."""
        assert parse_flag("27") == 27
        assert parse_flag("92") == 92

    def test_unknown_string_returns_zero(self):
        """Unknown string flag returns 0."""
        assert parse_flag("UnknownSlot") == 0

    def test_non_int_non_str_returns_zero(self):
        """Non-int, non-str returns 0."""
        assert parse_flag(None) == 0
        assert parse_flag(3.14) == 0


# ---------------------------------------------------------------------------
# FLAG_STRING_MAP completeness
# ---------------------------------------------------------------------------

class TestFlagStringMap:
    """Test FLAG_STRING_MAP covers EVE slot types."""

    def test_low_slots_present(self):
        for i in range(8):
            assert f"LoSlot{i}" in FLAG_STRING_MAP

    def test_med_slots_present(self):
        for i in range(8):
            assert f"MedSlot{i}" in FLAG_STRING_MAP

    def test_hi_slots_present(self):
        for i in range(8):
            assert f"HiSlot{i}" in FLAG_STRING_MAP

    def test_rig_slots_present(self):
        for i in range(3):
            assert f"RigSlot{i}" in FLAG_STRING_MAP

    def test_subsystem_slots_present(self):
        for i in range(4):
            assert f"SubSystemSlot{i}" in FLAG_STRING_MAP

    def test_special_flags_present(self):
        for key in ("DroneBay", "FighterBay", "Cargo"):
            assert key in FLAG_STRING_MAP


# ---------------------------------------------------------------------------
# FittingItem pydantic validator
# ---------------------------------------------------------------------------

class TestFittingItem:
    """Test FittingItem model with flag coercion."""

    def test_integer_flag(self):
        item = FittingItem(type_id=3170, flag=27, quantity=1)
        assert item.flag == 27

    def test_string_flag_coerced(self):
        item = FittingItem(type_id=3170, flag="HiSlot0", quantity=1)
        assert item.flag == 27

    def test_string_numeric_flag_coerced(self):
        item = FittingItem(type_id=3170, flag="19", quantity=1)
        assert item.flag == 19

    def test_unknown_string_flag_becomes_zero(self):
        item = FittingItem(type_id=3170, flag="Bogus", quantity=1)
        assert item.flag == 0


# ---------------------------------------------------------------------------
# SlotUsage calculation (_calc_slot_usage logic extracted)
# ---------------------------------------------------------------------------

def _calc_slot_usage_pure(ship_attrs, items):
    """Extracted pure logic from FittingStatsService._calc_slot_usage."""
    hi_used = sum(1 for i in items if 27 <= i.flag <= 34)
    med_used = sum(1 for i in items if 19 <= i.flag <= 26)
    low_used = sum(1 for i in items if 11 <= i.flag <= 18)
    rig_used = sum(1 for i in items if 92 <= i.flag <= 99)

    return SlotUsage(
        hi_total=int(ship_attrs.get(ATTR_HI_SLOTS, 0)),
        hi_used=hi_used,
        med_total=int(ship_attrs.get(ATTR_MED_SLOTS, 0)),
        med_used=med_used,
        low_total=int(ship_attrs.get(ATTR_LOW_SLOTS, 0)),
        low_used=low_used,
        rig_total=int(ship_attrs.get(ATTR_RIG_SLOTS, 0)),
        rig_used=rig_used,
    )


class TestSlotUsageCalculation:
    """Test slot usage counting by flag ranges."""

    def test_empty_fitting(self):
        ship_attrs = {ATTR_HI_SLOTS: 8, ATTR_MED_SLOTS: 5, ATTR_LOW_SLOTS: 3, ATTR_RIG_SLOTS: 3}
        result = _calc_slot_usage_pure(ship_attrs, [])
        assert result.hi_used == 0
        assert result.med_used == 0
        assert result.low_used == 0
        assert result.rig_used == 0
        assert result.hi_total == 8

    def test_high_slot_counting(self):
        items = [
            FittingItem(type_id=3170, flag=27, quantity=1),
            FittingItem(type_id=3170, flag=28, quantity=1),
            FittingItem(type_id=3170, flag=29, quantity=1),
        ]
        ship_attrs = {ATTR_HI_SLOTS: 8, ATTR_MED_SLOTS: 5, ATTR_LOW_SLOTS: 3, ATTR_RIG_SLOTS: 3}
        result = _calc_slot_usage_pure(ship_attrs, items)
        assert result.hi_used == 3

    def test_mixed_slot_counting(self):
        items = [
            FittingItem(type_id=3170, flag=27, quantity=1),  # hi
            FittingItem(type_id=3841, flag=19, quantity=1),  # med
            FittingItem(type_id=3841, flag=20, quantity=1),  # med
            FittingItem(type_id=1306, flag=11, quantity=1),  # low
            FittingItem(type_id=26086, flag=92, quantity=1), # rig
        ]
        ship_attrs = {ATTR_HI_SLOTS: 6, ATTR_MED_SLOTS: 5, ATTR_LOW_SLOTS: 4, ATTR_RIG_SLOTS: 3}
        result = _calc_slot_usage_pure(ship_attrs, items)
        assert result.hi_used == 1
        assert result.med_used == 2
        assert result.low_used == 1
        assert result.rig_used == 1

    def test_missing_ship_attr_defaults_to_zero(self):
        result = _calc_slot_usage_pure({}, [])
        assert result.hi_total == 0
        assert result.med_total == 0


# ---------------------------------------------------------------------------
# Pydantic model defaults
# ---------------------------------------------------------------------------

class TestModelDefaults:
    """Test that Pydantic models have sensible defaults."""

    def test_slot_usage_defaults(self):
        s = SlotUsage()
        assert s.hi_total == 0
        assert s.hi_used == 0

    def test_resource_usage_defaults(self):
        r = ResourceUsage()
        assert r.pg_total == 0
        assert r.cpu_total == 0

    def test_damage_breakdown_defaults(self):
        d = DamageBreakdown()
        assert d.em == 0
        assert d.thermal == 0
        assert d.kinetic == 0
        assert d.explosive == 0

    def test_resist_profile_defaults(self):
        r = ResistProfile()
        assert r.em == 0
        assert r.thermal == 0

    def test_offense_stats_defaults(self):
        o = OffenseStats()
        assert o.total_dps == 0
        assert o.weapon_dps == 0
        assert o.drone_dps == 0
        assert o.volley_damage == 0
        assert o.damage_breakdown.em == 0

    def test_defense_stats_defaults(self):
        d = DefenseStats()
        assert d.total_ehp == 0
        assert d.tank_type == "unknown"

    def test_navigation_stats_defaults(self):
        n = NavigationStats()
        assert n.max_velocity == 0
        assert n.align_time == 0
        assert n.warp_speed == 0
        assert n.agility == 0
        assert n.signature_radius == 0
        assert n.mass == 0

    def test_capacitor_stats_defaults(self):
        c = CapacitorStats()
        assert c.capacity == 0
        assert c.recharge_time == 0
        assert c.peak_recharge_rate == 0
        assert c.usage_rate == 0
        assert c.stable is True
        assert c.stable_percent == 100.0
        assert c.lasts_seconds == 0

    def test_targeting_stats_defaults(self):
        t = TargetingStats()
        assert t.max_range == 0
        assert t.scan_resolution == 0
        assert t.max_locked_targets == 0
        assert t.sensor_strength == 0
        assert t.sensor_type == ""

    def test_resource_usage_extended_defaults(self):
        r = ResourceUsage()
        assert r.calibration_total == 0
        assert r.calibration_used == 0
        assert r.turret_hardpoints_total == 0
        assert r.turret_hardpoints_used == 0
        assert r.launcher_hardpoints_total == 0
        assert r.launcher_hardpoints_used == 0
        assert r.drone_bay_total == 0
        assert r.drone_bay_used == 0
        assert r.drone_bandwidth_total == 0
        assert r.drone_bandwidth_used == 0


# ---------------------------------------------------------------------------
# SDE attribute constants
# ---------------------------------------------------------------------------

class TestAttributeConstants:
    """Verify SDE attribute ID constants are correct per EVE data."""

    def test_slot_attr_ids(self):
        assert ATTR_HI_SLOTS == 14
        assert ATTR_MED_SLOTS == 13
        assert ATTR_LOW_SLOTS == 12
        assert ATTR_RIG_SLOTS == 1137

    def test_resource_attr_ids(self):
        assert ATTR_POWER_OUTPUT == 11
        assert ATTR_CPU_OUTPUT == 48

    def test_new_attribute_constants(self):
        assert ATTR_CALIBRATION_OUTPUT == 1132
        assert ATTR_CAP_CAPACITY == 482
        assert ATTR_CAP_RECHARGE == 55
        assert ATTR_DRONE_CAPACITY == 283
        assert ATTR_DRONE_BANDWIDTH == 1271
        assert ATTR_TURRET_SLOTS == 102
        assert ATTR_LAUNCHER_SLOTS == 101
        assert ATTR_MAX_TARGET_RANGE == 76
        assert ATTR_SCAN_RES == 564
        assert ATTR_MAX_LOCKED == 192
        assert ATTR_SCAN_RADAR == 208
        assert ATTR_SCAN_LADAR == 209
        assert ATTR_SCAN_MAGNETO == 210
        assert ATTR_SCAN_GRAVI == 211
        assert ATTR_WARP_SPEED_MULT == 600
        assert ATTR_MASS == 4

    def test_effect_constants(self):
        assert EFFECT_TURRET_FITTED == 42
        assert EFFECT_LAUNCHER_FITTED == 40


# ---------------------------------------------------------------------------
# Capacitor simulation (pure function)
# ---------------------------------------------------------------------------

class TestCalculateCapacitor:
    """Test EVE capacitor simulation."""

    def test_empty_fit_is_stable(self):
        """No active modules = 100% cap stable."""
        result = calculate_capacitor(cap_capacity=2000, cap_recharge_ms=300000, module_cap_per_sec=0)
        assert result.stable
        assert result.stable_percent == 100.0
        assert result.peak_recharge_rate > 0
        assert result.capacity == 2000.0
        assert result.recharge_time == 300.0

    def test_moderate_usage_stable(self):
        """Usage below peak recharge = stable at some %."""
        result = calculate_capacitor(cap_capacity=2000, cap_recharge_ms=300000, module_cap_per_sec=2.0)
        assert result.stable
        assert 0 < result.stable_percent < 100
        assert result.usage_rate == 2.0

    def test_heavy_usage_unstable(self):
        """Usage exceeding peak recharge = cap runs out."""
        result = calculate_capacitor(cap_capacity=2000, cap_recharge_ms=300000, module_cap_per_sec=50.0)
        assert not result.stable
        assert result.lasts_seconds > 0
        assert result.stable_percent == 0
        assert result.usage_rate == 50.0

    def test_zero_cap_returns_default(self):
        result = calculate_capacitor(0, 0, 0)
        assert result.capacity == 0
        assert result.stable

    def test_negative_cap_returns_default(self):
        result = calculate_capacitor(-100, 300000, 0)
        assert result.capacity == 0

    def test_negative_recharge_returns_default(self):
        result = calculate_capacitor(2000, -1, 0)
        assert result.capacity == 0

    def test_peak_recharge_rate(self):
        """peak = 2.5 * cap / tau_s."""
        result = calculate_capacitor(2000, 300000, 0)
        # tau_s = 300, peak = 2.5 * 2000 / 300 = 16.67
        assert abs(result.peak_recharge_rate - 16.67) < 0.1

    def test_exactly_at_peak_is_unstable(self):
        """Usage exactly at peak recharge rate = unstable (edge case)."""
        # peak = 2.5 * 2000 / 300 = 16.667
        result = calculate_capacitor(2000, 300000, 16.67)
        assert not result.stable
        assert result.lasts_seconds > 0

    def test_just_below_peak_is_stable(self):
        """Usage just below peak recharge = stable near 25%."""
        result = calculate_capacitor(2000, 300000, 16.0)
        assert result.stable
        # Stable percent should be near 25% (where peak recharge occurs)
        assert result.stable_percent > 0

    def test_lasts_seconds_calculation(self):
        """Time-step simulation gives slightly longer than cap/usage due to recharge."""
        result = calculate_capacitor(2000, 300000, 100.0)
        assert not result.stable
        # Simple: 2000/100 = 20s, but recharge adds ~1-2s
        assert 20.0 < result.lasts_seconds <= 23.0

    def test_very_low_usage_stable_near_100(self):
        """Very low usage = stable near 100%."""
        result = calculate_capacitor(2000, 300000, 0.01)
        assert result.stable
        assert result.stable_percent > 95


# ---------------------------------------------------------------------------
# Align time calculation (pure function)
# ---------------------------------------------------------------------------

class TestCalculateAlignTime:
    """Test EVE align time calculation with server-tick ceil()."""

    def test_frigate_align(self):
        """Typical frigate: mass=1.1M, agility=3.2 -> raw ~4.88s."""
        align = calculate_align_time(mass=1_100_000, agility=3.2)
        assert align == pytest.approx(4.88, abs=0.01)

    def test_battleship_align(self):
        """Battleship: mass=100M, agility=0.12 -> raw ~16.64s."""
        align = calculate_align_time(mass=100_000_000, agility=0.12)
        assert align == pytest.approx(16.64, abs=0.01)

    def test_zero_mass(self):
        assert calculate_align_time(0, 3.2) == 0

    def test_zero_agility(self):
        assert calculate_align_time(1_100_000, 0) == 0

    def test_negative_mass(self):
        assert calculate_align_time(-1_000_000, 3.2) == 0

    def test_negative_agility(self):
        assert calculate_align_time(1_100_000, -1.0) == 0

    def test_known_value(self):
        """ln(0.25) = -1.386294..., raw = 1.386294s."""
        align = calculate_align_time(mass=1_000_000, agility=1.0)
        assert align == pytest.approx(1.39, abs=0.01)

    def test_capital_align(self):
        """Capital: mass=1.2B, agility=0.015 -> raw ~24.95s."""
        align = calculate_align_time(mass=1_200_000_000, agility=0.015)
        assert align == pytest.approx(24.95, abs=0.01)


class TestAlignTimeContinuous:
    """Continuous align time (as shown in EVE client simulation)."""

    def test_continuous_value(self):
        """2.01s raw -> 2.01s (continuous, not ceiled)."""
        result = calculate_align_time(1_000_000, 1.4498)
        assert result == pytest.approx(2.01, abs=0.01)

    def test_sub_one_second(self):
        """Short align returns actual value."""
        result = calculate_align_time(100_000, 0.36)
        assert result == pytest.approx(0.05, abs=0.01)

    def test_returns_float(self):
        """Return type must be float."""
        result = calculate_align_time(1_000_000, 3.0)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# Lock Time calculation (pure function)
# ---------------------------------------------------------------------------

class TestLockTime:
    """Test EVE lock time formula: 40000 / (scan_res * asinh(sig)^2)."""

    def test_battleship_locking_frigate(self):
        """BS scan res ~100, frigate sig 35m -> slow lock."""
        result = calculate_lock_time(scan_resolution=100, sig_radius=35)
        assert result > 10  # should be ~30s

    def test_frigate_locking_battleship(self):
        """Frigate scan res ~600, BS sig 450m -> fast lock."""
        result = calculate_lock_time(scan_resolution=600, sig_radius=450)
        assert result < 2  # near instant

    def test_zero_scan_res(self):
        assert calculate_lock_time(0, 100) == 0

    def test_zero_sig(self):
        assert calculate_lock_time(100, 0) == 0

    def test_minimum_one_second(self):
        """Even with huge scan res and sig, minimum is 1s."""
        result = calculate_lock_time(10000, 10000)
        assert result >= 1.0


# ---------------------------------------------------------------------------
# Shield Regen & Repair Rates (pure functions)
# ---------------------------------------------------------------------------

class TestRegenRates:
    """Test shield passive regen and active repair rate calculations."""

    def test_shield_peak_regen(self):
        """Peak shield regen = 2.5 * shield_hp / recharge_time_s."""
        # 5000 HP, 200s (200_000ms) recharge -> peak = 2.5 * 5000 / 200 = 62.5 HP/s
        result = calculate_shield_peak_regen(5000, 200_000)
        assert result == pytest.approx(62.5)

    def test_armor_rep_rate(self):
        """Armor rep HP/s = repair_amount / (cycle_time_ms / 1000)."""
        # 400 HP per 4500ms cycle -> 88.89 HP/s
        result = calculate_rep_rate(400, 4500)
        assert result == pytest.approx(88.89, abs=0.01)

    def test_zero_recharge(self):
        assert calculate_shield_peak_regen(5000, 0) == 0

    def test_zero_shield_hp(self):
        assert calculate_shield_peak_regen(0, 200_000) == 0

    def test_zero_repair_amount(self):
        assert calculate_rep_rate(0, 4500) == 0

    def test_zero_cycle_time(self):
        assert calculate_rep_rate(400, 0) == 0


# ---------------------------------------------------------------------------
# Cap Booster in Discrete Simulation
# ---------------------------------------------------------------------------

class TestCapBoosterSimulation:
    """Test cap booster injection in discrete capacitor simulation."""

    def test_cap_booster_improves_stability(self):
        """Cap booster injects GJ periodically, improving cap stability."""
        # Heavy drain without booster — borderline stable at very low %
        no_boost = calculate_capacitor(2000, 100_000, 50.0,
            module_drains=[(250, 5000)])
        # With booster: 800 GJ per 12s = 66.7 GJ/s inject — much more stable
        with_boost = calculate_capacitor(2000, 100_000, 50.0,
            module_drains=[(250, 5000)],
            cap_injectors=[(800, 12000)])
        assert with_boost.stable_percent > no_boost.stable_percent

    def test_no_injectors_unchanged(self):
        """No injectors = same as before."""
        result = calculate_capacitor(2000, 100_000, 15.0,
            module_drains=[(75, 5000)], cap_injectors=[])
        result2 = calculate_capacitor(2000, 100_000, 15.0,
            module_drains=[(75, 5000)])
        assert result.lasts_seconds == result2.lasts_seconds


# ---------------------------------------------------------------------------
# Weapon DPS calculation (pure function)
# ---------------------------------------------------------------------------

class TestCalculateWeaponDps:
    """Test weapon DPS calculation from damage multiplier, RoF, and charge damage."""

    def test_basic_weapon_dps(self):
        """Weapon with RoF=5000ms, mult=3.0, kinetic=75.6 -> 45.36 DPS."""
        result = calculate_weapon_dps(
            damage_mult=3.0, rate_of_fire_ms=5000,
            charge_em=0, charge_thermal=0, charge_kinetic=75.6, charge_explosive=0
        )
        assert abs(result["dps"] - 45.36) < 0.1
        assert abs(result["kinetic"] - 45.36) < 0.1
        assert result["em"] == 0
        assert result["thermal"] == 0
        assert result["explosive"] == 0

    def test_mixed_damage_breakdown(self):
        """50/50 kin/exp split distributes DPS equally."""
        result = calculate_weapon_dps(
            damage_mult=2.0, rate_of_fire_ms=4000,
            charge_em=0, charge_thermal=0, charge_kinetic=50, charge_explosive=50
        )
        total = result["dps"]
        assert total > 0
        assert abs(result["kinetic"] - total / 2) < 0.1
        assert abs(result["explosive"] - total / 2) < 0.1

    def test_four_way_damage_split(self):
        """Equal damage across all 4 types."""
        result = calculate_weapon_dps(
            damage_mult=1.0, rate_of_fire_ms=1000,
            charge_em=25, charge_thermal=25, charge_kinetic=25, charge_explosive=25
        )
        # Total volley = 1.0 * 100 = 100, dps = 100 / 1.0 = 100
        assert abs(result["dps"] - 100) < 0.1
        assert abs(result["em"] - 25) < 0.1
        assert abs(result["thermal"] - 25) < 0.1
        assert abs(result["kinetic"] - 25) < 0.1
        assert abs(result["explosive"] - 25) < 0.1

    def test_zero_rof_returns_zero(self):
        """Zero rate of fire returns zero DPS."""
        result = calculate_weapon_dps(0, 0, 0, 0, 0, 0)
        assert result["dps"] == 0
        assert result["volley"] == 0

    def test_zero_damage_mult_returns_zero(self):
        """Zero damage multiplier returns zero DPS."""
        result = calculate_weapon_dps(
            damage_mult=0, rate_of_fire_ms=5000,
            charge_em=10, charge_thermal=20, charge_kinetic=30, charge_explosive=40
        )
        assert result["dps"] == 0

    def test_negative_rof_returns_zero(self):
        """Negative rate of fire returns zero DPS."""
        result = calculate_weapon_dps(
            damage_mult=3.0, rate_of_fire_ms=-1000,
            charge_em=0, charge_thermal=0, charge_kinetic=50, charge_explosive=0
        )
        assert result["dps"] == 0

    def test_volley_damage(self):
        """Volley = mult * total_charge_dmg."""
        result = calculate_weapon_dps(
            damage_mult=3.0, rate_of_fire_ms=5000,
            charge_em=10, charge_thermal=20, charge_kinetic=30, charge_explosive=40
        )
        assert abs(result["volley"] - 300) < 0.1  # 3.0 * 100

    def test_high_rof_weapon(self):
        """Fast weapon (1000ms cycle) = higher DPS."""
        result = calculate_weapon_dps(
            damage_mult=1.0, rate_of_fire_ms=1000,
            charge_em=0, charge_thermal=50, charge_kinetic=0, charge_explosive=0
        )
        # volley = 1.0 * 50 = 50, dps = 50 / 1.0 = 50
        assert abs(result["dps"] - 50) < 0.1

    def test_zero_charge_damage_returns_zero_dps(self):
        """Weapon with no charge damage = 0 DPS (all breakdown zero too)."""
        result = calculate_weapon_dps(
            damage_mult=3.0, rate_of_fire_ms=5000,
            charge_em=0, charge_thermal=0, charge_kinetic=0, charge_explosive=0
        )
        assert result["dps"] == 0
        assert result["volley"] == 0
        assert result["em"] == 0
        assert result["thermal"] == 0
        assert result["kinetic"] == 0
        assert result["explosive"] == 0

    def test_result_keys(self):
        """Result dict has all expected keys."""
        result = calculate_weapon_dps(1, 1000, 10, 0, 0, 0)
        assert set(result.keys()) == {"dps", "em", "thermal", "kinetic", "explosive", "volley"}


# ---------------------------------------------------------------------------
# Drone DPS calculation (pure function)
# ---------------------------------------------------------------------------

class TestCalculateDroneDps:
    """Test drone DPS calculation."""

    def test_single_warrior(self):
        """Warrior II: mult=3.19, rof=3000, em=3.2, exp=4.8 -> ~8.5 DPS."""
        result = calculate_drone_dps(
            drone_damage_mult=3.19, drone_rof_ms=3000,
            em=3.2, thermal=0, kinetic=0, explosive=4.8, count=1
        )
        # volley = 3.19 * 8.0 = 25.52, dps = 25.52 / 3.0 = 8.507
        assert result["dps"] > 8
        assert result["dps"] < 10

    def test_five_warriors(self):
        """5x Warrior II -> ~42.5 DPS."""
        result = calculate_drone_dps(
            drone_damage_mult=3.19, drone_rof_ms=3000,
            em=3.2, thermal=0, kinetic=0, explosive=4.8, count=5
        )
        assert result["dps"] > 40
        assert result["dps"] < 50

    def test_drone_damage_breakdown(self):
        """Drone DPS splits proportionally by damage type."""
        result = calculate_drone_dps(
            drone_damage_mult=2.0, drone_rof_ms=2000,
            em=5, thermal=5, kinetic=5, explosive=5, count=1
        )
        # Total dmg per shot = 20, volley = 40, dps = 40/2 = 20
        assert abs(result["dps"] - 20) < 0.1
        assert abs(result["em"] - 5) < 0.1
        assert abs(result["thermal"] - 5) < 0.1
        assert abs(result["kinetic"] - 5) < 0.1
        assert abs(result["explosive"] - 5) < 0.1

    def test_zero_count(self):
        """Zero drone count returns zero DPS."""
        result = calculate_drone_dps(1, 1000, 10, 10, 10, 10, count=0)
        assert result["dps"] == 0

    def test_zero_rof(self):
        """Zero RoF returns zero DPS."""
        result = calculate_drone_dps(3.0, 0, 10, 10, 10, 10, count=5)
        assert result["dps"] == 0

    def test_zero_damage_mult(self):
        """Zero damage mult returns zero DPS."""
        result = calculate_drone_dps(0, 3000, 10, 10, 10, 10, count=5)
        assert result["dps"] == 0

    def test_negative_rof(self):
        """Negative RoF returns zero DPS."""
        result = calculate_drone_dps(3.0, -1000, 10, 10, 10, 10, count=1)
        assert result["dps"] == 0

    def test_single_damage_type_drone(self):
        """Drone with only thermal damage."""
        result = calculate_drone_dps(
            drone_damage_mult=2.0, drone_rof_ms=4000,
            em=0, thermal=12, kinetic=0, explosive=0, count=3
        )
        # volley = 2 * 12 = 24, dps/drone = 24/4 = 6, total = 18
        assert abs(result["dps"] - 18) < 0.1
        assert abs(result["thermal"] - 18) < 0.1
        assert result["em"] == 0
        assert result["kinetic"] == 0
        assert result["explosive"] == 0

    def test_result_keys(self):
        """Result dict has all expected keys."""
        result = calculate_drone_dps(1, 1000, 10, 0, 0, 0, count=1)
        assert set(result.keys()) == {"dps", "em", "thermal", "kinetic", "explosive"}

    def test_count_scales_linearly(self):
        """DPS scales linearly with drone count."""
        single = calculate_drone_dps(3.0, 3000, 5, 5, 5, 5, count=1)
        double = calculate_drone_dps(3.0, 3000, 5, 5, 5, 5, count=2)
        assert abs(double["dps"] - single["dps"] * 2) < 0.01


# ---------------------------------------------------------------------------
# New attribute constants
# ---------------------------------------------------------------------------

class TestNewAttributeConstants:
    """Verify new SDE attribute ID constants."""

    def test_damage_attr_ids(self):
        assert ATTR_DAMAGE_MULT == 64
        assert ATTR_EM_DAMAGE == 114
        assert ATTR_EXPLOSIVE_DAMAGE == 116
        assert ATTR_KINETIC_DAMAGE == 117
        assert ATTR_THERMAL_DAMAGE == 118

    def test_charge_group_attr_ids(self):
        assert ATTR_CHARGE_GROUP1 == 604
        assert ATTR_META_LEVEL == 633

    def test_drone_flag(self):
        assert FLAG_DRONE_BAY == 87

    def test_repair_attr_ids(self):
        assert ATTR_SHIELD_BOOST_AMOUNT == 68
        assert ATTR_ARMOR_REPAIR_AMOUNT == 84
        assert ATTR_HULL_REPAIR_AMOUNT == 1886

    def test_ship_extra_attr_ids(self):
        assert ATTR_DRONE_CONTROL_RANGE == 858
        assert ATTR_CARGO_CAPACITY == 38


# ---------------------------------------------------------------------------
# RepairStats model defaults
# ---------------------------------------------------------------------------

class TestRepairStatsDefaults:
    """Test RepairStats Pydantic model defaults."""

    def test_defaults(self):
        r = RepairStats()
        assert r.shield_rep == 0
        assert r.armor_rep == 0
        assert r.hull_rep == 0

    def test_custom_values(self):
        r = RepairStats(shield_rep=20.5, armor_rep=10.3, hull_rep=5.1)
        assert r.shield_rep == 20.5
        assert r.armor_rep == 10.3
        assert r.hull_rep == 5.1


# ---------------------------------------------------------------------------
# Extended model defaults (new fields on existing models)
# ---------------------------------------------------------------------------

class TestExtendedModelDefaults:
    """Test new fields on existing models have correct defaults."""

    def test_targeting_drone_control_range_default(self):
        t = TargetingStats()
        assert t.drone_control_range == 0

    def test_navigation_cargo_capacity_default(self):
        n = NavigationStats()
        assert n.cargo_capacity == 0

    def test_fitting_stats_response_has_repairs(self):
        """FittingStatsResponse includes repairs field with default."""
        from app.services.fitting_stats import FittingStatsResponse
        resp = FittingStatsResponse(
            ship={"type_id": 1, "name": "Test", "group_name": "Test"},
            slots=SlotUsage(),
            resources=ResourceUsage(),
            offense=OffenseStats(),
            defense=DefenseStats(),
            capacitor=CapacitorStats(),
            navigation=NavigationStats(),
            targeting=TargetingStats(),
        )
        assert resp.repairs.shield_rep == 0
        assert resp.repairs.armor_rep == 0
        assert resp.repairs.hull_rep == 0


# ---------------------------------------------------------------------------
# Repair calculation (_calc_repairs via MockDB)
# ---------------------------------------------------------------------------

class _MockCursorForRepairs:
    """Mock cursor that returns pre-set rows for repair tests."""

    def __init__(self, rows=None):
        self._rows = rows or []

    def execute(self, sql, params=None):
        pass

    def fetchall(self):
        return self._rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _MockDBForRepairs:
    """Mock DB object providing cursor() as context manager with cursor_factory kwarg."""

    def __init__(self, cursor):
        self._cursor = cursor

    @contextmanager
    def cursor(self, cursor_factory=None):
        yield self._cursor


def _make_repair_service(db_rows):
    """Create a FittingStatsService with mocked DB for repair tests."""
    cursor = _MockCursorForRepairs(db_rows)
    db = _MockDBForRepairs(cursor)
    return FittingStatsService(db=db, redis=None)


class TestRepairStats:
    """Test _calc_repairs() method on FittingStatsService."""

    def test_shield_booster_rep_rate(self):
        """Shield Booster I: 80 HP / 4000ms = 20 HP/s."""
        db_rows = [
            {"typeID": 3538, "attributeID": ATTR_SHIELD_BOOST_AMOUNT, "value": 80.0},
            {"typeID": 3538, "attributeID": ATTR_DURATION, "value": 4000.0},
        ]
        service = _make_repair_service(db_rows)
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[FittingItem(type_id=3538, flag=19, quantity=1)],
        )
        result = service._calc_repairs(req)
        assert result.shield_rep == 20.0
        assert result.armor_rep == 0
        assert result.hull_rep == 0

    def test_armor_repairer_rep_rate(self):
        """Armor Repairer I: 60 HP / 6000ms = 10 HP/s."""
        db_rows = [
            {"typeID": 3057, "attributeID": ATTR_ARMOR_REPAIR_AMOUNT, "value": 60.0},
            {"typeID": 3057, "attributeID": ATTR_DURATION, "value": 6000.0},
        ]
        service = _make_repair_service(db_rows)
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[FittingItem(type_id=3057, flag=12, quantity=1)],
        )
        result = service._calc_repairs(req)
        assert result.armor_rep == 10.0
        assert result.shield_rep == 0
        assert result.hull_rep == 0

    def test_hull_repairer_rep_rate(self):
        """Hull Repairer I: 40 HP / 5000ms = 8 HP/s."""
        db_rows = [
            {"typeID": 4999, "attributeID": ATTR_HULL_REPAIR_AMOUNT, "value": 40.0},
            {"typeID": 4999, "attributeID": ATTR_DURATION, "value": 5000.0},
        ]
        service = _make_repair_service(db_rows)
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[FittingItem(type_id=4999, flag=11, quantity=1)],
        )
        result = service._calc_repairs(req)
        assert result.hull_rep == 8.0
        assert result.shield_rep == 0
        assert result.armor_rep == 0

    def test_no_repair_modules_returns_zeros(self):
        """Fitting with only drones and cargo returns zero repairs."""
        service = _make_repair_service([])
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[
                FittingItem(type_id=2488, flag=87, quantity=5),  # drones
                FittingItem(type_id=11379, flag=5, quantity=1),  # cargo
            ],
        )
        result = service._calc_repairs(req)
        assert result.shield_rep == 0
        assert result.armor_rep == 0
        assert result.hull_rep == 0

    def test_empty_fitting_returns_zeros(self):
        """Fitting with no items at all returns zero repairs."""
        service = _make_repair_service([])
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[],
        )
        result = service._calc_repairs(req)
        assert result.shield_rep == 0
        assert result.armor_rep == 0
        assert result.hull_rep == 0

    def test_multiple_repairers_sum(self):
        """Two armor repairers should sum their rates."""
        db_rows = [
            {"typeID": 3057, "attributeID": ATTR_ARMOR_REPAIR_AMOUNT, "value": 60.0},
            {"typeID": 3057, "attributeID": ATTR_DURATION, "value": 6000.0},
        ]
        service = _make_repair_service(db_rows)
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[
                FittingItem(type_id=3057, flag=11, quantity=1),
                FittingItem(type_id=3057, flag=12, quantity=1),
            ],
        )
        result = service._calc_repairs(req)
        # 60/6 = 10 HP/s per module, qty=1 each, 2 items = 20 HP/s
        assert result.armor_rep == 20.0

    def test_drones_excluded_from_repairs(self):
        """Items with flag=87 (drones) should not be counted as repair modules."""
        db_rows = [
            {"typeID": 3538, "attributeID": ATTR_SHIELD_BOOST_AMOUNT, "value": 80.0},
            {"typeID": 3538, "attributeID": ATTR_DURATION, "value": 4000.0},
        ]
        service = _make_repair_service(db_rows)
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[
                FittingItem(type_id=3538, flag=87, quantity=5),  # drone bay
            ],
        )
        result = service._calc_repairs(req)
        assert result.shield_rep == 0
        assert result.armor_rep == 0
        assert result.hull_rep == 0

    def test_cargo_excluded_from_repairs(self):
        """Items with flag=5 (cargo) should not be counted as repair modules."""
        db_rows = [
            {"typeID": 3538, "attributeID": ATTR_SHIELD_BOOST_AMOUNT, "value": 80.0},
            {"typeID": 3538, "attributeID": ATTR_DURATION, "value": 4000.0},
        ]
        service = _make_repair_service(db_rows)
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[
                FittingItem(type_id=3538, flag=5, quantity=1),  # cargo
            ],
        )
        result = service._calc_repairs(req)
        assert result.shield_rep == 0
        assert result.armor_rep == 0
        assert result.hull_rep == 0

    def test_module_without_duration_skipped(self):
        """Module with no duration attribute should be skipped."""
        db_rows = [
            {"typeID": 3538, "attributeID": ATTR_SHIELD_BOOST_AMOUNT, "value": 80.0},
            # No ATTR_DURATION row
        ]
        service = _make_repair_service(db_rows)
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[FittingItem(type_id=3538, flag=19, quantity=1)],
        )
        result = service._calc_repairs(req)
        assert result.shield_rep == 0

    def test_quantity_multiplied(self):
        """Quantity multiplier applies to rep rate."""
        db_rows = [
            {"typeID": 3538, "attributeID": ATTR_SHIELD_BOOST_AMOUNT, "value": 100.0},
            {"typeID": 3538, "attributeID": ATTR_DURATION, "value": 5000.0},
        ]
        service = _make_repair_service(db_rows)
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[FittingItem(type_id=3538, flag=19, quantity=3)],
        )
        result = service._calc_repairs(req)
        # 100 / 5.0 = 20 HP/s * 3 = 60 HP/s
        assert result.shield_rep == 60.0

    def test_mixed_repair_types(self):
        """Fitting with shield booster and armor repairer returns both rates."""
        db_rows = [
            {"typeID": 3538, "attributeID": ATTR_SHIELD_BOOST_AMOUNT, "value": 80.0},
            {"typeID": 3538, "attributeID": ATTR_DURATION, "value": 4000.0},
            {"typeID": 3057, "attributeID": ATTR_ARMOR_REPAIR_AMOUNT, "value": 60.0},
            {"typeID": 3057, "attributeID": ATTR_DURATION, "value": 6000.0},
        ]
        service = _make_repair_service(db_rows)
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[
                FittingItem(type_id=3538, flag=19, quantity=1),  # shield booster
                FittingItem(type_id=3057, flag=11, quantity=1),  # armor repairer
            ],
        )
        result = service._calc_repairs(req)
        assert result.shield_rep == 20.0  # 80 / 4.0
        assert result.armor_rep == 10.0   # 60 / 6.0
        assert result.hull_rep == 0


# ---------------------------------------------------------------------------
# Hardpoint validation (_validate_fitting hardpoint check via MockDB)
# ---------------------------------------------------------------------------

class _MultiResultCursor:
    """Mock cursor that returns different rows for successive execute() calls."""

    def __init__(self, result_sets):
        self._results = list(result_sets)
        self._idx = 0

    def execute(self, sql, params=None):
        pass

    def fetchall(self):
        if self._idx < len(self._results):
            rows = self._results[self._idx]
            self._idx += 1
            return rows
        return []

    def fetchone(self):
        if self._idx < len(self._results):
            rows = self._results[self._idx]
            self._idx += 1
            return rows[0] if rows else None
        return None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _MultiResultDB:
    """Mock DB that always yields the same multi-result cursor."""

    def __init__(self, cursor):
        self._cursor = cursor

    @contextmanager
    def cursor(self, cursor_factory=None):
        yield self._cursor


def _make_validate_service(result_sets):
    cursor = _MultiResultCursor(result_sets)
    db = _MultiResultDB(cursor)
    return FittingStatsService(db=db, redis=None)


class TestHardpointValidation:
    """Test that _validate_fitting catches turret/launcher hardpoint overfit."""

    def test_launcher_overfit_detected(self):
        """Fitting 4 launchers on a 3-launcher ship produces a violation."""
        # _validate_fitting DB call order (no rigs → _sum_rig_attr returns early):
        # 1. _sum_cpu_pg_with_skills → attributes (CPU+PG)
        # 2. _sum_cpu_pg_with_skills → effects (turret/launcher)
        # 3. load_fitting_constraints → fetchall
        # 4. _load_module_groups → fetchall
        # 5. hardpoint effects query → fetchall
        ship_attrs = {
            ATTR_CPU_OUTPUT: 200.0,
            ATTR_POWER_OUTPUT: 40.0,
            ATTR_CALIBRATION_OUTPUT: 400.0,
            ATTR_TURRET_SLOTS: 0,
            ATTR_LAUNCHER_SLOTS: 3,
        }
        items = [
            FittingItem(type_id=2410, flag=27, quantity=1),  # launcher 1
            FittingItem(type_id=2410, flag=28, quantity=1),  # launcher 2
            FittingItem(type_id=2410, flag=29, quantity=1),  # launcher 3
            FittingItem(type_id=2410, flag=30, quantity=1),  # launcher 4 (excess!)
        ]
        result_sets = [
            [{"typeID": 2410, "attributeID": ATTR_CPU_NEED, "value": 30.0},
             {"typeID": 2410, "attributeID": ATTR_POWER_NEED, "value": 5.0}],  # 1: CPU+PG attrs
            [{"typeID": 2410, "effectID": EFFECT_LAUNCHER_FITTED}],  # 2: weapon effects
            [],                                         # 3: maxGroupFitted/maxTypeFitted
            [{"typeID": 2410, "groupID": 137}],        # 4: module groups
            [{"typeID": 2410, "effectID": EFFECT_LAUNCHER_FITTED}],  # 5: hardpoint effects
        ]
        service = _make_validate_service(result_sets)
        violations = service._validate_fitting(ship_attrs, items)
        hp_violations = [v for v in violations if v["resource"] == "launcher_hardpoints"]
        assert len(hp_violations) == 1
        assert hp_violations[0]["used"] == 4
        assert hp_violations[0]["total"] == 3

    def test_within_hardpoint_limit_no_violation(self):
        """Fitting 3 launchers on a 3-launcher ship is fine."""
        ship_attrs = {
            ATTR_CPU_OUTPUT: 200.0,
            ATTR_POWER_OUTPUT: 40.0,
            ATTR_CALIBRATION_OUTPUT: 400.0,
            ATTR_TURRET_SLOTS: 0,
            ATTR_LAUNCHER_SLOTS: 3,
        }
        items = [
            FittingItem(type_id=2410, flag=27, quantity=1),
            FittingItem(type_id=2410, flag=28, quantity=1),
            FittingItem(type_id=2410, flag=29, quantity=1),
        ]
        result_sets = [
            [{"typeID": 2410, "attributeID": ATTR_CPU_NEED, "value": 30.0},
             {"typeID": 2410, "attributeID": ATTR_POWER_NEED, "value": 5.0}],
            [{"typeID": 2410, "effectID": EFFECT_LAUNCHER_FITTED}],
            [],
            [{"typeID": 2410, "groupID": 137}],
            [{"typeID": 2410, "effectID": EFFECT_LAUNCHER_FITTED}],
        ]
        service = _make_validate_service(result_sets)
        violations = service._validate_fitting(ship_attrs, items)
        hp_violations = [v for v in violations if v["resource"] in ("launcher_hardpoints", "turret_hardpoints")]
        assert len(hp_violations) == 0

    def test_turret_overfit_detected(self):
        """Fitting 3 turrets on a 2-turret ship."""
        ship_attrs = {
            ATTR_CPU_OUTPUT: 400.0,
            ATTR_POWER_OUTPUT: 100.0,
            ATTR_CALIBRATION_OUTPUT: 400.0,
            ATTR_TURRET_SLOTS: 2,
            ATTR_LAUNCHER_SLOTS: 0,
        }
        items = [
            FittingItem(type_id=3170, flag=27, quantity=1),
            FittingItem(type_id=3170, flag=28, quantity=1),
            FittingItem(type_id=3170, flag=29, quantity=1),
        ]
        result_sets = [
            [{"typeID": 3170, "attributeID": ATTR_CPU_NEED, "value": 20.0},
             {"typeID": 3170, "attributeID": ATTR_POWER_NEED, "value": 10.0}],
            [{"typeID": 3170, "effectID": EFFECT_TURRET_FITTED}],
            [],
            [{"typeID": 3170, "groupID": 74}],
            [{"typeID": 3170, "effectID": EFFECT_TURRET_FITTED}],
        ]
        service = _make_validate_service(result_sets)
        violations = service._validate_fitting(ship_attrs, items)
        hp_violations = [v for v in violations if v["resource"] == "turret_hardpoints"]
        assert len(hp_violations) == 1
        assert hp_violations[0]["used"] == 3
        assert hp_violations[0]["total"] == 2


# ---------------------------------------------------------------------------
# Propmod speed effects (AB/MWD)
# ---------------------------------------------------------------------------


from app.services.fitting_stats import (
    EFFECT_AFTERBURNER,
    EFFECT_MWD,
    ATTR_SPEED_BOOST_FACTOR,
    ATTR_SPEED_FACTOR,
    ATTR_MASS_ADDITION,
    ATTR_MAX_VELOCITY,
)


def _make_propmod_service(result_sets):
    """Create FittingStatsService with mocked DB for propmod tests.

    _apply_propmod_effects makes 2 DB calls:
    1. dgmTypeEffects for AB/MWD effect lookup
    2. dgmTypeAttributes for propmod attrs
    """
    cursor = _MultiResultCursor(result_sets)
    db = _MultiResultDB(cursor)
    return FittingStatsService(db=db, redis=None)


class TestPropmodEffects:
    """Test _apply_propmod_effects for AB and MWD speed calculation."""

    def test_afterburner_speed_boost(self):
        """AB I on a frigate: velocity * (1 + speedBoostFactor/100 * thrust/mass)."""
        # AB I: speedBoostFactor=135, speedFactor(thrust)=1125000
        # Ship: mass=1,000,000 kg, velocity=400 m/s
        ship_attrs = {ATTR_MAX_VELOCITY: 400.0, ATTR_MASS: 1_000_000.0}
        items = [FittingItem(type_id=439, flag=19, quantity=1)]  # AB in mid slot

        result_sets = [
            # 1: dgmTypeEffects → AB effect
            [{"typeID": 439, "effectID": EFFECT_AFTERBURNER}],
            # 2: dgmTypeAttributes
            [
                {"attributeID": ATTR_SPEED_BOOST_FACTOR, "value": 135.0},
                {"attributeID": ATTR_SPEED_FACTOR, "value": 1_125_000.0},
            ],
        ]
        service = _make_propmod_service(result_sets)
        result = service._apply_propmod_effects(ship_attrs, items)

        # speed_boost = 135/100 * 1125000/1000000 * 1.25(AC V) = 1.8984375
        # velocity = 400 * (1 + 1.8984375) = 400 * 2.8984375 = 1159.375
        ac_mult = 1.25  # Acceleration Control V
        expected = 400.0 * (1 + 1.35 * 1_125_000.0 / 1_000_000.0 * ac_mult)
        assert result[ATTR_MAX_VELOCITY] == pytest.approx(expected)
        # Mass unchanged for AB
        assert result[ATTR_MASS] == pytest.approx(1_000_000.0)

    def test_mwd_speed_boost_with_mass_addition(self):
        """MWD I: adds mass before speed calc, reducing effective boost."""
        # MWD I: speedBoostFactor=500, thrust=5000000, massAddition=50000000
        # Ship: mass=10,000,000, velocity=300
        ship_attrs = {ATTR_MAX_VELOCITY: 300.0, ATTR_MASS: 10_000_000.0}
        items = [FittingItem(type_id=434, flag=20, quantity=1)]  # MWD in mid

        result_sets = [
            [{"typeID": 434, "effectID": EFFECT_MWD}],
            [
                {"attributeID": ATTR_SPEED_BOOST_FACTOR, "value": 500.0},
                {"attributeID": ATTR_SPEED_FACTOR, "value": 5_000_000.0},
                {"attributeID": ATTR_MASS_ADDITION, "value": 50_000_000.0},
            ],
        ]
        service = _make_propmod_service(result_sets)
        result = service._apply_propmod_effects(ship_attrs, items)

        # Mass after MWD: 10M + 50M = 60M
        assert result[ATTR_MASS] == pytest.approx(60_000_000.0)
        # speed_boost = 500/100 * 5000000/60000000 * 1.25(AC V) = 0.52083
        ac_mult = 1.25
        expected = 300.0 * (1 + 500.0 / 100.0 * 5_000_000.0 / 60_000_000.0 * ac_mult)
        assert result[ATTR_MAX_VELOCITY] == pytest.approx(expected)

    def test_no_propmod_unchanged(self):
        """No propmod fitted → ship_attrs returned as-is."""
        ship_attrs = {ATTR_MAX_VELOCITY: 400.0, ATTR_MASS: 1_000_000.0}
        items = [FittingItem(type_id=3538, flag=19, quantity=1)]  # Shield Booster

        result_sets = [
            [],  # No propmod effects found
        ]
        service = _make_propmod_service(result_sets)
        result = service._apply_propmod_effects(ship_attrs, items)

        assert result[ATTR_MAX_VELOCITY] == 400.0
        assert result[ATTR_MASS] == 1_000_000.0

    def test_no_mid_slots_unchanged(self):
        """Items only in low/hi slots → no propmod lookup."""
        ship_attrs = {ATTR_MAX_VELOCITY: 400.0, ATTR_MASS: 1_000_000.0}
        items = [FittingItem(type_id=439, flag=11, quantity=1)]  # Low slot

        service = FittingStatsService.__new__(FittingStatsService)
        result = service._apply_propmod_effects(ship_attrs, items)

        assert result[ATTR_MAX_VELOCITY] == 400.0

    def test_mwd_no_mass_addition_attr(self):
        """MWD without massAddition attr → mass stays, speed still calculated."""
        ship_attrs = {ATTR_MAX_VELOCITY: 300.0, ATTR_MASS: 10_000_000.0}
        items = [FittingItem(type_id=434, flag=19, quantity=1)]

        result_sets = [
            [{"typeID": 434, "effectID": EFFECT_MWD}],
            [
                {"attributeID": ATTR_SPEED_BOOST_FACTOR, "value": 500.0},
                {"attributeID": ATTR_SPEED_FACTOR, "value": 5_000_000.0},
                # No ATTR_MASS_ADDITION
            ],
        ]
        service = _make_propmod_service(result_sets)
        result = service._apply_propmod_effects(ship_attrs, items)

        # Mass unchanged (mass_add=0, not > 0)
        assert result[ATTR_MASS] == pytest.approx(10_000_000.0)
        # speed_boost = 500/100 * 5000000/10000000 * 1.25(AC V) = 3.125
        ac_mult = 1.25
        expected = 300.0 * (1 + 500.0 / 100.0 * 5_000_000.0 / 10_000_000.0 * ac_mult)
        assert result[ATTR_MAX_VELOCITY] == pytest.approx(expected)

    def test_zero_thrust_unchanged(self):
        """If thrust is zero, no speed boost applied."""
        ship_attrs = {ATTR_MAX_VELOCITY: 400.0, ATTR_MASS: 1_000_000.0}
        items = [FittingItem(type_id=439, flag=19, quantity=1)]

        result_sets = [
            [{"typeID": 439, "effectID": EFFECT_AFTERBURNER}],
            [
                {"attributeID": ATTR_SPEED_BOOST_FACTOR, "value": 135.0},
                {"attributeID": ATTR_SPEED_FACTOR, "value": 0.0},
            ],
        ]
        service = _make_propmod_service(result_sets)
        result = service._apply_propmod_effects(ship_attrs, items)

        assert result[ATTR_MAX_VELOCITY] == 400.0  # Unchanged

    def test_only_first_propmod_active(self):
        """Two propmods fitted → only the first one is active."""
        ship_attrs = {ATTR_MAX_VELOCITY: 400.0, ATTR_MASS: 1_000_000.0}
        items = [
            FittingItem(type_id=439, flag=19, quantity=1),    # AB in mid 1
            FittingItem(type_id=434, flag=20, quantity=1),    # MWD in mid 2
        ]

        result_sets = [
            # effects for both
            [
                {"typeID": 439, "effectID": EFFECT_AFTERBURNER},
                {"typeID": 434, "effectID": EFFECT_MWD},
            ],
            # Propmod attrs — for AB (first found)
            [
                {"attributeID": ATTR_SPEED_BOOST_FACTOR, "value": 135.0},
                {"attributeID": ATTR_SPEED_FACTOR, "value": 1_125_000.0},
            ],
        ]
        service = _make_propmod_service(result_sets)
        result = service._apply_propmod_effects(ship_attrs, items)

        # AB applied: speed_boost = 135/100 * 1125000/1000000 * 1.25(AC V) = 1.8984375
        ac_mult = 1.25
        expected = 400.0 * (1 + 1.35 * 1_125_000.0 / 1_000_000.0 * ac_mult)
        assert result[ATTR_MAX_VELOCITY] == pytest.approx(expected)
        # No mass addition (AB)
        assert result[ATTR_MASS] == pytest.approx(1_000_000.0)


# ---------------------------------------------------------------------------
# Turret Tracking (Task 7)
# ---------------------------------------------------------------------------

class TestTurretTracking:
    def test_stationary_in_optimal(self):
        """Stationary target in optimal range → 100% hit."""
        from app.services.fitting_stats.calculations import calculate_turret_hit_chance
        result = calculate_turret_hit_chance(
            angular_velocity=0, tracking=0.1, weapon_sig_res=40,
            target_sig=450, distance=5000, optimal=10000, falloff=5000
        )
        assert result == pytest.approx(1.0)

    def test_fast_small_target(self):
        """Fast frigate at close range → low hit chance for large guns."""
        from app.services.fitting_stats.calculations import calculate_turret_hit_chance
        result = calculate_turret_hit_chance(
            angular_velocity=0.08, tracking=0.02, weapon_sig_res=400,
            target_sig=35, distance=5000, optimal=20000, falloff=10000
        )
        assert result < 0.1

    def test_beyond_falloff(self):
        """Target beyond optimal+falloff → very low hit chance."""
        from app.services.fitting_stats.calculations import calculate_turret_hit_chance
        result = calculate_turret_hit_chance(
            angular_velocity=0, tracking=0.1, weapon_sig_res=40,
            target_sig=450, distance=50000, optimal=10000, falloff=5000
        )
        assert result < 0.01

    def test_zero_angular_always_hits(self):
        from app.services.fitting_stats.calculations import calculate_turret_hit_chance
        result = calculate_turret_hit_chance(0, 0, 40, 450, 5000, 10000, 5000)
        assert result == pytest.approx(1.0)

    def test_zero_tracking_zero_angular(self):
        """Both tracking and angular are zero → hit chance 1.0."""
        from app.services.fitting_stats.calculations import calculate_turret_hit_chance
        result = calculate_turret_hit_chance(0, 0, 40, 450, 5000, 10000, 5000)
        assert result == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Missile Application (Task 8)
# ---------------------------------------------------------------------------

class TestMissileApplication:
    def test_full_application_large_slow_target(self):
        """Large slow target → 100% missile damage."""
        from app.services.fitting_stats.calculations import calculate_missile_application
        result = calculate_missile_application(
            target_sig=450, target_velocity=50,
            explosion_radius=150, explosion_velocity=100, drf=5.53
        )
        assert result == pytest.approx(1.0)

    def test_small_target_sig_reduction(self):
        """Small target → damage reduced by sig ratio."""
        from app.services.fitting_stats.calculations import calculate_missile_application
        result = calculate_missile_application(
            target_sig=35, target_velocity=0,
            explosion_radius=150, explosion_velocity=100, drf=5.53
        )
        assert result == pytest.approx(35.0 / 150.0, abs=0.01)

    def test_fast_small_target(self):
        """Fast frigate → complex term dominates."""
        from app.services.fitting_stats.calculations import calculate_missile_application
        result = calculate_missile_application(
            target_sig=35, target_velocity=400,
            explosion_radius=150, explosion_velocity=100, drf=5.53
        )
        assert result < 35.0 / 150.0  # worse than just sig reduction

    def test_stationary_target(self):
        """Stationary target → velocity term = infinity → capped at sig ratio."""
        from app.services.fitting_stats.calculations import calculate_missile_application
        result = calculate_missile_application(
            target_sig=35, target_velocity=0,
            explosion_radius=150, explosion_velocity=100, drf=5.53
        )
        assert result == pytest.approx(35.0 / 150.0, abs=0.01)

    def test_zero_explosion_radius(self):
        from app.services.fitting_stats.calculations import calculate_missile_application
        result = calculate_missile_application(35, 400, 0, 100, 5.53)
        assert result == 1.0


# ---------------------------------------------------------------------------
# Warp Time (Task 10)
# ---------------------------------------------------------------------------

class TestWarpTime:
    def test_short_warp_1au(self):
        """1 AU warp — mostly accel/decel."""
        from app.services.fitting_stats.calculations import calculate_warp_time
        result = calculate_warp_time(warp_speed_au=3.0, distance_au=1.0)
        assert 5 < result < 15

    def test_long_warp_100au(self):
        """100 AU warp — mostly cruise."""
        from app.services.fitting_stats.calculations import calculate_warp_time
        result = calculate_warp_time(warp_speed_au=3.0, distance_au=100.0)
        assert 30 < result < 80

    def test_fast_ship_faster_than_slow(self):
        """Interceptor 8 AU/s is faster than BS 3 AU/s."""
        from app.services.fitting_stats.calculations import calculate_warp_time
        fast = calculate_warp_time(warp_speed_au=8.0, distance_au=20.0)
        slow = calculate_warp_time(warp_speed_au=3.0, distance_au=20.0)
        assert fast < slow

    def test_zero_distance(self):
        from app.services.fitting_stats.calculations import calculate_warp_time
        assert calculate_warp_time(3.0, 0) == 0

    def test_zero_speed(self):
        from app.services.fitting_stats.calculations import calculate_warp_time
        assert calculate_warp_time(0, 10.0) == 0


# ---------------------------------------------------------------------------
# Effective Repair (Task 13)
# ---------------------------------------------------------------------------

class TestEffectiveRepair:
    def test_armor_rep_ehp_with_resists(self):
        """100 HP/s raw → higher EHP/s with resists."""
        from app.services.fitting_stats.calculations import calculate_effective_rep
        result = calculate_effective_rep(100, 0.3)
        assert result == pytest.approx(333.3, abs=0.1)

    def test_no_resists(self):
        """0% resist → 1.0 pass-through → EHP/s = HP/s."""
        from app.services.fitting_stats.calculations import calculate_effective_rep
        result = calculate_effective_rep(100, 1.0)
        assert result == pytest.approx(100.0)

    def test_zero_rep(self):
        from app.services.fitting_stats.calculations import calculate_effective_rep
        assert calculate_effective_rep(0, 0.5) == 0

    def test_zero_pass_through(self):
        from app.services.fitting_stats.calculations import calculate_effective_rep
        assert calculate_effective_rep(100, 0) == 0


# ---------------------------------------------------------------------------
# Scanability (Task 16)
# ---------------------------------------------------------------------------

class TestScanability:
    def test_tengu_harder_to_scan_than_drake(self):
        """Tengu (small sig, high sensor) harder than Drake."""
        from app.services.fitting_stats.calculations import calculate_scanability
        tengu = calculate_scanability(sig_radius=150, sensor_strength=28)
        drake = calculate_scanability(sig_radius=310, sensor_strength=17)
        assert tengu < drake

    def test_scanability_ratio(self):
        from app.services.fitting_stats.calculations import calculate_scanability
        result = calculate_scanability(sig_radius=150, sensor_strength=28)
        assert result == pytest.approx(5.36, abs=0.01)

    def test_zero_sensor(self):
        from app.services.fitting_stats.calculations import calculate_scanability
        assert calculate_scanability(100, 0) == 0


# ---------------------------------------------------------------------------
# Target Profiles (Task 6)
# ---------------------------------------------------------------------------

class TestTargetProfiles:
    def test_frigate_profile(self):
        from app.services.fitting_stats.constants import TARGET_PROFILES
        frig = TARGET_PROFILES["frigate"]
        assert frig["sig_radius"] == 35
        assert frig["velocity"] == 400
        assert frig["distance"] == 5000

    def test_cruiser_profile(self):
        from app.services.fitting_stats.constants import TARGET_PROFILES
        cruiser = TARGET_PROFILES["cruiser"]
        assert cruiser["sig_radius"] == 150

    def test_all_profiles_have_required_keys(self):
        from app.services.fitting_stats.constants import TARGET_PROFILES
        for name, profile in TARGET_PROFILES.items():
            assert "sig_radius" in profile, f"{name} missing sig_radius"
            assert "velocity" in profile, f"{name} missing velocity"
            assert "distance" in profile, f"{name} missing distance"

    def test_seven_profiles(self):
        from app.services.fitting_stats.constants import TARGET_PROFILES
        assert len(TARGET_PROFILES) == 7


# ---------------------------------------------------------------------------
# Damage Profiles (Task 14)
# ---------------------------------------------------------------------------

class TestDamageProfiles:
    def test_omni_profile_uniform(self):
        from app.services.fitting_stats.constants import DAMAGE_PROFILES
        omni = DAMAGE_PROFILES["omni"]
        assert omni["em"] == 0.25
        assert omni["thermal"] == 0.25
        assert omni["kinetic"] == 0.25
        assert omni["explosive"] == 0.25

    def test_all_profiles_sum_to_one(self):
        from app.services.fitting_stats.constants import DAMAGE_PROFILES
        for name, profile in DAMAGE_PROFILES.items():
            total = profile["em"] + profile["thermal"] + profile["kinetic"] + profile["explosive"]
            assert total == pytest.approx(1.0), f"{name} sums to {total}"

    def test_eleven_profiles(self):
        from app.services.fitting_stats.constants import DAMAGE_PROFILES
        assert len(DAMAGE_PROFILES) == 11


# ---------------------------------------------------------------------------
# Applied DPS Model (Task 9)
# ---------------------------------------------------------------------------

class TestAppliedDPSModel:
    def test_default_values(self):
        from app.services.fitting_stats.models import AppliedDPS
        adps = AppliedDPS()
        assert adps.target_profile == "none"
        assert adps.total_applied_dps == 0

    def test_custom_profile(self):
        from app.services.fitting_stats.models import TargetProfile
        tp = TargetProfile(name="custom", sig_radius=100, velocity=200, distance=10000)
        assert tp.sig_radius == 100


# ---------------------------------------------------------------------------
# Navigation Stats with Warp Time (Task 11)
# ---------------------------------------------------------------------------

class TestNavigationStatsWarpTime:
    def test_warp_time_fields_exist(self):
        from app.services.fitting_stats.models import NavigationStats
        nav = NavigationStats(warp_speed=3.0, warp_time_5au=10.5, warp_time_20au=15.2)
        assert nav.warp_time_5au == 10.5
        assert nav.warp_time_20au == 15.2

    def test_warp_time_defaults_to_zero(self):
        from app.services.fitting_stats.models import NavigationStats
        nav = NavigationStats()
        assert nav.warp_time_5au == 0
        assert nav.warp_time_20au == 0


# ---------------------------------------------------------------------------
# Repair Stats EHP/s (Task 13)
# ---------------------------------------------------------------------------

class TestRepairStatsEHP:
    def test_ehp_fields_exist(self):
        from app.services.fitting_stats.models import RepairStats
        r = RepairStats(shield_rep_ehp=200.0, armor_rep_ehp=150.0, sustained_tank_ehp=350.0)
        assert r.sustained_tank_ehp == 350.0

    def test_ehp_fields_default_zero(self):
        from app.services.fitting_stats.models import RepairStats
        r = RepairStats()
        assert r.shield_rep_ehp == 0
        assert r.armor_rep_ehp == 0
        assert r.sustained_tank_ehp == 0


# ---------------------------------------------------------------------------
# Integration: Full Calculation Pipeline (Task 17)
# ---------------------------------------------------------------------------

class TestIntegrationPipeline:
    """End-to-end integration tests verifying all calculation functions
    compose correctly for realistic EVE fitting scenarios.

    These tests use only pure functions (no DB) and verify the complete
    data flow from ship attributes through to final stats.
    """

    def test_battleship_full_calculation_pipeline(self):
        """Simulate a battleship (Raven-like) fitting through all calc stages.

        Verifies: align, lock, warp, cap, turret tracking, missile app,
        shield regen, weapon DPS, drone DPS, scanability, effective rep.
        """
        from app.services.fitting_stats.calculations import (
            calculate_align_time, calculate_lock_time,
            calculate_warp_time, calculate_capacitor,
            calculate_turret_hit_chance, calculate_missile_application,
            calculate_shield_peak_regen, calculate_effective_rep,
            calculate_scanability, calculate_weapon_dps, calculate_drone_dps,
        )

        # Ship attrs (Raven-like BS)
        mass = 97_300_000.0
        agility = 0.084
        scan_res = 115.0
        sig_radius = 470.0
        warp_speed = 3.0
        cap_capacity = 5625.0
        cap_recharge_ms = 1_000_000.0  # 1000s
        shield_hp = 7500.0
        shield_recharge_ms = 2_500_000.0  # 2500s
        sensor_strength = 22.0

        # 1. Navigation
        align = calculate_align_time(mass, agility)
        assert align > 0
        assert isinstance(align, float)  # continuous value

        warp_5au = calculate_warp_time(warp_speed, 5.0)
        warp_20au = calculate_warp_time(warp_speed, 20.0)
        assert warp_5au > 0
        assert warp_20au > warp_5au  # longer warp takes more time

        # 2. Targeting
        lock_time = calculate_lock_time(scan_res, 150.0)  # vs cruiser
        assert lock_time > 0
        lock_vs_frig = calculate_lock_time(scan_res, 35.0)  # vs frigate
        assert lock_vs_frig > lock_time  # smaller sig = slower lock

        scanability = calculate_scanability(sig_radius, sensor_strength)
        assert scanability > 0
        assert scanability == round(sig_radius / sensor_strength, 2)

        # 3. Capacitor (no modules = stable at 100%)
        cap = calculate_capacitor(cap_capacity, cap_recharge_ms, 0)
        assert cap.stable is True
        assert cap.stable_percent == 100.0
        assert cap.peak_recharge_rate > 0

        # 4. Cap with moderate drain
        cap_drain = calculate_capacitor(cap_capacity, cap_recharge_ms, 10.0)
        assert cap_drain.usage_rate == 10.0
        assert cap_drain.stable is True
        assert 25 < cap_drain.stable_percent < 100

        # 5. Shield passive regen
        regen = calculate_shield_peak_regen(shield_hp, shield_recharge_ms)
        assert regen > 0
        expected_regen = 2.5 * shield_hp / (shield_recharge_ms / 1000.0)
        assert abs(regen - round(expected_regen, 2)) < 0.01

        # 6. Effective repair (100 HP/s through 50% pass-through = 200 EHP/s)
        ehp_s = calculate_effective_rep(100.0, 0.5)
        assert ehp_s == 200.0

        # 7. Turret tracking vs BS target (should hit well)
        angular_vs_bs = 100.0 / 30000.0  # 100 m/s at 30km
        hit_bs = calculate_turret_hit_chance(
            angular_vs_bs, 0.05, 40.0, 450.0, 30000.0, 25000.0, 15000.0
        )
        assert hit_bs > 0.8  # should track BS easily

        # Turret vs frigate (much harder to track)
        angular_vs_frig = 400.0 / 5000.0  # 400 m/s at 5km
        hit_frig = calculate_turret_hit_chance(
            angular_vs_frig, 0.05, 40.0, 35.0, 5000.0, 25000.0, 15000.0
        )
        assert hit_frig < hit_bs  # harder to track small target

        # 8. Missile application
        # Cruise missiles vs BS target (full application)
        missile_vs_bs = calculate_missile_application(
            target_sig=450, target_velocity=100,
            explosion_radius=300, explosion_velocity=100, drf=5.53
        )
        assert missile_vs_bs > 0.9  # good application vs BS

        # Cruise missiles vs frigate (poor application)
        missile_vs_frig = calculate_missile_application(
            target_sig=35, target_velocity=400,
            explosion_radius=300, explosion_velocity=100, drf=5.53
        )
        assert missile_vs_frig < missile_vs_bs  # much worse vs small fast targets

        # 9. Weapon DPS
        dps = calculate_weapon_dps(
            damage_mult=3.5, rate_of_fire_ms=12000.0,
            charge_em=0, charge_thermal=105, charge_kinetic=105, charge_explosive=0
        )
        assert dps["dps"] > 0
        assert dps["volley"] > 0
        assert abs(dps["thermal"] - dps["kinetic"]) < 0.1  # equal damage split

        # 10. Drone DPS
        ddps = calculate_drone_dps(
            drone_damage_mult=1.0, drone_rof_ms=5000.0,
            em=0, thermal=4, kinetic=12, explosive=0, count=5
        )
        assert ddps["dps"] > 0
        assert ddps["kinetic"] > ddps["thermal"]  # proportional to base damage

    def test_cap_booster_vs_passive_recharge(self):
        """Verify cap booster injection produces longer cap life than passive."""
        from app.services.fitting_stats.calculations import calculate_capacitor

        cap = 3000.0
        recharge_ms = 300_000.0  # 300s, tight

        # Heavy drain without booster — should be unstable
        no_booster = calculate_capacitor(cap, recharge_ms, 50.0,
                                          module_drains=[(200, 10000)])
        # With cap injector — should last longer or be stable
        with_booster = calculate_capacitor(cap, recharge_ms, 50.0,
                                            module_drains=[(200, 10000)],
                                            cap_injectors=[(400, 12000)])

        if no_booster.stable and with_booster.stable:
            assert with_booster.stable_percent >= no_booster.stable_percent
        elif not no_booster.stable and with_booster.stable:
            pass  # boosted made it stable, that's better
        elif not no_booster.stable and not with_booster.stable:
            assert with_booster.lasts_seconds >= no_booster.lasts_seconds

    def test_all_target_profiles_produce_valid_applied_dps(self):
        """Every target profile must produce valid tracking/application values."""
        from app.services.fitting_stats.calculations import (
            calculate_turret_hit_chance, calculate_missile_application,
        )
        from app.services.fitting_stats.constants import TARGET_PROFILES

        for name, profile in TARGET_PROFILES.items():
            sig = profile["sig_radius"]
            vel = profile["velocity"]
            dist = profile["distance"]

            # Turret hit chance: use typical BS guns
            if dist > 0:
                angular = vel / dist if dist > 0 else 0
                hit = calculate_turret_hit_chance(
                    angular, 0.04, 40.0, sig, dist, 20000.0, 12000.0
                )
                assert 0 <= hit <= 1.0, f"{name}: turret hit {hit}"

            # Missile application: cruise missiles
            app = calculate_missile_application(
                sig, vel, 300.0, 100.0, 5.53
            )
            assert 0 <= app <= 1.0, f"{name}: missile app {app}"

    def test_all_damage_profiles_sum_to_one(self):
        """Every damage profile must sum to 1.0 for valid EHP calculation."""
        from app.services.fitting_stats.constants import DAMAGE_PROFILES
        for name, profile in DAMAGE_PROFILES.items():
            total = sum(profile.values())
            assert abs(total - 1.0) < 0.01, f"{name}: sums to {total}"

    def test_interceptor_vs_battleship_navigation(self):
        """Interceptor must be faster in all navigation metrics."""
        from app.services.fitting_stats.calculations import (
            calculate_align_time, calculate_warp_time,
        )

        # Interceptor (Ares-like)
        inty_align = calculate_align_time(mass=1_100_000, agility=0.0027)
        inty_warp = calculate_warp_time(warp_speed_au=8.0, distance_au=10.0)

        # Battleship (Raven-like)
        bs_align = calculate_align_time(mass=97_300_000, agility=0.084)
        bs_warp = calculate_warp_time(warp_speed_au=3.0, distance_au=10.0)

        assert inty_align < bs_align, "Interceptor should align faster"
        assert inty_warp < bs_warp, "Interceptor should warp faster"

    def test_weapon_dps_matches_volley_over_rof(self):
        """DPS = volley / (ROF / 1000). Verify identity holds."""
        from app.services.fitting_stats.calculations import calculate_weapon_dps

        result = calculate_weapon_dps(
            damage_mult=2.5, rate_of_fire_ms=8000.0,
            charge_em=50, charge_thermal=0, charge_kinetic=50, charge_explosive=0
        )
        expected_dps = result["volley"] / (8000.0 / 1000.0)
        assert abs(result["dps"] - expected_dps) < 0.01

    def test_model_composition(self):
        """Verify FittingStatsResponse can be constructed with all new fields."""
        from app.services.fitting_stats.models import (
            FittingStatsResponse, FittingStatsRequest, SlotUsage, ResourceUsage,
            OffenseStats, DefenseStats, CapacitorStats, NavigationStats,
            TargetingStats, RepairStats, AppliedDPS, TargetProfile,
        )

        # Build a complete response with all fields populated
        resp = FittingStatsResponse(
            ship={"type_id": 24698, "name": "Drake", "group_name": "Battlecruiser"},
            slots=SlotUsage(),
            resources=ResourceUsage(),
            offense=OffenseStats(weapon_dps=250.0, drone_dps=50.0, total_dps=300.0),
            defense=DefenseStats(total_ehp=45000),
            capacitor=CapacitorStats(capacity=3000, stable=True, stable_percent=65.0),
            navigation=NavigationStats(
                max_velocity=250, align_time=8, warp_speed=3.0,
                warp_time_5au=10.5, warp_time_20au=25.3,
            ),
            targeting=TargetingStats(
                max_range=75000, scan_resolution=330, scanability=5.2
            ),
            repairs=RepairStats(
                shield_rep=100, armor_rep=0,
                shield_rep_ehp=180.0, armor_rep_ehp=0,
                sustained_tank_ehp=180.0,
            ),
            applied_dps=AppliedDPS(
                target_profile="cruiser",
                turret_applied_dps=0, missile_applied_dps=200.0,
                drone_applied_dps=45.0, total_applied_dps=245.0,
                turret_hit_chance=0, missile_damage_factor=0.85,
            ),
        )

        assert resp.offense.total_dps == 300.0
        assert resp.navigation.warp_time_5au == 10.5
        assert resp.targeting.scanability == 5.2
        assert resp.repairs.sustained_tank_ehp == 180.0
        assert resp.applied_dps.missile_damage_factor == 0.85
