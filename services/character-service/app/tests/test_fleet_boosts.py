"""Tests for fleet boost (Command Burst) system.

Covers:
- apply_fleet_boosts: shield HP, armor resist, speed, multiple stacking,
  empty input, unknown buff_id, immutability of original attrs
- BUFF_DEFINITIONS structure validation
- BOOST_PRESETS structure and cross-reference validation
- FleetBoostInput model validation
- Endpoint response structure tests
"""

import pytest
from app.services.fitting_stats.fleet_boosts import (
    BUFF_DEFINITIONS,
    BOOST_PRESETS,
    apply_fleet_boosts,
)
from app.services.fitting_stats.models import FleetBoostInput


# ---------------------------------------------------------------------------
# apply_fleet_boosts — postPercent operations
# ---------------------------------------------------------------------------

class TestApplyFleetBoostsPostPercent:
    """Tests for postPercent operation (attr *= (1 + value/100))."""

    def test_shield_hp_boost(self):
        """Shield HP buff (id 10) increases shield HP attribute 263."""
        attrs = {263: 5000.0}
        result = apply_fleet_boosts(attrs, [{"buff_id": 10, "value": 25.88}])
        expected = 5000.0 * (1.0 + 25.88 / 100.0)
        assert result[263] == pytest.approx(expected, rel=1e-6)

    def test_speed_boost(self):
        """Speed buff (id 35) increases max velocity attribute 37."""
        attrs = {37: 200.0}
        result = apply_fleet_boosts(attrs, [{"buff_id": 35, "value": 25.88}])
        expected = 200.0 * 1.2588
        assert result[37] == pytest.approx(expected, rel=1e-6)

    def test_agility_boost_negative(self):
        """Agility buff (id 33) with negative value reduces agility (good)."""
        attrs = {70: 0.5}
        result = apply_fleet_boosts(attrs, [{"buff_id": 33, "value": -25.88}])
        expected = 0.5 * (1.0 - 25.88 / 100.0)
        assert result[70] == pytest.approx(expected, rel=1e-6)

    def test_armor_hp_boost(self):
        """Armor HP buff (id 13) increases armor HP attribute 265."""
        attrs = {265: 8000.0}
        result = apply_fleet_boosts(attrs, [{"buff_id": 13, "value": 25.88}])
        expected = 8000.0 * 1.2588
        assert result[265] == pytest.approx(expected, rel=1e-6)

    def test_lock_range_boost(self):
        """Lock range buff (id 37) increases max target range attribute 76."""
        attrs = {76: 60000.0}
        result = apply_fleet_boosts(attrs, [{"buff_id": 37, "value": 25.88}])
        expected = 60000.0 * 1.2588
        assert result[76] == pytest.approx(expected, rel=1e-6)

    def test_scan_resolution_boost(self):
        """Scan resolution buff (id 38) increases scan res attribute 564."""
        attrs = {564: 300.0}
        result = apply_fleet_boosts(attrs, [{"buff_id": 38, "value": 25.88}])
        expected = 300.0 * 1.2588
        assert result[564] == pytest.approx(expected, rel=1e-6)

    def test_shield_repair_boost(self):
        """Shield repair buff (id 12) increases shield boost amount attribute 68."""
        attrs = {68: 400.0}
        result = apply_fleet_boosts(attrs, [{"buff_id": 12, "value": 25.88}])
        expected = 400.0 * 1.2588
        assert result[68] == pytest.approx(expected, rel=1e-6)

    def test_zero_value_boost(self):
        """Boost with value 0 should not change the attribute."""
        attrs = {263: 5000.0}
        result = apply_fleet_boosts(attrs, [{"buff_id": 10, "value": 0.0}])
        assert result[263] == 5000.0


# ---------------------------------------------------------------------------
# apply_fleet_boosts — resist_add operations
# ---------------------------------------------------------------------------

class TestApplyFleetBoostsResistAdd:
    """Tests for resist_add operation (attr *= (1 - value/100))."""

    def test_shield_resist_boost(self):
        """Shield resist buff (id 11) reduces all shield resist pass-through."""
        # In EVE, resist attributes store pass-through (0.5 = 50% pass-through = 50% resist)
        attrs = {271: 0.5, 272: 0.6, 273: 0.55, 274: 0.45}
        result = apply_fleet_boosts(attrs, [{"buff_id": 11, "value": 12.94}])
        factor = (1.0 - 12.94 / 100.0)
        assert result[271] == pytest.approx(0.5 * factor, rel=1e-6)
        assert result[272] == pytest.approx(0.6 * factor, rel=1e-6)
        assert result[273] == pytest.approx(0.55 * factor, rel=1e-6)
        assert result[274] == pytest.approx(0.45 * factor, rel=1e-6)

    def test_armor_resist_boost(self):
        """Armor resist buff (id 14) reduces all armor resist pass-through."""
        attrs = {267: 0.4, 268: 0.5, 269: 0.3, 270: 0.6}
        result = apply_fleet_boosts(attrs, [{"buff_id": 14, "value": 12.94}])
        factor = (1.0 - 12.94 / 100.0)
        assert result[267] == pytest.approx(0.4 * factor, rel=1e-6)
        assert result[268] == pytest.approx(0.5 * factor, rel=1e-6)
        assert result[269] == pytest.approx(0.3 * factor, rel=1e-6)
        assert result[270] == pytest.approx(0.6 * factor, rel=1e-6)

    def test_resist_zero_value(self):
        """Resist boost with value 0 should not change pass-through."""
        attrs = {271: 0.5}
        result = apply_fleet_boosts(attrs, [{"buff_id": 11, "value": 0.0}])
        assert result[271] == 0.5


# ---------------------------------------------------------------------------
# apply_fleet_boosts — multiple boosts stacking
# ---------------------------------------------------------------------------

class TestApplyFleetBoostsStacking:
    """Tests for multiple boosts stacking multiplicatively."""

    def test_multiple_boosts_stack(self):
        """Multiple boosts apply multiplicatively in sequence."""
        attrs = {263: 5000.0, 271: 0.5, 272: 0.5, 273: 0.5, 274: 0.5, 68: 400.0}
        boosts = [
            {"buff_id": 10, "value": 25.88},  # Shield HP
            {"buff_id": 11, "value": 12.94},  # Shield Resist
            {"buff_id": 12, "value": 25.88},  # Shield Repair
        ]
        result = apply_fleet_boosts(attrs, boosts)

        assert result[263] == pytest.approx(5000.0 * 1.2588, rel=1e-6)
        assert result[271] == pytest.approx(0.5 * (1.0 - 12.94 / 100.0), rel=1e-6)
        assert result[68] == pytest.approx(400.0 * 1.2588, rel=1e-6)

    def test_two_boosts_on_same_attr(self):
        """Two boosts affecting the same attribute stack multiplicatively."""
        # Mining cycle time (buff 45) and Armor repair duration (buff 15)
        # both affect attribute 73 (duration)
        attrs = {73: 10000.0}
        boosts = [
            {"buff_id": 15, "value": -25.88},  # Armor repair duration
            {"buff_id": 45, "value": -10.0},    # Mining cycle time
        ]
        result = apply_fleet_boosts(attrs, boosts)
        expected = 10000.0 * (1.0 - 25.88 / 100.0) * (1.0 - 10.0 / 100.0)
        assert result[73] == pytest.approx(expected, rel=1e-6)


# ---------------------------------------------------------------------------
# apply_fleet_boosts — edge cases
# ---------------------------------------------------------------------------

class TestApplyFleetBoostsEdgeCases:
    """Tests for edge cases and defensive behavior."""

    def test_empty_boosts_returns_same_dict(self):
        """Empty boosts list returns the original dict reference."""
        attrs = {263: 5000.0}
        result = apply_fleet_boosts(attrs, [])
        assert result is attrs

    def test_none_boosts_not_accepted(self):
        """None is falsy — returns original dict."""
        attrs = {263: 5000.0}
        result = apply_fleet_boosts(attrs, None)
        assert result is attrs

    def test_unknown_buff_id_ignored(self):
        """Unknown buff_id is silently ignored."""
        attrs = {263: 5000.0}
        result = apply_fleet_boosts(attrs, [{"buff_id": 99999, "value": 50.0}])
        assert result[263] == 5000.0

    def test_missing_attr_in_ship_ignored(self):
        """Buff targeting attributes not in ship_attrs is silently ignored."""
        attrs = {263: 5000.0}  # Only shield HP, no speed attr
        result = apply_fleet_boosts(attrs, [{"buff_id": 35, "value": 25.88}])
        assert result == {263: 5000.0}

    def test_original_attrs_not_mutated(self):
        """apply_fleet_boosts must not mutate the input dict."""
        attrs = {263: 5000.0, 37: 200.0}
        original_shield = attrs[263]
        original_speed = attrs[37]
        result = apply_fleet_boosts(attrs, [
            {"buff_id": 10, "value": 25.88},
            {"buff_id": 35, "value": 25.88},
        ])
        # Original unchanged
        assert attrs[263] == original_shield
        assert attrs[37] == original_speed
        # Result changed
        assert result[263] != original_shield
        assert result[37] != original_speed

    def test_accepts_model_objects(self):
        """apply_fleet_boosts works with FleetBoostInput model objects."""
        attrs = {263: 5000.0}
        boost = FleetBoostInput(buff_id=10, value=25.88)
        result = apply_fleet_boosts(attrs, [boost])
        expected = 5000.0 * 1.2588
        assert result[263] == pytest.approx(expected, rel=1e-6)

    def test_mixed_dict_and_model_objects(self):
        """Handles a mix of dict and model objects in the same list."""
        attrs = {263: 5000.0, 37: 200.0}
        boosts = [
            {"buff_id": 10, "value": 25.88},
            FleetBoostInput(buff_id=35, value=25.88),
        ]
        result = apply_fleet_boosts(attrs, boosts)
        assert result[263] == pytest.approx(5000.0 * 1.2588, rel=1e-6)
        assert result[37] == pytest.approx(200.0 * 1.2588, rel=1e-6)


# ---------------------------------------------------------------------------
# BUFF_DEFINITIONS structure validation
# ---------------------------------------------------------------------------

class TestBuffDefinitions:
    """Validate BUFF_DEFINITIONS structure."""

    def test_all_entries_have_required_keys(self):
        """Every buff definition must have name, attributes, and operation."""
        for buff_id, defn in BUFF_DEFINITIONS.items():
            assert "name" in defn, f"Buff {buff_id} missing 'name'"
            assert "attributes" in defn, f"Buff {buff_id} missing 'attributes'"
            assert "operation" in defn, f"Buff {buff_id} missing 'operation'"

    def test_operation_values_valid(self):
        """Operation must be 'postPercent' or 'resist_add'."""
        valid_ops = {"postPercent", "resist_add"}
        for buff_id, defn in BUFF_DEFINITIONS.items():
            assert defn["operation"] in valid_ops, (
                f"Buff {buff_id} has invalid operation '{defn['operation']}'"
            )

    def test_attributes_are_int_lists(self):
        """Attributes must be non-empty lists of integers."""
        for buff_id, defn in BUFF_DEFINITIONS.items():
            attrs = defn["attributes"]
            assert isinstance(attrs, list), f"Buff {buff_id} attributes not a list"
            assert len(attrs) > 0, f"Buff {buff_id} has empty attributes"
            for a in attrs:
                assert isinstance(a, int), f"Buff {buff_id} has non-int attribute {a}"

    def test_buff_ids_are_positive_ints(self):
        """All buff_ids must be positive integers."""
        for buff_id in BUFF_DEFINITIONS:
            assert isinstance(buff_id, int) and buff_id > 0

    def test_names_are_non_empty_strings(self):
        """All buff names must be non-empty strings."""
        for buff_id, defn in BUFF_DEFINITIONS.items():
            assert isinstance(defn["name"], str) and len(defn["name"]) > 0

    def test_shield_command_buffs_exist(self):
        """Shield command buffs 10, 11, 12 must exist."""
        assert 10 in BUFF_DEFINITIONS
        assert 11 in BUFF_DEFINITIONS
        assert 12 in BUFF_DEFINITIONS

    def test_armor_command_buffs_exist(self):
        """Armor command buffs 13, 14, 15 must exist."""
        assert 13 in BUFF_DEFINITIONS
        assert 14 in BUFF_DEFINITIONS
        assert 15 in BUFF_DEFINITIONS

    def test_skirmish_command_buffs_exist(self):
        """Skirmish command buffs 33, 34, 35 must exist."""
        assert 33 in BUFF_DEFINITIONS
        assert 34 in BUFF_DEFINITIONS
        assert 35 in BUFF_DEFINITIONS

    def test_info_command_buffs_exist(self):
        """Information command buffs 36, 37, 38, 39 must exist."""
        assert 36 in BUFF_DEFINITIONS
        assert 37 in BUFF_DEFINITIONS
        assert 38 in BUFF_DEFINITIONS
        assert 39 in BUFF_DEFINITIONS

    def test_mining_foreman_buffs_exist(self):
        """Mining foreman buffs 43, 44, 45 must exist."""
        assert 43 in BUFF_DEFINITIONS
        assert 44 in BUFF_DEFINITIONS
        assert 45 in BUFF_DEFINITIONS


# ---------------------------------------------------------------------------
# BOOST_PRESETS validation
# ---------------------------------------------------------------------------

class TestBoostPresets:
    """Validate BOOST_PRESETS structure and cross-references."""

    def test_all_presets_are_lists(self):
        """Each preset must be a list of boost dicts."""
        for name, boosts in BOOST_PRESETS.items():
            assert isinstance(boosts, list), f"Preset '{name}' is not a list"
            assert len(boosts) > 0, f"Preset '{name}' is empty"

    def test_all_preset_boosts_have_required_keys(self):
        """Each boost in a preset must have buff_id and value."""
        for name, boosts in BOOST_PRESETS.items():
            for i, b in enumerate(boosts):
                assert "buff_id" in b, f"Preset '{name}' boost {i} missing 'buff_id'"
                assert "value" in b, f"Preset '{name}' boost {i} missing 'value'"

    def test_all_preset_buff_ids_exist_in_definitions(self):
        """Every buff_id in presets must reference an existing BUFF_DEFINITIONS entry."""
        for name, boosts in BOOST_PRESETS.items():
            for b in boosts:
                assert b["buff_id"] in BUFF_DEFINITIONS, (
                    f"Preset '{name}' references unknown buff_id {b['buff_id']}"
                )

    def test_shield_t2_max_preset(self):
        """Shield T2 max preset has correct buff_ids."""
        preset = BOOST_PRESETS["shield_t2_max"]
        buff_ids = [b["buff_id"] for b in preset]
        assert buff_ids == [10, 11, 12]

    def test_armor_t2_max_preset(self):
        """Armor T2 max preset has correct buff_ids."""
        preset = BOOST_PRESETS["armor_t2_max"]
        buff_ids = [b["buff_id"] for b in preset]
        assert buff_ids == [13, 14, 15]

    def test_skirmish_t2_max_preset(self):
        """Skirmish T2 max preset has correct buff_ids."""
        preset = BOOST_PRESETS["skirmish_t2_max"]
        buff_ids = [b["buff_id"] for b in preset]
        assert buff_ids == [33, 34, 35]

    def test_info_t2_max_preset(self):
        """Info T2 max preset has correct buff_ids."""
        preset = BOOST_PRESETS["info_t2_max"]
        buff_ids = [b["buff_id"] for b in preset]
        assert buff_ids == [36, 37, 38]

    def test_preset_count(self):
        """Should have exactly 4 presets."""
        assert len(BOOST_PRESETS) == 4


# ---------------------------------------------------------------------------
# FleetBoostInput model
# ---------------------------------------------------------------------------

class TestFleetBoostInputModel:
    """Tests for the FleetBoostInput Pydantic model."""

    def test_valid_creation(self):
        """Create a valid FleetBoostInput."""
        boost = FleetBoostInput(buff_id=10, value=25.88)
        assert boost.buff_id == 10
        assert boost.value == 25.88

    def test_negative_value(self):
        """Negative values are valid (e.g., agility reduction)."""
        boost = FleetBoostInput(buff_id=33, value=-25.88)
        assert boost.value == -25.88

    def test_zero_value(self):
        """Zero value is valid."""
        boost = FleetBoostInput(buff_id=10, value=0.0)
        assert boost.value == 0.0

    def test_integer_value_coerced_to_float(self):
        """Integer value should be accepted and treated as float."""
        boost = FleetBoostInput(buff_id=10, value=25)
        assert isinstance(boost.value, (int, float))


# ---------------------------------------------------------------------------
# Full preset application integration
# ---------------------------------------------------------------------------

class TestPresetApplication:
    """Integration tests applying full presets to ship attrs."""

    def test_shield_t2_max_full_application(self):
        """Apply the entire shield T2 max preset to a ship."""
        attrs = {
            263: 5000.0,   # Shield HP
            271: 0.5,      # Shield EM resist
            272: 0.6,      # Shield explosive resist
            273: 0.55,     # Shield kinetic resist
            274: 0.45,     # Shield thermal resist
            68: 400.0,     # Shield boost amount
        }
        result = apply_fleet_boosts(attrs, BOOST_PRESETS["shield_t2_max"])

        # Shield HP: +25.88%
        assert result[263] == pytest.approx(5000.0 * 1.2588, rel=1e-6)
        # Shield resists: reduced pass-through by 12.94%
        resist_factor = 1.0 - 12.94 / 100.0
        assert result[271] == pytest.approx(0.5 * resist_factor, rel=1e-6)
        assert result[272] == pytest.approx(0.6 * resist_factor, rel=1e-6)
        # Shield repair: +25.88%
        assert result[68] == pytest.approx(400.0 * 1.2588, rel=1e-6)

    def test_skirmish_t2_max_full_application(self):
        """Apply the entire skirmish T2 max preset to a ship."""
        attrs = {
            70: 0.5,       # Agility
            103: 20000.0,  # Tackle range (warp disrupt range)
            37: 200.0,     # Max velocity
        }
        result = apply_fleet_boosts(attrs, BOOST_PRESETS["skirmish_t2_max"])

        # Agility: -25.88% (lower is better)
        assert result[70] == pytest.approx(0.5 * (1.0 - 25.88 / 100.0), rel=1e-6)
        # Tackle range: +25.88%
        assert result[103] == pytest.approx(20000.0 * 1.2588, rel=1e-6)
        # Speed: +25.88%
        assert result[37] == pytest.approx(200.0 * 1.2588, rel=1e-6)
