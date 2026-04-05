"""Tests for Triglavian spool-up DPS calculations."""
import pytest
from math import ceil

from app.services.fitting_stats.spool import (
    calculate_spool_dps,
    is_spool_weapon,
    ATTR_SPOOL_BONUS_PER_CYCLE,
    ATTR_SPOOL_MAX_BONUS,
)


class TestCalculateSpoolDps:
    """Test spool-up DPS calculations."""

    def test_min_dps_equals_base(self):
        """At cycle 0, DPS equals base DPS."""
        result = calculate_spool_dps(100.0, 0.05, 1.5)
        assert result["min_dps"] == pytest.approx(100.0)

    def test_max_dps_with_max_bonus(self):
        """Max DPS = base * (1 + maxBonus)."""
        result = calculate_spool_dps(100.0, 0.05, 1.5)
        assert result["max_dps"] == pytest.approx(250.0)

    def test_avg_dps_is_midpoint(self):
        """Average DPS = (min + max) / 2."""
        result = calculate_spool_dps(100.0, 0.05, 1.5)
        assert result["avg_dps"] == pytest.approx(175.0)

    def test_cycles_to_max(self):
        """cycles_to_max = ceil(maxBonus / bonusPerCycle)."""
        result = calculate_spool_dps(100.0, 0.05, 1.5)
        assert result["cycles_to_max"] == 30

    def test_cycles_to_max_non_integer(self):
        """When maxBonus / bonusPerCycle is not integer, ceil rounds up."""
        result = calculate_spool_dps(100.0, 0.07, 1.5)
        # 1.5 / 0.07 = 21.428... -> ceil = 22
        assert result["cycles_to_max"] == 22

    def test_zero_bonus_returns_flat(self):
        """When bonus_per_cycle is 0, DPS is flat (no spool)."""
        result = calculate_spool_dps(200.0, 0.0, 0.0)
        assert result["min_dps"] == pytest.approx(200.0)
        assert result["max_dps"] == pytest.approx(200.0)
        assert result["avg_dps"] == pytest.approx(200.0)
        assert result["cycles_to_max"] == 0
        assert result["time_to_max_s"] == pytest.approx(0.0)

    def test_zero_max_bonus_returns_flat(self):
        """When max_bonus is 0 but bonus_per_cycle > 0, DPS is flat."""
        result = calculate_spool_dps(150.0, 0.05, 0.0)
        assert result["min_dps"] == pytest.approx(150.0)
        assert result["max_dps"] == pytest.approx(150.0)
        assert result["avg_dps"] == pytest.approx(150.0)
        assert result["cycles_to_max"] == 0

    def test_time_to_max_with_cycle_time(self):
        """time_to_max = cycles_to_max * cycle_time_s."""
        # cycle_time_ms = 5000 (5 seconds), 30 cycles -> 150s
        result = calculate_spool_dps(100.0, 0.05, 1.5, cycle_time_ms=5000.0)
        assert result["time_to_max_s"] == pytest.approx(150.0)

    def test_time_to_max_zero_cycle_time(self):
        """When cycle_time_ms is 0, time_to_max is 0."""
        result = calculate_spool_dps(100.0, 0.05, 1.5, cycle_time_ms=0.0)
        assert result["time_to_max_s"] == pytest.approx(0.0)

    def test_small_bonus_per_cycle(self):
        """Vedmak-like: 5% per cycle, +50% max."""
        result = calculate_spool_dps(200.0, 0.05, 0.5)
        assert result["min_dps"] == pytest.approx(200.0)
        assert result["max_dps"] == pytest.approx(300.0)
        assert result["avg_dps"] == pytest.approx(250.0)
        assert result["cycles_to_max"] == 10

    def test_large_bonus_per_cycle(self):
        """Large per-cycle bonus, reaches max quickly."""
        result = calculate_spool_dps(100.0, 0.5, 1.5)
        assert result["cycles_to_max"] == 3
        assert result["max_dps"] == pytest.approx(250.0)

    def test_fractional_base_dps(self):
        """Works with fractional base DPS."""
        result = calculate_spool_dps(123.456, 0.05, 1.5)
        assert result["min_dps"] == pytest.approx(123.456)
        assert result["max_dps"] == pytest.approx(123.456 * 2.5)

    def test_return_keys(self):
        """Verify all expected keys are present."""
        result = calculate_spool_dps(100.0, 0.05, 1.5)
        assert set(result.keys()) == {"min_dps", "max_dps", "avg_dps", "cycles_to_max", "time_to_max_s"}

    def test_zero_base_dps(self):
        """Zero base DPS returns all zeros."""
        result = calculate_spool_dps(0.0, 0.05, 1.5)
        assert result["min_dps"] == pytest.approx(0.0)
        assert result["max_dps"] == pytest.approx(0.0)
        assert result["avg_dps"] == pytest.approx(0.0)


class TestIsSpoolWeapon:
    """Test spool weapon detection."""

    def test_has_both_attrs(self):
        """Module with both spool attrs is a spool weapon."""
        attrs = {ATTR_SPOOL_BONUS_PER_CYCLE: 0.05, ATTR_SPOOL_MAX_BONUS: 1.5}
        assert is_spool_weapon(attrs) is True

    def test_missing_bonus_per_cycle(self):
        """Module with only max bonus is NOT a spool weapon."""
        attrs = {ATTR_SPOOL_MAX_BONUS: 1.5}
        assert is_spool_weapon(attrs) is False

    def test_missing_max_bonus(self):
        """Module with only bonus_per_cycle is NOT a spool weapon."""
        attrs = {ATTR_SPOOL_BONUS_PER_CYCLE: 0.05}
        assert is_spool_weapon(attrs) is False

    def test_empty_attrs(self):
        """Empty attrs dict is not a spool weapon."""
        assert is_spool_weapon({}) is False

    def test_zero_values(self):
        """Zero values for both attrs is not a spool weapon."""
        attrs = {ATTR_SPOOL_BONUS_PER_CYCLE: 0.0, ATTR_SPOOL_MAX_BONUS: 0.0}
        assert is_spool_weapon(attrs) is False

    def test_only_bonus_per_cycle_zero(self):
        """bonus_per_cycle=0 with valid max_bonus is not a spool weapon."""
        attrs = {ATTR_SPOOL_BONUS_PER_CYCLE: 0.0, ATTR_SPOOL_MAX_BONUS: 1.5}
        assert is_spool_weapon(attrs) is False

    def test_only_max_bonus_zero(self):
        """Valid bonus_per_cycle with max_bonus=0 is not a spool weapon."""
        attrs = {ATTR_SPOOL_BONUS_PER_CYCLE: 0.05, ATTR_SPOOL_MAX_BONUS: 0.0}
        assert is_spool_weapon(attrs) is False

    def test_with_other_attrs(self):
        """Spool attrs mixed with other attrs still detects correctly."""
        attrs = {
            42: 1000.0,
            ATTR_SPOOL_BONUS_PER_CYCLE: 0.05,
            ATTR_SPOOL_MAX_BONUS: 1.5,
            73: 5000.0,
        }
        assert is_spool_weapon(attrs) is True

    def test_none_values(self):
        """None values for spool attrs is not a spool weapon."""
        attrs = {ATTR_SPOOL_BONUS_PER_CYCLE: None, ATTR_SPOOL_MAX_BONUS: None}
        assert is_spool_weapon(attrs) is False


class TestSpoolConstants:
    """Test that spool attribute constants are correct."""

    def test_bonus_per_cycle_attr_id(self):
        assert ATTR_SPOOL_BONUS_PER_CYCLE == 2733

    def test_max_bonus_attr_id(self):
        assert ATTR_SPOOL_MAX_BONUS == 2734
