"""Tests for T3D Tactical Destroyer mode effect loading and application.

T3D modes (Defense/Propulsion/Sharpshooter) are virtual items in SDE group 1306
with PostDiv effects that modify ship attributes. Mode items have published=0,
so the loader must NOT filter by published=1.

TestLoadModeEffects: Tests for _load_mode_effects (Task 1).
TestApplyModeModifiers: Tests for _apply_mode_modifiers (Task 2).
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.dogma.engine import DogmaEngine
from app.services.dogma.modifier_parser import DogmaModifier
from app.tests.conftest import MultiResultCursor


# Example YAML modifierInfo for a Sharpshooter mode effect (PostDiv on scan resolution)
SAMPLE_MODIFIER_YAML = """- domain: shipID
  func: ItemModifier
  modifiedAttributeID: 564
  modifyingAttributeID: 2759
  operation: 5
"""

# YAML with multiple modifiers (e.g., mode adjusting both scan res and max velocity)
MULTI_MODIFIER_YAML = """- domain: shipID
  func: ItemModifier
  modifiedAttributeID: 564
  modifyingAttributeID: 2759
  operation: 5
- domain: shipID
  func: ItemModifier
  modifiedAttributeID: 37
  modifyingAttributeID: 2760
  operation: 5
"""


class TestLoadModeEffects:
    """Test _load_mode_effects method on DogmaEngine."""

    def _make_engine(self, cursor):
        """Create a DogmaEngine with a mock DB that returns the given cursor."""
        engine = DogmaEngine.__new__(DogmaEngine)
        mock_db = MagicMock()
        mock_db.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_db.cursor.return_value.__exit__ = MagicMock(return_value=False)
        engine.db = mock_db
        return engine

    def test_basic_mode_effects_loading(self):
        """Load a single PostDiv modifier + mode attributes for a T3D mode."""
        # First query: dgmTypeEffects + dgmEffects (mode effects)
        effects_rows = [
            {
                "typeID": 34562,
                "effectID": 6751,
                "effectName": "intrdestSharpshoterMode",
                "modifierInfo": SAMPLE_MODIFIER_YAML,
            }
        ]
        # Second query: dgmTypeAttributes (mode attributes)
        attrs_rows = [
            {"attributeID": 2759, "value": 0.75},  # scanResolutionBonus
        ]

        cursor = MultiResultCursor([effects_rows, attrs_rows])
        engine = self._make_engine(cursor)

        modifiers, mode_attrs = engine._load_mode_effects(34562)

        # Should return one DogmaModifier
        assert len(modifiers) == 1
        mod = modifiers[0]
        assert isinstance(mod, DogmaModifier)
        assert mod.domain == "shipID"
        assert mod.func == "ItemModifier"
        assert mod.modified_attr_id == 564  # scanResolution
        assert mod.modifying_attr_id == 2759
        assert mod.operation == 5  # PostDiv

        # Should return mode attributes
        assert mode_attrs == {2759: 0.75}

    def test_no_effects_returns_empty(self):
        """A mode with no effects returns empty modifiers and empty attrs."""
        cursor = MultiResultCursor([[], []])
        engine = self._make_engine(cursor)

        modifiers, mode_attrs = engine._load_mode_effects(99999)

        assert modifiers == []
        assert mode_attrs == {}

    def test_multiple_modifiers_from_single_effect(self):
        """A mode effect can contain multiple modifiers in its YAML."""
        effects_rows = [
            {
                "typeID": 34562,
                "effectID": 6751,
                "effectName": "intrdestSharpshoterMode",
                "modifierInfo": MULTI_MODIFIER_YAML,
            }
        ]
        attrs_rows = [
            {"attributeID": 2759, "value": 0.75},
            {"attributeID": 2760, "value": 1.25},
        ]

        cursor = MultiResultCursor([effects_rows, attrs_rows])
        engine = self._make_engine(cursor)

        modifiers, mode_attrs = engine._load_mode_effects(34562)

        assert len(modifiers) == 2
        # First modifier: scan resolution
        assert modifiers[0].modified_attr_id == 564
        assert modifiers[0].modifying_attr_id == 2759
        assert modifiers[0].operation == 5
        # Second modifier: max velocity
        assert modifiers[1].modified_attr_id == 37
        assert modifiers[1].modifying_attr_id == 2760
        assert modifiers[1].operation == 5

        # Both attributes loaded
        assert mode_attrs == {2759: 0.75, 2760: 1.25}

    def test_multiple_effects_combined(self):
        """Multiple separate effects on the same mode are all parsed."""
        effects_rows = [
            {
                "typeID": 34562,
                "effectID": 6751,
                "effectName": "effect1",
                "modifierInfo": SAMPLE_MODIFIER_YAML,
            },
            {
                "typeID": 34562,
                "effectID": 6752,
                "effectName": "effect2",
                "modifierInfo": """- domain: shipID
  func: ItemModifier
  modifiedAttributeID: 9
  modifyingAttributeID: 2761
  operation: 5
""",
            },
        ]
        attrs_rows = [
            {"attributeID": 2759, "value": 0.75},
            {"attributeID": 2761, "value": 1.10},
        ]

        cursor = MultiResultCursor([effects_rows, attrs_rows])
        engine = self._make_engine(cursor)

        modifiers, mode_attrs = engine._load_mode_effects(34562)

        assert len(modifiers) == 2
        modified_attrs = {m.modified_attr_id for m in modifiers}
        assert 564 in modified_attrs  # scanResolution from effect1
        assert 9 in modified_attrs    # hull HP from effect2

        assert 2759 in mode_attrs
        assert 2761 in mode_attrs

    def test_mode_attrs_coalesce_pattern(self):
        """Mode attribute values use COALESCE(valueFloat, valueInt::float)."""
        effects_rows = [
            {
                "typeID": 34562,
                "effectID": 6751,
                "effectName": "testMode",
                "modifierInfo": SAMPLE_MODIFIER_YAML,
            }
        ]
        # The value column from COALESCE should be float
        attrs_rows = [
            {"attributeID": 2759, "value": 0.85},
        ]

        cursor = MultiResultCursor([effects_rows, attrs_rows])
        engine = self._make_engine(cursor)

        modifiers, mode_attrs = engine._load_mode_effects(34562)

        assert mode_attrs[2759] == pytest.approx(0.85)

    def test_effect_with_null_modifier_info_filtered_by_sql(self):
        """Effects with NULL modifierInfo are excluded by the SQL WHERE clause.

        The SQL includes 'AND e."modifierInfo" IS NOT NULL', so the cursor
        will never return rows with null modifierInfo. We verify the method
        handles an empty effect list gracefully.
        """
        # SQL filters out nulls, so cursor returns nothing
        cursor = MultiResultCursor([[], []])
        engine = self._make_engine(cursor)

        modifiers, mode_attrs = engine._load_mode_effects(34562)

        assert modifiers == []
        assert mode_attrs == {}

    def test_return_types(self):
        """Verify the method returns (list, dict) tuple."""
        effects_rows = [
            {
                "typeID": 34562,
                "effectID": 6751,
                "effectName": "testMode",
                "modifierInfo": SAMPLE_MODIFIER_YAML,
            }
        ]
        attrs_rows = [
            {"attributeID": 2759, "value": 0.75},
        ]

        cursor = MultiResultCursor([effects_rows, attrs_rows])
        engine = self._make_engine(cursor)

        result = engine._load_mode_effects(34562)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], list)
        assert isinstance(result[1], dict)

    def test_sql_does_not_filter_by_published(self):
        """The SQL query must NOT filter by published=1.

        Mode items in SDE have published=0, so adding a published filter
        would break T3D mode loading. We verify the executed SQL does not
        contain 'published'.
        """
        cursor = MultiResultCursor([[], []])
        engine = self._make_engine(cursor)

        engine._load_mode_effects(34562)

        # Check all executed SQL statements
        for sql, params in cursor._executed:
            assert "published" not in sql.lower(), (
                "SQL must NOT filter by published (mode items have published=0)"
            )


class TestApplyModeModifiers:
    """Test _apply_mode_modifiers method on DogmaEngine.

    This method applies T3D mode PostDiv (operation 5) modifiers to ship and
    module attributes. Mode modifiers are NOT stacking penalized.

    Three modifier types:
    1. ItemModifier (domain=shipID): PostDiv directly on ship attributes
    2. LocationRequiredSkillModifier (domain=shipID, skillTypeID): PostDiv on
       modules requiring a specific skill
    3. OwnerRequiredSkillModifier (domain=charID, skillTypeID): PostDiv on
       modules by owner skill
    """

    @staticmethod
    def _make_engine():
        """Create a DogmaEngine without DB (method is pure logic, no DB)."""
        engine = DogmaEngine.__new__(DogmaEngine)
        return engine

    # ---- ItemModifier (ship attribute PostDiv) ----

    def test_item_modifier_postdiv_reduces_attribute(self):
        """PostDiv with value > 1 reduces the ship attribute (e.g., sig/1.5)."""
        engine = self._make_engine()
        ship_attrs = {564: 400.0}  # scanResolution = 400
        module_attrs = {}
        mode_modifiers = [
            DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=564, modifying_attr_id=2759,
                operation=5,
            ),
        ]
        mode_attrs = {2759: 1.5}  # divider > 1 reduces scan res
        module_groups = {}
        module_required_skills = {}

        result_ship, result_modules = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, mode_modifiers, mode_attrs,
            module_groups, module_required_skills,
        )

        # 400 / 1.5 = 266.67
        assert result_ship[564] == pytest.approx(400.0 / 1.5)

    def test_item_modifier_postdiv_increases_attribute(self):
        """PostDiv with value < 1 increases the attribute (e.g., damage/0.667)."""
        engine = self._make_engine()
        ship_attrs = {37: 300.0}  # maxVelocity = 300
        module_attrs = {}
        mode_modifiers = [
            DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=37, modifying_attr_id=2760,
                operation=5,
            ),
        ]
        mode_attrs = {2760: 0.667}  # divider < 1 increases velocity
        module_groups = {}
        module_required_skills = {}

        result_ship, result_modules = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, mode_modifiers, mode_attrs,
            module_groups, module_required_skills,
        )

        # 300 / 0.667 = ~449.78
        assert result_ship[37] == pytest.approx(300.0 / 0.667)

    def test_item_modifier_multiple_ship_attrs(self):
        """Multiple ItemModifiers apply to different ship attributes independently."""
        engine = self._make_engine()
        ship_attrs = {564: 400.0, 37: 300.0, 552: 35.0}  # scanRes, velocity, sigRadius
        module_attrs = {}
        mode_modifiers = [
            DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=564, modifying_attr_id=2759,
                operation=5,
            ),
            DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=37, modifying_attr_id=2760,
                operation=5,
            ),
            DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=552, modifying_attr_id=2761,
                operation=5,
            ),
        ]
        mode_attrs = {2759: 0.75, 2760: 1.25, 2761: 1.5}
        module_groups = {}
        module_required_skills = {}

        result_ship, result_modules = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, mode_modifiers, mode_attrs,
            module_groups, module_required_skills,
        )

        assert result_ship[564] == pytest.approx(400.0 / 0.75)
        assert result_ship[37] == pytest.approx(300.0 / 1.25)
        assert result_ship[552] == pytest.approx(35.0 / 1.5)

    def test_item_modifier_skips_missing_ship_attr(self):
        """If the ship does not have the target attribute, the modifier is skipped."""
        engine = self._make_engine()
        ship_attrs = {37: 300.0}  # only velocity, no scanRes
        module_attrs = {}
        mode_modifiers = [
            DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=564, modifying_attr_id=2759,  # targets scanRes
                operation=5,
            ),
        ]
        mode_attrs = {2759: 0.75}
        module_groups = {}
        module_required_skills = {}

        result_ship, result_modules = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, mode_modifiers, mode_attrs,
            module_groups, module_required_skills,
        )

        # Ship attrs unchanged (564 was never present)
        assert 564 not in result_ship
        assert result_ship[37] == 300.0

    def test_item_modifier_skips_missing_mode_attr(self):
        """If mode_attrs lacks the modifying attribute, the modifier is skipped."""
        engine = self._make_engine()
        ship_attrs = {564: 400.0}
        module_attrs = {}
        mode_modifiers = [
            DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=564, modifying_attr_id=9999,  # not in mode_attrs
                operation=5,
            ),
        ]
        mode_attrs = {2759: 0.75}  # does not contain 9999
        module_groups = {}
        module_required_skills = {}

        result_ship, result_modules = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, mode_modifiers, mode_attrs,
            module_groups, module_required_skills,
        )

        # Ship attrs unchanged (modifier source not found)
        assert result_ship[564] == 400.0

    # ---- LocationRequiredSkillModifier (module attrs by skill) ----

    def test_location_skill_modifier_applies_to_matching_modules(self):
        """LocationRequiredSkillModifier divides module attrs if module requires the skill."""
        engine = self._make_engine()
        ship_attrs = {564: 400.0}
        # Two turrets: 3170 (requires Gunnery 3300) and 3171 (requires Gunnery 3300)
        module_attrs = {
            3170: {64: 5.0},   # damageMultiplier = 5.0
            3171: {64: 4.5},   # damageMultiplier = 4.5
        }
        mode_modifiers = [
            DogmaModifier(
                domain="shipID", func="LocationRequiredSkillModifier",
                modified_attr_id=64, modifying_attr_id=2762,
                operation=5, skill_type_id=3300,  # Gunnery
            ),
        ]
        mode_attrs = {2762: 0.8}  # divider < 1 increases damage
        module_groups = {3170: 55, 3171: 55}
        module_required_skills = {3170: {3300}, 3171: {3300}}

        result_ship, result_modules = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, mode_modifiers, mode_attrs,
            module_groups, module_required_skills,
        )

        # Both modules have Gunnery skill → both get divided
        assert result_modules[3170][64] == pytest.approx(5.0 / 0.8)
        assert result_modules[3171][64] == pytest.approx(4.5 / 0.8)
        # Ship unchanged
        assert result_ship[564] == 400.0

    def test_location_skill_modifier_skips_non_matching_modules(self):
        """LocationRequiredSkillModifier does not affect modules lacking the skill."""
        engine = self._make_engine()
        ship_attrs = {}
        module_attrs = {
            3170: {64: 5.0},   # turret (requires Gunnery 3300)
            2000: {64: 3.0},   # drone (requires Drones 3436, not Gunnery)
        }
        mode_modifiers = [
            DogmaModifier(
                domain="shipID", func="LocationRequiredSkillModifier",
                modified_attr_id=64, modifying_attr_id=2762,
                operation=5, skill_type_id=3300,  # Gunnery
            ),
        ]
        mode_attrs = {2762: 0.8}
        module_groups = {3170: 55, 2000: 100}
        module_required_skills = {3170: {3300}, 2000: {3436}}  # drone has Drones, not Gunnery

        result_ship, result_modules = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, mode_modifiers, mode_attrs,
            module_groups, module_required_skills,
        )

        # Turret gets the modifier (has Gunnery)
        assert result_modules[3170][64] == pytest.approx(5.0 / 0.8)
        # Drone is unchanged (no Gunnery skill)
        assert result_modules[2000][64] == 3.0

    def test_location_skill_modifier_skips_missing_module_attr(self):
        """LocationRequiredSkillModifier skips if module lacks target attribute."""
        engine = self._make_engine()
        ship_attrs = {}
        module_attrs = {
            3170: {51: 100.0},  # has tracking (51), NOT damageMultiplier (64)
        }
        mode_modifiers = [
            DogmaModifier(
                domain="shipID", func="LocationRequiredSkillModifier",
                modified_attr_id=64, modifying_attr_id=2762,
                operation=5, skill_type_id=3300,
            ),
        ]
        mode_attrs = {2762: 0.8}
        module_groups = {3170: 55}
        module_required_skills = {3170: {3300}}

        result_ship, result_modules = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, mode_modifiers, mode_attrs,
            module_groups, module_required_skills,
        )

        # Module attrs unchanged (64 not present)
        assert result_modules[3170] == {51: 100.0}

    # ---- OwnerRequiredSkillModifier (module attrs by owner skill) ----

    def test_owner_skill_modifier_applies_to_matching_modules(self):
        """OwnerRequiredSkillModifier divides module attrs for owner-skill matching."""
        engine = self._make_engine()
        ship_attrs = {}
        module_attrs = {
            5000: {654: 8000.0},  # missile velocity
        }
        mode_modifiers = [
            DogmaModifier(
                domain="charID", func="OwnerRequiredSkillModifier",
                modified_attr_id=654, modifying_attr_id=2763,
                operation=5, skill_type_id=3319,  # Missile Launcher Operation
            ),
        ]
        mode_attrs = {2763: 0.9}
        module_groups = {5000: 510}
        module_required_skills = {5000: {3319}}

        result_ship, result_modules = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, mode_modifiers, mode_attrs,
            module_groups, module_required_skills,
        )

        assert result_modules[5000][654] == pytest.approx(8000.0 / 0.9)

    def test_owner_skill_modifier_skips_non_matching_modules(self):
        """OwnerRequiredSkillModifier skips modules that don't require the skill."""
        engine = self._make_engine()
        ship_attrs = {}
        module_attrs = {
            5000: {654: 8000.0},  # requires MLO
            5001: {654: 6000.0},  # requires Gunnery, not MLO
        }
        mode_modifiers = [
            DogmaModifier(
                domain="charID", func="OwnerRequiredSkillModifier",
                modified_attr_id=654, modifying_attr_id=2763,
                operation=5, skill_type_id=3319,
            ),
        ]
        mode_attrs = {2763: 0.9}
        module_groups = {5000: 510, 5001: 55}
        module_required_skills = {5000: {3319}, 5001: {3300}}

        result_ship, result_modules = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, mode_modifiers, mode_attrs,
            module_groups, module_required_skills,
        )

        assert result_modules[5000][654] == pytest.approx(8000.0 / 0.9)
        assert result_modules[5001][654] == 6000.0  # unchanged

    # ---- Mixed modifier types ----

    def test_mixed_modifier_types(self):
        """Ship + module modifiers from different types all apply correctly."""
        engine = self._make_engine()
        ship_attrs = {552: 50.0, 37: 300.0}  # sigRadius, velocity
        module_attrs = {
            3170: {64: 5.0},   # turret damage
            5000: {654: 8000.0},  # missile velocity
        }
        mode_modifiers = [
            # ItemModifier: sig radius on ship
            DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=552, modifying_attr_id=2761,
                operation=5,
            ),
            # ItemModifier: velocity on ship
            DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=37, modifying_attr_id=2760,
                operation=5,
            ),
            # LocationRequiredSkillModifier: turret damage
            DogmaModifier(
                domain="shipID", func="LocationRequiredSkillModifier",
                modified_attr_id=64, modifying_attr_id=2762,
                operation=5, skill_type_id=3300,
            ),
            # OwnerRequiredSkillModifier: missile velocity
            DogmaModifier(
                domain="charID", func="OwnerRequiredSkillModifier",
                modified_attr_id=654, modifying_attr_id=2763,
                operation=5, skill_type_id=3319,
            ),
        ]
        mode_attrs = {2761: 1.5, 2760: 0.8, 2762: 0.75, 2763: 1.1}
        module_groups = {3170: 55, 5000: 510}
        module_required_skills = {3170: {3300}, 5000: {3319}}

        result_ship, result_modules = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, mode_modifiers, mode_attrs,
            module_groups, module_required_skills,
        )

        # Ship attrs
        assert result_ship[552] == pytest.approx(50.0 / 1.5)
        assert result_ship[37] == pytest.approx(300.0 / 0.8)
        # Module attrs
        assert result_modules[3170][64] == pytest.approx(5.0 / 0.75)
        assert result_modules[5000][654] == pytest.approx(8000.0 / 1.1)

    # ---- Not stacking penalized ----

    def test_multiple_modifiers_same_attr_not_stacking_penalized(self):
        """Multiple PostDiv modifiers on the same ship attr apply independently (no stacking penalty)."""
        engine = self._make_engine()
        ship_attrs = {552: 100.0}  # sigRadius
        module_attrs = {}
        mode_modifiers = [
            DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=552, modifying_attr_id=2761,
                operation=5,
            ),
            DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=552, modifying_attr_id=2762,
                operation=5,
            ),
        ]
        mode_attrs = {2761: 1.5, 2762: 1.2}
        module_groups = {}
        module_required_skills = {}

        result_ship, result_modules = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, mode_modifiers, mode_attrs,
            module_groups, module_required_skills,
        )

        # Each applies independently: 100 / 1.5 / 1.2 = 55.556
        assert result_ship[552] == pytest.approx(100.0 / 1.5 / 1.2)

    # ---- Edge cases ----

    def test_empty_modifiers_returns_unchanged(self):
        """Empty modifier list returns copies of original attrs unchanged."""
        engine = self._make_engine()
        ship_attrs = {564: 400.0, 37: 300.0}
        module_attrs = {3170: {64: 5.0}}

        result_ship, result_modules = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, [], {},
            {}, {},
        )

        assert result_ship == {564: 400.0, 37: 300.0}
        assert result_modules == {3170: {64: 5.0}}

    def test_does_not_mutate_input_dicts(self):
        """Method returns new dicts, does not modify originals."""
        engine = self._make_engine()
        ship_attrs = {564: 400.0}
        module_attrs = {3170: {64: 5.0}}
        mode_modifiers = [
            DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=564, modifying_attr_id=2759,
                operation=5,
            ),
            DogmaModifier(
                domain="shipID", func="LocationRequiredSkillModifier",
                modified_attr_id=64, modifying_attr_id=2762,
                operation=5, skill_type_id=3300,
            ),
        ]
        mode_attrs = {2759: 0.75, 2762: 0.8}
        module_groups = {3170: 55}
        module_required_skills = {3170: {3300}}

        result_ship, result_modules = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, mode_modifiers, mode_attrs,
            module_groups, module_required_skills,
        )

        # Originals must be untouched
        assert ship_attrs[564] == 400.0
        assert module_attrs[3170][64] == 5.0
        # Results are different objects
        assert result_ship is not ship_attrs
        assert result_modules[3170] is not module_attrs[3170]

    def test_returns_tuple_of_two_dicts(self):
        """Return type is a tuple of (dict, dict)."""
        engine = self._make_engine()
        result = engine._apply_mode_modifiers(
            {564: 400.0}, {3170: {64: 5.0}}, [], {},
            {}, {},
        )

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], dict)
        assert isinstance(result[1], dict)

    def test_postdiv_by_one_no_change(self):
        """PostDiv by 1.0 leaves the attribute unchanged."""
        engine = self._make_engine()
        ship_attrs = {552: 50.0}
        mode_modifiers = [
            DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=552, modifying_attr_id=2761,
                operation=5,
            ),
        ]
        mode_attrs = {2761: 1.0}

        result_ship, _ = engine._apply_mode_modifiers(
            ship_attrs, {}, mode_modifiers, mode_attrs, {}, {},
        )

        assert result_ship[552] == pytest.approx(50.0)

    def test_location_skill_modifier_no_skill_type_id_skipped(self):
        """LocationRequiredSkillModifier with skill_type_id=None is skipped."""
        engine = self._make_engine()
        ship_attrs = {}
        module_attrs = {3170: {64: 5.0}}
        mode_modifiers = [
            DogmaModifier(
                domain="shipID", func="LocationRequiredSkillModifier",
                modified_attr_id=64, modifying_attr_id=2762,
                operation=5, skill_type_id=None,  # No skill type
            ),
        ]
        mode_attrs = {2762: 0.8}
        module_groups = {3170: 55}
        module_required_skills = {3170: {3300}}

        result_ship, result_modules = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, mode_modifiers, mode_attrs,
            module_groups, module_required_skills,
        )

        # Module should be unchanged (no skill_type_id)
        assert result_modules[3170][64] == 5.0

    def test_owner_skill_modifier_no_skill_type_id_skipped(self):
        """OwnerRequiredSkillModifier with skill_type_id=None is skipped."""
        engine = self._make_engine()
        ship_attrs = {}
        module_attrs = {5000: {654: 8000.0}}
        mode_modifiers = [
            DogmaModifier(
                domain="charID", func="OwnerRequiredSkillModifier",
                modified_attr_id=654, modifying_attr_id=2763,
                operation=5, skill_type_id=None,
            ),
        ]
        mode_attrs = {2763: 0.9}
        module_groups = {5000: 510}
        module_required_skills = {5000: {3319}}

        result_ship, result_modules = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, mode_modifiers, mode_attrs,
            module_groups, module_required_skills,
        )

        assert result_modules[5000][654] == 8000.0

    def test_defense_mode_scenario(self):
        """Defense mode: reduces sig radius (div > 1), increases resists (div < 1 on resist attrs)."""
        engine = self._make_engine()
        # Defense mode: sig radius smaller, ship tougher (resist attrs are raw 0-1 values)
        ship_attrs = {
            552: 70.0,     # sigRadius
            271: 0.5,      # shieldEmDamageResonance (50% pass-through = 50% resist)
            272: 0.6,      # shieldExplosiveDamageResonance
        }
        module_attrs = {}
        mode_modifiers = [
            # Sig radius: divide by 1.33 (sig gets smaller)
            DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=552, modifying_attr_id=2770,
                operation=5,
            ),
            # Shield EM resonance: divide by 0.85 (resonance goes up = more pass-through...
            # or divide by >1 for less pass-through = better resist)
            DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=271, modifying_attr_id=2771,
                operation=5,
            ),
        ]
        mode_attrs = {2770: 1.33, 2771: 0.85}
        module_groups = {}
        module_required_skills = {}

        result_ship, _ = engine._apply_mode_modifiers(
            ship_attrs, module_attrs, mode_modifiers, mode_attrs,
            module_groups, module_required_skills,
        )

        assert result_ship[552] == pytest.approx(70.0 / 1.33)
        assert result_ship[271] == pytest.approx(0.5 / 0.85)
        # Shield explosive unchanged (no modifier for it)
        assert result_ship[272] == 0.6


class TestPipelineIntegration:
    """Test Task 3: mode_type_id integrated into pipeline and API models."""

    def test_calculate_modified_attributes_accepts_mode_type_id(self):
        """calculate_modified_attributes signature includes mode_type_id parameter."""
        import inspect
        sig = inspect.signature(DogmaEngine.calculate_modified_attributes)
        params = list(sig.parameters.keys())
        assert "mode_type_id" in params, (
            "calculate_modified_attributes must accept mode_type_id parameter"
        )

    def test_mode_type_id_defaults_to_none(self):
        """mode_type_id parameter defaults to None."""
        import inspect
        sig = inspect.signature(DogmaEngine.calculate_modified_attributes)
        param = sig.parameters["mode_type_id"]
        assert param.default is None

    def test_fitting_stats_request_accepts_mode_type_id(self):
        """FittingStatsRequest model accepts mode_type_id field."""
        from app.services.fitting_stats.models import FittingStatsRequest
        req = FittingStatsRequest(
            ship_type_id=34317,
            items=[],
            mode_type_id=34562,
        )
        assert req.mode_type_id == 34562

    def test_fitting_stats_request_mode_type_id_defaults_none(self):
        """FittingStatsRequest.mode_type_id defaults to None."""
        from app.services.fitting_stats.models import FittingStatsRequest
        req = FittingStatsRequest(
            ship_type_id=34317,
            items=[],
        )
        assert req.mode_type_id is None

    def test_fitting_stats_response_has_mode_field(self):
        """FittingStatsResponse model has an optional mode field."""
        from app.services.fitting_stats.models import FittingStatsResponse
        import inspect
        fields = FittingStatsResponse.model_fields
        assert "mode" in fields, "FittingStatsResponse must have a 'mode' field"

    def test_fitting_stats_response_mode_defaults_none(self):
        """FittingStatsResponse.mode defaults to None."""
        from app.services.fitting_stats.models import (
            FittingStatsResponse, SlotUsage, ResourceUsage, OffenseStats,
            DefenseStats, CapacitorStats, NavigationStats, TargetingStats,
        )
        resp = FittingStatsResponse(
            ship={"type_id": 34317, "name": "Confessor", "group_name": "Tactical Destroyer"},
            slots=SlotUsage(),
            resources=ResourceUsage(),
            offense=OffenseStats(),
            defense=DefenseStats(),
            capacitor=CapacitorStats(),
            navigation=NavigationStats(),
            targeting=TargetingStats(),
        )
        assert resp.mode is None

    def test_fitting_stats_response_mode_with_value(self):
        """FittingStatsResponse.mode can be set to a mode name string."""
        from app.services.fitting_stats.models import (
            FittingStatsResponse, SlotUsage, ResourceUsage, OffenseStats,
            DefenseStats, CapacitorStats, NavigationStats, TargetingStats,
        )
        resp = FittingStatsResponse(
            ship={"type_id": 34317, "name": "Confessor", "group_name": "Tactical Destroyer"},
            slots=SlotUsage(),
            resources=ResourceUsage(),
            offense=OffenseStats(),
            defense=DefenseStats(),
            capacitor=CapacitorStats(),
            navigation=NavigationStats(),
            targeting=TargetingStats(),
            mode="Confessor Defense Mode",
        )
        assert resp.mode == "Confessor Defense Mode"


class TestModesEndpoint:
    """Test Task 4: T3D mode listing endpoint in sde_browser.py."""

    def _make_mock_app(self, cursor):
        """Create a mock FastAPI Request with a DB that returns the given cursor."""
        mock_db = MagicMock()
        mock_db.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        mock_db.cursor.return_value.__exit__ = MagicMock(return_value=False)

        mock_request = MagicMock()
        mock_request.app.state.db = mock_db
        return mock_request

    def test_t3d_ship_returns_modes(self):
        """Confessor (group 1305) returns 3 modes from group 1306."""
        from app.routers.sde_browser import get_ship_modes

        # First query: ship info (Confessor, group 1305)
        ship_row = [{"typeName": "Confessor", "groupID": 1305}]
        # Second query: mode items matching "Confessor%"
        mode_rows = [
            {"type_id": 34562, "name": "Confessor Defense Mode"},
            {"type_id": 34563, "name": "Confessor Propulsion Mode"},
            {"type_id": 34564, "name": "Confessor Sharpshooter Mode"},
        ]

        cursor = MultiResultCursor([ship_row, mode_rows])
        request = self._make_mock_app(cursor)

        result = get_ship_modes(request, ship_type_id=34317)

        assert len(result) == 3
        names = [r["name"] for r in result]
        assert "Confessor Defense Mode" in names
        assert "Confessor Propulsion Mode" in names
        assert "Confessor Sharpshooter Mode" in names

    def test_non_t3d_ship_returns_empty(self):
        """A non-T3D ship (e.g., Rifter, group != 1305) returns empty list."""
        from app.routers.sde_browser import get_ship_modes

        # Ship is a Rifter (group 25 = Frigate, not 1305)
        ship_row = [{"typeName": "Rifter", "groupID": 25}]

        cursor = MultiResultCursor([ship_row])
        request = self._make_mock_app(cursor)

        result = get_ship_modes(request, ship_type_id=587)

        assert result == []

    def test_unknown_ship_returns_empty(self):
        """An unknown ship type ID returns empty list."""
        from app.routers.sde_browser import get_ship_modes

        # No ship found
        cursor = MultiResultCursor([[]])
        request = self._make_mock_app(cursor)

        result = get_ship_modes(request, ship_type_id=99999)

        assert result == []

    def test_modes_query_uses_ship_name_pattern(self):
        """Mode query uses LIKE with ship name prefix pattern."""
        from app.routers.sde_browser import get_ship_modes

        ship_row = [{"typeName": "Jackdaw", "groupID": 1305}]
        mode_rows = [
            {"type_id": 35674, "name": "Jackdaw Defense Mode"},
            {"type_id": 35675, "name": "Jackdaw Propulsion Mode"},
            {"type_id": 35676, "name": "Jackdaw Sharpshooter Mode"},
        ]

        cursor = MultiResultCursor([ship_row, mode_rows])
        request = self._make_mock_app(cursor)

        result = get_ship_modes(request, ship_type_id=37135)

        assert len(result) == 3
        # Verify the second query used a LIKE pattern with "Jackdaw%"
        second_sql, second_params = cursor._executed[1]
        assert "LIKE" in second_sql
        assert second_params["pattern"] == "Jackdaw%"
