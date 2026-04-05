"""Tests for notification_sync — YAML parsing, timestamp conversion, timer relevance."""

import pytest
from datetime import datetime, timezone

from app.services.notification_sync import (
    parse_notification_body,
    convert_esi_timestamp,
    is_timer_relevant,
    extract_timer_data,
    STRUCTURE_ATTACK_TYPES,
    SOV_TYPES,
    TIMER_RELEVANT_TYPES,
)


# --- parse_notification_body ---


class TestParseNotificationBody:
    def test_empty_string(self):
        assert parse_notification_body("") == {}

    def test_none_input(self):
        assert parse_notification_body(None) == {}

    def test_simple_yaml(self):
        text = "structureID: 12345\nsolarsystemID: 30000142"
        result = parse_notification_body(text)
        assert result["structureID"] == 12345
        assert result["solarsystemID"] == 30000142

    def test_yaml_with_nested(self):
        text = "structureID: 99\ntimeLeft: 36000000000\nownerCorpLinkData:\n- showinfo\n- 2\n- 98000001"
        result = parse_notification_body(text)
        assert result["structureID"] == 99
        assert result["timeLeft"] == 36000000000
        assert result["ownerCorpLinkData"] == ["showinfo", 2, 98000001]

    def test_yaml_returns_dict(self):
        text = "key: value"
        result = parse_notification_body(text)
        assert isinstance(result, dict)

    def test_yaml_non_dict_returns_empty(self):
        text = "- item1\n- item2"
        result = parse_notification_body(text)
        assert result == {}

    def test_invalid_yaml_returns_empty(self):
        text = "{{invalid:: yaml"
        result = parse_notification_body(text)
        assert result == {}

    def test_numeric_values(self):
        text = "corpID: 98000001\nallianceID: 99000001\nshieldPercentage: 0.95"
        result = parse_notification_body(text)
        assert result["corpID"] == 98000001
        assert result["allianceID"] == 99000001
        assert result["shieldPercentage"] == 0.95

    def test_boolean_values(self):
        text = "isActive: true\nwasAttacked: false"
        result = parse_notification_body(text)
        assert result["isActive"] is True
        assert result["wasAttacked"] is False


# --- convert_esi_timestamp ---


class TestConvertEsiTimestamp:
    def test_z_suffix(self):
        result = convert_esi_timestamp("2024-01-15T12:30:00Z")
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 12
        assert result.minute == 30

    def test_offset_suffix(self):
        result = convert_esi_timestamp("2024-06-01T08:00:00+00:00")
        assert result.year == 2024
        assert result.hour == 8

    def test_empty_string(self):
        assert convert_esi_timestamp("") is None

    def test_none_input(self):
        assert convert_esi_timestamp(None) is None

    def test_invalid_format(self):
        assert convert_esi_timestamp("not-a-date") is None

    def test_returns_datetime(self):
        result = convert_esi_timestamp("2025-12-31T23:59:59Z")
        assert isinstance(result, datetime)


# --- is_timer_relevant ---


class TestIsTimerRelevant:
    @pytest.mark.parametrize("ntype", list(STRUCTURE_ATTACK_TYPES))
    def test_structure_types_are_relevant(self, ntype):
        assert is_timer_relevant(ntype) is True

    @pytest.mark.parametrize("ntype", list(SOV_TYPES))
    def test_sov_types_are_relevant(self, ntype):
        assert is_timer_relevant(ntype) is True

    def test_irrelevant_type(self):
        assert is_timer_relevant("CorpNewCEOMsg") is False

    def test_empty_type(self):
        assert is_timer_relevant("") is False

    def test_case_sensitive(self):
        assert is_timer_relevant("structureunderattack") is False

    def test_set_integrity(self):
        assert TIMER_RELEVANT_TYPES == STRUCTURE_ATTACK_TYPES | SOV_TYPES


# --- extract_timer_data ---


class TestExtractTimerData:
    def test_returns_none_for_irrelevant(self):
        assert extract_timer_data("CorpNewCEOMsg", {}) is None

    def test_basic_structure_attack(self):
        body = {
            "structureID": 12345,
            "structureTypeID": 35832,
            "solarsystemID": 30000142,
            "corpID": 98000001,
            "allianceID": 99000001,
        }
        result = extract_timer_data("StructureUnderAttack", body)
        assert result is not None
        assert result["structure_id"] == 12345
        assert result["structure_type_id"] == 35832
        assert result["system_id"] == 30000142
        assert result["owner_corporation_id"] == 98000001
        assert result["owner_alliance_id"] == 99000001

    def test_time_left_conversion(self):
        body = {
            "solarsystemID": 30000142,
            "timeLeft": 36000000000,  # 3600 seconds = 1 hour
        }
        result = extract_timer_data("StructureLostShields", body)
        assert result["time_left_seconds"] == pytest.approx(3600.0)

    def test_time_left_large(self):
        body = {
            "solarsystemID": 30000142,
            "timeLeft": 1296000000000,  # 129600 seconds = 36 hours
        }
        result = extract_timer_data("StructureLostArmor", body)
        assert result["time_left_seconds"] == pytest.approx(129600.0)

    def test_sov_structure_reinforced(self):
        body = {
            "solarSystemID": 30000142,
            "corpID": 98000001,
            "timeLeft": 72000000000,
        }
        result = extract_timer_data("SovStructureReinforced", body)
        assert result["system_id"] == 30000142
        assert result["time_left_seconds"] == pytest.approx(7200.0)

    def test_owner_corp_from_link_data(self):
        body = {
            "solarsystemID": 30000142,
            "ownerCorpLinkData": ["showinfo", 2, 98765432],
        }
        result = extract_timer_data("StructureOnline", body)
        assert result["owner_corporation_id"] == 98765432

    def test_owner_corp_direct_takes_priority(self):
        body = {
            "solarsystemID": 30000142,
            "corpID": 11111111,
            "ownerCorpLinkData": ["showinfo", 2, 98765432],
        }
        result = extract_timer_data("StructureOnline", body)
        assert result["owner_corporation_id"] == 11111111

    def test_vulnerability_time(self):
        body = {
            "solarsystemID": 30000142,
            "decloakTime": 1705320000,
        }
        result = extract_timer_data("StructureAnchoring", body)
        assert result["vulnerability_time"] == 1705320000

    def test_missing_solar_system(self):
        body = {"structureID": 12345}
        result = extract_timer_data("StructureUnderAttack", body)
        assert result["system_id"] is None

    def test_notification_type_preserved(self):
        body = {"solarsystemID": 30000142}
        result = extract_timer_data("SovStructureDestroyed", body)
        assert result["notification_type"] == "SovStructureDestroyed"
