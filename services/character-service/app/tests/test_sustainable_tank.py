"""Tests for cap-limited sustainable tank calculation."""
import pytest
from app.services.fitting_stats.calculations import calculate_sustainable_tank


class TestSustainableTank:
    def test_cap_stable_full_rep(self):
        """When cap is stable, full rep rate is sustained."""
        result = calculate_sustainable_tank(
            raw_shield_rep=100.0, raw_armor_rep=0.0,
            cap_stable=True, cap_stable_pct=60.0,
            rep_cap_need_per_sec=20.0,
            cap_recharge_rate=25.0,
        )
        assert result["shield_sustained"] == pytest.approx(100.0)

    def test_cap_unstable_limited_rep(self):
        """When cap is not stable, rep rate limited by cap availability."""
        result = calculate_sustainable_tank(
            raw_shield_rep=100.0, raw_armor_rep=0.0,
            cap_stable=False, cap_stable_pct=0.0,
            rep_cap_need_per_sec=50.0,
            cap_recharge_rate=25.0,
        )
        assert result["shield_sustained"] == pytest.approx(50.0)

    def test_no_reppers_zero_tank(self):
        """No reppers means zero sustainable tank."""
        result = calculate_sustainable_tank(
            raw_shield_rep=0.0, raw_armor_rep=0.0,
            cap_stable=True, cap_stable_pct=100.0,
            rep_cap_need_per_sec=0.0,
            cap_recharge_rate=50.0,
        )
        assert result["shield_sustained"] == 0.0
        assert result["armor_sustained"] == 0.0

    def test_armor_rep_also_limited(self):
        """Armor rep is also limited when cap unstable."""
        result = calculate_sustainable_tank(
            raw_shield_rep=0.0, raw_armor_rep=200.0,
            cap_stable=False, cap_stable_pct=0.0,
            rep_cap_need_per_sec=100.0,
            cap_recharge_rate=75.0,
        )
        assert result["armor_sustained"] == pytest.approx(150.0)

    def test_cap_recharge_exceeds_need(self):
        """Cap recharge exceeds rep need — full rep sustained."""
        result = calculate_sustainable_tank(
            raw_shield_rep=100.0, raw_armor_rep=0.0,
            cap_stable=False, cap_stable_pct=0.0,
            rep_cap_need_per_sec=20.0,
            cap_recharge_rate=100.0,
        )
        assert result["shield_sustained"] == pytest.approx(100.0)

    def test_both_reps_limited_equally(self):
        """Both shield and armor rep limited by same cap ratio."""
        result = calculate_sustainable_tank(
            raw_shield_rep=80.0, raw_armor_rep=120.0,
            cap_stable=False, cap_stable_pct=0.0,
            rep_cap_need_per_sec=200.0,
            cap_recharge_rate=100.0,
        )
        # 50% ratio
        assert result["shield_sustained"] == pytest.approx(40.0)
        assert result["armor_sustained"] == pytest.approx(60.0)
