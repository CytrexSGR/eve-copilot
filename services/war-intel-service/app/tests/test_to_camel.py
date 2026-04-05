"""Tests for to_camel() snake_case -> camelCase conversion."""

import pytest
from app.models.base import to_camel


class TestSingleWord:
    def test_single_word(self):
        assert to_camel("name") == "name"

    def test_single_letter(self):
        assert to_camel("x") == "x"

    def test_empty_string(self):
        assert to_camel("") == ""


class TestTwoWords:
    @pytest.mark.parametrize("input_str,expected", [
        ("total_kills", "totalKills"),
        ("isk_destroyed", "iskDestroyed"),
        ("alliance_id", "allianceId"),
        ("ship_value", "shipValue"),
        ("kill_efficiency", "killEfficiency"),
    ])
    def test_two_word_conversion(self, input_str, expected):
        assert to_camel(input_str) == expected


class TestMultiWord:
    @pytest.mark.parametrize("input_str,expected", [
        ("total_kills_count", "totalKillsCount"),
        ("avg_kill_value", "avgKillValue"),
        ("solo_kill_pct", "soloKillPct"),
        ("victim_corporation_id", "victimCorporationId"),
        ("max_capital_kill_value", "maxCapitalKillValue"),
    ])
    def test_multi_word_conversion(self, input_str, expected):
        assert to_camel(input_str) == expected


class TestEdgeCases:
    def test_already_camel(self):
        # Single word without underscore stays as-is
        assert to_camel("totalKills") == "totalKills"

    def test_leading_underscore(self):
        # Leading underscore produces empty first component
        result = to_camel("_private")
        assert result == "Private"

    def test_trailing_underscore(self):
        result = to_camel("name_")
        assert result == "name"

    def test_double_underscore(self):
        result = to_camel("a__b")
        assert result == "aB"

    def test_all_caps_word(self):
        assert to_camel("isk_eff") == "iskEff"

    def test_numeric_suffix(self):
        assert to_camel("level_5") == "level5"
