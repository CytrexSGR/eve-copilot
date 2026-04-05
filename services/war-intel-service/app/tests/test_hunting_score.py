import pytest
from app.services.hunting.score_calculator import calculate_hunting_score


class TestHuntingScore:
    def test_high_npc_activity_high_score(self):
        """System with heavy ratting = high density score."""
        score = calculate_hunting_score(
            adm_military=4.8, npc_kills_per_day=1200,
            player_deaths_per_week=3, avg_kill_value=320_000_000,
            jumps_to_staging=8, capital_presence=False
        )
        assert score > 45

    def test_active_pvp_system_high_score(self):
        """FW/lowsec system with many kills and good ISK (e.g. Kourmonen)."""
        score = calculate_hunting_score(
            adm_military=0, npc_kills_per_day=300,
            player_deaths_per_week=15, avg_kill_value=192_000_000,
            jumps_to_staging=10, capital_presence=False
        )
        assert score > 30

    def test_low_activity_low_score(self):
        score = calculate_hunting_score(
            adm_military=1.0, npc_kills_per_day=50,
            player_deaths_per_week=0, avg_kill_value=100_000_000,
            jumps_to_staging=20, capital_presence=False
        )
        assert score < 15

    def test_capital_umbrella_reduces_score(self):
        base = calculate_hunting_score(
            adm_military=4.0, npc_kills_per_day=800,
            player_deaths_per_week=2, avg_kill_value=500_000_000,
            jumps_to_staging=5, capital_presence=False
        )
        with_caps = calculate_hunting_score(
            adm_military=4.0, npc_kills_per_day=800,
            player_deaths_per_week=2, avg_kill_value=500_000_000,
            jumps_to_staging=5, capital_presence=True
        )
        assert with_caps < base
        assert base - with_caps == 10  # Exact capital penalty

    def test_score_bounded_0_100(self):
        score = calculate_hunting_score(
            adm_military=5.0, npc_kills_per_day=5000,
            player_deaths_per_week=0, avg_kill_value=3_000_000_000,
            jumps_to_staging=2, capital_presence=False
        )
        assert 0 <= score <= 100

    def test_zero_everything_scores_zero(self):
        score = calculate_hunting_score(
            adm_military=0, npc_kills_per_day=0,
            player_deaths_per_week=0, avg_kill_value=0,
            jumps_to_staging=0, capital_presence=False
        )
        assert score == 0

    def test_high_value_kills_boost_score(self):
        """Expensive kills (freighters, bling fits) push score up."""
        low_value = calculate_hunting_score(
            adm_military=3.0, npc_kills_per_day=400,
            player_deaths_per_week=5, avg_kill_value=50_000_000,
            jumps_to_staging=10, capital_presence=False
        )
        high_value = calculate_hunting_score(
            adm_military=3.0, npc_kills_per_day=400,
            player_deaths_per_week=5, avg_kill_value=500_000_000,
            jumps_to_staging=10, capital_presence=False
        )
        assert high_value > low_value
        assert high_value - low_value > 15  # Value makes significant difference

    def test_npc_plus_adm_higher_than_either_alone(self):
        """NPC kills + ADM together give highest density score."""
        both = calculate_hunting_score(
            adm_military=4.0, npc_kills_per_day=500,
            player_deaths_per_week=5, avg_kill_value=200_000_000,
            jumps_to_staging=10, capital_presence=False
        )
        npc_only = calculate_hunting_score(
            adm_military=0, npc_kills_per_day=500,
            player_deaths_per_week=5, avg_kill_value=200_000_000,
            jumps_to_staging=10, capital_presence=False
        )
        adm_only = calculate_hunting_score(
            adm_military=4.0, npc_kills_per_day=0,
            player_deaths_per_week=5, avg_kill_value=200_000_000,
            jumps_to_staging=10, capital_presence=False
        )
        assert both > npc_only
        assert both > adm_only

    def test_no_npc_data_falls_back_to_adm(self):
        """Without NPC data, ADM alone drives density."""
        score = calculate_hunting_score(
            adm_military=4.0, npc_kills_per_day=0,
            player_deaths_per_week=10, avg_kill_value=200_000_000,
            jumps_to_staging=10, capital_presence=False
        )
        # ADM=4 → density = 0.8 * 35 = 28, kills + value contribute too
        assert score > 30

    def test_distance_penalty_capped(self):
        """Distance penalty caps at 5 points regardless of distance."""
        near = calculate_hunting_score(
            adm_military=3.0, npc_kills_per_day=300,
            player_deaths_per_week=5, avg_kill_value=200_000_000,
            jumps_to_staging=2, capital_presence=False
        )
        far = calculate_hunting_score(
            adm_military=3.0, npc_kills_per_day=300,
            player_deaths_per_week=5, avg_kill_value=200_000_000,
            jumps_to_staging=100, capital_presence=False
        )
        assert near > far
        assert near - far <= 5  # Distance penalty capped at 5
