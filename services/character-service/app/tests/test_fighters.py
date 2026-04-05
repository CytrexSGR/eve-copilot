"""Tests for fighter DPS calculations."""
import pytest
from contextlib import contextmanager
from unittest.mock import MagicMock

from app.services.fitting_stats.models import FighterInput, FighterDPSStats, OffenseStats
from app.services.fitting_stats.constants import (
    GROUP_LIGHT_FIGHTER, GROUP_HEAVY_FIGHTER, GROUP_SUPPORT_FIGHTER,
    FIGHTER_COMBAT_GROUPS,
    EFFECT_FIGHTER_ATTACK, EFFECT_FIGHTER_MISSILES, EFFECT_FIGHTER_BOMB,
    ATTR_SQUADRON_SIZE,
    ATTR_RATE_OF_FIRE, ATTR_DAMAGE_MULT,
    ATTR_EM_DAMAGE, ATTR_THERMAL_DAMAGE, ATTR_KINETIC_DAMAGE, ATTR_EXPLOSIVE_DAMAGE,
)
from app.services.fitting_stats.fighters import (
    calculate_fighter_dps,
    load_fighter_data,
    apply_ship_fighter_bonus,
)


# ---------------------------------------------------------------------------
# Task 8: FighterInput and FighterDPSStats model tests
# ---------------------------------------------------------------------------

class TestFighterInput:
    """Test FighterInput model."""

    def test_default_quantity(self):
        """Default quantity is 1."""
        f = FighterInput(type_id=40556)
        assert f.type_id == 40556
        assert f.quantity == 1

    def test_explicit_quantity(self):
        """Explicit quantity is preserved."""
        f = FighterInput(type_id=40556, quantity=3)
        assert f.quantity == 3

    def test_type_id_required(self):
        """type_id is required."""
        with pytest.raises(Exception):
            FighterInput()


class TestFighterDPSStats:
    """Test FighterDPSStats model."""

    def test_defaults(self):
        """All fields have sensible defaults."""
        s = FighterDPSStats()
        assert s.type_name == ""
        assert s.type_id == 0
        assert s.squadron_size == 0
        assert s.squadrons == 0
        assert s.dps_per_squadron == 0.0
        assert s.total_dps == 0.0
        assert s.damage_type == "unknown"

    def test_populated(self):
        """All fields can be set."""
        s = FighterDPSStats(
            type_name="Dragonfly I",
            type_id=40556,
            squadron_size=9,
            squadrons=3,
            dps_per_squadron=100.0,
            total_dps=300.0,
            damage_type="thermal",
        )
        assert s.type_name == "Dragonfly I"
        assert s.total_dps == 300.0
        assert s.damage_type == "thermal"


class TestOffenseFighterFields:
    """Test OffenseStats fighter-related fields."""

    def test_default_fighter_dps(self):
        """fighter_dps defaults to 0."""
        o = OffenseStats()
        assert o.fighter_dps == 0.0
        assert o.fighter_details is None

    def test_fighter_details_set(self):
        """fighter_details can hold a list."""
        detail = FighterDPSStats(type_name="Test", total_dps=50.0)
        o = OffenseStats(fighter_dps=50.0, fighter_details=[detail])
        assert o.fighter_dps == 50.0
        assert len(o.fighter_details) == 1


# ---------------------------------------------------------------------------
# Task 8: Fighter constants
# ---------------------------------------------------------------------------

class TestFighterConstants:
    """Test fighter group and effect constants."""

    def test_fighter_groups(self):
        assert GROUP_LIGHT_FIGHTER == 1652
        assert GROUP_HEAVY_FIGHTER == 1653
        assert GROUP_SUPPORT_FIGHTER == 1537

    def test_combat_groups_excludes_support(self):
        """Support fighters are not in combat groups."""
        assert GROUP_LIGHT_FIGHTER in FIGHTER_COMBAT_GROUPS
        assert GROUP_HEAVY_FIGHTER in FIGHTER_COMBAT_GROUPS
        assert GROUP_SUPPORT_FIGHTER not in FIGHTER_COMBAT_GROUPS

    def test_effect_ids(self):
        assert EFFECT_FIGHTER_ATTACK == 6465
        assert EFFECT_FIGHTER_MISSILES == 6431
        assert EFFECT_FIGHTER_BOMB == 6485

    def test_squadron_size_attr(self):
        assert ATTR_SQUADRON_SIZE == 2215


# ---------------------------------------------------------------------------
# Task 9: calculate_fighter_dps tests
# ---------------------------------------------------------------------------

class TestCalculateFighterDps:
    """Test fighter DPS calculation logic."""

    def _make_attrs(self, squadron_size=9, cycle_ms=4000.0, dmg_mult=1.0,
                    em=0, thermal=100, kinetic=0, explosive=0):
        """Build a fighter attrs dict."""
        return {
            ATTR_SQUADRON_SIZE: squadron_size,
            ATTR_RATE_OF_FIRE: cycle_ms,
            ATTR_DAMAGE_MULT: dmg_mult,
            ATTR_EM_DAMAGE: em,
            ATTR_THERMAL_DAMAGE: thermal,
            ATTR_KINETIC_DAMAGE: kinetic,
            ATTR_EXPLOSIVE_DAMAGE: explosive,
        }

    def test_basic_dps(self):
        """DPS = squadron_size * dmg_mult * sum(damage) / cycle_s."""
        # 9 * 1.0 * 100 / 4.0 = 225.0
        attrs = self._make_attrs(squadron_size=9, cycle_ms=4000.0, dmg_mult=1.0,
                                  thermal=100)
        result = calculate_fighter_dps(attrs, squadrons=1)
        assert result["dps_per_squadron"] == pytest.approx(225.0)
        assert result["total_dps"] == pytest.approx(225.0)
        assert result["squadron_size"] == 9

    def test_multiple_damage_types(self):
        """Sum of all damage types is used."""
        # 9 * 1.0 * (50 + 50 + 25 + 25) / 4.0 = 9 * 150 / 4 = 337.5
        attrs = self._make_attrs(squadron_size=9, cycle_ms=4000.0, dmg_mult=1.0,
                                  em=50, thermal=50, kinetic=25, explosive=25)
        result = calculate_fighter_dps(attrs, squadrons=1)
        assert result["dps_per_squadron"] == pytest.approx(337.5)

    def test_damage_multiplier(self):
        """Damage multiplier is applied."""
        # 9 * 2.0 * 100 / 4.0 = 450.0
        attrs = self._make_attrs(squadron_size=9, cycle_ms=4000.0, dmg_mult=2.0,
                                  thermal=100)
        result = calculate_fighter_dps(attrs, squadrons=1)
        assert result["dps_per_squadron"] == pytest.approx(450.0)

    def test_multiple_squadrons(self):
        """Multiple squadrons multiply total DPS."""
        attrs = self._make_attrs(squadron_size=9, cycle_ms=4000.0, dmg_mult=1.0,
                                  thermal=100)
        result = calculate_fighter_dps(attrs, squadrons=3)
        assert result["dps_per_squadron"] == pytest.approx(225.0)
        assert result["total_dps"] == pytest.approx(675.0)

    def test_zero_cycle_time(self):
        """Zero cycle time returns 0 DPS gracefully."""
        attrs = self._make_attrs(cycle_ms=0.0, thermal=100)
        result = calculate_fighter_dps(attrs, squadrons=1)
        assert result["dps_per_squadron"] == 0.0
        assert result["total_dps"] == 0.0

    def test_missing_cycle_time(self):
        """Missing cycle time attr returns 0 DPS."""
        attrs = {ATTR_SQUADRON_SIZE: 9, ATTR_DAMAGE_MULT: 1.0, ATTR_THERMAL_DAMAGE: 100}
        result = calculate_fighter_dps(attrs, squadrons=1)
        assert result["dps_per_squadron"] == 0.0

    def test_default_squadron_size(self):
        """If squadron size attr missing, default to 1."""
        attrs = {
            ATTR_RATE_OF_FIRE: 4000.0,
            ATTR_DAMAGE_MULT: 1.0,
            ATTR_THERMAL_DAMAGE: 100,
        }
        result = calculate_fighter_dps(attrs, squadrons=1)
        # 1 * 1.0 * 100 / 4.0 = 25.0
        assert result["dps_per_squadron"] == pytest.approx(25.0)
        assert result["squadron_size"] == 1

    def test_default_damage_mult(self):
        """If damage_mult attr missing, default to 1.0."""
        attrs = {
            ATTR_SQUADRON_SIZE: 9,
            ATTR_RATE_OF_FIRE: 4000.0,
            ATTR_THERMAL_DAMAGE: 100,
        }
        result = calculate_fighter_dps(attrs, squadrons=1)
        assert result["dps_per_squadron"] == pytest.approx(225.0)

    def test_primary_damage_type_thermal(self):
        """Primary damage type is the highest component."""
        attrs = self._make_attrs(em=10, thermal=100, kinetic=20, explosive=5)
        result = calculate_fighter_dps(attrs, squadrons=1)
        assert result["damage_type"] == "thermal"

    def test_primary_damage_type_em(self):
        attrs = self._make_attrs(em=200, thermal=10, kinetic=10, explosive=10)
        result = calculate_fighter_dps(attrs, squadrons=1)
        assert result["damage_type"] == "em"

    def test_primary_damage_type_kinetic(self):
        attrs = self._make_attrs(em=0, thermal=0, kinetic=150, explosive=50)
        result = calculate_fighter_dps(attrs, squadrons=1)
        assert result["damage_type"] == "kinetic"

    def test_primary_damage_type_explosive(self):
        attrs = self._make_attrs(em=10, thermal=10, kinetic=10, explosive=100)
        result = calculate_fighter_dps(attrs, squadrons=1)
        assert result["damage_type"] == "explosive"

    def test_zero_damage_returns_unknown(self):
        """No damage values gives unknown type."""
        attrs = self._make_attrs(em=0, thermal=0, kinetic=0, explosive=0)
        result = calculate_fighter_dps(attrs, squadrons=1)
        assert result["damage_type"] == "unknown"
        assert result["dps_per_squadron"] == 0.0

    def test_return_keys(self):
        """Verify all expected keys are present."""
        attrs = self._make_attrs()
        result = calculate_fighter_dps(attrs, squadrons=1)
        assert "dps_per_squadron" in result
        assert "total_dps" in result
        assert "damage_type" in result
        assert "squadron_size" in result


# ---------------------------------------------------------------------------
# Task 10: load_fighter_data with mock DB
# ---------------------------------------------------------------------------

class TestLoadFighterData:
    """Test fighter attribute loading from SDE."""

    def _make_mock_db(self, type_rows, attr_rows):
        """Create a mock DB with cursor returning type info then attributes."""
        call_count = {"n": 0}
        results = [type_rows, attr_rows]

        class FakeCursor:
            def execute(self, sql, params=None):
                pass

            def fetchall(self):
                idx = call_count["n"]
                call_count["n"] += 1
                if idx < len(results):
                    return results[idx]
                return []

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        db = MagicMock()
        db.cursor.return_value = FakeCursor()
        return db

    def test_loads_single_fighter(self):
        """Load one fighter type with attributes."""
        type_rows = [{"typeID": 40556, "typeName": "Dragonfly I", "groupID": 1652}]
        attr_rows = [
            {"typeID": 40556, "attributeID": ATTR_SQUADRON_SIZE, "value": 9.0},
            {"typeID": 40556, "attributeID": ATTR_RATE_OF_FIRE, "value": 4000.0},
            {"typeID": 40556, "attributeID": ATTR_DAMAGE_MULT, "value": 1.0},
            {"typeID": 40556, "attributeID": ATTR_THERMAL_DAMAGE, "value": 68.0},
        ]
        db = self._make_mock_db(type_rows, attr_rows)

        inputs = [{"type_id": 40556, "quantity": 2}]
        result = load_fighter_data(db, inputs)

        assert len(result) == 1
        assert result[0]["type_id"] == 40556
        assert result[0]["type_name"] == "Dragonfly I"
        assert result[0]["group_id"] == 1652
        assert result[0]["quantity"] == 2
        assert ATTR_THERMAL_DAMAGE in result[0]["attrs"]
        assert result[0]["attrs"][ATTR_THERMAL_DAMAGE] == 68.0

    def test_loads_multiple_fighters(self):
        """Load two different fighter types."""
        type_rows = [
            {"typeID": 40556, "typeName": "Dragonfly I", "groupID": 1652},
            {"typeID": 40559, "typeName": "Mantis", "groupID": 1653},
        ]
        attr_rows = [
            {"typeID": 40556, "attributeID": ATTR_RATE_OF_FIRE, "value": 4000.0},
            {"typeID": 40559, "attributeID": ATTR_RATE_OF_FIRE, "value": 6000.0},
        ]
        db = self._make_mock_db(type_rows, attr_rows)

        inputs = [
            {"type_id": 40556, "quantity": 1},
            {"type_id": 40559, "quantity": 2},
        ]
        result = load_fighter_data(db, inputs)
        assert len(result) == 2
        type_ids = {r["type_id"] for r in result}
        assert type_ids == {40556, 40559}

    def test_missing_type_skipped(self):
        """Fighter type not found in SDE is skipped."""
        type_rows = []  # no types found
        attr_rows = []
        db = self._make_mock_db(type_rows, attr_rows)

        inputs = [{"type_id": 99999, "quantity": 1}]
        result = load_fighter_data(db, inputs)
        assert len(result) == 0

    def test_empty_inputs(self):
        """Empty input list returns empty result."""
        db = self._make_mock_db([], [])
        result = load_fighter_data(db, [])
        assert result == []


# ---------------------------------------------------------------------------
# Task 12: apply_ship_fighter_bonus tests
# ---------------------------------------------------------------------------

class TestApplyShipFighterBonus:
    """Test ship fighter damage bonus application."""

    def test_1x_multiplier(self):
        """1.0 multiplier returns same DPS."""
        assert apply_ship_fighter_bonus(100.0, 1.0) == 100.0

    def test_1_25x_multiplier(self):
        """1.25x multiplier (e.g., 5% per level * 5 levels)."""
        assert apply_ship_fighter_bonus(100.0, 1.25) == 125.0

    def test_rounding(self):
        """Result is rounded to 1 decimal."""
        result = apply_ship_fighter_bonus(100.0, 1.333)
        assert result == 133.3

    def test_zero_dps(self):
        """Zero DPS stays zero."""
        assert apply_ship_fighter_bonus(0.0, 1.5) == 0.0

    def test_zero_multiplier(self):
        """Zero multiplier returns zero."""
        assert apply_ship_fighter_bonus(100.0, 0.0) == 0.0

    def test_large_multiplier(self):
        """Large multiplier for supercarrier bonuses."""
        # Supercarriers can have significant fighter bonuses
        result = apply_ship_fighter_bonus(200.0, 2.0)
        assert result == 400.0
