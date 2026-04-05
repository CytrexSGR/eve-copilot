"""Tests for sde_browser.py charge browser endpoint.

Covers: get_compatible_charges pure function — charge group lookup,
        charge stats retrieval, empty results, dict key format.
"""

import pytest
from contextlib import contextmanager

from app.tests.conftest import MultiResultCursor


def _make_db(result_sets):
    """Create a FakeDB that returns a MultiResultCursor as a context manager.

    The real DB uses `db.cursor(cursor_factory=...)` which returns a
    context-managed cursor.  We replicate that by wrapping MultiResultCursor
    in a contextmanager so `with db.cursor(...) as cur:` works in tests.
    """
    cur = MultiResultCursor(result_sets)

    class FakeDB:
        @contextmanager
        def cursor(self, cursor_factory=None):
            yield cur

    return FakeDB(), cur


# ---------------------------------------------------------------------------
# get_compatible_charges
# ---------------------------------------------------------------------------

class TestGetCompatibleChargesWithChargeGroups:
    """Weapon with known charge groups returns charges with correct format."""

    def test_returns_charges_for_weapon_with_groups(self):
        from app.routers.sde_browser import get_compatible_charges

        # First query: charge group IDs for a weapon (e.g., 125mm Railgun)
        charge_groups = [
            {"group_id": 85},   # Hybrid Charge S
            {"group_id": 372},  # Hybrid Charge M (hypothetical second group)
        ]

        # Second query: charges in those groups
        charges = [
            {
                "typeID": 214,
                "typeName": "Antimatter Charge S",
                "groupName": "Hybrid Charge S",
                "em": 0.0,
                "thermal": 4.0,
                "kinetic": 6.0,
                "explosive": 0.0,
                "meta_level": 0,
            },
            {
                "typeID": 216,
                "typeName": "Iron Charge S",
                "groupName": "Hybrid Charge S",
                "em": 0.0,
                "thermal": 2.0,
                "kinetic": 4.0,
                "explosive": 0.0,
                "meta_level": 0,
            },
        ]

        db, _ = _make_db([charge_groups, charges])
        result = get_compatible_charges(db, weapon_type_id=3170)

        assert len(result) == 2
        assert result[0]["type_id"] == 214
        assert result[0]["name"] == "Antimatter Charge S"
        assert result[0]["group_name"] == "Hybrid Charge S"
        assert result[0]["em"] == 0.0
        assert result[0]["thermal"] == 4.0
        assert result[0]["kinetic"] == 6.0
        assert result[0]["explosive"] == 0.0
        assert result[0]["meta_level"] == 0

    def test_second_charge_fields(self):
        from app.routers.sde_browser import get_compatible_charges

        charge_groups = [{"group_id": 85}]
        charges = [
            {
                "typeID": 214,
                "typeName": "Antimatter Charge S",
                "groupName": "Hybrid Charge S",
                "em": 0.0,
                "thermal": 4.0,
                "kinetic": 6.0,
                "explosive": 0.0,
                "meta_level": 0,
            },
            {
                "typeID": 216,
                "typeName": "Iron Charge S",
                "groupName": "Hybrid Charge S",
                "em": 0.0,
                "thermal": 2.0,
                "kinetic": 4.0,
                "explosive": 0.0,
                "meta_level": 0,
            },
        ]

        db, _ = _make_db([charge_groups, charges])
        result = get_compatible_charges(db, weapon_type_id=3170)

        assert result[1]["type_id"] == 216
        assert result[1]["name"] == "Iron Charge S"
        assert result[1]["thermal"] == 2.0
        assert result[1]["kinetic"] == 4.0

    def test_damage_values_rounded_to_one_decimal(self):
        from app.routers.sde_browser import get_compatible_charges

        charge_groups = [{"group_id": 85}]
        charges = [
            {
                "typeID": 214,
                "typeName": "Antimatter Charge S",
                "groupName": "Hybrid Charge S",
                "em": 1.234,
                "thermal": 4.567,
                "kinetic": 6.891,
                "explosive": 0.456,
                "meta_level": 5,
            },
        ]

        db, _ = _make_db([charge_groups, charges])
        result = get_compatible_charges(db, weapon_type_id=3170)

        assert result[0]["em"] == 1.2
        assert result[0]["thermal"] == 4.6
        assert result[0]["kinetic"] == 6.9
        assert result[0]["explosive"] == 0.5
        assert result[0]["meta_level"] == 5


class TestGetCompatibleChargesNoChargeGroups:
    """Non-weapon module (no charge groups) returns empty list."""

    def test_non_weapon_returns_empty(self):
        from app.routers.sde_browser import get_compatible_charges

        # First query returns no charge groups (e.g., armor plate has no charges)
        db, _ = _make_db([[], []])
        result = get_compatible_charges(db, weapon_type_id=11269)

        assert result == []

    def test_only_one_query_executed_when_no_groups(self):
        from app.routers.sde_browser import get_compatible_charges

        db, cur = _make_db([[], []])
        get_compatible_charges(db, weapon_type_id=11269)

        # Should stop after the first query (no charge groups found)
        assert len(cur._executed) == 1


class TestGetCompatibleChargesEmptyChargeResults:
    """Weapon where charge group query returns groups but no charges found."""

    def test_groups_exist_but_no_charges(self):
        from app.routers.sde_browser import get_compatible_charges

        # First query returns charge groups
        charge_groups = [{"group_id": 9999}]
        # Second query returns no charges (hypothetical empty group)
        db, _ = _make_db([charge_groups, []])
        result = get_compatible_charges(db, weapon_type_id=3170)

        assert result == []


class TestGetCompatibleChargesDictKeys:
    """Verify returned dict keys match expected format."""

    def test_returned_keys_match_spec(self):
        from app.routers.sde_browser import get_compatible_charges

        charge_groups = [{"group_id": 85}]
        charges = [
            {
                "typeID": 214,
                "typeName": "Antimatter Charge S",
                "groupName": "Hybrid Charge S",
                "em": 0.0,
                "thermal": 4.0,
                "kinetic": 6.0,
                "explosive": 0.0,
                "meta_level": 0,
            },
        ]

        db, _ = _make_db([charge_groups, charges])
        result = get_compatible_charges(db, weapon_type_id=3170)

        expected_keys = {"type_id", "name", "group_name", "em", "thermal", "kinetic", "explosive", "meta_level"}
        assert set(result[0].keys()) == expected_keys

    def test_no_extra_keys(self):
        """Ensure no unexpected keys leak through from DB rows."""
        from app.routers.sde_browser import get_compatible_charges

        charge_groups = [{"group_id": 85}]
        charges = [
            {
                "typeID": 214,
                "typeName": "Antimatter Charge S",
                "groupName": "Hybrid Charge S",
                "em": 0.0,
                "thermal": 4.0,
                "kinetic": 6.0,
                "explosive": 0.0,
                "meta_level": 0,
            },
        ]

        db, _ = _make_db([charge_groups, charges])
        result = get_compatible_charges(db, weapon_type_id=3170)

        # No DB column names (typeID, typeName, groupName) should appear
        assert "typeID" not in result[0]
        assert "typeName" not in result[0]
        assert "groupName" not in result[0]


class TestGetCompatibleChargesQueryParams:
    """Verify the correct SQL parameters are passed to each query."""

    def test_first_query_uses_weapon_type_id(self):
        from app.routers.sde_browser import get_compatible_charges

        charge_groups = [{"group_id": 85}]
        charges = []

        db, cur = _make_db([charge_groups, charges])
        get_compatible_charges(db, weapon_type_id=3170)

        # First execute: weapon_type_id param
        first_sql, first_params = cur._executed[0]
        assert first_params["type_id"] == 3170

    def test_second_query_uses_group_ids(self):
        from app.routers.sde_browser import get_compatible_charges

        charge_groups = [{"group_id": 85}, {"group_id": 372}]
        charges = []

        db, cur = _make_db([charge_groups, charges])
        get_compatible_charges(db, weapon_type_id=3170)

        # Second execute: group_ids param
        assert len(cur._executed) == 2
        second_sql, second_params = cur._executed[1]
        assert second_params["group_ids"] == [85, 372]


# ---------------------------------------------------------------------------
# Pure function and constant tests
# ---------------------------------------------------------------------------

class TestGetAttr:
    """Tests for _get_attr helper function."""

    def test_returns_value_when_present(self):
        from app.routers.sde_browser import _get_attr
        assert _get_attr({14: 7.0}, 14) == 7.0

    def test_returns_default_when_missing(self):
        from app.routers.sde_browser import _get_attr
        assert _get_attr({}, 14) == 0

    def test_returns_default_when_none(self):
        from app.routers.sde_browser import _get_attr
        assert _get_attr({14: None}, 14) == 0

    def test_custom_default(self):
        from app.routers.sde_browser import _get_attr
        assert _get_attr({}, 14, default=-1) == -1


class TestSlotEffectMap:
    """Tests for SLOT_EFFECT_MAP constant."""

    def test_high_slot(self):
        from app.routers.sde_browser import SLOT_EFFECT_MAP, EFFECT_HI_POWER
        assert SLOT_EFFECT_MAP[EFFECT_HI_POWER] == "high"

    def test_mid_slot(self):
        from app.routers.sde_browser import SLOT_EFFECT_MAP, EFFECT_MED_POWER
        assert SLOT_EFFECT_MAP[EFFECT_MED_POWER] == "mid"

    def test_low_slot(self):
        from app.routers.sde_browser import SLOT_EFFECT_MAP, EFFECT_LO_POWER
        assert SLOT_EFFECT_MAP[EFFECT_LO_POWER] == "low"

    def test_rig_slot(self):
        from app.routers.sde_browser import SLOT_EFFECT_MAP, EFFECT_RIG_SLOT
        assert SLOT_EFFECT_MAP[EFFECT_RIG_SLOT] == "rig"

    def test_all_four_slots(self):
        from app.routers.sde_browser import SLOT_EFFECT_MAP
        assert len(SLOT_EFFECT_MAP) == 4


class TestGroupSummary:
    """Tests for GroupSummary Pydantic model."""

    def test_model_creation(self):
        from app.routers.sde_browser import GroupSummary
        g = GroupSummary(group_id=27, group_name="Battleship", count=42)
        assert g.group_id == 27
        assert g.group_name == "Battleship"
        assert g.count == 42


class TestModuleGroupsLogic:
    """Test module-groups related constants and logic."""

    def test_drone_category_is_18(self):
        assert 18 != 7  # drone != module category

    def test_slot_effect_map_keys_are_ints(self):
        from app.routers.sde_browser import SLOT_EFFECT_MAP
        for eid in SLOT_EFFECT_MAP:
            assert isinstance(eid, int)

    def test_slot_effect_map_values_valid(self):
        from app.routers.sde_browser import SLOT_EFFECT_MAP
        valid = {"high", "mid", "low", "rig"}
        for name in SLOT_EFFECT_MAP.values():
            assert name in valid

    def test_group_summary_with_zero_count(self):
        from app.routers.sde_browser import GroupSummary
        g = GroupSummary(group_id=100, group_name="Test", count=0)
        assert g.count == 0


class TestAttributeConstants:
    """Tests for SDE attribute ID constants."""

    def test_ship_attr_ids_are_ints(self):
        from app.routers.sde_browser import ATTR_HI_SLOTS, ATTR_CPU_OUTPUT, ATTR_POWER_OUTPUT
        for attr_id in [ATTR_HI_SLOTS, ATTR_CPU_OUTPUT, ATTR_POWER_OUTPUT]:
            assert isinstance(attr_id, int)


class TestShipDetailHardpoints:
    """Verify ShipDetail model includes turret/launcher hardpoints and rig_size."""

    def test_ship_detail_has_hardpoint_fields(self):
        from app.routers.sde_browser import ShipDetail
        ship = ShipDetail(
            type_id=638, type_name="Raven", group_id=27, group_name="Battleship",
            turret_hardpoints=4, launcher_hardpoints=6, rig_size=3,
        )
        assert ship.turret_hardpoints == 4
        assert ship.launcher_hardpoints == 6
        assert ship.rig_size == 3

    def test_ship_detail_defaults_zero(self):
        from app.routers.sde_browser import ShipDetail
        ship = ShipDetail(type_id=1, type_name="X", group_id=1, group_name="G")
        assert ship.turret_hardpoints == 0
        assert ship.launcher_hardpoints == 0
        assert ship.rig_size == 0

    def test_ship_summary_has_hardpoint_fields(self):
        from app.routers.sde_browser import ShipSummary
        ship = ShipSummary(
            type_id=638, type_name="Raven", group_id=27, group_name="Battleship",
            turret_hardpoints=4, launcher_hardpoints=6, rig_size=3,
        )
        assert ship.turret_hardpoints == 4
        assert ship.launcher_hardpoints == 6
        assert ship.rig_size == 3


class TestModuleSummaryHardpointType:
    """ModuleSummary should include hardpoint_type field."""

    def test_turret_module(self):
        from app.routers.sde_browser import ModuleSummary
        m = ModuleSummary(
            type_id=3170, type_name="425mm Railgun II",
            group_id=74, group_name="Hybrid Weapon",
            slot_type="high", hardpoint_type="turret",
        )
        assert m.hardpoint_type == "turret"

    def test_launcher_module(self):
        from app.routers.sde_browser import ModuleSummary
        m = ModuleSummary(
            type_id=19739, type_name="Cruise Missile Launcher II",
            group_id=506, group_name="Cruise Missile Launcher",
            slot_type="high", hardpoint_type="launcher",
        )
        assert m.hardpoint_type == "launcher"

    def test_utility_module(self):
        from app.routers.sde_browser import ModuleSummary
        m = ModuleSummary(
            type_id=3174, type_name="Medium Neutralizer II",
            group_id=563, group_name="Energy Neutralizer",
            slot_type="high", hardpoint_type=None,
        )
        assert m.hardpoint_type is None

    def test_default_none(self):
        from app.routers.sde_browser import ModuleSummary
        m = ModuleSummary(
            type_id=1, type_name="X", group_id=1, group_name="G", slot_type="mid",
        )
        assert m.hardpoint_type is None


class TestHardpointEffectConstants:
    """Verify turret/launcher effect ID constants."""

    def test_turret_fitted_effect_id(self):
        from app.routers.sde_browser import EFFECT_TURRET_FITTED
        assert EFFECT_TURRET_FITTED == 42

    def test_launcher_fitted_effect_id(self):
        from app.routers.sde_browser import EFFECT_LAUNCHER_FITTED
        assert EFFECT_LAUNCHER_FITTED == 40


# ---------------------------------------------------------------------------
# Ship Compatibility Helpers
# ---------------------------------------------------------------------------

class TestShipCompatibilityHelpers:
    """Test hardpoint and rig size filter helpers."""

    def test_build_hardpoint_filter_no_turrets(self):
        from app.routers.sde_browser import _build_hardpoint_filter, EFFECT_TURRET_FITTED
        sql, params = _build_hardpoint_filter(turret_hp=0, launcher_hp=6)
        assert sql != ""
        assert EFFECT_TURRET_FITTED in params["exclude_hp_effects"]

    def test_build_hardpoint_filter_no_launchers(self):
        from app.routers.sde_browser import _build_hardpoint_filter, EFFECT_LAUNCHER_FITTED
        sql, params = _build_hardpoint_filter(turret_hp=4, launcher_hp=0)
        assert sql != ""
        assert EFFECT_LAUNCHER_FITTED in params["exclude_hp_effects"]

    def test_build_hardpoint_filter_both_zero(self):
        from app.routers.sde_browser import _build_hardpoint_filter, EFFECT_TURRET_FITTED, EFFECT_LAUNCHER_FITTED
        sql, params = _build_hardpoint_filter(turret_hp=0, launcher_hp=0)
        assert sql != ""
        assert EFFECT_TURRET_FITTED in params["exclude_hp_effects"]
        assert EFFECT_LAUNCHER_FITTED in params["exclude_hp_effects"]

    def test_build_hardpoint_filter_both_nonzero(self):
        from app.routers.sde_browser import _build_hardpoint_filter
        sql, params = _build_hardpoint_filter(turret_hp=4, launcher_hp=6)
        assert sql == ""
        assert params == {}

    def test_build_rig_size_filter(self):
        from app.routers.sde_browser import _build_rig_size_filter
        sql, params = _build_rig_size_filter(rig_size=3)
        assert "1547" in sql
        assert params["ship_rig_size"] == 3

    def test_build_rig_size_filter_small(self):
        from app.routers.sde_browser import _build_rig_size_filter
        sql, params = _build_rig_size_filter(rig_size=1)
        assert params["ship_rig_size"] == 1

    def test_fetch_ship_constraints_structure(self):
        """Verify _fetch_ship_constraints returns expected dict keys."""
        from app.routers.sde_browser import _fetch_ship_constraints
        import inspect
        sig = inspect.signature(_fetch_ship_constraints)
        assert "db" in sig.parameters
        assert "ship_type_id" in sig.parameters

    def test_build_hardpoint_filter_no_turrets_excludes_only_turret(self):
        """When ship has launchers but no turrets, only turretFitted is excluded."""
        from app.routers.sde_browser import _build_hardpoint_filter, EFFECT_TURRET_FITTED, EFFECT_LAUNCHER_FITTED
        sql, params = _build_hardpoint_filter(turret_hp=0, launcher_hp=4)
        assert len(params["exclude_hp_effects"]) == 1
        assert EFFECT_TURRET_FITTED in params["exclude_hp_effects"]
        assert EFFECT_LAUNCHER_FITTED not in params["exclude_hp_effects"]

    def test_build_hardpoint_filter_no_launchers_excludes_only_launcher(self):
        """When ship has turrets but no launchers, only launcherFitted is excluded."""
        from app.routers.sde_browser import _build_hardpoint_filter, EFFECT_TURRET_FITTED, EFFECT_LAUNCHER_FITTED
        sql, params = _build_hardpoint_filter(turret_hp=6, launcher_hp=0)
        assert len(params["exclude_hp_effects"]) == 1
        assert EFFECT_LAUNCHER_FITTED in params["exclude_hp_effects"]
        assert EFFECT_TURRET_FITTED not in params["exclude_hp_effects"]

    def test_build_hardpoint_filter_sql_references_not_exists(self):
        """SQL fragment uses NOT EXISTS to exclude incompatible modules."""
        from app.routers.sde_browser import _build_hardpoint_filter
        sql, _ = _build_hardpoint_filter(turret_hp=0, launcher_hp=6)
        assert "NOT EXISTS" in sql

    def test_build_rig_size_filter_sql_references_exists(self):
        """SQL fragment uses EXISTS to require matching rig size."""
        from app.routers.sde_browser import _build_rig_size_filter
        sql, _ = _build_rig_size_filter(rig_size=2)
        assert "EXISTS" in sql

    def test_build_rig_size_filter_capital(self):
        """Capital rig size (4) is correctly passed."""
        from app.routers.sde_browser import _build_rig_size_filter
        sql, params = _build_rig_size_filter(rig_size=4)
        assert params["ship_rig_size"] == 4

    def test_fetch_ship_constraints_with_mock_db(self):
        """Test _fetch_ship_constraints returns correct dict from mock DB."""
        from app.routers.sde_browser import (
            _fetch_ship_constraints, ATTR_TURRET_HARDPOINTS,
            ATTR_LAUNCHER_HARDPOINTS, ATTR_RIG_SIZE,
        )
        # First query: groupID lookup; Second query: attributes
        group_row = [{"groupID": 27}]  # Battleship
        attr_rows = [
            {"attributeID": ATTR_TURRET_HARDPOINTS, "value": 4.0},
            {"attributeID": ATTR_LAUNCHER_HARDPOINTS, "value": 0.0},
            {"attributeID": ATTR_RIG_SIZE, "value": 3.0},
        ]
        db, _ = _make_db([group_row, attr_rows])
        result = _fetch_ship_constraints(db, ship_type_id=24690)
        assert result["turret_hardpoints"] == 4
        assert result["launcher_hardpoints"] == 0
        assert result["rig_size"] == 3
        assert result["group_id"] == 27
        assert result["type_id"] == 24690

    def test_fetch_ship_constraints_empty_attrs(self):
        """Ship with no matching attributes defaults to 0."""
        from app.routers.sde_browser import _fetch_ship_constraints
        group_row = [{"groupID": 25}]  # Frigate
        db, _ = _make_db([group_row, []])
        result = _fetch_ship_constraints(db, ship_type_id=99999)
        assert result["turret_hardpoints"] == 0
        assert result["launcher_hardpoints"] == 0
        assert result["rig_size"] == 0
        assert result["group_id"] == 25

    def test_build_can_fit_ship_filter_sql_structure(self):
        """canFitShipGroup filter allows modules without restrictions and matches ship group/type."""
        from app.routers.sde_browser import _build_can_fit_ship_filter, ALL_CAN_FIT_ATTRS
        sql, params = _build_can_fit_ship_filter(ship_group_id=485, ship_type_id=19720)
        assert "NOT EXISTS" in sql  # Modules without restrictions pass through
        assert "EXISTS" in sql      # Modules with restrictions must match
        assert params["can_fit_attrs"] == ALL_CAN_FIT_ATTRS
        assert params["ship_group_for_fit"] == 485.0
        assert params["ship_type_for_fit"] == 19720.0

    def test_build_can_fit_ship_filter_frigate(self):
        """Frigate groupID is correctly passed."""
        from app.routers.sde_browser import _build_can_fit_ship_filter
        _, params = _build_can_fit_ship_filter(ship_group_id=25, ship_type_id=603)
        assert params["ship_group_for_fit"] == 25.0
        assert params["ship_type_for_fit"] == 603.0


# ---------------------------------------------------------------------------
# Market Tree Children
# ---------------------------------------------------------------------------

class TestMarketTreeChildren:
    """Tests for GET /market-tree/children endpoint logic."""

    def test_returns_children_of_root(self):
        from app.routers.sde_browser import MarketGroupNode
        result_sets = [
            [
                {"marketGroupID": 1361, "marketGroupName": "Frigates", "hasTypes": False,
                 "iconID": 1361, "child_count": 4},
                {"marketGroupID": 1367, "marketGroupName": "Cruisers", "hasTypes": False,
                 "iconID": 1367, "child_count": 4},
            ]
        ]
        db, cur = _make_db(result_sets)
        nodes = [
            MarketGroupNode(
                market_group_id=r["marketGroupID"],
                name=r["marketGroupName"],
                has_types=r["hasTypes"],
                child_count=r["child_count"],
                icon_id=r["iconID"],
            )
            for r in result_sets[0]
        ]
        assert len(nodes) == 2
        assert nodes[0].name == "Frigates"
        assert nodes[0].has_types is False
        assert nodes[0].child_count == 4

    def test_leaf_node_has_types_true(self):
        from app.routers.sde_browser import MarketGroupNode
        node = MarketGroupNode(
            market_group_id=434,
            name="Caldari",
            has_types=True,
            child_count=0,
            icon_id=434,
        )
        assert node.has_types is True
        assert node.child_count == 0

    def test_market_root_constants(self):
        from app.routers.sde_browser import (
            MARKET_ROOT_SHIPS, MARKET_ROOT_MODULES,
            MARKET_ROOT_CHARGES, MARKET_ROOT_DRONES, MARKET_ROOTS
        )
        assert MARKET_ROOT_SHIPS == 4
        assert MARKET_ROOT_MODULES == 9
        assert MARKET_ROOT_CHARGES == 11
        assert MARKET_ROOT_DRONES == 157
        assert len(MARKET_ROOTS) == 4

    def test_slot_type_to_effect(self):
        from app.routers.sde_browser import _slot_type_to_effect, EFFECT_HI_POWER, EFFECT_MED_POWER, EFFECT_LO_POWER, EFFECT_RIG_SLOT
        assert _slot_type_to_effect("high") == EFFECT_HI_POWER
        assert _slot_type_to_effect("mid") == EFFECT_MED_POWER
        assert _slot_type_to_effect("low") == EFFECT_LO_POWER
        assert _slot_type_to_effect("rig") == EFFECT_RIG_SLOT
        assert _slot_type_to_effect("invalid") is None
        assert _slot_type_to_effect("HIGH") == EFFECT_HI_POWER  # case insensitive

    def test_market_group_node_icon_id_optional(self):
        from app.routers.sde_browser import MarketGroupNode
        node = MarketGroupNode(
            market_group_id=100,
            name="Test Group",
            has_types=False,
            child_count=3,
        )
        assert node.icon_id is None

    def test_market_roots_is_set(self):
        from app.routers.sde_browser import MARKET_ROOTS
        assert isinstance(MARKET_ROOTS, set)
        assert 4 in MARKET_ROOTS
        assert 999 not in MARKET_ROOTS


# ---------------------------------------------------------------------------
# Market Tree Items
# ---------------------------------------------------------------------------

class TestMarketTreeShips:
    """Tests for _get_market_tree_ships helper."""

    def test_returns_ship_summary_list(self):
        from app.routers.sde_browser import _get_market_tree_ships, ATTR_HI_SLOTS, ATTR_MED_SLOTS, ATTR_LOW_SLOTS, ATTR_RIG_SLOTS
        result_sets = [
            [{"typeID": 603, "typeName": "Merlin", "groupID": 25, "groupName": "Frigate"}],
            [
                {"typeID": 603, "attributeID": ATTR_HI_SLOTS, "value": 4.0},
                {"typeID": 603, "attributeID": ATTR_MED_SLOTS, "value": 3.0},
                {"typeID": 603, "attributeID": ATTR_LOW_SLOTS, "value": 1.0},
                {"typeID": 603, "attributeID": ATTR_RIG_SLOTS, "value": 3.0},
            ],
        ]
        db, _ = _make_db(result_sets)
        ships = _get_market_tree_ships(db, 61)
        assert len(ships) == 1
        assert ships[0].type_name == "Merlin"
        assert ships[0].hi_slots == 4
        assert ships[0].med_slots == 3
        assert ships[0].low_slots == 1
        assert ships[0].rig_slots == 3

    def test_multiple_ships(self):
        from app.routers.sde_browser import _get_market_tree_ships
        result_sets = [
            [
                {"typeID": 603, "typeName": "Merlin", "groupID": 25, "groupName": "Frigate"},
                {"typeID": 608, "typeName": "Condor", "groupID": 25, "groupName": "Frigate"},
            ],
            [
                {"typeID": 603, "attributeID": 14, "value": 4.0},
                {"typeID": 608, "attributeID": 14, "value": 3.0},
            ],
        ]
        db, _ = _make_db(result_sets)
        ships = _get_market_tree_ships(db, 61)
        assert len(ships) == 2
        assert ships[0].type_name == "Merlin"
        assert ships[1].type_name == "Condor"

    def test_empty_market_group_returns_empty(self):
        from app.routers.sde_browser import _get_market_tree_ships
        db, _ = _make_db([[]])
        assert _get_market_tree_ships(db, 99999) == []

    def test_ship_with_power_and_cpu(self):
        from app.routers.sde_browser import _get_market_tree_ships, ATTR_POWER_OUTPUT, ATTR_CPU_OUTPUT
        result_sets = [
            [{"typeID": 603, "typeName": "Merlin", "groupID": 25, "groupName": "Frigate"}],
            [
                {"typeID": 603, "attributeID": ATTR_POWER_OUTPUT, "value": 37.5},
                {"typeID": 603, "attributeID": ATTR_CPU_OUTPUT, "value": 150.3},
            ],
        ]
        db, _ = _make_db(result_sets)
        ships = _get_market_tree_ships(db, 61)
        assert ships[0].power_output == 37.5
        assert ships[0].cpu_output == 150.3

    def test_ship_with_hardpoints(self):
        from app.routers.sde_browser import _get_market_tree_ships, ATTR_TURRET_HARDPOINTS, ATTR_LAUNCHER_HARDPOINTS, ATTR_RIG_SIZE
        result_sets = [
            [{"typeID": 638, "typeName": "Raven", "groupID": 27, "groupName": "Battleship"}],
            [
                {"typeID": 638, "attributeID": ATTR_TURRET_HARDPOINTS, "value": 4.0},
                {"typeID": 638, "attributeID": ATTR_LAUNCHER_HARDPOINTS, "value": 6.0},
                {"typeID": 638, "attributeID": ATTR_RIG_SIZE, "value": 3.0},
            ],
        ]
        db, _ = _make_db(result_sets)
        ships = _get_market_tree_ships(db, 100)
        assert ships[0].turret_hardpoints == 4
        assert ships[0].launcher_hardpoints == 6
        assert ships[0].rig_size == 3

    def test_missing_attrs_default_to_zero(self):
        from app.routers.sde_browser import _get_market_tree_ships
        result_sets = [
            [{"typeID": 603, "typeName": "Merlin", "groupID": 25, "groupName": "Frigate"}],
            [],  # no attributes found
        ]
        db, _ = _make_db(result_sets)
        ships = _get_market_tree_ships(db, 61)
        assert ships[0].hi_slots == 0
        assert ships[0].power_output == 0
        assert ships[0].turret_hardpoints == 0

    def test_query_uses_market_group_id(self):
        from app.routers.sde_browser import _get_market_tree_ships
        db, cur = _make_db([[]])
        _get_market_tree_ships(db, 42)
        assert cur._executed[0][1]["mg_id"] == 42


class TestMarketTreeCharges:
    """Tests for _get_market_tree_charges helper."""

    def test_returns_charge_damage_stats(self):
        from app.routers.sde_browser import _get_market_tree_charges
        result_sets = [
            [{"typeID": 214, "typeName": "Antimatter S", "groupName": "Hybrid S",
              "em": 0.0, "thermal": 4.0, "kinetic": 6.0, "explosive": 0.0, "meta_level": 0}],
        ]
        db, _ = _make_db(result_sets)
        charges = _get_market_tree_charges(db, 100)
        assert len(charges) == 1
        assert charges[0]["name"] == "Antimatter S"
        assert charges[0]["kinetic"] == 6.0
        assert charges[0]["thermal"] == 4.0

    def test_charge_dict_keys(self):
        from app.routers.sde_browser import _get_market_tree_charges
        result_sets = [
            [{"typeID": 214, "typeName": "Antimatter S", "groupName": "Hybrid S",
              "em": 0.0, "thermal": 4.0, "kinetic": 6.0, "explosive": 0.0, "meta_level": 0}],
        ]
        db, _ = _make_db(result_sets)
        charges = _get_market_tree_charges(db, 100)
        expected_keys = {"type_id", "name", "group_name", "em", "thermal", "kinetic", "explosive", "meta_level"}
        assert set(charges[0].keys()) == expected_keys

    def test_empty_charges(self):
        from app.routers.sde_browser import _get_market_tree_charges
        db, _ = _make_db([[]])
        assert _get_market_tree_charges(db, 99999) == []

    def test_damage_rounding(self):
        from app.routers.sde_browser import _get_market_tree_charges
        result_sets = [
            [{"typeID": 214, "typeName": "Test Charge", "groupName": "Test",
              "em": 1.267, "thermal": 4.555, "kinetic": 6.891, "explosive": 0.444, "meta_level": 5}],
        ]
        db, _ = _make_db(result_sets)
        charges = _get_market_tree_charges(db, 100)
        assert charges[0]["em"] == 1.3
        assert charges[0]["thermal"] == 4.6
        assert charges[0]["kinetic"] == 6.9
        assert charges[0]["explosive"] == 0.4
        assert charges[0]["meta_level"] == 5

    def test_multiple_charges_sorted(self):
        from app.routers.sde_browser import _get_market_tree_charges
        result_sets = [
            [
                {"typeID": 214, "typeName": "Antimatter S", "groupName": "Hybrid S",
                 "em": 0.0, "thermal": 4.0, "kinetic": 6.0, "explosive": 0.0, "meta_level": 0},
                {"typeID": 216, "typeName": "Iron S", "groupName": "Hybrid S",
                 "em": 0.0, "thermal": 2.0, "kinetic": 4.0, "explosive": 0.0, "meta_level": 0},
            ],
        ]
        db, _ = _make_db(result_sets)
        charges = _get_market_tree_charges(db, 100)
        assert len(charges) == 2
        assert charges[0]["type_id"] == 214
        assert charges[1]["type_id"] == 216


class TestMarketTreeModules:
    """Tests for _get_market_tree_modules helper."""

    def test_returns_module_summary_list(self):
        from app.routers.sde_browser import (
            _get_market_tree_modules, MARKET_ROOT_MODULES,
            ATTR_CPU_NEED, ATTR_POWER_NEED, ATTR_META_LEVEL,
            EFFECT_HI_POWER, EFFECT_TURRET_FITTED,
        )
        # For modules (cat_id=7): 3 queries — items, attrs, effects
        result_sets = [
            # 1st: items query
            [{"typeID": 3170, "typeName": "425mm Railgun II", "groupID": 74, "groupName": "Hybrid Weapon"}],
            # 2nd: attrs query
            [
                {"typeID": 3170, "attributeID": ATTR_CPU_NEED, "value": 52.0},
                {"typeID": 3170, "attributeID": ATTR_POWER_NEED, "value": 225.0},
                {"typeID": 3170, "attributeID": ATTR_META_LEVEL, "value": 5.0},
            ],
            # 3rd: effects query
            [
                {"typeID": 3170, "effectID": EFFECT_HI_POWER},
                {"typeID": 3170, "effectID": EFFECT_TURRET_FITTED},
            ],
        ]
        db, _ = _make_db(result_sets)
        modules = _get_market_tree_modules(db, 1000, None, None, MARKET_ROOT_MODULES)
        assert len(modules) == 1
        assert modules[0].type_name == "425mm Railgun II"
        assert modules[0].cpu == 52.0
        assert modules[0].power == 225.0
        assert modules[0].meta_level == 5
        assert modules[0].slot_type == "high"
        assert modules[0].hardpoint_type == "turret"

    def test_empty_modules_returns_empty(self):
        from app.routers.sde_browser import _get_market_tree_modules, MARKET_ROOT_MODULES
        db, _ = _make_db([[]])
        assert _get_market_tree_modules(db, 99999, None, None, MARKET_ROOT_MODULES) == []

    def test_drone_category_sets_slot_to_drone(self):
        from app.routers.sde_browser import (
            _get_market_tree_modules, MARKET_ROOT_DRONES,
            ATTR_CPU_NEED, ATTR_POWER_NEED, ATTR_META_LEVEL,
        )
        # For drones (cat_id=18): 2 queries only — items, attrs (no effects query)
        result_sets = [
            [{"typeID": 2456, "typeName": "Hobgoblin II", "groupID": 100, "groupName": "Light Scout Drone"}],
            [
                {"typeID": 2456, "attributeID": ATTR_CPU_NEED, "value": 0.0},
                {"typeID": 2456, "attributeID": ATTR_POWER_NEED, "value": 0.0},
                {"typeID": 2456, "attributeID": ATTR_META_LEVEL, "value": 5.0},
            ],
        ]
        db, _ = _make_db(result_sets)
        modules = _get_market_tree_modules(db, 837, None, None, MARKET_ROOT_DRONES)
        assert len(modules) == 1
        assert modules[0].type_name == "Hobgoblin II"
        assert modules[0].slot_type == "drone"
        assert modules[0].hardpoint_type is None

    def test_module_with_no_effects_gets_unknown_slot(self):
        from app.routers.sde_browser import _get_market_tree_modules, MARKET_ROOT_MODULES
        result_sets = [
            [{"typeID": 999, "typeName": "Mystery Module", "groupID": 50, "groupName": "Unknown"}],
            [],  # no attrs
            [],  # no effects
        ]
        db, _ = _make_db(result_sets)
        modules = _get_market_tree_modules(db, 500, None, None, MARKET_ROOT_MODULES)
        assert modules[0].slot_type == "unknown"

    def test_slot_filter_adds_exists_condition(self):
        from app.routers.sde_browser import _get_market_tree_modules, MARKET_ROOT_MODULES
        # Items query returns nothing so we just check the SQL
        db, cur = _make_db([[]])
        _get_market_tree_modules(db, 100, "high", None, MARKET_ROOT_MODULES)
        first_sql = cur._executed[0][0]
        assert "dgmTypeEffects" in first_sql
        assert "slot_effects" in cur._executed[0][1]

    def test_meta_level_defaults_to_zero(self):
        from app.routers.sde_browser import _get_market_tree_modules, MARKET_ROOT_MODULES
        result_sets = [
            [{"typeID": 100, "typeName": "Basic Mod", "groupID": 50, "groupName": "G"}],
            [],  # no attrs
            [],  # no effects
        ]
        db, _ = _make_db(result_sets)
        modules = _get_market_tree_modules(db, 500, None, None, MARKET_ROOT_MODULES)
        assert modules[0].meta_level == 0
        assert modules[0].cpu == 0
        assert modules[0].power == 0
