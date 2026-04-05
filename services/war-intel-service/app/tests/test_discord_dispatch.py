"""Tests for discord_dispatch — filter matching and embed building."""

import pytest
from datetime import datetime, timezone

from app.services.discord_dispatch import _matches_filters, _build_embed


# --- _matches_filters ---


class TestMatchesFilters:
    def test_no_filters_matches_all(self):
        relay = {}
        event = {"region_id": 10000002, "alliance_id": 99000001, "isk_value": 100}
        assert _matches_filters(relay, event) is True

    def test_region_filter_match(self):
        relay = {"filter_regions": [10000002, 10000030]}
        event = {"region_id": 10000002}
        assert _matches_filters(relay, event) is True

    def test_region_filter_no_match(self):
        relay = {"filter_regions": [10000002, 10000030]}
        event = {"region_id": 10000043}
        assert _matches_filters(relay, event) is False

    def test_region_filter_no_region_in_event(self):
        relay = {"filter_regions": [10000002]}
        event = {}
        assert _matches_filters(relay, event) is True

    def test_alliance_filter_match(self):
        relay = {"filter_alliances": [99000001, 99000002]}
        event = {"alliance_id": 99000001}
        assert _matches_filters(relay, event) is True

    def test_alliance_filter_no_match(self):
        relay = {"filter_alliances": [99000001]}
        event = {"alliance_id": 99000099}
        assert _matches_filters(relay, event) is False

    def test_alliance_filter_no_alliance_in_event(self):
        relay = {"filter_alliances": [99000001]}
        event = {}
        assert _matches_filters(relay, event) is True

    def test_isk_threshold_above(self):
        relay = {"min_isk_threshold": 1_000_000_000}
        event = {"isk_value": 2_000_000_000}
        assert _matches_filters(relay, event) is True

    def test_isk_threshold_below(self):
        relay = {"min_isk_threshold": 1_000_000_000}
        event = {"isk_value": 500_000_000}
        assert _matches_filters(relay, event) is False

    def test_isk_threshold_exact(self):
        relay = {"min_isk_threshold": 1_000_000_000}
        event = {"isk_value": 1_000_000_000}
        assert _matches_filters(relay, event) is True

    def test_isk_threshold_zero_ignored(self):
        relay = {"min_isk_threshold": 0}
        event = {"isk_value": 100}
        assert _matches_filters(relay, event) is True

    def test_isk_threshold_none_ignored(self):
        relay = {"min_isk_threshold": None}
        event = {"isk_value": 100}
        assert _matches_filters(relay, event) is True

    def test_combined_region_and_alliance_match(self):
        relay = {
            "filter_regions": [10000002],
            "filter_alliances": [99000001],
        }
        event = {"region_id": 10000002, "alliance_id": 99000001}
        assert _matches_filters(relay, event) is True

    def test_combined_region_match_alliance_no_match(self):
        relay = {
            "filter_regions": [10000002],
            "filter_alliances": [99000001],
        }
        event = {"region_id": 10000002, "alliance_id": 99000099}
        assert _matches_filters(relay, event) is False

    def test_combined_all_filters(self):
        relay = {
            "filter_regions": [10000002],
            "filter_alliances": [99000001],
            "min_isk_threshold": 500_000_000,
        }
        event = {"region_id": 10000002, "alliance_id": 99000001, "isk_value": 1_000_000_000}
        assert _matches_filters(relay, event) is True

    def test_combined_all_filters_isk_fail(self):
        relay = {
            "filter_regions": [10000002],
            "filter_alliances": [99000001],
            "min_isk_threshold": 500_000_000,
        }
        event = {"region_id": 10000002, "alliance_id": 99000001, "isk_value": 100_000_000}
        assert _matches_filters(relay, event) is False

    def test_empty_filter_lists_match_all(self):
        relay = {"filter_regions": [], "filter_alliances": []}
        event = {"region_id": 10000002, "alliance_id": 99000001}
        assert _matches_filters(relay, event) is True


# --- _build_embed ---


class TestBuildEmbed:
    def test_timer_created_embed(self):
        data = {
            "structure_name": "Astrahus",
            "system_name": "Jita",
            "timer_type": "armor",
            "timer_end": "2025-01-15T12:00:00Z",
        }
        embed = _build_embed("timer_created", data)
        assert embed["color"] == 0xFF8800
        assert "Astrahus" in embed["title"]
        assert "Jita" in embed["description"]
        assert "armor" in embed["description"]

    def test_timer_expiring_embed(self):
        data = {
            "structure_name": "Fortizar",
            "system_name": "1DQ1-A",
            "hours_until": 2,
        }
        embed = _build_embed("timer_expiring", data)
        assert embed["color"] == 0xFF4444
        assert "Fortizar" in embed["title"]
        assert "2" in embed["description"]

    def test_high_value_kill_embed(self):
        data = {
            "ship_name": "Titan",
            "isk_value": 100_000_000_000,
            "system_name": "B-R5RB",
            "victim_name": "TestPilot",
        }
        embed = _build_embed("high_value_kill", data)
        assert embed["color"] == 0x3FB950
        assert "Titan" in embed["title"]
        assert "TestPilot" in embed["description"]
        assert "B-R5RB" in embed["description"]

    def test_battle_started_embed(self):
        data = {
            "system_name": "HED-GP",
            "kill_count": 45,
            "isk_destroyed": 5_000_000_000,
        }
        embed = _build_embed("battle_started", data)
        assert embed["color"] == 0x00D4FF
        assert "HED-GP" in embed["title"]
        assert "45" in embed["description"]

    def test_structure_attack_embed(self):
        data = {
            "structure_name": "Keepstar",
            "system_name": "M-OEE8",
            "attacker_name": "PanFam",
        }
        embed = _build_embed("structure_attack", data)
        assert embed["color"] == 0xFF0000
        assert "Keepstar" in embed["title"]
        assert "PanFam" in embed["description"]

    def test_unknown_event_type_fallback_color(self):
        embed = _build_embed("unknown_event", {})
        assert embed["color"] == 0x888888

    def test_embed_has_footer(self):
        embed = _build_embed("timer_created", {"structure_name": "X"})
        assert embed["footer"]["text"] == "EVE Co-Pilot Intel"

    def test_embed_has_timestamp(self):
        embed = _build_embed("timer_created", {"structure_name": "X"})
        assert "timestamp" in embed

    def test_missing_data_uses_unknown(self):
        embed = _build_embed("timer_created", {})
        assert "Unknown" in embed["title"]

    def test_all_five_event_types_produce_embeds(self):
        types = ["timer_created", "timer_expiring", "battle_started",
                 "structure_attack", "high_value_kill"]
        for t in types:
            embed = _build_embed(t, {"structure_name": "X", "ship_name": "Y",
                                     "system_name": "Z", "victim_name": "V",
                                     "attacker_name": "A", "timer_type": "armor",
                                     "timer_end": "now", "hours_until": 1,
                                     "isk_value": 1000, "kill_count": 5,
                                     "isk_destroyed": 2000})
            assert "title" in embed
            assert "color" in embed
