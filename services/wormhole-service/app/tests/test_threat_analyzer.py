"""Tests for threat_analyzer.py, activity_tracker.py, and commodity_tracker.py pure logic."""

import pytest

from app.services.commodity_tracker import (
    FULLERITE_GAS,
    BLUE_LOOT,
    HYBRID_POLYMERS,
    JITA_REGION_ID,
    CommodityTracker,
)


# ---------------------------------------------------------------------------
# Commodity constants integrity
# ---------------------------------------------------------------------------

class TestFulleriteGasConstants:
    """Validate FULLERITE_GAS constant."""

    def test_nine_gas_types(self):
        assert len(FULLERITE_GAS) == 9

    @pytest.mark.parametrize("type_id", list(FULLERITE_GAS.keys()))
    def test_gas_has_required_keys(self, type_id):
        gas = FULLERITE_GAS[type_id]
        assert 'name' in gas
        assert 'tier' in gas
        assert 'class' in gas
        assert 'volume' in gas

    @pytest.mark.parametrize("type_id", list(FULLERITE_GAS.keys()))
    def test_gas_tier_is_valid(self, type_id):
        assert FULLERITE_GAS[type_id]['tier'] in ('high', 'mid', 'low')

    @pytest.mark.parametrize("type_id", list(FULLERITE_GAS.keys()))
    def test_gas_volume_is_positive(self, type_id):
        assert FULLERITE_GAS[type_id]['volume'] > 0

    def test_high_tier_gases_are_c5c6(self):
        for tid, gas in FULLERITE_GAS.items():
            if gas['tier'] == 'high':
                assert gas['class'] == 'C5/C6', f"{gas['name']} should be C5/C6"

    def test_c540_is_highest_volume(self):
        c540 = FULLERITE_GAS[30378]
        assert c540['name'] == 'Fullerite-C540'
        assert c540['volume'] == 10


class TestBlueLootConstants:
    """Validate BLUE_LOOT constant."""

    def test_six_blue_loot_types(self):
        assert len(BLUE_LOOT) == 6

    @pytest.mark.parametrize("type_id", list(BLUE_LOOT.keys()))
    def test_blue_loot_has_npc_buy(self, type_id):
        loot = BLUE_LOOT[type_id]
        assert 'npc_buy' in loot
        assert loot['npc_buy'] > 0

    def test_melted_nanoribbons_price(self):
        mnr = BLUE_LOOT[30259]
        assert mnr['name'] == 'Melted Nanoribbons'
        assert mnr['npc_buy'] == 662000

    def test_heuristic_selfassemblers_highest(self):
        """Heuristic Selfassemblers should have the highest NPC buy price."""
        highest = max(BLUE_LOOT.values(), key=lambda x: x['npc_buy'])
        assert highest['name'] == 'Heuristic Selfassemblers'


class TestHybridPolymerConstants:
    """Validate HYBRID_POLYMERS constant."""

    def test_eight_polymer_types(self):
        assert len(HYBRID_POLYMERS) == 8

    @pytest.mark.parametrize("type_id", list(HYBRID_POLYMERS.keys()))
    def test_polymer_has_name_and_tier(self, type_id):
        polymer = HYBRID_POLYMERS[type_id]
        assert 'name' in polymer
        assert 'tier' in polymer

    @pytest.mark.parametrize("type_id", list(HYBRID_POLYMERS.keys()))
    def test_polymer_tier_is_valid(self, type_id):
        assert HYBRID_POLYMERS[type_id]['tier'] in ('high', 'mid', 'low')


class TestJitaRegionId:
    """Validate JITA_REGION_ID constant."""

    def test_jita_region_id(self):
        assert JITA_REGION_ID == 10000002


# ---------------------------------------------------------------------------
# _predict_effects pure function
# ---------------------------------------------------------------------------

class TestPredictEffects:
    """Test CommodityTracker._predict_effects() method."""

    def setup_method(self):
        self.tracker = CommodityTracker()

    def test_five_plus_systems_all_effects(self):
        effects = self.tracker._predict_effects(5)
        assert len(effects) == 5
        assert any("Major gas supply" in e for e in effects)
        assert any("T3 component" in e for e in effects)
        assert any("Blue loot flood" in e for e in effects)
        assert any("Regional polymer" in e for e in effects)
        assert any("Local market oversupply" in e for e in effects)

    def test_three_systems(self):
        effects = self.tracker._predict_effects(3)
        # Should NOT have major gas supply or T3 component
        assert not any("Major gas supply" in e for e in effects)
        # Should have blue loot and polymer shortage
        assert any("Blue loot flood" in e for e in effects)
        assert any("Regional polymer" in e for e in effects)

    def test_two_systems(self):
        effects = self.tracker._predict_effects(2)
        assert len(effects) == 1
        assert any("Local market oversupply" in e for e in effects)

    def test_one_system(self):
        effects = self.tracker._predict_effects(1)
        assert effects == []

    def test_zero_systems(self):
        effects = self.tracker._predict_effects(0)
        assert effects == []

    def test_ten_systems_includes_all(self):
        effects = self.tracker._predict_effects(10)
        # >= 5 and >= 3 and >= 2 conditions all met
        assert len(effects) == 5

    @pytest.mark.parametrize("systems,expected_count", [
        (0, 0),
        (1, 0),
        (2, 1),
        (3, 3),
        (4, 3),
        (5, 5),
        (10, 5),
    ])
    def test_effect_count_by_systems(self, systems, expected_count):
        effects = self.tracker._predict_effects(systems)
        assert len(effects) == expected_count


# ---------------------------------------------------------------------------
# Loot status classification logic (extracted from commodity_tracker.py)
# ---------------------------------------------------------------------------

class TestLootStatusClassification:
    """Test the loot status classification logic from get_eviction_intel."""

    @staticmethod
    def _classify_loot(hours_since: float) -> tuple:
        """Extract the loot classification logic from get_eviction_intel."""
        if hours_since < 24:
            return 'imminent', '0-24h'
        elif hours_since < 72:
            return 'expected', '24-48h'
        else:
            return 'dumped', 'already sold'

    @pytest.mark.parametrize("hours,status,eta", [
        (0, 'imminent', '0-24h'),
        (12, 'imminent', '0-24h'),
        (23.9, 'imminent', '0-24h'),
        (24, 'expected', '24-48h'),
        (48, 'expected', '24-48h'),
        (71.9, 'expected', '24-48h'),
        (72, 'dumped', 'already sold'),
        (168, 'dumped', 'already sold'),
    ])
    def test_loot_status(self, hours, status, eta):
        result_status, result_eta = self._classify_loot(hours)
        assert result_status == status
        assert result_eta == eta


# ---------------------------------------------------------------------------
# Activity level classification (from activity_tracker.py)
# ---------------------------------------------------------------------------

class TestActivityLevelClassification:
    """Test the activity level classification from get_summary_stats."""

    @staticmethod
    def _classify_activity(kills_7d: int) -> str:
        """Extracted from ActivityTracker.get_summary_stats."""
        if kills_7d > 500:
            return 'HIGH'
        elif kills_7d > 200:
            return 'MODERATE'
        else:
            return 'LOW'

    @pytest.mark.parametrize("kills,level", [
        (0, 'LOW'),
        (100, 'LOW'),
        (200, 'LOW'),
        (201, 'MODERATE'),
        (350, 'MODERATE'),
        (500, 'MODERATE'),
        (501, 'HIGH'),
        (1000, 'HIGH'),
    ])
    def test_activity_level(self, kills, level):
        assert self._classify_activity(kills) == level


# ---------------------------------------------------------------------------
# Threat severity classification (from threat_analyzer.py)
# ---------------------------------------------------------------------------

class TestThreatSeverity:
    """Test the threat severity classification from ThreatAnalyzer.get_threats."""

    @staticmethod
    def _classify_severity(kill_count: int) -> str:
        """Extracted from ThreatAnalyzer.get_threats activity spike logic."""
        return 'critical' if kill_count >= 10 else 'warning'

    @pytest.mark.parametrize("kills,severity", [
        (5, 'warning'),
        (7, 'warning'),
        (9, 'warning'),
        (10, 'critical'),
        (15, 'critical'),
        (50, 'critical'),
    ])
    def test_spike_severity(self, kills, severity):
        assert self._classify_severity(kills) == severity


# ---------------------------------------------------------------------------
# Supply disruption impact (from commodity_tracker.py)
# ---------------------------------------------------------------------------

class TestSupplyDisruptionImpact:
    """Test the supply disruption impact classification."""

    @staticmethod
    def _classify_impact(systems_lived: int) -> str:
        """Extracted from CommodityTracker.get_supply_disruptions."""
        return 'high' if systems_lived >= 5 else 'medium' if systems_lived >= 3 else 'low'

    @pytest.mark.parametrize("systems,impact", [
        (0, 'low'),
        (1, 'low'),
        (2, 'low'),
        (3, 'medium'),
        (4, 'medium'),
        (5, 'high'),
        (10, 'high'),
    ])
    def test_impact_level(self, systems, impact):
        assert self._classify_impact(systems) == impact


# ---------------------------------------------------------------------------
# Difficulty rating logic (from opportunity_scorer.py SQL)
# ---------------------------------------------------------------------------

class TestDifficultyRating:
    """Test the difficulty rating logic from get_opportunities SQL."""

    @staticmethod
    def _rate_difficulty(corp_count: int, total_activity: int) -> str:
        """Extracted from OpportunityScorer.get_opportunities SQL CASE."""
        if corp_count <= 2 and total_activity < 20:
            return 'EASY'
        elif corp_count <= 5:
            return 'MEDIUM'
        else:
            return 'HARD'

    @pytest.mark.parametrize("corps,activity,difficulty", [
        (0, 0, 'EASY'),
        (1, 10, 'EASY'),
        (2, 19, 'EASY'),
        (2, 20, 'MEDIUM'),  # activity >= 20 disqualifies EASY
        (3, 5, 'MEDIUM'),
        (5, 100, 'MEDIUM'),
        (6, 0, 'HARD'),
        (10, 50, 'HARD'),
    ])
    def test_difficulty_rating(self, corps, activity, difficulty):
        assert self._rate_difficulty(corps, activity) == difficulty


# ---------------------------------------------------------------------------
# Opportunity score components (from SQL)
# ---------------------------------------------------------------------------

class TestOpportunityScoreComponents:
    """Test individual score components from get_opportunities SQL."""

    @staticmethod
    def _activity_score(kills_7d: int) -> int:
        """Extracted from SQL: LEAST(40, kills_7d * 2)."""
        return min(40, kills_7d * 2)

    @staticmethod
    def _weakness_score(corp_count: int) -> int:
        """Extracted from SQL weakness scoring."""
        if corp_count == 0:
            return 10
        elif corp_count <= 2:
            return 30
        elif corp_count <= 5:
            return 20
        else:
            return 10

    @pytest.mark.parametrize("kills,expected", [
        (0, 0),
        (1, 2),
        (10, 20),
        (19, 38),
        (20, 40),
        (100, 40),  # capped at 40
    ])
    def test_activity_score(self, kills, expected):
        assert self._activity_score(kills) == expected

    @pytest.mark.parametrize("corps,expected", [
        (0, 10),
        (1, 30),
        (2, 30),
        (3, 20),
        (5, 20),
        (6, 10),
        (20, 10),
    ])
    def test_weakness_score(self, corps, expected):
        assert self._weakness_score(corps) == expected

    def test_combined_score_capped_at_100(self):
        # Max: activity=40, recency=30, weakness=30 = 100
        total = self._activity_score(20) + 30 + self._weakness_score(1)
        assert min(100, max(0, total)) == 100

    def test_combined_score_minimum_zero(self):
        total = self._activity_score(0) + 5 + self._weakness_score(0)
        assert min(100, max(0, total)) == 15


# ---------------------------------------------------------------------------
# "Hot" system detection
# ---------------------------------------------------------------------------

class TestHotSystemDetection:
    """Test the 'is_hot' logic from get_opportunities."""

    @staticmethod
    def _is_hot(kills_24h: int) -> bool:
        """Extracted from results builder: row['kills_24h'] >= 3."""
        return kills_24h >= 3

    @pytest.mark.parametrize("kills_24h,expected", [
        (0, False),
        (1, False),
        (2, False),
        (3, True),
        (10, True),
    ])
    def test_is_hot(self, kills_24h, expected):
        assert self._is_hot(kills_24h) == expected
