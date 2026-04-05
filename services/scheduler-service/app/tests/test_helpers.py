"""Tests for pure helper functions across scheduler job modules.

Tests functions from:
- aggregate_corp_hourly_stats: calculate_engagement_size, calculate_damage_types,
  classify_victim_ship, detect_ewar_attackers, infer_equipment_profile
- aggregate_hourly_stats: RACE_DAMAGE, EWAR_GROUPS, RACE_EQUIPMENT_PROFILE,
  infer_equipment_profile, detect_coalition_allies
- pilot_skill_estimates: calculate_sp_for_level, SP_PER_LEVEL
- alliance_fingerprints: detect_primary_doctrine
"""

import pytest

# --- Corp Hourly Stats helpers (accept sde_cache as param) ---
from app.jobs.aggregate_corp_hourly_stats import (
    calculate_engagement_size,
    calculate_damage_types as corp_calculate_damage_types,
    classify_victim_ship as corp_classify_victim_ship,
    detect_ewar_attackers as corp_detect_ewar_attackers,
    infer_equipment_profile as corp_infer_equipment_profile,
    ENGAGEMENT_SOLO,
    ENGAGEMENT_SMALL,
    ENGAGEMENT_MEDIUM,
    ENGAGEMENT_LARGE,
    CAPITAL_GROUPS,
    RACE_DAMAGE as CORP_RACE_DAMAGE,
    EWAR_GROUPS as CORP_EWAR_GROUPS,
)

# --- Alliance Hourly Stats helpers (use _get_ship_info which touches global cache) ---
from app.jobs.aggregate_hourly_stats import (
    RACE_DAMAGE,
    EWAR_GROUPS,
    RACE_EQUIPMENT_PROFILE,
    detect_coalition_allies,
)

# --- Pilot Skill Estimates ---
from app.jobs.pilot_skill_estimates import (
    calculate_sp_for_level,
    SP_PER_LEVEL,
)

# --- Alliance Fingerprints ---
from app.jobs.alliance_fingerprints import detect_primary_doctrine


# =============================================================================
# Shared SDE cache fixture for corp helpers
# =============================================================================

@pytest.fixture
def sde_cache():
    """Minimal SDE cache with a few test ships."""
    return {
        'ships': {
            # Caldari (race 1)
            670: {'race_id': 1, 'group_name': 'Capsule'},
            24690: {'race_id': 1, 'group_name': 'Battleship'},
            # Minmatar (race 2)
            587: {'race_id': 2, 'group_name': 'Frigate'},
            # Amarr (race 4)
            24692: {'race_id': 4, 'group_name': 'Battleship'},
            # Gallente (race 8)
            24694: {'race_id': 8, 'group_name': 'Cruiser'},
            # Electronic Attack Ship (EWAR)
            11174: {'race_id': 1, 'group_name': 'Electronic Attack Ship'},
            # Interdictor
            22456: {'race_id': 2, 'group_name': 'Interdictor'},
            # Force Recon Ship
            11969: {'race_id': 8, 'group_name': 'Force Recon Ship'},
            # Capital ships
            99901: {'race_id': 4, 'group_name': 'Carrier'},
            99902: {'race_id': 1, 'group_name': 'Titan'},
            # No race (None)
            99903: {'race_id': None, 'group_name': 'Shuttle'},
        }
    }


# =============================================================================
# calculate_engagement_size
# =============================================================================

class TestCalculateEngagementSize:
    """Test engagement size classification thresholds."""

    @pytest.mark.parametrize("count,expected", [
        (1, "solo"),
        (2, "solo"),
        (3, "solo"),          # ENGAGEMENT_SOLO boundary
        (4, "small"),
        (10, "small"),        # ENGAGEMENT_SMALL boundary
        (11, "medium"),
        (30, "medium"),       # ENGAGEMENT_MEDIUM boundary
        (31, "large"),
        (100, "large"),       # ENGAGEMENT_LARGE boundary
        (101, "blob"),
        (500, "blob"),
    ])
    def test_engagement_classification(self, count, expected):
        assert calculate_engagement_size(count) == expected

    def test_thresholds_consistent_with_constants(self):
        """Verify thresholds match declared constants."""
        assert ENGAGEMENT_SOLO == 3
        assert ENGAGEMENT_SMALL == 10
        assert ENGAGEMENT_MEDIUM == 30
        assert ENGAGEMENT_LARGE == 100


# =============================================================================
# calculate_damage_types (corp version — explicit sde_cache)
# =============================================================================

class TestCorpCalculateDamageTypes:
    """Test damage type distribution from attacker races."""

    def test_caldari_attackers(self, sde_cache):
        """Caldari ships should produce kinetic+thermal damage (3+ ships for int truncation)."""
        attackers = [{'ship_type_id': 24690}] * 3  # 3x Caldari BS
        result = corp_calculate_damage_types(attackers, sde_cache)
        assert result['kinetic'] > 0  # 0.55 * 3 = 1.65 -> int(1) = 1
        assert result['thermal'] > 0  # 0.45 * 3 = 1.35 -> int(1) = 1
        assert result['em'] == 0
        assert result['explosive'] == 0

    def test_caldari_fleet_three(self, sde_cache):
        """3 Caldari ships accumulate enough for both kinetic and thermal to be positive."""
        attackers = [{'ship_type_id': 24690}] * 3
        result = corp_calculate_damage_types(attackers, sde_cache)
        assert result['kinetic'] > 0   # 0.55 * 3 = 1.65 -> 1
        assert result['thermal'] > 0   # 0.45 * 3 = 1.35 -> 1
        assert result['em'] == 0
        assert result['explosive'] == 0

    def test_amarr_attackers(self, sde_cache):
        """Amarr ships should produce EM+thermal damage (needs 2+ for int truncation)."""
        attackers = [{'ship_type_id': 24692}, {'ship_type_id': 24692}]  # 2x Amarr BS
        result = corp_calculate_damage_types(attackers, sde_cache)
        assert result['em'] > 0  # 0.55 * 2 = 1.1 -> 1
        assert result['kinetic'] == 0
        assert result['explosive'] == 0

    def test_empty_attackers(self, sde_cache):
        """No attackers -> all zeros."""
        result = corp_calculate_damage_types([], sde_cache)
        assert result == {"em": 0, "thermal": 0, "kinetic": 0, "explosive": 0}

    def test_unknown_ship_type(self, sde_cache):
        """Unknown ship type should not contribute damage."""
        attackers = [{'ship_type_id': 99999}]  # Not in SDE cache
        result = corp_calculate_damage_types(attackers, sde_cache)
        assert all(v == 0 for v in result.values())

    def test_attacker_without_ship_type(self, sde_cache):
        """Attacker with no ship_type_id should be skipped."""
        attackers = [{'ship_type_id': None}, {}]
        result = corp_calculate_damage_types(attackers, sde_cache)
        assert all(v == 0 for v in result.values())

    def test_mixed_fleet(self, sde_cache):
        """Mixed Caldari + Minmatar fleet should show kinetic and explosive (int-truncated)."""
        attackers = [
            {'ship_type_id': 24690},  # Caldari (kinetic 0.55 + thermal 0.45)
            {'ship_type_id': 587},    # Minmatar (explosive 0.55 + kinetic 0.45)
        ]
        result = corp_calculate_damage_types(attackers, sde_cache)
        # kinetic: 0.55 + 0.45 = 1.0 -> int(1.0) = 1
        assert result['kinetic'] == 1
        # explosive: 0.55 -> int(0.55) = 0 (single attacker)
        # thermal: 0.45 -> int(0.45) = 0 (single attacker)
        # Values are int-truncated per damage type across all attackers
        assert result['em'] == 0


# =============================================================================
# classify_victim_ship (corp version)
# =============================================================================

class TestCorpClassifyVictimShip:
    """Test ship classification via SDE cache."""

    def test_known_ship(self, sde_cache):
        assert corp_classify_victim_ship(24690, sde_cache) == "Battleship"

    def test_unknown_ship(self, sde_cache):
        assert corp_classify_victim_ship(99999, sde_cache) == "Unknown"

    def test_capsule(self, sde_cache):
        assert corp_classify_victim_ship(670, sde_cache) == "Capsule"


# =============================================================================
# detect_ewar_attackers (corp version)
# =============================================================================

class TestCorpDetectEwarAttackers:
    """Test EWAR detection from attacker ship types."""

    def test_ewar_ship_detected(self, sde_cache):
        attackers = [{'ship_type_id': 11174}]  # Electronic Attack Ship
        result = corp_detect_ewar_attackers(attackers, sde_cache)
        assert "Electronic Attack Ship" in result
        assert result["Electronic Attack Ship"]["count"] == 1
        assert result["Electronic Attack Ship"]["ewar_type"] == "ecm"

    def test_interdictor_detected(self, sde_cache):
        attackers = [{'ship_type_id': 22456}]  # Interdictor
        result = corp_detect_ewar_attackers(attackers, sde_cache)
        assert "Interdictor" in result
        assert result["Interdictor"]["ewar_type"] == "bubble"

    def test_no_ewar(self, sde_cache):
        """Non-EWAR ships should not appear in result."""
        attackers = [{'ship_type_id': 24690}]  # Regular battleship
        result = corp_detect_ewar_attackers(attackers, sde_cache)
        assert result == {}

    def test_multiple_ewar_same_type(self, sde_cache):
        """Multiple EWAR ships of same group should be counted."""
        attackers = [
            {'ship_type_id': 11174},
            {'ship_type_id': 11174},
        ]
        result = corp_detect_ewar_attackers(attackers, sde_cache)
        assert result["Electronic Attack Ship"]["count"] == 2


# =============================================================================
# infer_equipment_profile (corp version)
# =============================================================================

class TestCorpInferEquipmentProfile:
    """Test equipment inference from ship race."""

    def test_caldari_missile_shield(self, sde_cache):
        result = corp_infer_equipment_profile(24690, 100_000_000, sde_cache)
        assert result["weapon_class"] == "missile"
        assert result["tank_type"] == "shield"
        assert result["ship_value"] == 100_000_000

    def test_amarr_laser_armor(self, sde_cache):
        result = corp_infer_equipment_profile(24692, 50_000_000, sde_cache)
        assert result["weapon_class"] == "laser"
        assert result["tank_type"] == "armor"

    def test_gallente_hybrid_armor(self, sde_cache):
        result = corp_infer_equipment_profile(24694, 0, sde_cache)
        assert result["weapon_class"] == "hybrid"
        assert result["tank_type"] == "armor"

    def test_unknown_ship_mixed(self, sde_cache):
        result = corp_infer_equipment_profile(99999, 0, sde_cache)
        assert result["weapon_class"] == "mixed"
        assert result["tank_type"] == "mixed"

    def test_no_race_ship_mixed(self, sde_cache):
        """Ship with race_id=None should return mixed."""
        result = corp_infer_equipment_profile(99903, 0, sde_cache)
        assert result["weapon_class"] == "mixed"
        assert result["tank_type"] == "mixed"


# =============================================================================
# detect_coalition_allies (alliance hourly stats)
# =============================================================================

class TestDetectCoalitionAllies:
    """Test co-attacker alliance detection."""

    def test_finds_allies(self):
        attackers = [
            {'alliance_id': 100},
            {'alliance_id': 200},
            {'alliance_id': 300},
        ]
        result = detect_coalition_allies(attackers, own_alliance_id=100)
        assert sorted(result) == [200, 300]

    def test_excludes_own_alliance(self):
        attackers = [
            {'alliance_id': 100},
            {'alliance_id': 100},
        ]
        result = detect_coalition_allies(attackers, own_alliance_id=100)
        assert result == []

    def test_handles_none_alliance(self):
        attackers = [
            {'alliance_id': None},
            {'alliance_id': 200},
            {},
        ]
        result = detect_coalition_allies(attackers, own_alliance_id=100)
        assert result == [200]

    def test_empty_attackers(self):
        assert detect_coalition_allies([], own_alliance_id=100) == []


# =============================================================================
# calculate_sp_for_level (pilot skill estimates)
# =============================================================================

class TestCalculateSpForLevel:
    """Test EVE SP calculation formula."""

    def test_level_1_multiplier_1(self):
        """Level 1, multiplier 1 = 250 SP."""
        assert calculate_sp_for_level(1.0, 1) == 250

    def test_level_5_multiplier_1(self):
        """Level 5, multiplier 1 = 256,000 SP."""
        assert calculate_sp_for_level(1.0, 5) == 256_000

    def test_multiplier_scales_linearly(self):
        """SP scales linearly with multiplier."""
        sp_1x = calculate_sp_for_level(1.0, 3)
        sp_5x = calculate_sp_for_level(5.0, 3)
        assert sp_5x == sp_1x * 5

    @pytest.mark.parametrize("level,expected_base_sp", [
        (1, 250),
        (2, 1414),
        (3, 8000),
        (4, 45255),
        (5, 256000),
    ])
    def test_all_levels_base_sp(self, level, expected_base_sp):
        """Verify SP_PER_LEVEL constants for multiplier=1."""
        assert calculate_sp_for_level(1.0, level) == expected_base_sp

    def test_invalid_level_zero(self):
        """Level 0 returns 0 SP."""
        assert calculate_sp_for_level(1.0, 0) == 0

    def test_invalid_level_six(self):
        """Level 6 returns 0 SP."""
        assert calculate_sp_for_level(1.0, 6) == 0

    def test_invalid_level_negative(self):
        """Negative level returns 0 SP."""
        assert calculate_sp_for_level(1.0, -1) == 0

    def test_high_multiplier(self):
        """High multiplier (16x) skill like Capital Ships V."""
        sp = calculate_sp_for_level(16.0, 5)
        assert sp == 256_000 * 16


# =============================================================================
# detect_primary_doctrine (alliance fingerprints)
# =============================================================================

class TestDetectPrimaryDoctrine:
    """Test doctrine detection from ship fingerprints."""

    def test_hac_fleet(self):
        ships = [
            {"ship_class": "Heavy Assault Cruiser", "uses": 80},
            {"ship_class": "Logistics", "uses": 10},
            {"ship_class": "Interdictor", "uses": 10},
        ]
        assert detect_primary_doctrine(ships) == "HAC Fleet"

    def test_battleship_fleet(self):
        ships = [
            {"ship_class": "Battleship", "uses": 60},
            {"ship_class": "Logistics", "uses": 20},
        ]
        assert detect_primary_doctrine(ships) == "Battleship Fleet"

    def test_mixed_fleet(self):
        """No class >= 30% -> Mixed Fleet."""
        ships = [
            {"ship_class": "Cruiser", "uses": 20},
            {"ship_class": "Battleship", "uses": 20},
            {"ship_class": "Frigate", "uses": 20},
            {"ship_class": "Destroyer", "uses": 20},
        ]
        assert detect_primary_doctrine(ships) == "Mixed Fleet"

    def test_empty_ships(self):
        assert detect_primary_doctrine([]) == "Unknown"

    def test_bomber_fleet(self):
        ships = [
            {"ship_class": "Stealth Bomber", "uses": 50},
            {"ship_class": "Frigate", "uses": 10},
        ]
        assert detect_primary_doctrine(ships) == "Bomber Fleet"

    def test_capital_fleet(self):
        ships = [
            {"ship_class": "Dreadnought", "uses": 30},
            {"ship_class": "Carrier", "uses": 30},
            {"ship_class": "Force Auxiliary", "uses": 10},
        ]
        # Dreadnought is mapped to "Capital Fleet"
        assert "Fleet" in detect_primary_doctrine(ships)

    def test_unknown_ship_class_above_threshold(self):
        """Ship class not in doctrine_map but >30% -> '<class> Fleet'."""
        ships = [
            {"ship_class": "Mining Barge", "uses": 80},
            {"ship_class": "Frigate", "uses": 10},
        ]
        assert detect_primary_doctrine(ships) == "Mining Barge Fleet"


# =============================================================================
# Constants validation
# =============================================================================

class TestConstants:
    """Verify SDE/game constant consistency."""

    def test_race_damage_covers_4_races(self):
        assert set(RACE_DAMAGE.keys()) == {1, 2, 4, 8}

    def test_race_damage_sums_to_one(self):
        """Each race's damage ratios should sum to ~1.0."""
        for race_id, damages in RACE_DAMAGE.items():
            total = sum(damages.values())
            assert abs(total - 1.0) < 0.001, f"Race {race_id} damage sums to {total}"

    def test_ewar_groups_contain_expected(self):
        assert "Electronic Attack Ship" in EWAR_GROUPS
        assert "Interdictor" in EWAR_GROUPS
        assert "Heavy Interdictor" in EWAR_GROUPS

    def test_equipment_profiles_cover_4_races(self):
        assert set(RACE_EQUIPMENT_PROFILE.keys()) == {1, 2, 4, 8}

    def test_capital_groups_include_key_types(self):
        assert "Carrier" in CAPITAL_GROUPS
        assert "Dreadnought" in CAPITAL_GROUPS
        assert "Titan" in CAPITAL_GROUPS
        assert "Supercarrier" in CAPITAL_GROUPS

    def test_sp_per_level_has_5_entries(self):
        assert set(SP_PER_LEVEL.keys()) == {1, 2, 3, 4, 5}

    def test_sp_per_level_monotonically_increasing(self):
        for i in range(1, 5):
            assert SP_PER_LEVEL[i] < SP_PER_LEVEL[i + 1], (
                f"SP_PER_LEVEL[{i}]={SP_PER_LEVEL[i]} >= SP_PER_LEVEL[{i+1}]={SP_PER_LEVEL[i+1]}"
            )
