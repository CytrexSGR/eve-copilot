import pytest
from unittest.mock import MagicMock
from app.services.dogma.engine import DogmaEngine
from app.services.dogma.modifier_parser import DogmaModifier


class TestDogmaEngineApplyModifiers:
    """Test modifier application logic with pre-loaded data (no DB)."""

    def test_item_modifier_add(self):
        """Shield Extender II adds 400 shield HP to ship."""
        engine = DogmaEngine.__new__(DogmaEngine)  # skip __init__
        # Ship base attributes
        ship_attrs = {263: 2000.0}  # shieldCapacity = 2000
        # Module attributes (type_id -> {attr_id -> value})
        module_attrs = {3831: {72: 400.0}}  # shieldCapacityBonus = 400
        # Modifiers: LSE II adds shieldCapacityBonus to ship's shieldCapacity
        modifiers = [(3831, DogmaModifier(
            domain="shipID", func="ItemModifier",
            modified_attr_id=263, modifying_attr_id=72, operation=2,
        ))]

        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        assert result[263] == pytest.approx(2400.0)

    def test_item_modifier_add_multiple(self):
        """Two shield extenders add HP additively."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {263: 2000.0}
        module_attrs = {3831: {72: 400.0}}
        # Two instances of same module (both flagged separately)
        modifiers = [
            (3831, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=263, modifying_attr_id=72, operation=2)),
            (3831, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=263, modifying_attr_id=72, operation=2)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        assert result[263] == pytest.approx(2800.0)

    def test_post_mul_with_stacking(self):
        """Two Gyrostabilizer IIs multiply damage (stacking penalized)."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {}
        # Gyrostab II has damageMultiplier = 1.1 (10% bonus)
        module_attrs = {
            519: {64: 1.1},
        }
        ship_attrs[64] = 1.0  # base damageMultiplier
        modifiers = [
            (519, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=64, modifying_attr_id=64, operation=4)),
            (519, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=64, modifying_attr_id=64, operation=4)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # 1.0 * 1.1 * (1 + 0.1*0.869) = 1.0 * 1.1 * 1.0869 ~ 1.1956
        assert result[64] == pytest.approx(1.1956, abs=0.01)

    def test_post_percent_with_stacking(self):
        """Nanofiber Internal Structure (-15% agility via PostPercent)."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {70: 0.3}  # agility = 0.3
        # Nanofiber has agilityBonus = -15.0 (percent)
        module_attrs = {2603: {-1: -15.0}}
        modifiers = [
            (2603, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=70, modifying_attr_id=-1, operation=6)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # 0.3 * (1 + (-15)/100) = 0.3 * 0.85 = 0.255
        assert result[70] == pytest.approx(0.255, abs=0.001)

    def test_operation_ordering(self):
        """Op 2 (add) applies before op 4 (multiply)."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {263: 1000.0}
        module_attrs = {
            1: {72: 500.0},   # adds 500 (op 2)
            2: {73: 1.5},     # multiplies by 1.5 (op 4)
        }
        modifiers = [
            (2, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=263, modifying_attr_id=73, operation=4)),
            (1, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=263, modifying_attr_id=72, operation=2)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # (1000 + 500) * 1.5 = 2250
        assert result[263] == pytest.approx(2250.0, abs=1)

    def test_unaffected_attrs_unchanged(self):
        """Attributes not targeted by modifiers remain at base value."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {263: 2000.0, 37: 300.0}  # shield + velocity
        module_attrs = {3831: {72: 400.0}}
        modifiers = [
            (3831, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=263, modifying_attr_id=72, operation=2)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        assert result[37] == 300.0  # velocity unchanged

    def test_location_group_modifier(self):
        """Gyrostab modifies damageMultiplier on all Projectile Turret items."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {}
        # Two fitted turrets (type 2961=280mm, type 2969=650mm), both group 55
        module_attrs = {
            2961: {64: 2.475},   # base damageMultiplier of turret 1
            2969: {64: 3.3},     # base damageMultiplier of turret 2
            519: {64: 1.1},      # Gyrostab II modifying value
        }
        # Module group mapping: type_id -> groupID
        module_groups = {2961: 55, 2969: 55, 519: 302}

        modifiers = [
            (519, DogmaModifier(domain="shipID", func="LocationGroupModifier",
                modified_attr_id=64, modifying_attr_id=64, operation=4,
                group_id=55)),
        ]
        result_modules = engine._apply_location_modifiers(
            module_attrs, modifiers, module_groups
        )
        # Both turrets get 1.1x multiplier
        assert result_modules[2961][64] == pytest.approx(2.475 * 1.1, abs=0.01)
        assert result_modules[2969][64] == pytest.approx(3.3 * 1.1, abs=0.01)


class TestDamageControlFix:
    """Test that Damage Control resist modifiers use PostMul instead of PreAssign."""

    def test_dc_resist_multiplied_not_replaced(self):
        """DC II shield resist (0.875) should multiply ship base (0.8), not replace it.

        Vexor shield thermal: base=0.8, DC=0.875
        - WRONG (old): 0.875 (replaces base) → 12.5% resist
        - CORRECT: 0.8 * 0.875 = 0.7 → 30% resist
        """
        engine = DogmaEngine.__new__(DogmaEngine)
        # Vexor-like ship: shield thermal resist = 0.8
        ship_attrs = {274: 0.8}  # ATTR_SHIELD_THERMAL_RESIST
        # DC II: shieldThermalDamageResonance = 0.875
        module_attrs = {2048: {274: 0.875}}

        # Modifier with operation=4 (PostMul, after our fix)
        modifiers = [
            (2048, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=274, modifying_attr_id=274, operation=4)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # 0.8 * 0.875 = 0.7
        assert result[274] == pytest.approx(0.7, abs=0.001)

    def test_dc_all_shield_resists_multiplicative(self):
        """DC II should multiply all 4 shield resists with ship base values."""
        engine = DogmaEngine.__new__(DogmaEngine)
        # Vexor shield resists: EM=1.0, Th=0.8, Ki=0.6, Ex=0.5
        ship_attrs = {271: 1.0, 274: 0.8, 273: 0.6, 272: 0.5}
        # DC II shield values: all 0.875
        module_attrs = {2048: {271: 0.875, 274: 0.875, 273: 0.875, 272: 0.875}}

        modifiers = [
            (2048, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=271, modifying_attr_id=271, operation=4)),
            (2048, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=274, modifying_attr_id=274, operation=4)),
            (2048, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=273, modifying_attr_id=273, operation=4)),
            (2048, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=272, modifying_attr_id=272, operation=4)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # EM: 1.0 * 0.875 = 0.875 → 12.5% resist
        assert result[271] == pytest.approx(0.875, abs=0.001)
        # Th: 0.8 * 0.875 = 0.70 → 30% resist
        assert result[274] == pytest.approx(0.70, abs=0.001)
        # Ki: 0.6 * 0.875 = 0.525 → 47.5% resist
        assert result[273] == pytest.approx(0.525, abs=0.001)
        # Ex: 0.5 * 0.875 = 0.4375 → 56.25% resist
        assert result[272] == pytest.approx(0.4375, abs=0.001)

    def test_dc_armor_resists_multiplicative(self):
        """DC II armor resists should also multiply."""
        engine = DogmaEngine.__new__(DogmaEngine)
        # Vexor armor: EM=0.5, Th=0.65, Ki=0.65, Ex=0.9
        ship_attrs = {267: 0.5, 270: 0.65, 269: 0.65, 268: 0.9}
        # DC II armor: all 0.85
        module_attrs = {2048: {267: 0.85, 270: 0.85, 269: 0.85, 268: 0.85}}

        modifiers = [
            (2048, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=267, modifying_attr_id=267, operation=4)),
            (2048, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=270, modifying_attr_id=270, operation=4)),
            (2048, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=269, modifying_attr_id=269, operation=4)),
            (2048, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=268, modifying_attr_id=268, operation=4)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # EM: 0.5 * 0.85 = 0.425
        assert result[267] == pytest.approx(0.425, abs=0.001)
        # Th: 0.65 * 0.85 = 0.5525
        assert result[270] == pytest.approx(0.5525, abs=0.001)

    def test_resist_attr_ids_set_complete(self):
        """Verify RESIST_ATTR_IDS contains all resist attributes."""
        from app.services.dogma.engine import DogmaEngine
        resists = DogmaEngine.RESIST_ATTR_IDS
        # Shield: EM=271, Exp=272, Ki=273, Th=274
        assert 271 in resists
        assert 272 in resists
        assert 273 in resists
        assert 274 in resists
        # Armor: EM=267, Exp=268, Ki=269, Th=270
        assert 267 in resists
        assert 268 in resists
        assert 269 in resists
        assert 270 in resists
        # Hull: Ki=109, Th=110, Exp=111, EM=113
        assert 109 in resists
        assert 110 in resists
        assert 111 in resists
        assert 113 in resists


class TestOwnerRequiredSkillModifier:
    """Test OwnerRequiredSkillModifier (DDA bonus on drones)."""

    def test_dda_bonus_on_matching_drone(self):
        """DDA II (+23.8%) applies to drone requiring skill 3436 (Drones)."""
        engine = DogmaEngine.__new__(DogmaEngine)
        # Drone attrs: damageMultiplier = 1.92 (Ogre II)
        # DDA attrs: damageBonusPercentage = 23.8
        module_attrs = {
            2446: {64: 1.92},     # Ogre II damageMultiplier
            33844: {1255: 23.8},  # DDA II damage bonus
        }
        base_module_attrs = dict(module_attrs)

        # DDA modifier: +23.8% on damageMultiplier for entities requiring skill 3436
        modifiers = [
            (33844, DogmaModifier(domain="charID", func="OwnerRequiredSkillModifier",
                modified_attr_id=64, modifying_attr_id=1255, operation=6,
                skill_type_id=3436)),
        ]
        # Ogre II requires skill 3436 (Drones)
        module_required_skills = {
            2446: {12486, 3436},   # Heavy Drone Op + Drones
            33844: {3318, 3436},   # Drone Interfacing + Drones
        }

        result = engine._apply_owner_skill_modifiers(
            module_attrs, base_module_attrs, modifiers, module_required_skills
        )
        # Ogre: 1.92 * (1 + 23.8/100) = 1.92 * 1.238 = 2.377
        assert result[2446][64] == pytest.approx(2.377, abs=0.01)

    def test_dda_does_not_affect_non_drone_modules(self):
        """DDA bonus should NOT apply to modules that don't require Drones skill."""
        engine = DogmaEngine.__new__(DogmaEngine)
        module_attrs = {
            3170: {64: 2.5},     # Turret (no Drones skill required)
            33844: {1255: 23.8}, # DDA II
        }
        base_module_attrs = dict(module_attrs)
        modifiers = [
            (33844, DogmaModifier(domain="charID", func="OwnerRequiredSkillModifier",
                modified_attr_id=64, modifying_attr_id=1255, operation=6,
                skill_type_id=3436)),
        ]
        module_required_skills = {
            3170: {3300},   # Turret requires Gunnery, not Drones
            33844: {3318, 3436},
        }

        result = engine._apply_owner_skill_modifiers(
            module_attrs, base_module_attrs, modifiers, module_required_skills
        )
        assert result[3170][64] == 2.5  # Unchanged

    def test_two_ddas_stack_penalized(self):
        """Two DDAs apply with stacking penalty."""
        engine = DogmaEngine.__new__(DogmaEngine)
        module_attrs = {
            2446: {64: 1.92},     # Ogre II
            33844: {1255: 23.8},  # DDA II
        }
        base_module_attrs = dict(module_attrs)
        # Two DDA instances
        modifiers = [
            (33844, DogmaModifier(domain="charID", func="OwnerRequiredSkillModifier",
                modified_attr_id=64, modifying_attr_id=1255, operation=6,
                skill_type_id=3436)),
            (33844, DogmaModifier(domain="charID", func="OwnerRequiredSkillModifier",
                modified_attr_id=64, modifying_attr_id=1255, operation=6,
                skill_type_id=3436)),
        ]
        module_required_skills = {
            2446: {12486, 3436},
            33844: {3318, 3436},
        }

        result = engine._apply_owner_skill_modifiers(
            module_attrs, base_module_attrs, modifiers, module_required_skills
        )
        # Two 23.8% bonuses with stacking: first = 23.8%, second penalized
        # Should be > 1.92 * 1.238 but < 1.92 * 1.238 * 1.238
        single_bonus = 1.92 * 1.238
        double_bonus = 1.92 * 1.238 * 1.238
        assert result[2446][64] > single_bonus
        assert result[2446][64] < double_bonus

    def test_no_required_skills_no_bonus(self):
        """Module with no required skills info gets no bonus."""
        engine = DogmaEngine.__new__(DogmaEngine)
        module_attrs = {
            2446: {64: 1.92},
            33844: {1255: 23.8},
        }
        base_module_attrs = dict(module_attrs)
        modifiers = [
            (33844, DogmaModifier(domain="charID", func="OwnerRequiredSkillModifier",
                modified_attr_id=64, modifying_attr_id=1255, operation=6,
                skill_type_id=3436)),
        ]
        # Empty required skills — drone info not loaded
        module_required_skills = {}

        result = engine._apply_owner_skill_modifiers(
            module_attrs, base_module_attrs, modifiers, module_required_skills
        )
        assert result[2446][64] == 1.92  # Unchanged


class TestShipRoleBonuses:
    """Test ship role bonus application."""

    def test_ship_role_item_modifier(self):
        """Ship role bonus: ItemModifier on ship attribute (PostPercent)."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {37: 200.0}  # velocity
        module_attrs = {}
        # Ship bonus: +10% velocity per level, attr 315 = 10, skill = Navigation (3449)
        ship_modifiers = [DogmaModifier(
            domain="shipID", func="ItemModifier",
            modified_attr_id=37, modifying_attr_id=315, operation=6,
            skill_type_id=3449,
        )]
        base_ship_attrs = {315: 10.0}  # 10% per level

        result_ship, result_modules, charge_bonuses = engine._apply_ship_role_bonuses(
            ship_attrs, module_attrs, ship_modifiers,
            base_ship_attrs, {}, {}, {},
        )
        # 10 * 5 = 50% → 200 * 1.5 = 300
        assert result_ship[37] == pytest.approx(300.0)

    def test_ship_role_owner_required_skill(self):
        """Ship role: OwnerRequiredSkillModifier on drone damage (Vexor-like)."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {}
        # Ogre II drone with base damageMultiplier
        module_attrs = {2446: {64: 1.92}}
        # Vexor: +10% drone damage per Gallente Cruiser level
        ship_modifiers = [DogmaModifier(
            domain="charID", func="OwnerRequiredSkillModifier",
            modified_attr_id=64, modifying_attr_id=658, operation=6,
            skill_type_id=3436,  # Targets entities requiring Drones skill
        )]
        base_ship_attrs = {658: 10.0}  # 10% per level
        # Ogre II requires Drones (3436)
        module_required_skills = {2446: {3436, 12486}}

        result_ship, result_modules, charge_bonuses = engine._apply_ship_role_bonuses(
            ship_attrs, module_attrs, ship_modifiers,
            base_ship_attrs, {}, module_required_skills, {},
        )
        # 10 * 5 = 50% → 1.92 * 1.5 = 2.88
        assert result_modules[2446][64] == pytest.approx(2.88)

    def test_ship_role_location_group_modifier(self):
        """Ship role: LocationGroupModifier on turret damage (group 74 = Hybrid)."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {}
        # Hybrid turret with base damage mult
        module_attrs = {3170: {64: 2.5}}
        ship_modifiers = [DogmaModifier(
            domain="shipID", func="LocationGroupModifier",
            modified_attr_id=64, modifying_attr_id=486, operation=6,
            group_id=74,  # Hybrid turrets
            skill_type_id=3304,  # Gallente Cruiser
        )]
        base_ship_attrs = {486: 5.0}  # 5% per level
        module_groups = {3170: 74}

        result_ship, result_modules, charge_bonuses = engine._apply_ship_role_bonuses(
            ship_attrs, module_attrs, ship_modifiers,
            base_ship_attrs, module_groups, {}, {},
        )
        # 5 * 5 = 25% → 2.5 * 1.25 = 3.125
        assert result_modules[3170][64] == pytest.approx(3.125)

    def test_ship_role_no_matching_module(self):
        """Ship role bonus doesn't apply to non-matching modules."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {}
        module_attrs = {3170: {64: 2.5}}  # Turret, group 55
        ship_modifiers = [DogmaModifier(
            domain="charID", func="OwnerRequiredSkillModifier",
            modified_attr_id=64, modifying_attr_id=658, operation=6,
            skill_type_id=3436,
        )]
        base_ship_attrs = {658: 10.0}
        # Turret does NOT require Drones
        module_required_skills = {3170: {3300}}

        result_ship, result_modules, charge_bonuses = engine._apply_ship_role_bonuses(
            ship_attrs, module_attrs, ship_modifiers,
            base_ship_attrs, {}, module_required_skills, {},
        )
        assert result_modules[3170][64] == 2.5  # Unchanged

    def test_ship_role_fixed_bonus_no_skill(self):
        """Role bonus without skillTypeID uses value directly."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {37: 200.0}
        module_attrs = {}
        # Fixed role bonus: +50% velocity (no skill scaling)
        ship_modifiers = [DogmaModifier(
            domain="shipID", func="ItemModifier",
            modified_attr_id=37, modifying_attr_id=999, operation=6,
            is_role_bonus=True,
        )]
        base_ship_attrs = {999: 50.0}

        result_ship, _, charge_bonuses = engine._apply_ship_role_bonuses(
            ship_attrs, module_attrs, ship_modifiers,
            base_ship_attrs, {}, {}, {},
        )
        # No skill scaling: 200 * (1 + 50/100) = 300
        assert result_ship[37] == pytest.approx(300.0)


class TestApplySingleModifier:
    """Test the _apply_single_modifier static helper."""

    def test_pre_assign(self):
        attrs = {37: 200.0}
        DogmaEngine._apply_single_modifier(attrs, 37, 100.0, 0)
        assert attrs[37] == 100.0

    def test_mod_add(self):
        attrs = {263: 2000.0}
        DogmaEngine._apply_single_modifier(attrs, 263, 400.0, 2)
        assert attrs[263] == 2400.0

    def test_post_mul(self):
        attrs = {64: 2.0}
        DogmaEngine._apply_single_modifier(attrs, 64, 1.5, 4)
        assert attrs[64] == pytest.approx(3.0)

    def test_post_percent(self):
        attrs = {37: 200.0}
        DogmaEngine._apply_single_modifier(attrs, 37, 25.0, 6)
        assert attrs[37] == pytest.approx(250.0)

    def test_post_assign(self):
        attrs = {37: 200.0}
        DogmaEngine._apply_single_modifier(attrs, 37, 999.0, 7)
        assert attrs[37] == 999.0

    def test_missing_attr_skipped(self):
        attrs = {37: 200.0}
        DogmaEngine._apply_single_modifier(attrs, 263, 400.0, 2)
        assert 263 not in attrs  # Not added


class TestSupplementInvTypesAttrs:
    """Test that mass/capacity from invTypes is loaded when missing from dgmTypeAttributes."""

    def _make_engine_with_cursor(self, mass=None, capacity=None):
        """Create DogmaEngine with mocked DB returning mass/capacity."""
        engine = DogmaEngine.__new__(DogmaEngine)
        cursor = MagicMock()
        cursor.fetchone.return_value = {"mass": mass, "capacity": capacity}
        db = MagicMock()
        db.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        db.cursor.return_value.__exit__ = MagicMock(return_value=False)
        engine.db = db
        return engine

    def test_mass_loaded_when_missing(self):
        """Ship mass loaded from invTypes when not in dgmTypeAttributes."""
        engine = self._make_engine_with_cursor(mass=150000000.0, capacity=30000.0)
        attrs = {263: 5000.0}  # some other attr, no mass
        result = engine._supplement_invtypes_attrs(28606, attrs)
        assert result[4] == 150000000.0  # ATTR_MASS
        assert result[38] == 30000.0  # ATTR_CAPACITY

    def test_mass_loaded_when_zero(self):
        """Ship mass loaded from invTypes when dgmTypeAttributes has 0."""
        engine = self._make_engine_with_cursor(mass=150000000.0, capacity=30000.0)
        attrs = {4: 0.0, 38: 0.0}
        result = engine._supplement_invtypes_attrs(28606, attrs)
        assert result[4] == 150000000.0
        assert result[38] == 30000.0

    def test_existing_values_preserved(self):
        """Existing non-zero mass/capacity not overwritten."""
        engine = self._make_engine_with_cursor(mass=999999.0, capacity=888.0)
        attrs = {4: 500000.0, 38: 100.0}
        result = engine._supplement_invtypes_attrs(28606, attrs)
        assert result[4] == 500000.0  # preserved
        assert result[38] == 100.0  # preserved

    def test_no_db_call_when_both_present(self):
        """No DB query when both mass and capacity already in attrs."""
        engine = DogmaEngine.__new__(DogmaEngine)
        engine.db = MagicMock()
        attrs = {4: 500000.0, 38: 100.0}
        result = engine._supplement_invtypes_attrs(28606, attrs)
        engine.db.cursor.assert_not_called()
        assert result is attrs  # same dict, no copy

    def test_mass_multiplier_works_with_loaded_mass(self):
        """Industrial Core PostMul ×10 works when mass loaded from invTypes.

        Before fix: mass = 0 (not in dgmTypeAttributes) → 0 × 10 = 0
        After fix: mass = 150M (from invTypes) → 150M × 10 = 1.5B
        """
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {4: 150000000.0}  # loaded from invTypes
        module_attrs = {58950: {1471: 10.0}}  # Industrial Core massMultiplier=10
        modifiers = [
            (58950, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=4, modifying_attr_id=1471, operation=4)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        assert result[4] == pytest.approx(1500000000.0)  # 1.5B kg


class TestRigDrawbackNotStackingPenalized:
    """Rig drawback effects are NOT stacking penalized.

    Drawback effects (is_drawback=True) are applied multiplicatively
    but independently, without the stacking penalty formula.
    Regular PostPercent mods are stacking penalized among themselves.
    """

    def test_single_rig_drawback_on_ship_cpu(self):
        """Single rig drawback applies -10% to CPU output."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {48: 550.0}  # cpuOutput
        # Rig's drawbackPercent attr (1138) = -10.0
        module_attrs = {25918: {1138: -10.0}}
        modifiers = [
            (25918, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=48, modifying_attr_id=1138, operation=6,
                is_drawback=True)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # 550 * (1 + (-10)/100) = 550 * 0.90 = 495
        assert result[48] == pytest.approx(495.0)

    def test_three_rig_drawbacks_not_stacking_penalized(self):
        """Three rig drawbacks are NOT stacking penalized — each applies fully."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {48: 550.0}  # cpuOutput = 550
        module_attrs = {
            25918: {1138: -10.0},
            26328: {1138: -10.0},
        }
        modifiers = [
            (26328, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=48, modifying_attr_id=1138, operation=6,
                is_drawback=True)),
            (26328, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=48, modifying_attr_id=1138, operation=6,
                is_drawback=True)),
            (25918, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=48, modifying_attr_id=1138, operation=6,
                is_drawback=True)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # 550 * 0.90 * 0.90 * 0.90 = 400.95 (no stacking penalty)
        assert result[48] == pytest.approx(550.0 * 0.9 * 0.9 * 0.9, abs=0.1)

    def test_cpu_with_core_skill_and_three_drawbacks(self):
        """CPU calculation: base (after core skill) * 3 drawbacks (not stacking penalized).

        Ship_attrs already includes core skill (+25%): 550 * 1.25 = 687.5
        3 rig drawbacks -10% each, applied independently.
        """
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {48: 687.5}
        module_attrs = {
            25918: {1138: -10.0},
            26328: {1138: -10.0},
        }
        modifiers = [
            (26328, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=48, modifying_attr_id=1138, operation=6,
                is_drawback=True)),
            (26328, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=48, modifying_attr_id=1138, operation=6,
                is_drawback=True)),
            (25918, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=48, modifying_attr_id=1138, operation=6,
                is_drawback=True)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # 687.5 * 0.90 * 0.90 * 0.90 = 501.1875
        assert result[48] == pytest.approx(687.5 * 0.9 * 0.9 * 0.9, abs=0.1)

    def test_drawback_mixed_with_regular_modifiers(self):
        """Drawback and regular modifiers on same attribute apply independently.

        Regular mods are stacking penalized among themselves.
        Drawback applied separately, not stacking penalized.
        """
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {48: 500.0}
        module_attrs = {
            100: {200: 10.0},   # Regular module: +10% CPU
            101: {200: 10.0},   # Regular module: +10% CPU
            200: {1138: -10.0}, # Rig drawback: -10% CPU
        }
        modifiers = [
            (100, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=48, modifying_attr_id=200, operation=6)),
            (101, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=48, modifying_attr_id=200, operation=6)),
            (200, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=48, modifying_attr_id=1138, operation=6,
                is_drawback=True)),
        ]
        from app.services.dogma.stacking import apply_stacking_penalized_multipliers
        # Regular mods stacking penalized: [1.10, 1.10]
        regular_mult = apply_stacking_penalized_multipliers([1.10, 1.10])
        # Drawback applied independently: * 0.90
        expected = 500.0 * regular_mult * 0.90
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        assert result[48] == pytest.approx(expected, abs=0.1)

    def test_drawback_sig_radius_penalty(self):
        """Rig drawback on signature radius: two rigs, each +10% sig, NOT stacking penalized."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {552: 200.0}  # sigRadius
        module_attrs = {300: {1138: 10.0}}  # +10% sig (drawback is positive for sig)
        modifiers = [
            (300, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=552, modifying_attr_id=1138, operation=6,
                is_drawback=True)),
            (300, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=552, modifying_attr_id=1138, operation=6,
                is_drawback=True)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # 200 * 1.10 * 1.10 = 242.0 (no stacking penalty)
        assert result[552] == pytest.approx(200.0 * 1.10 * 1.10, abs=0.1)

    def test_drawback_location_group_modifier_no_stacking(self):
        """Rig drawback via LocationGroupModifier (weapon PG penalty) not stacking penalized."""
        engine = DogmaEngine.__new__(DogmaEngine)
        # Hybrid turret PG need = 100
        module_attrs = {
            3170: {30: 100.0},    # Turret powerNeed
            400: {1138: 10.0},    # Rig drawback +10% PG for hybrids (group 74)
        }
        module_groups = {3170: 74, 400: 999}  # turret is group 74
        # Two rigs, each +10% PG penalty on hybrid turrets
        modifiers = [
            (400, DogmaModifier(domain="shipID", func="LocationGroupModifier",
                modified_attr_id=30, modifying_attr_id=1138, operation=6,
                group_id=74, is_drawback=True)),
            (400, DogmaModifier(domain="shipID", func="LocationGroupModifier",
                modified_attr_id=30, modifying_attr_id=1138, operation=6,
                group_id=74, is_drawback=True)),
        ]
        result = engine._apply_location_modifiers(module_attrs, modifiers, module_groups)
        # 100 * 1.10 * 1.10 = 121.0 (no stacking penalty)
        assert result[3170][30] == pytest.approx(121.0, abs=0.1)

    def test_non_drawback_flag_default_false(self):
        """DogmaModifier defaults to is_drawback=False."""
        mod = DogmaModifier(domain="shipID", func="ItemModifier",
            modified_attr_id=48, modifying_attr_id=72, operation=2)
        assert mod.is_drawback is False


class TestActivationRequiredEffects:
    """Test that activation-required effects (siege/bastion/industrial core) are excluded."""

    def test_activation_required_set_contains_expected_ids(self):
        """ACTIVATION_REQUIRED_EFFECTS contains the 4 known effect IDs."""
        expected = {4575, 8119, 6582, 6658}
        assert DogmaEngine.ACTIVATION_REQUIRED_EFFECTS == expected

    def test_industrial_core_effect_excluded(self):
        """Industrial Core effectID 4575 is in the exclusion set."""
        assert 4575 in DogmaEngine.ACTIVATION_REQUIRED_EFFECTS

    def test_siege_module_effect_excluded(self):
        """Siege Module effectID 6582 is in the exclusion set."""
        assert 6582 in DogmaEngine.ACTIVATION_REQUIRED_EFFECTS

    def test_bastion_module_effect_excluded(self):
        """Bastion Module effectID 6658 is in the exclusion set."""
        assert 6658 in DogmaEngine.ACTIVATION_REQUIRED_EFFECTS

    def test_compact_industrial_core_excluded(self):
        """Compact Industrial Core effectID 8119 is in the exclusion set."""
        assert 8119 in DogmaEngine.ACTIVATION_REQUIRED_EFFECTS

    def test_regular_effect_not_excluded(self):
        """Regular effects like online (16) are NOT in the exclusion set."""
        assert 16 not in DogmaEngine.ACTIVATION_REQUIRED_EFFECTS
        assert 42 not in DogmaEngine.ACTIVATION_REQUIRED_EFFECTS  # turretFitted
        assert 40 not in DogmaEngine.ACTIVATION_REQUIRED_EFFECTS  # launcherFitted


class TestSkillVirtualModules:
    """Test skills-as-virtual-modules pipeline."""

    def _make_engine_with_mock_db(self, fetchall_results=None, fetchone_result=None):
        """Create DogmaEngine with mocked DB cursor."""
        engine = DogmaEngine.__new__(DogmaEngine)
        cursor = MagicMock()
        cursor.fetchall.return_value = fetchall_results or []
        cursor.fetchone.return_value = fetchone_result
        db = MagicMock()
        db.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
        db.cursor.return_value.__exit__ = MagicMock(return_value=False)
        engine.db = db
        return engine, cursor

    def test_get_all_skill_type_ids_returns_set(self):
        """All-V mode: queries SDE for skills with valid YAML effects."""
        engine, cursor = self._make_engine_with_mock_db(
            fetchall_results=[
                {"typeID": 3419},  # Shield Management
                {"typeID": 3426},  # CPU Management
                {"typeID": 3413},  # PG Management
            ]
        )
        result = engine._get_all_skill_type_ids()
        assert result == {3419, 3426, 3413}

    def test_get_all_skill_type_ids_empty(self):
        """Returns empty set when no skills found."""
        engine, _ = self._make_engine_with_mock_db(fetchall_results=[])
        result = engine._get_all_skill_type_ids()
        assert result == set()

    def test_get_all_skill_type_ids_filters_null_effects(self):
        """SQL query must exclude 'null...' modifierInfo (legacy effects)."""
        engine, cursor = self._make_engine_with_mock_db(
            fetchall_results=[{"typeID": 3419}]
        )
        engine._get_all_skill_type_ids()
        # Verify the SQL contains the null filter
        sql = cursor.execute.call_args[0][0]
        assert "NOT LIKE" in sql or "null" in sql.lower()

    def test_load_skill_virtual_modules_injects_skill_level(self):
        """Skill attrs loaded from SDE + attr 280 (skillLevel) injected."""
        engine = DogmaEngine.__new__(DogmaEngine)
        # Mock _load_all_attributes to return skill base attrs
        engine._load_all_attributes = MagicMock(return_value={
            3419: {337: 5.0, 275: 1.0},  # Shield Mgmt: shieldCapacityBonus=5, attr275=1
        })
        skill_levels = {3419: 5}
        skill_type_ids = [3419]
        result = engine._load_skill_virtual_modules(skill_type_ids, skill_levels, default_level=5)
        # attr 280 (skillLevel) should be injected
        assert result[3419][280] == 5.0
        # base attrs preserved
        assert result[3419][337] == 5.0

    def test_load_skill_virtual_modules_missing_skill_uses_default(self):
        """Skills not in skill_levels dict use default level."""
        engine = DogmaEngine.__new__(DogmaEngine)
        engine._load_all_attributes = MagicMock(return_value={
            3419: {337: 5.0},
        })
        skill_levels = {}  # No skills specified
        result = engine._load_skill_virtual_modules([3419], skill_levels, default_level=5)
        assert result[3419][280] == 5.0  # default All V

    def test_load_skill_virtual_modules_character_mode_level_0(self):
        """Character mode: untrained skill gets level 0."""
        engine = DogmaEngine.__new__(DogmaEngine)
        engine._load_all_attributes = MagicMock(return_value={
            3419: {337: 5.0},
        })
        skill_levels = {}  # Character has no skills
        result = engine._load_skill_virtual_modules([3419], skill_levels, default_level=0)
        assert result[3419][280] == 0.0  # untrained

    def test_load_skill_virtual_modules_empty_list(self):
        """Empty skill list returns empty dict."""
        engine = DogmaEngine.__new__(DogmaEngine)
        engine._load_all_attributes = MagicMock(return_value={})
        result = engine._load_skill_virtual_modules([], {}, default_level=5)
        assert result == {}

    def test_apply_skill_self_modifiers_premul(self):
        """Shield Management: attr 337 (base 5.0) *= attr 280 (level 5) -> 25.0.

        This is the 2-step chain Step 1: self-modifier with op 0 used as PreMul.
        EVE Dogma applies op 0 as multiplication for skill self-modifiers,
        NOT as assignment (which is how _apply_single_modifier handles it).
        """
        engine, cursor = self._make_engine_with_mock_db(
            fetchall_results=[
                {
                    "typeID": 3419,
                    "effectID": 280,
                    "effectName": "shieldCapacityMultiply",
                    "modifierInfo": (
                        "- domain: itemID\n"
                        "  func: ItemModifier\n"
                        "  modifiedAttributeID: 337\n"
                        "  modifyingAttributeID: 280\n"
                        "  operation: 0\n"
                    ),
                    "durationAttributeID": None,
                    "effectCategory": None,
                },
            ]
        )
        skill_attrs = {
            3419: {337: 5.0, 280: 5.0},  # shieldCapacityBonus=5, skillLevel=5
        }
        engine._apply_skill_self_modifiers([3419], skill_attrs)
        # Op 0 as PreMul: 5.0 * 5.0 = 25.0
        assert skill_attrs[3419][337] == pytest.approx(25.0)

    def test_apply_skill_self_modifiers_level_zero(self):
        """Untrained skill (level 0): intermediate bonus = base * 0 = 0."""
        engine, cursor = self._make_engine_with_mock_db(
            fetchall_results=[
                {
                    "typeID": 3419,
                    "effectID": 280,
                    "effectName": "shieldCapacityMultiply",
                    "modifierInfo": (
                        "- domain: itemID\n"
                        "  func: ItemModifier\n"
                        "  modifiedAttributeID: 337\n"
                        "  modifyingAttributeID: 280\n"
                        "  operation: 0\n"
                    ),
                    "durationAttributeID": None,
                    "effectCategory": None,
                },
            ]
        )
        skill_attrs = {
            3419: {337: 5.0, 280: 0.0},  # skillLevel=0
        }
        engine._apply_skill_self_modifiers([3419], skill_attrs)
        assert skill_attrs[3419][337] == pytest.approx(0.0)

    def test_apply_skill_self_modifiers_non_op0_uses_normal_apply(self):
        """Self-modifiers with op != 0 apply normally (e.g., ModAdd)."""
        engine, cursor = self._make_engine_with_mock_db(
            fetchall_results=[
                {
                    "typeID": 9999,
                    "effectID": 100,
                    "effectName": "someEffect",
                    "modifierInfo": (
                        "- domain: itemID\n"
                        "  func: ItemModifier\n"
                        "  modifiedAttributeID: 500\n"
                        "  modifyingAttributeID: 280\n"
                        "  operation: 2\n"
                    ),
                    "durationAttributeID": None,
                    "effectCategory": None,
                },
            ]
        )
        skill_attrs = {
            9999: {500: 10.0, 280: 5.0},
        }
        engine._apply_skill_self_modifiers([9999], skill_attrs)
        # Op 2 (ModAdd): 10.0 + 5.0 = 15.0
        assert skill_attrs[9999][500] == pytest.approx(15.0)

    def test_apply_skill_self_modifiers_skips_non_item_modifiers(self):
        """Only domain=itemID, func=ItemModifier effects are processed."""
        engine, cursor = self._make_engine_with_mock_db(
            fetchall_results=[
                {
                    "typeID": 3419,
                    "effectID": 446,
                    "effectName": "shieldCapacityBonus",
                    "modifierInfo": (
                        "- domain: shipID\n"
                        "  func: ItemModifier\n"
                        "  modifiedAttributeID: 263\n"
                        "  modifyingAttributeID: 337\n"
                        "  operation: 6\n"
                    ),
                    "durationAttributeID": None,
                    "effectCategory": None,
                },
            ]
        )
        skill_attrs = {
            3419: {337: 5.0, 263: 100.0, 280: 5.0},
        }
        engine._apply_skill_self_modifiers([3419], skill_attrs)
        # shipID modifier should NOT be applied -- only itemID self-modifiers
        assert skill_attrs[3419][337] == 5.0  # unchanged
        assert skill_attrs[3419][263] == 100.0  # unchanged

    def test_apply_skill_self_modifiers_multiple_skills(self):
        """Multiple skills each get their own self-modifiers applied."""
        engine, cursor = self._make_engine_with_mock_db(
            fetchall_results=[
                {
                    "typeID": 3419,  # Shield Management
                    "effectID": 280,
                    "effectName": "shieldCapMul",
                    "modifierInfo": (
                        "- domain: itemID\n"
                        "  func: ItemModifier\n"
                        "  modifiedAttributeID: 337\n"
                        "  modifyingAttributeID: 280\n"
                        "  operation: 0\n"
                    ),
                    "durationAttributeID": None,
                    "effectCategory": None,
                },
                {
                    "typeID": 3426,  # CPU Management
                    "effectID": 281,
                    "effectName": "cpuMul",
                    "modifierInfo": (
                        "- domain: itemID\n"
                        "  func: ItemModifier\n"
                        "  modifiedAttributeID: 335\n"
                        "  modifyingAttributeID: 280\n"
                        "  operation: 0\n"
                    ),
                    "durationAttributeID": None,
                    "effectCategory": None,
                },
            ]
        )
        skill_attrs = {
            3419: {337: 5.0, 280: 5.0},   # Shield Mgmt: bonus=5, level=5
            3426: {335: 5.0, 280: 4.0},   # CPU Mgmt: bonus=5, level=4
        }
        engine._apply_skill_self_modifiers([3419, 3426], skill_attrs)
        assert skill_attrs[3419][337] == pytest.approx(25.0)  # 5 * 5
        assert skill_attrs[3426][335] == pytest.approx(20.0)  # 5 * 4

    def test_load_skill_pipeline_modifiers_excludes_self_mods(self):
        """_load_skill_pipeline_modifiers returns only non-self modifiers."""
        engine, cursor = self._make_engine_with_mock_db(
            fetchall_results=[
                # Self-modifier (should be excluded)
                {
                    "typeID": 3419,
                    "effectID": 280,
                    "effectName": "shieldCapMul",
                    "modifierInfo": (
                        "- domain: itemID\n"
                        "  func: ItemModifier\n"
                        "  modifiedAttributeID: 337\n"
                        "  modifyingAttributeID: 280\n"
                        "  operation: 0\n"
                    ),
                    "durationAttributeID": None,
                    "effectCategory": None,
                },
                # Ship modifier (should be included)
                {
                    "typeID": 3419,
                    "effectID": 446,
                    "effectName": "shieldCapBonus",
                    "modifierInfo": (
                        "- domain: shipID\n"
                        "  func: ItemModifier\n"
                        "  modifiedAttributeID: 263\n"
                        "  modifyingAttributeID: 337\n"
                        "  operation: 6\n"
                    ),
                    "durationAttributeID": None,
                    "effectCategory": None,
                },
            ]
        )
        result = engine._load_skill_pipeline_modifiers([3419])
        # Only the shipID modifier should be returned
        assert len(result) == 1
        tid, mod = result[0]
        assert tid == 3419
        assert mod.domain == "shipID"
        assert mod.modified_attr_id == 263

    def test_load_skill_pipeline_modifiers_includes_location_group(self):
        """LocationGroupModifier from skills (compensation skills) is included."""
        engine, cursor = self._make_engine_with_mock_db(
            fetchall_results=[
                {
                    "typeID": 22806,  # Shield Compensation
                    "effectID": 999,
                    "effectName": "shieldCompensation",
                    "modifierInfo": (
                        "- domain: shipID\n"
                        "  func: LocationGroupModifier\n"
                        "  modifiedAttributeID: 271\n"
                        "  modifyingAttributeID: 337\n"
                        "  operation: 6\n"
                        "  groupID: 295\n"
                    ),
                    "durationAttributeID": None,
                    "effectCategory": None,
                },
            ]
        )
        result = engine._load_skill_pipeline_modifiers([22806])
        assert len(result) == 1
        _, mod = result[0]
        assert mod.func == "LocationGroupModifier"
        assert mod.group_id == 295

    def test_load_skill_pipeline_modifiers_includes_location_req_skill(self):
        """LocationRequiredSkillModifier from skills (fitting reduction) is included."""
        engine, cursor = self._make_engine_with_mock_db(
            fetchall_results=[
                {
                    "typeID": 11207,  # Advanced Weapon Upgrades
                    "effectID": 888,
                    "effectName": "advWeaponUpgrades",
                    "modifierInfo": (
                        "- domain: shipID\n"
                        "  func: LocationRequiredSkillModifier\n"
                        "  modifiedAttributeID: 30\n"
                        "  modifyingAttributeID: 313\n"
                        "  operation: 6\n"
                        "  skillTypeID: 3300\n"
                    ),
                    "durationAttributeID": None,
                    "effectCategory": None,
                },
            ]
        )
        result = engine._load_skill_pipeline_modifiers([11207])
        assert len(result) == 1
        _, mod = result[0]
        assert mod.func == "LocationRequiredSkillModifier"
        assert mod.skill_type_id == 3300

    def test_load_skill_pipeline_modifiers_empty_for_no_skills(self):
        """Empty skill list returns empty modifier list."""
        engine = DogmaEngine.__new__(DogmaEngine)
        result = engine._load_skill_pipeline_modifiers([])
        assert result == []

    def test_skill_ship_modifier_applied_to_ship_attrs(self):
        """Shield Management V: +25% shield HP via skill virtual module pipeline.

        Verifies the full path: skill loaded -> self-mod PreMul -> ship modifier applied.
        Uses _apply_modifiers directly to test the wired-up modifier data.
        """
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {263: 2000.0}  # shieldCapacity base

        # Simulate pre-computed skill attrs (after step 1.5e):
        # Shield Mgmt attr 337 = 5.0 * 5 = 25.0 (shieldCapacityBonus)
        module_attrs = {
            3419: {337: 25.0, 280: 5.0},  # skill attrs merged into module_attrs
        }

        # Skill pipeline modifier: shipID ItemModifier, attr 263 PostPercent from attr 337
        modifiers = [
            (3419, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=263, modifying_attr_id=337, operation=6)),
        ]

        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # 2000 * (1 + 25/100) = 2000 * 1.25 = 2500
        assert result[263] == pytest.approx(2500.0)

    def test_skill_location_group_modifier_on_modules(self):
        """Compensation skill modifies module resist via LocationGroupModifier.

        Shield Compensation: +2%/level on group 295 (Shield Resistance Amplifier).
        Pre-computed: attr 337 = 2.0 * 5 = 10.0
        """
        engine = DogmaEngine.__new__(DogmaEngine)
        # Shield Resistance Amplifier (group 295) with base thermal resist
        module_attrs = {
            2293: {274: -20.0},  # shieldThermalDamageResonance bonus
            22806: {337: 10.0, 280: 5.0},  # skill attrs
        }
        module_groups = {2293: 295}

        modifiers = [
            (22806, DogmaModifier(domain="shipID", func="LocationGroupModifier",
                modified_attr_id=274, modifying_attr_id=337, operation=6,
                group_id=295)),
        ]

        result = engine._apply_location_modifiers(
            module_attrs, modifiers, module_groups
        )
        # -20 * (1 + 10/100) = -20 * 1.10 = -22.0
        assert result[2293][274] == pytest.approx(-22.0)

    def test_e2e_shield_management_v_adds_25pct(self):
        """End-to-end: Shield Management V -> +25% shield HP.

        Full chain: load attrs -> inject level 5 -> self-mod PreMul (5*5=25) ->
        shipID PostPercent (+25%) -> ship shieldCapacity 2000 -> 2500.
        """
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {263: 2000.0}
        # Pre-computed: skill self-mod already applied
        skill_attrs = {3419: {337: 25.0, 280: 5.0}}
        module_attrs = dict(skill_attrs)  # merged
        modifiers = [
            (3419, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=263, modifying_attr_id=337, operation=6)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        assert result[263] == pytest.approx(2500.0)

    def test_e2e_cpu_management_iv_adds_20pct(self):
        """CPU Management IV -> +20% CPU output."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {48: 300.0}
        skill_attrs = {3426: {335: 20.0, 280: 4.0}}  # 5*4=20
        module_attrs = dict(skill_attrs)
        modifiers = [
            (3426, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=48, modifying_attr_id=335, operation=6)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        assert result[48] == pytest.approx(360.0)  # 300 * 1.20

    def test_e2e_cap_systems_op_v_reduces_recharge(self):
        """Cap Systems Operation V -> -25% recharge time."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {55: 400000.0}
        # CSO: -5%/level -> attr bonus = -5, level 5 -> -5*5 = -25
        skill_attrs = {3417: {338: -25.0, 280: 5.0}}
        module_attrs = dict(skill_attrs)
        modifiers = [
            (3417, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=55, modifying_attr_id=338, operation=6)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        assert result[55] == pytest.approx(300000.0)  # 400000 * 0.75

    def test_e2e_navigation_v_adds_25pct_velocity(self):
        """Navigation V -> +25% max velocity."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {37: 200.0}
        skill_attrs = {3449: {339: 25.0, 280: 5.0}}  # 5*5=25
        module_attrs = dict(skill_attrs)
        modifiers = [
            (3449, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=37, modifying_attr_id=339, operation=6)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        assert result[37] == pytest.approx(250.0)  # 200 * 1.25

    def test_e2e_agility_two_skills_stack(self):
        """Spaceship Command (-10%) + Evasive Maneuvering (-25%) stack multiplicatively."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {70: 1.0}
        # SC V: -2%/lv -> -2*5=-10, EM V: -5%/lv -> -5*5=-25
        skill_attrs = {
            3327: {340: -10.0, 280: 5.0},
            3453: {341: -25.0, 280: 5.0},
        }
        module_attrs = dict(skill_attrs)
        modifiers = [
            (3327, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=70, modifying_attr_id=340, operation=6)),
            (3453, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=70, modifying_attr_id=341, operation=6)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # Stacking penalized: both are PostPercent on same attr
        assert result[70] < 1.0
        assert result[70] > 0.5

    def test_e2e_missing_attr_skipped(self):
        """Skill bonus for missing ship attribute is skipped gracefully."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {48: 300.0}  # Only CPU, no shield
        skill_attrs = {3419: {337: 25.0, 280: 5.0}}
        module_attrs = dict(skill_attrs)
        modifiers = [
            (3419, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=263, modifying_attr_id=337, operation=6)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        assert result[48] == 300.0  # unchanged
        # attr 263 may be initialized to 0.0 by the engine (PostPercent on 0 = 0)
        assert result.get(263, 0.0) == pytest.approx(0.0)

    def test_e2e_level_zero_no_bonus(self):
        """Untrained skill (level 0): intermediate bonus = 0, no ship modification."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {263: 2000.0}
        # Level 0: self-mod PreMul -> 5.0 * 0 = 0.0
        skill_attrs = {3419: {337: 0.0, 280: 0.0}}
        module_attrs = dict(skill_attrs)
        modifiers = [
            (3419, DogmaModifier(domain="shipID", func="ItemModifier",
                modified_attr_id=263, modifying_attr_id=337, operation=6)),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # 2000 * (1 + 0/100) = 2000 (no change)
        assert result[263] == pytest.approx(2000.0)

    def test_self_modifier_premul_not_preassign(self):
        """CRITICAL: Op 0 must be PreMul (*=) not PreAssign (=) for skill self-mods.

        If incorrectly treated as PreAssign:
          attr 337 = attr 280 -> 337 = 5.0 (wrong, overwrites base)
        Correct PreMul:
          attr 337 *= attr 280 -> 5.0 * 5.0 = 25.0
        """
        engine, cursor = self._make_engine_with_mock_db(
            fetchall_results=[
                {
                    "typeID": 3419,
                    "effectID": 280,
                    "effectName": "shieldCapMul",
                    "modifierInfo": (
                        "- domain: itemID\n"
                        "  func: ItemModifier\n"
                        "  modifiedAttributeID: 337\n"
                        "  modifyingAttributeID: 280\n"
                        "  operation: 0\n"
                    ),
                    "durationAttributeID": None,
                    "effectCategory": None,
                },
            ]
        )
        skill_attrs = {3419: {337: 5.0, 280: 5.0}}
        engine._apply_skill_self_modifiers([3419], skill_attrs)
        # MUST be 25.0 (PreMul), NOT 5.0 (PreAssign)
        assert skill_attrs[3419][337] == pytest.approx(25.0)
        assert skill_attrs[3419][337] != 5.0  # explicit check against PreAssign


class TestRigDrawbackReduction:
    """Test step 5.95: rigging skill drawback reduction pre-application.

    Rigging skills (e.g., Launcher Rigging 26260) reduce rig drawback (attr 1138)
    via LocationGroupModifier PostPercent BEFORE step 6's drawback effects read
    the value. Without this pre-application, drawback effects use the unreduced
    base value (e.g., 10% CPU penalty instead of 6% with Launcher Rigging IV).
    """

    @staticmethod
    def _run_step_595(module_attrs, location_modifiers, module_groups):
        """Execute step 5.95 logic in isolation and return remaining modifiers."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ATTR_RIG_DRAWBACK = 1138
        remaining_location_modifiers = []
        for source_type_id, mod in location_modifiers:
            if mod.func == "LocationGroupModifier" and mod.modified_attr_id == ATTR_RIG_DRAWBACK:
                mod_value = module_attrs.get(source_type_id, {}).get(mod.modifying_attr_id)
                if mod_value is not None and mod.group_id is not None:
                    for tid, attrs in module_attrs.items():
                        if module_groups.get(tid) == mod.group_id and ATTR_RIG_DRAWBACK in attrs:
                            engine._apply_single_modifier(
                                attrs, ATTR_RIG_DRAWBACK, mod_value, mod.operation
                            )
                # Don't re-apply in step 6
            else:
                remaining_location_modifiers.append((source_type_id, mod))
        return remaining_location_modifiers

    def test_launcher_rigging_reduces_drawback(self):
        """Launcher Rigging IV reduces rig drawback from 10 to 6 (PostPercent -40%)."""
        # Launcher Rigging skill (26260): attr 1139 = -40 (after self-mod: -10 * level 4)
        # Rig (31650): attr 1138 = 10.0 (drawback), group 779 (Rig Launcher)
        module_attrs = {
            26260: {1139: -40.0},  # Launcher Rigging skill with computed reduction
            31650: {1138: 10.0},   # Rigor Pump I drawback
        }
        module_groups = {31650: 779}
        location_modifiers = [
            (26260, DogmaModifier(
                domain="shipID", func="LocationGroupModifier",
                modified_attr_id=1138, modifying_attr_id=1139, operation=6,
                group_id=779,
            )),
        ]
        remaining = self._run_step_595(module_attrs, location_modifiers, module_groups)
        # Drawback: 10 * (1 + (-40)/100) = 10 * 0.6 = 6.0
        assert module_attrs[31650][1138] == pytest.approx(6.0)
        # Modifier consumed (not passed to step 6)
        assert len(remaining) == 0

    def test_multiple_rigs_same_group_all_reduced(self):
        """All rigs in the same group get their drawback reduced."""
        module_attrs = {
            26260: {1139: -40.0},
            31650: {1138: 10.0},   # Rig 1
            31592: {1138: 10.0},   # Rig 2
            31604: {1138: 10.0},   # Rig 3
        }
        module_groups = {31650: 779, 31592: 779, 31604: 779}
        location_modifiers = [
            (26260, DogmaModifier(
                domain="shipID", func="LocationGroupModifier",
                modified_attr_id=1138, modifying_attr_id=1139, operation=6,
                group_id=779,
            )),
        ]
        remaining = self._run_step_595(module_attrs, location_modifiers, module_groups)
        assert module_attrs[31650][1138] == pytest.approx(6.0)
        assert module_attrs[31592][1138] == pytest.approx(6.0)
        assert module_attrs[31604][1138] == pytest.approx(6.0)
        assert len(remaining) == 0

    def test_non_drawback_modifiers_pass_through(self):
        """LocationGroupModifier NOT targeting attr 1138 passes to step 6."""
        module_attrs = {
            26260: {1139: -40.0},
            31650: {1138: 10.0, 50: 30.0},
        }
        module_groups = {31650: 779}
        # One drawback modifier (consumed) + one CPU modifier (passes through)
        location_modifiers = [
            (26260, DogmaModifier(
                domain="shipID", func="LocationGroupModifier",
                modified_attr_id=1138, modifying_attr_id=1139, operation=6,
                group_id=779,
            )),
            (26260, DogmaModifier(
                domain="shipID", func="LocationGroupModifier",
                modified_attr_id=50, modifying_attr_id=1139, operation=6,
                group_id=779,
            )),
        ]
        remaining = self._run_step_595(module_attrs, location_modifiers, module_groups)
        # Drawback reduced
        assert module_attrs[31650][1138] == pytest.approx(6.0)
        # CPU modifier passed through
        assert len(remaining) == 1
        assert remaining[0][1].modified_attr_id == 50

    def test_different_modifier_funcs_pass_through(self):
        """Non-LocationGroupModifier funcs pass through unchanged."""
        module_attrs = {
            3318: {310: -25.0},  # WU skill
            2404: {50: 24.0, 1138: 10.0},  # LML II
        }
        module_groups = {2404: 137}
        location_modifiers = [
            (3318, DogmaModifier(
                domain="shipID", func="LocationRequiredSkillModifier",
                modified_attr_id=50, modifying_attr_id=310, operation=6,
                skill_type_id=3319,
            )),
        ]
        remaining = self._run_step_595(module_attrs, location_modifiers, module_groups)
        # LRS modifier passes through
        assert len(remaining) == 1
        # Module attrs unchanged
        assert module_attrs[2404][50] == 24.0
        assert module_attrs[2404][1138] == 10.0

    def test_rig_wrong_group_not_affected(self):
        """Rigs in a different group are not reduced."""
        module_attrs = {
            26260: {1139: -40.0},
            31650: {1138: 10.0},   # Group 779 (launcher rig)
            99999: {1138: 10.0},   # Group 780 (different rig type)
        }
        module_groups = {31650: 779, 99999: 780}
        location_modifiers = [
            (26260, DogmaModifier(
                domain="shipID", func="LocationGroupModifier",
                modified_attr_id=1138, modifying_attr_id=1139, operation=6,
                group_id=779,  # Only targets group 779
            )),
        ]
        remaining = self._run_step_595(module_attrs, location_modifiers, module_groups)
        # Group 779 reduced
        assert module_attrs[31650][1138] == pytest.approx(6.0)
        # Group 780 NOT reduced
        assert module_attrs[99999][1138] == pytest.approx(10.0)

    def test_no_drawback_attr_on_module_skipped(self):
        """Module without attr 1138 is not affected."""
        module_attrs = {
            26260: {1139: -40.0},
            2404: {50: 24.0},  # LML II has no drawback attr
        }
        module_groups = {2404: 779}
        location_modifiers = [
            (26260, DogmaModifier(
                domain="shipID", func="LocationGroupModifier",
                modified_attr_id=1138, modifying_attr_id=1139, operation=6,
                group_id=779,
            )),
        ]
        remaining = self._run_step_595(module_attrs, location_modifiers, module_groups)
        # Module unchanged
        assert module_attrs[2404][50] == 24.0
        assert 1138 not in module_attrs[2404]

    def test_missing_source_attr_no_crash(self):
        """If source skill lacks the modifying attr, modifier is still consumed."""
        module_attrs = {
            26260: {},  # Skill missing attr 1139
            31650: {1138: 10.0},
        }
        module_groups = {31650: 779}
        location_modifiers = [
            (26260, DogmaModifier(
                domain="shipID", func="LocationGroupModifier",
                modified_attr_id=1138, modifying_attr_id=1139, operation=6,
                group_id=779,
            )),
        ]
        remaining = self._run_step_595(module_attrs, location_modifiers, module_groups)
        # Drawback unchanged (no source value)
        assert module_attrs[31650][1138] == pytest.approx(10.0)
        # Modifier still consumed
        assert len(remaining) == 0

    def test_jury_rigging_level_5_full_reduction(self):
        """Rigging V: -50% reduction → drawback 10 → 5."""
        module_attrs = {
            26260: {1139: -50.0},  # -10 * level 5
            31650: {1138: 10.0},
        }
        module_groups = {31650: 779}
        location_modifiers = [
            (26260, DogmaModifier(
                domain="shipID", func="LocationGroupModifier",
                modified_attr_id=1138, modifying_attr_id=1139, operation=6,
                group_id=779,
            )),
        ]
        remaining = self._run_step_595(module_attrs, location_modifiers, module_groups)
        # 10 * (1 + (-50)/100) = 10 * 0.5 = 5.0
        assert module_attrs[31650][1138] == pytest.approx(5.0)


class TestSkillModifierNoStacking:
    """Skill-origin modifiers must NOT be stacking penalized.

    In EVE, only fitted module bonuses receive stacking penalty.
    Skill bonuses (Spaceship Command, Evasive Maneuvering, etc.) are
    applied as independent multipliers without diminishing returns.
    """

    def test_skill_modifier_no_stacking_in_apply_modifiers(self):
        """Skill PostPercent modifiers applied without stacking penalty.

        IS II (-20%) + Spaceship Command V (-10%) + Evasive Maneuvering V (-25%):
        Without stacking: 6.0 * 0.80 * 0.90 * 0.75 = 3.2400 (EVE correct)
        With stacking:    6.0 * 0.80 * (1-0.10*0.869) * (1-0.25*0.571) ~ 3.5057 (WRONG)
        """
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {70: 6.0}  # base agility
        # Values are ALREADY level-scaled (from _apply_skill_self_modifiers step 1.5e)
        module_attrs = {
            1405: {70: -20.0},   # IS II: -20% agility (module)
            33091: {70: -10.0},  # Spaceship Command V: -2% * 5 = -10% (skill, pre-scaled)
            33092: {70: -25.0},  # Evasive Maneuvering V: -5% * 5 = -25% (skill, pre-scaled)
        }
        modifiers = [
            # IS II module modifier — SHOULD be stacking penalized
            (1405, DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=70, modifying_attr_id=70, operation=6,
            )),
            # Spaceship Command skill — NOT stacking penalized
            (33091, DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=70, modifying_attr_id=70, operation=6,
                is_skill=True,
            )),
            # Evasive Maneuvering skill — NOT stacking penalized
            (33092, DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=70, modifying_attr_id=70, operation=6,
                is_skill=True,
            )),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # Only IS II gets stacking penalty (alone, so no penalty effect)
        # 6.0 * (1 + -20/100) * (1 + -10/100) * (1 + -25/100) = 6.0 * 0.80 * 0.90 * 0.75 = 3.24
        assert result[70] == pytest.approx(3.24, abs=0.01)

    def test_two_modules_stacked_skill_independent(self):
        """Two IS IIs get stacking penalty, skill modifier does not."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {70: 6.0}
        module_attrs = {
            1405: {70: -20.0},   # IS II: -20%
            33091: {70: -10.0},  # Spaceship Command V: -10% (skill, pre-scaled)
        }
        modifiers = [
            # Two IS II modules — stacking penalized together
            (1405, DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=70, modifying_attr_id=70, operation=6,
            )),
            (1405, DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=70, modifying_attr_id=70, operation=6,
            )),
            # Skill — NOT stacking penalized
            (33091, DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=70, modifying_attr_id=70, operation=6,
                is_skill=True,
            )),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # Two IS II: stacking penalized: (1-0.20) * (1-0.20*0.869) = 0.80 * 0.8262 = 0.66096
        # Skill: 1 + (-10/100) = 0.90
        # Final: 6.0 * 0.66096 * 0.90 = 3.56918
        from app.services.dogma.stacking import apply_stacking_penalized_multipliers
        stacked = apply_stacking_penalized_multipliers([0.80, 0.80])
        expected = 6.0 * stacked * 0.90
        assert result[70] == pytest.approx(expected, abs=0.01)

    def test_skill_post_mul_no_stacking(self):
        """Skill PostMul (op 4) modifier applied without stacking."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {64: 1.0}  # damageMultiplier
        module_attrs = {
            33001: {64: 1.25},  # skill: 25% damage bonus (op4 = PostMul)
        }
        modifiers = [
            (33001, DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=64, modifying_attr_id=64, operation=4,
                is_skill=True,
            )),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # Direct multiply, no stacking: 1.0 * 1.25 = 1.25
        assert result[64] == pytest.approx(1.25)

    def test_multiple_skills_no_stacking(self):
        """Multiple skill PostPercent modifiers — each applies fully."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {263: 1000.0}  # shieldCapacity
        module_attrs = {
            33010: {263: 5.0},   # Shield Management V: +25% → attr value = 5*5 = 25 → but here 5.0 is raw
            33011: {263: 10.0},  # Some other skill: +10%
        }
        modifiers = [
            (33010, DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=263, modifying_attr_id=263, operation=6,
                is_skill=True,
            )),
            (33011, DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=263, modifying_attr_id=263, operation=6,
                is_skill=True,
            )),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # Each applied independently: 1000 * (1+5/100) * (1+10/100) = 1000 * 1.05 * 1.10 = 1155
        assert result[263] == pytest.approx(1155.0)

    def test_module_modifier_still_stacking_penalized(self):
        """Regular module modifiers still get stacking penalty (sanity check)."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {263: 1000.0}
        module_attrs = {
            3831: {72: 10.0},  # Module: +10% shield
        }
        modifiers = [
            (3831, DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=263, modifying_attr_id=72, operation=6,
            )),
            (3831, DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=263, modifying_attr_id=72, operation=6,
            )),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        # With stacking: 1000 * SP([1.10, 1.10]) ≠ 1000 * 1.10 * 1.10
        assert result[263] != pytest.approx(1210.0)  # NOT the non-stacked result
        from app.services.dogma.stacking import apply_stacking_penalized_multipliers
        expected = 1000.0 * apply_stacking_penalized_multipliers([1.10, 1.10])
        assert result[263] == pytest.approx(expected, abs=0.01)

    def test_skill_in_location_modifiers_group(self):
        """Skill LocationGroupModifier not stacking penalized."""
        engine = DogmaEngine.__new__(DogmaEngine)
        module_attrs = {
            # Two modules in group 53 (Energy Turret)
            3001: {64: 10.0},  # damageMultiplier base
            3002: {64: 10.0},
            # Skill modifier source
            33099: {64: 15.0},  # +15% damage bonus
        }
        module_groups = {3001: 53, 3002: 53, 33099: 0}
        modifiers = [
            (33099, DogmaModifier(
                domain="shipID", func="LocationGroupModifier",
                modified_attr_id=64, modifying_attr_id=64, operation=6,
                group_id=53, is_skill=True,
            )),
        ]
        result = engine._apply_location_modifiers(module_attrs, modifiers, module_groups)
        # Skill modifier: applied without stacking penalty
        # 10.0 * (1 + 15/100) = 11.5
        assert result[3001][64] == pytest.approx(11.5)
        assert result[3002][64] == pytest.approx(11.5)

    def test_skill_in_owner_skill_modifiers(self):
        """Skill OwnerRequiredSkillModifier not stacking penalized."""
        engine = DogmaEngine.__new__(DogmaEngine)
        module_attrs = {
            # Drone with damageMultiplier
            2000: {64: 1.0},
        }
        base_module_attrs = {
            # Skill modifier source
            33050: {64: 1.20},  # skill: 20% damage bonus (op4)
            33051: {64: 1.10},  # skill: 10% damage bonus (op4)
        }
        module_required_skills = {2000: {3436}}  # drone requires Drones skill
        modifiers = [
            (33050, DogmaModifier(
                domain="charID", func="OwnerRequiredSkillModifier",
                modified_attr_id=64, modifying_attr_id=64, operation=4,
                skill_type_id=3436, is_skill=True,
            )),
            (33051, DogmaModifier(
                domain="charID", func="OwnerRequiredSkillModifier",
                modified_attr_id=64, modifying_attr_id=64, operation=4,
                skill_type_id=3436, is_skill=True,
            )),
        ]
        result = engine._apply_owner_skill_modifiers(
            module_attrs, base_module_attrs, modifiers, module_required_skills,
        )
        # Both applied independently: 1.0 * 1.20 * 1.10 = 1.32
        assert result[2000][64] == pytest.approx(1.32)

    def test_module_in_owner_skill_still_stacked(self):
        """Module OwnerRequiredSkillModifier still stacking penalized (sanity check)."""
        engine = DogmaEngine.__new__(DogmaEngine)
        module_attrs = {
            2000: {64: 1.0},
        }
        base_module_attrs = {
            500: {64: 1.20},  # DDA: 20% damage bonus (module, not skill)
        }
        module_required_skills = {2000: {3436}}
        modifiers = [
            (500, DogmaModifier(
                domain="charID", func="OwnerRequiredSkillModifier",
                modified_attr_id=64, modifying_attr_id=64, operation=4,
                skill_type_id=3436,
                # is_skill=False (default) → stacking penalized
            )),
            (500, DogmaModifier(
                domain="charID", func="OwnerRequiredSkillModifier",
                modified_attr_id=64, modifying_attr_id=64, operation=4,
                skill_type_id=3436,
            )),
        ]
        result = engine._apply_owner_skill_modifiers(
            module_attrs, base_module_attrs, modifiers, module_required_skills,
        )
        # With stacking penalty: NOT 1.0 * 1.20 * 1.20 = 1.44
        from app.services.dogma.stacking import apply_stacking_penalized_multipliers
        expected = 1.0 * apply_stacking_penalized_multipliers([1.20, 1.20])
        assert result[2000][64] == pytest.approx(expected, abs=0.001)
        assert result[2000][64] != pytest.approx(1.44)  # NOT the non-stacked value


class TestSkillDefaultParameter:
    """Test that _skill_default is a local parameter, not mutable instance state.

    Thread-safety fix: _skill_default was mutable instance state set per-call
    in calculate_modified_attributes(). Now passed as explicit parameter to
    _apply_ship_role_bonuses() and _load_skill_virtual_modules().
    """

    def test_skill_default_not_on_instance_after_call(self):
        """After calling _apply_ship_role_bonuses, _skill_default must NOT be stored on the instance.

        The old code stored self._skill_default as mutable instance state. The refactored
        code passes it as a parameter, so the instance attribute should not exist.
        """
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {37: 200.0}
        module_attrs = {}
        # Per-level bonus: +10% velocity per level, attr 315 = 10
        ship_modifiers = [DogmaModifier(
            domain="shipID", func="ItemModifier",
            modified_attr_id=37, modifying_attr_id=315, operation=6,
        )]
        base_ship_attrs = {315: 10.0, 182: 3449.0}  # 10% per level, requiredSkill1=3449

        # Call with explicit skill_default parameter
        engine._apply_ship_role_bonuses(
            ship_attrs, module_attrs, ship_modifiers,
            base_ship_attrs, {}, {}, {},
            ship_type_id=None, skill_default=5,
        )
        # Instance must NOT have _skill_default attribute
        assert not hasattr(engine, '_skill_default'), (
            "_skill_default should not be stored as instance state"
        )

    def test_apply_ship_role_bonuses_uses_skill_default_param(self):
        """Per-level bonus must use the skill_default parameter, not a hardcoded value.

        With skill_default=5 (All V): bonus = 10 * 5 = 50% -> 200 * 1.5 = 300
        With skill_default=0 (untrained): bonus = 10 * 0 = 0% -> 200 * 1.0 = 200
        """
        engine = DogmaEngine.__new__(DogmaEngine)
        # Per-level bonus: +10% velocity per level (no specific skill in skill_levels)
        ship_modifiers = [DogmaModifier(
            domain="shipID", func="ItemModifier",
            modified_attr_id=37, modifying_attr_id=315, operation=6,
        )]
        base_ship_attrs = {315: 10.0, 182: 3449.0}  # 10% per level, requiredSkill1=3449

        # Case 1: skill_default=5 (All V mode)
        result_5, _, _ = engine._apply_ship_role_bonuses(
            {37: 200.0}, {}, ship_modifiers,
            base_ship_attrs, {}, {}, {},
            ship_type_id=None, skill_default=5,
        )
        # 10 * 5 = 50% -> 200 * 1.5 = 300
        assert result_5[37] == pytest.approx(300.0)

        # Case 2: skill_default=0 (character mode, skill untrained)
        result_0, _, _ = engine._apply_ship_role_bonuses(
            {37: 200.0}, {}, ship_modifiers,
            base_ship_attrs, {}, {}, {},
            ship_type_id=None, skill_default=0,
        )
        # 10 * 0 = 0% -> 200 * 1.0 = 200
        assert result_0[37] == pytest.approx(200.0)


class TestMissingOperations:
    """Test missing Dogma operations added to all apply methods.

    EVE Dogma operations:
        0: PreAssign (override value, last wins)
        2: ModAdd (add to base)
        3: ModSub (subtract from base)
        4: PostMul (multiply, stacking penalized for modules)
        5: PostDiv (divide, stacking penalized for modules)
        6: PostPercent (percentage bonus, stacking penalized for modules)
        7: PostAssign (final override, last wins)
    """

    # --- _apply_single_modifier: Op 3 (ModSub) and Op 5 (PostDiv) ---

    def test_single_modifier_op3_modsub(self):
        """Op 3 (ModSub) in _apply_single_modifier subtracts value from base."""
        attrs = {51: 100.0}
        DogmaEngine._apply_single_modifier(attrs, 51, 25.0, 3)
        assert attrs[51] == pytest.approx(75.0)

    def test_single_modifier_op5_postdiv(self):
        """Op 5 (PostDiv) in _apply_single_modifier divides base by value."""
        attrs = {51: 200.0}
        DogmaEngine._apply_single_modifier(attrs, 51, 4.0, 5)
        assert attrs[51] == pytest.approx(50.0)

    def test_single_modifier_op5_postdiv_zero_safe(self):
        """Op 5 (PostDiv) with value=0 does not divide (zero guard)."""
        attrs = {51: 200.0}
        DogmaEngine._apply_single_modifier(attrs, 51, 0.0, 5)
        assert attrs[51] == pytest.approx(200.0)  # unchanged

    # --- _apply_location_modifiers: regular (stacking penalized) bucket ---

    def test_location_mod_op3_modsub_regular(self):
        """Op 3 (ModSub) in location modifiers regular bucket."""
        engine = DogmaEngine.__new__(DogmaEngine)
        module_attrs = {1001: {51: 100.0}}
        mod = DogmaModifier(
            domain="shipID", func="LocationGroupModifier",
            modified_attr_id=51, modifying_attr_id=99,
            operation=3, group_id=55,
        )
        mods = [(2001, mod)]
        source_attrs = {2001: {99: 25.0}}
        result = engine._apply_location_modifiers(
            module_attrs, mods, {1001: 55}, source_attrs=source_attrs,
        )
        assert result[1001][51] == pytest.approx(75.0)

    def test_location_mod_op5_postdiv_regular(self):
        """Op 5 (PostDiv) in location modifiers regular bucket (stacking penalized)."""
        engine = DogmaEngine.__new__(DogmaEngine)
        module_attrs = {1001: {51: 200.0}}
        mod = DogmaModifier(
            domain="shipID", func="LocationGroupModifier",
            modified_attr_id=51, modifying_attr_id=99,
            operation=5, group_id=55,
        )
        mods = [(2001, mod)]
        source_attrs = {2001: {99: 4.0}}
        result = engine._apply_location_modifiers(
            module_attrs, mods, {1001: 55}, source_attrs=source_attrs,
        )
        # 200 / stacking_penalized([4.0]) = 200 / 4.0 = 50
        assert result[1001][51] == pytest.approx(50.0)

    def test_location_mod_op7_postassign_regular(self):
        """Op 7 (PostAssign) in location modifiers regular bucket."""
        engine = DogmaEngine.__new__(DogmaEngine)
        module_attrs = {1001: {51: 100.0}}
        mod = DogmaModifier(
            domain="shipID", func="LocationGroupModifier",
            modified_attr_id=51, modifying_attr_id=99,
            operation=7, group_id=55,
        )
        mods = [(2001, mod)]
        source_attrs = {2001: {99: 42.0}}
        result = engine._apply_location_modifiers(
            module_attrs, mods, {1001: 55}, source_attrs=source_attrs,
        )
        assert result[1001][51] == pytest.approx(42.0)

    # --- _apply_location_modifiers: drawback (non-stacking) bucket ---

    def test_location_mod_op3_modsub_drawback(self):
        """Op 3 (ModSub) in location modifiers drawback bucket."""
        engine = DogmaEngine.__new__(DogmaEngine)
        module_attrs = {1001: {51: 100.0}}
        mod = DogmaModifier(
            domain="shipID", func="LocationGroupModifier",
            modified_attr_id=51, modifying_attr_id=99,
            operation=3, group_id=55, is_drawback=True,
        )
        mods = [(2001, mod)]
        source_attrs = {2001: {99: 15.0}}
        result = engine._apply_location_modifiers(
            module_attrs, mods, {1001: 55}, source_attrs=source_attrs,
        )
        assert result[1001][51] == pytest.approx(85.0)

    def test_location_mod_op5_postdiv_drawback(self):
        """Op 5 (PostDiv) in location modifiers drawback bucket."""
        engine = DogmaEngine.__new__(DogmaEngine)
        module_attrs = {1001: {51: 200.0}}
        mod = DogmaModifier(
            domain="shipID", func="LocationGroupModifier",
            modified_attr_id=51, modifying_attr_id=99,
            operation=5, group_id=55, is_drawback=True,
        )
        mods = [(2001, mod)]
        source_attrs = {2001: {99: 4.0}}
        result = engine._apply_location_modifiers(
            module_attrs, mods, {1001: 55}, source_attrs=source_attrs,
        )
        # Not stacking penalized: 200 / 4.0 = 50
        assert result[1001][51] == pytest.approx(50.0)

    def test_location_mod_op7_postassign_drawback(self):
        """Op 7 (PostAssign) in location modifiers drawback bucket."""
        engine = DogmaEngine.__new__(DogmaEngine)
        module_attrs = {1001: {51: 100.0}}
        mod = DogmaModifier(
            domain="shipID", func="LocationGroupModifier",
            modified_attr_id=51, modifying_attr_id=99,
            operation=7, group_id=55, is_drawback=True,
        )
        mods = [(2001, mod)]
        source_attrs = {2001: {99: 77.0}}
        result = engine._apply_location_modifiers(
            module_attrs, mods, {1001: 55}, source_attrs=source_attrs,
        )
        assert result[1001][51] == pytest.approx(77.0)

    # --- _apply_owner_skill_modifiers: module-origin (stacking penalized) bucket ---

    def test_owner_skill_op0_preassign(self):
        """Op 0 (PreAssign) in owner skill modifiers module bucket."""
        engine = DogmaEngine.__new__(DogmaEngine)
        module_attrs = {1001: {64: 100.0}}
        base_attrs = {2001: {99: 50.0}}
        mod = DogmaModifier(
            domain="charID", func="OwnerRequiredSkillModifier",
            modified_attr_id=64, modifying_attr_id=99,
            operation=0, skill_type_id=3436,
        )
        result = engine._apply_owner_skill_modifiers(
            module_attrs, base_attrs, [(2001, mod)], {1001: {3436}},
        )
        assert result[1001][64] == pytest.approx(50.0)

    def test_owner_skill_op3_modsub(self):
        """Op 3 (ModSub) in owner skill modifiers module bucket."""
        engine = DogmaEngine.__new__(DogmaEngine)
        module_attrs = {1001: {64: 100.0}}
        base_attrs = {2001: {99: 20.0}}
        mod = DogmaModifier(
            domain="charID", func="OwnerRequiredSkillModifier",
            modified_attr_id=64, modifying_attr_id=99,
            operation=3, skill_type_id=3436,
        )
        result = engine._apply_owner_skill_modifiers(
            module_attrs, base_attrs, [(2001, mod)], {1001: {3436}},
        )
        assert result[1001][64] == pytest.approx(80.0)

    # --- _apply_modifiers: drawback bucket ---

    def test_modifiers_drawback_op0_preassign(self):
        """Op 0 (PreAssign) in _apply_modifiers drawback bucket."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {48: 500.0}
        module_attrs = {100: {99: 300.0}}
        modifiers = [
            (100, DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=48, modifying_attr_id=99, operation=0,
                is_drawback=True,
            )),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        assert result[48] == pytest.approx(300.0)

    def test_modifiers_drawback_op2_modadd(self):
        """Op 2 (ModAdd) in _apply_modifiers drawback bucket."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {48: 500.0}
        module_attrs = {100: {99: 50.0}}
        modifiers = [
            (100, DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=48, modifying_attr_id=99, operation=2,
                is_drawback=True,
            )),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        assert result[48] == pytest.approx(550.0)

    def test_modifiers_drawback_op3_modsub(self):
        """Op 3 (ModSub) in _apply_modifiers drawback bucket."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {48: 500.0}
        module_attrs = {100: {99: 75.0}}
        modifiers = [
            (100, DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=48, modifying_attr_id=99, operation=3,
                is_drawback=True,
            )),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        assert result[48] == pytest.approx(425.0)

    def test_modifiers_drawback_op7_postassign(self):
        """Op 7 (PostAssign) in _apply_modifiers drawback bucket."""
        engine = DogmaEngine.__new__(DogmaEngine)
        ship_attrs = {48: 500.0}
        module_attrs = {100: {99: 999.0}}
        modifiers = [
            (100, DogmaModifier(
                domain="shipID", func="ItemModifier",
                modified_attr_id=48, modifying_attr_id=99, operation=7,
                is_drawback=True,
            )),
        ]
        result = engine._apply_modifiers(ship_attrs, module_attrs, modifiers)
        assert result[48] == pytest.approx(999.0)
