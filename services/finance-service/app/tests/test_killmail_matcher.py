"""Tests for KillmailMatcher pure logic.

Tests parse_killmail_items(), _calculate_match_score(), and FLAG_SLOT_MAP
without requiring database connections.
"""

import pytest

from app.services.killmail_matcher import (
    FLAG_SLOT_MAP,
    ABYSSAL_MIN_TYPE_ID,
    ATTR_META_LEVEL,
    KillmailMatcher,
)


# ──────────────────── FLAG_SLOT_MAP Constants ────────────────────────────


class TestFlagSlotMap:
    """Validate the ESI flag-to-slot mapping constants."""

    def test_high_slot_flags(self):
        """Flags 27-34 map to 'high'."""
        for flag in range(27, 35):
            assert FLAG_SLOT_MAP[flag] == "high", f"Flag {flag} should be 'high'"

    def test_med_slot_flags(self):
        """Flags 19-26 map to 'med'."""
        for flag in range(19, 27):
            assert FLAG_SLOT_MAP[flag] == "med", f"Flag {flag} should be 'med'"

    def test_low_slot_flags(self):
        """Flags 11-18 map to 'low'."""
        for flag in range(11, 19):
            assert FLAG_SLOT_MAP[flag] == "low", f"Flag {flag} should be 'low'"

    def test_rig_slot_flags(self):
        """Flags 92-99 map to 'rig'."""
        for flag in range(92, 100):
            assert FLAG_SLOT_MAP[flag] == "rig", f"Flag {flag} should be 'rig'"

    def test_drone_flag(self):
        """Flag 87 maps to 'drones'."""
        assert FLAG_SLOT_MAP[87] == "drones"

    def test_total_flag_count(self):
        """FLAG_SLOT_MAP should have exactly 33 entries (8+8+8+8+1)."""
        assert len(FLAG_SLOT_MAP) == 33

    def test_cargo_flag_not_mapped(self):
        """Flag 5 (cargo) should not be in map."""
        assert 5 not in FLAG_SLOT_MAP

    def test_abyssal_min_type_id_constant(self):
        """ABYSSAL_MIN_TYPE_ID should be 47700."""
        assert ABYSSAL_MIN_TYPE_ID == 47700

    def test_meta_level_attribute_id(self):
        """ATTR_META_LEVEL should be 633."""
        assert ATTR_META_LEVEL == 633


# ──────────────────── parse_killmail_items() ─────────────────────────────


class TestParseKillmailItems:
    """Test killmail item parsing into slot-grouped structure."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.matcher = KillmailMatcher()

    def test_high_slot_items(self, sample_killmail_items_high_slots):
        """High-slot items (flags 27-34) are grouped under 'high'."""
        result = self.matcher.parse_killmail_items(sample_killmail_items_high_slots)
        assert "high" in result
        assert len(result["high"]) == 3
        assert result["high"][0]["type_id"] == 3170
        assert result["high"][0]["quantity"] == 1

    def test_med_slot_items(self):
        """Med-slot items (flags 19-26) are grouped under 'med'."""
        items = [{"flag": 19, "item_type_id": 3841, "quantity_destroyed": 1, "quantity_dropped": 0}]
        result = self.matcher.parse_killmail_items(items)
        assert "med" in result
        assert result["med"][0]["type_id"] == 3841

    def test_low_slot_items(self):
        """Low-slot items (flags 11-18) are grouped under 'low'."""
        items = [{"flag": 11, "item_type_id": 2048, "quantity_destroyed": 1, "quantity_dropped": 0}]
        result = self.matcher.parse_killmail_items(items)
        assert "low" in result
        assert result["low"][0]["type_id"] == 2048

    def test_rig_slot_items(self):
        """Rig items (flags 92-99) are grouped under 'rig'."""
        items = [{"flag": 92, "item_type_id": 26082, "quantity_destroyed": 1, "quantity_dropped": 0}]
        result = self.matcher.parse_killmail_items(items)
        assert "rig" in result
        assert result["rig"][0]["type_id"] == 26082

    def test_drone_items(self):
        """Flag 87 items are grouped under 'drones'."""
        items = [{"flag": 87, "item_type_id": 2488, "quantity_destroyed": 3, "quantity_dropped": 2}]
        result = self.matcher.parse_killmail_items(items)
        assert "drones" in result
        assert result["drones"][0]["type_id"] == 2488
        assert result["drones"][0]["quantity"] == 5  # 3 destroyed + 2 dropped

    def test_quantity_sum(self):
        """Total quantity is quantity_destroyed + quantity_dropped."""
        items = [{"flag": 27, "item_type_id": 100, "quantity_destroyed": 3, "quantity_dropped": 7}]
        result = self.matcher.parse_killmail_items(items)
        assert result["high"][0]["quantity"] == 10

    def test_zero_quantity_skipped(self):
        """Items with 0 total quantity are skipped."""
        items = [{"flag": 27, "item_type_id": 100, "quantity_destroyed": 0, "quantity_dropped": 0}]
        result = self.matcher.parse_killmail_items(items)
        assert result == {}

    def test_cargo_items_skipped(self):
        """Items with unmapped flags (e.g. cargo flag 5) are skipped."""
        items = [{"flag": 5, "item_type_id": 100, "quantity_destroyed": 1, "quantity_dropped": 0}]
        result = self.matcher.parse_killmail_items(items)
        assert result == {}

    def test_empty_list(self):
        """Empty item list returns empty dict."""
        result = self.matcher.parse_killmail_items([])
        assert result == {}

    def test_all_slots_populated(self, sample_killmail_items_all_slots):
        """Items across all slot types are correctly grouped."""
        result = self.matcher.parse_killmail_items(sample_killmail_items_all_slots)
        assert "high" in result
        assert "med" in result
        assert "low" in result
        assert "rig" in result
        assert "drones" in result

    def test_missing_fields_use_defaults(self):
        """Missing fields default to 0."""
        items = [{"flag": 27, "item_type_id": 100, "quantity_destroyed": 1}]
        result = self.matcher.parse_killmail_items(items)
        assert result["high"][0]["quantity"] == 1

    def test_multiple_items_same_slot(self):
        """Multiple items in the same slot are all included."""
        items = [
            {"flag": 27, "item_type_id": 100, "quantity_destroyed": 1, "quantity_dropped": 0},
            {"flag": 28, "item_type_id": 200, "quantity_destroyed": 1, "quantity_dropped": 0},
            {"flag": 29, "item_type_id": 300, "quantity_destroyed": 1, "quantity_dropped": 0},
        ]
        result = self.matcher.parse_killmail_items(items)
        assert len(result["high"]) == 3


# ──────────────────── _calculate_match_score() ───────────────────────────


class TestCalculateMatchScore:
    """Test match score calculation logic."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.matcher = KillmailMatcher()

    def test_all_exact_match(self):
        """All exact matches should give score 1.0."""
        result = {
            "exact": [{"type_id": 1}, {"type_id": 2}, {"type_id": 3}],
            "downgrades": [],
            "upgrades": [],
            "missing": [],
            "review_required": [],
            "extra": [],
        }
        score = self.matcher._calculate_match_score(result)
        assert score == 1.0

    def test_all_missing(self):
        """All missing items should give score 0.0."""
        result = {
            "exact": [],
            "downgrades": [],
            "upgrades": [],
            "missing": [{"type_id": 1}, {"type_id": 2}],
            "review_required": [],
            "extra": [],
        }
        score = self.matcher._calculate_match_score(result)
        assert score == 0.0

    def test_empty_result(self):
        """No items at all should give score 0.0."""
        result = {
            "exact": [],
            "downgrades": [],
            "upgrades": [],
            "missing": [],
            "review_required": [],
            "extra": [],
        }
        score = self.matcher._calculate_match_score(result)
        assert score == 0.0

    def test_upgrades_count_as_full(self):
        """Upgrades get weight 1.0 (same as exact)."""
        result = {
            "exact": [],
            "downgrades": [],
            "upgrades": [{"type_id": 1}, {"type_id": 2}],
            "missing": [],
            "review_required": [],
            "extra": [],
        }
        score = self.matcher._calculate_match_score(result)
        assert score == 1.0

    def test_downgrades_weight_0_7(self):
        """Downgrades get weight 0.7."""
        result = {
            "exact": [],
            "downgrades": [{"type_id": 1}],
            "upgrades": [],
            "missing": [],
            "review_required": [],
            "extra": [],
        }
        score = self.matcher._calculate_match_score(result)
        assert score == 0.7

    def test_review_required_weight_0_5(self):
        """Review required items get weight 0.5."""
        result = {
            "exact": [],
            "downgrades": [],
            "upgrades": [],
            "missing": [],
            "review_required": [{"type_id": 1}],
            "extra": [],
        }
        score = self.matcher._calculate_match_score(result)
        assert score == 0.5

    def test_mixed_score(self):
        """Mixed categories should produce weighted average.

        1 exact (1.0) + 1 downgrade (0.7) + 1 missing (0.0) = 1.7 / 3 = 0.57
        """
        result = {
            "exact": [{"type_id": 1}],
            "downgrades": [{"type_id": 2}],
            "upgrades": [],
            "missing": [{"type_id": 3}],
            "review_required": [],
            "extra": [],
        }
        score = self.matcher._calculate_match_score(result)
        assert score == 0.57

    def test_extra_items_ignored(self):
        """Extra items do not affect score at all."""
        result = {
            "exact": [{"type_id": 1}],
            "downgrades": [],
            "upgrades": [],
            "missing": [],
            "review_required": [],
            "extra": [{"type_id": 99}, {"type_id": 100}],
        }
        score = self.matcher._calculate_match_score(result)
        assert score == 1.0

    def test_quantity_respected_in_score(self):
        """Items with quantity > 1 should count multiple times.

        2 exact (weight 1.0 each) + 3 missing (weight 0.0 each) = 2.0 / 5 = 0.4
        """
        result = {
            "exact": [{"type_id": 1, "quantity": 2}],
            "downgrades": [],
            "upgrades": [],
            "missing": [{"type_id": 2, "quantity": 3}],
            "review_required": [],
            "extra": [],
        }
        score = self.matcher._calculate_match_score(result)
        assert score == 0.4

    def test_score_rounded_to_two_decimals(self):
        """Score should be rounded to 2 decimal places."""
        # 1 exact + 1 downgrade = (1.0 + 0.7) / 2 = 0.85
        result = {
            "exact": [{"type_id": 1}],
            "downgrades": [{"type_id": 2}],
            "upgrades": [],
            "missing": [],
            "review_required": [],
            "extra": [],
        }
        score = self.matcher._calculate_match_score(result)
        assert score == 0.85
        assert isinstance(score, float)
