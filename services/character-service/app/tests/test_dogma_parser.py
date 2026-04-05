import pytest
from app.services.dogma.modifier_parser import parse_modifier_info, DogmaModifier

class TestParseModifierInfo:
    def test_parse_single_item_modifier(self):
        yaml_text = """- domain: shipID
  func: ItemModifier
  modifiedAttributeID: 263
  modifyingAttributeID: 72
  operation: 2"""
        result = parse_modifier_info(yaml_text)
        assert len(result) == 1
        m = result[0]
        assert m.domain == "shipID"
        assert m.func == "ItemModifier"
        assert m.modified_attr_id == 263
        assert m.modifying_attr_id == 72
        assert m.operation == 2
        assert m.group_id is None
        assert m.skill_type_id is None

    def test_parse_location_group_modifier(self):
        yaml_text = """- domain: shipID
  func: LocationGroupModifier
  groupID: 55
  modifiedAttributeID: 64
  modifyingAttributeID: 64
  operation: 4"""
        result = parse_modifier_info(yaml_text)
        assert len(result) == 1
        assert result[0].func == "LocationGroupModifier"
        assert result[0].group_id == 55

    def test_parse_location_required_skill_modifier(self):
        yaml_text = """- domain: shipID
  func: LocationRequiredSkillModifier
  modifiedAttributeID: 51
  modifyingAttributeID: 213
  operation: 6
  skillTypeID: 3300"""
        result = parse_modifier_info(yaml_text)
        assert result[0].func == "LocationRequiredSkillModifier"
        assert result[0].skill_type_id == 3300

    def test_parse_multiple_modifiers(self):
        yaml_text = """- domain: shipID
  func: ItemModifier
  modifiedAttributeID: 263
  modifyingAttributeID: 72
  operation: 2
- domain: shipID
  func: ItemModifier
  modifiedAttributeID: 265
  modifyingAttributeID: 1159
  operation: 2"""
        result = parse_modifier_info(yaml_text)
        assert len(result) == 2
        assert result[0].modified_attr_id == 263
        assert result[1].modified_attr_id == 265

    def test_parse_none_returns_empty(self):
        assert parse_modifier_info(None) == []

    def test_parse_empty_string_returns_empty(self):
        assert parse_modifier_info("") == []

    def test_parse_malformed_yaml_returns_empty(self):
        assert parse_modifier_info("not valid yaml {{{}") == []
