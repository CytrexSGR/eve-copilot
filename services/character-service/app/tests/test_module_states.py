"""Tests for effectCategory filtering based on module states.

The SDE effectCategory column is always NULL, so the engine derives
the category from durationAttributeID and effectName:
  - effectName contains "overload"  → overload (5)
  - durationAttributeID is NOT NULL → active (1)
  - effectName contains "online"    → online (4)
  - otherwise                       → passive (0)

Module states and allowed categories:
  offline   → {} (no effects)
  online    → {0, 4}
  active    → {0, 1, 4}
  overheated→ {0, 1, 4, 5}
  default (None) → active → {0, 1, 4}
"""

import pytest
from unittest.mock import MagicMock

from app.services.dogma.engine import DogmaEngine


def _make_engine_with_rows(rows):
    """Create a DogmaEngine with a mocked DB cursor returning given rows.

    Each row should be a dict with keys:
      typeID, effectID, effectName, modifierInfo, durationAttributeID, effectCategory
    """
    engine = DogmaEngine.__new__(DogmaEngine)
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    db = MagicMock()
    db.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    db.cursor.return_value.__exit__ = MagicMock(return_value=False)
    engine.db = db
    return engine


# A simple modifierInfo string that produces one ItemModifier
# (PostPercent on shield capacity from attr 72)
SAMPLE_MODIFIER_INFO = (
    "- domain: shipID\n"
    "  func: ItemModifier\n"
    "  modifiedAttributeID: 263\n"
    "  modifyingAttributeID: 72\n"
    "  operator: 6\n"
)


def _make_effect_row(type_id, effect_id=100, effect_name=None,
                     effect_category_id=0, duration_attr_id=None,
                     modifier_info=None):
    """Create a DB row dict for _load_modifiers.

    The engine derives effectCategory from effectName and durationAttributeID,
    so this helper sets those fields to match the desired effect_category_id:
      0 → passive: no duration, generic name
      1 → active:  has durationAttributeID=73
      4 → online:  name contains "online"
      5 → overload: name contains "overload"
    """
    if effect_name is None:
        if effect_category_id == 5:
            effect_name = "overloadTestBonus"
        elif effect_category_id == 1:
            effect_name = "activeTestEffect"
            if duration_attr_id is None:
                duration_attr_id = 73  # typical duration attr
        elif effect_category_id == 4:
            effect_name = "shieldCapacityBonusOnline"
        else:
            effect_name = "passiveTestEffect"
    return {
        "typeID": type_id,
        "effectID": effect_id,
        "effectName": effect_name,
        "modifierInfo": modifier_info or SAMPLE_MODIFIER_INFO,
        "durationAttributeID": duration_attr_id,
        "effectCategory": None,  # Always NULL in SDE
    }


class TestModuleStateConstants:
    """Test MODULE_STATE_ALLOWED_CATEGORIES constant is correct."""

    def test_offline_allows_nothing(self):
        allowed = DogmaEngine.MODULE_STATE_ALLOWED_CATEGORIES["offline"]
        assert len(allowed) == 0
        assert isinstance(allowed, frozenset)

    def test_online_allows_passive_and_online(self):
        allowed = DogmaEngine.MODULE_STATE_ALLOWED_CATEGORIES["online"]
        assert allowed == frozenset({0, 4})

    def test_active_allows_passive_active_online(self):
        allowed = DogmaEngine.MODULE_STATE_ALLOWED_CATEGORIES["active"]
        assert allowed == frozenset({0, 1, 4})

    def test_overheated_allows_all_four(self):
        allowed = DogmaEngine.MODULE_STATE_ALLOWED_CATEGORIES["overheated"]
        assert allowed == frozenset({0, 1, 4, 5})


class TestModuleStatesNoneBackwardCompat:
    """When flag_states is None, behavior is unchanged (backward compatible)."""

    def test_none_flag_states_defaults_to_active(self):
        """With no flag_states, default 'active' filtering applies (excludes overload)."""
        rows = [
            _make_effect_row(3831, effect_id=1, effect_category_id=0),  # passive → allowed
            _make_effect_row(3831, effect_id=2, effect_category_id=1),  # active → allowed
            _make_effect_row(3831, effect_id=3, effect_category_id=5),  # overload → blocked
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers([3831], simulation_mode=True)
        assert len(result) == 2  # overload excluded in default active state

    def test_default_params_exclude_overload(self):
        """Without flag params, overload effects are excluded (default = active state)."""
        rows = [
            _make_effect_row(3831, effect_id=1, effect_category_id=5),  # overload
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers([3831], simulation_mode=True)
        assert len(result) == 0  # overload blocked in default active state


class TestOfflineModuleState:
    """Offline module produces zero modifiers."""

    def test_offline_module_produces_no_modifiers(self):
        """All effects are filtered for an offline module."""
        rows = [
            _make_effect_row(3831, effect_id=1, effect_category_id=0),  # passive
            _make_effect_row(3831, effect_id=2, effect_category_id=1),  # active
            _make_effect_row(3831, effect_id=4, effect_category_id=5),  # overload
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831], simulation_mode=True,
            module_flags=[19], flag_states={19: "offline"},
        )
        assert len(result) == 0

    def test_offline_one_module_active_another(self):
        """One module offline (0 effects), another active (gets passive+active+online)."""
        rows = [
            # Module 3831 effects
            _make_effect_row(3831, effect_id=1, effect_category_id=0),  # passive
            _make_effect_row(3831, effect_id=2, effect_category_id=1),  # active
            # Module 519 effects
            _make_effect_row(519, effect_id=3, effect_category_id=0),   # passive
            _make_effect_row(519, effect_id=4, effect_category_id=1),   # active
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831, 519], simulation_mode=True,
            module_flags=[19, 20], flag_states={19: "offline", 20: "active"},
        )
        # flag 19 (3831) offline → 0 effects, flag 20 (519) active → 2 effects
        module_3831_mods = [(t, m) for t, m in result if t == 3831]
        module_519_mods = [(t, m) for t, m in result if t == 519]
        assert len(module_3831_mods) == 0
        assert len(module_519_mods) == 2


class TestOnlineModuleState:
    """Online module gets passive (0) and online (4) effects."""

    def test_online_allows_passive_and_online_blocks_active_and_overload(self):
        rows = [
            _make_effect_row(3831, effect_id=1, effect_category_id=0),  # passive → allowed
            _make_effect_row(3831, effect_id=2, effect_category_id=1),  # active → blocked
            _make_effect_row(3831, effect_id=3, effect_category_id=4),  # online → allowed
            _make_effect_row(3831, effect_id=4, effect_category_id=5),  # overload → blocked
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831], simulation_mode=True,
            module_flags=[19], flag_states={19: "online"},
        )
        assert len(result) == 2  # passive + online

    def test_online_blocks_active_category(self):
        """Active effects (derived from durationAttributeID) blocked for online modules."""
        rows = [
            _make_effect_row(3831, effect_id=2, effect_category_id=1),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831], simulation_mode=True,
            module_flags=[19], flag_states={19: "online"},
        )
        assert len(result) == 0

    def test_online_blocks_overload_category(self):
        """Overload effects (derived from name) blocked for online modules."""
        rows = [
            _make_effect_row(3831, effect_id=4, effect_category_id=5),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831], simulation_mode=True,
            module_flags=[19], flag_states={19: "online"},
        )
        assert len(result) == 0


class TestActiveModuleState:
    """Active module gets passive (0) and active (1) effects."""

    def test_active_allows_passive_and_active(self):
        rows = [
            _make_effect_row(3831, effect_id=1, effect_category_id=0),  # passive → allowed
            _make_effect_row(3831, effect_id=2, effect_category_id=1),  # active → allowed
            _make_effect_row(3831, effect_id=4, effect_category_id=5),  # overload → blocked
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831], simulation_mode=True,
            module_flags=[19], flag_states={19: "active"},
        )
        assert len(result) == 2

    def test_active_blocks_overload(self):
        """Category 5 (overload) blocked for active modules."""
        rows = [
            _make_effect_row(3831, effect_id=4, effect_category_id=5),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831], simulation_mode=True,
            module_flags=[19], flag_states={19: "active"},
        )
        assert len(result) == 0

    def test_active_is_default_when_flag_not_in_states(self):
        """Flag not in flag_states dict defaults to active."""
        rows = [
            _make_effect_row(3831, effect_id=1, effect_category_id=0),  # passive → allowed
            _make_effect_row(3831, effect_id=2, effect_category_id=1),  # active → allowed
            _make_effect_row(3831, effect_id=4, effect_category_id=5),  # overload → blocked
        ]
        engine = _make_engine_with_rows(rows)
        # flag_states dict exists but doesn't contain flag 19
        result = engine._load_modifiers(
            [3831], simulation_mode=True,
            module_flags=[19], flag_states={99: "offline"},  # unrelated flag
        )
        # Defaults to "active" → allows 0, 1 → 2 modifiers
        assert len(result) == 2


class TestOverheatedModuleState:
    """Overheated module gets all derived categories: 0, 1, 5."""

    def test_overheated_allows_all_categories(self):
        rows = [
            _make_effect_row(3831, effect_id=1, effect_category_id=0),  # passive
            _make_effect_row(3831, effect_id=2, effect_category_id=1),  # active
            _make_effect_row(3831, effect_id=4, effect_category_id=5),  # overload
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831], simulation_mode=True,
            module_flags=[19], flag_states={19: "overheated"},
        )
        assert len(result) == 3

    def test_overheated_includes_overload_category(self):
        """Category 5 (overload) effects are included for overheated modules."""
        rows = [
            _make_effect_row(3831, effect_id=4, effect_category_id=5),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831], simulation_mode=True,
            module_flags=[19], flag_states={19: "overheated"},
        )
        assert len(result) == 1


class TestModuleStateMixedScenarios:
    """Test multiple modules with different states in the same fitting."""

    def test_mixed_states_three_modules(self):
        """Three modules: offline, online, overheated — correct filtering per module."""
        rows = [
            # Module A (type 100): 1 passive, 1 active effect
            _make_effect_row(100, effect_id=1, effect_category_id=0),
            _make_effect_row(100, effect_id=2, effect_category_id=1),
            # Module B (type 200): 2 passive effects
            _make_effect_row(200, effect_id=3, effect_category_id=0),
            _make_effect_row(200, effect_id=4, effect_category_id=0, effect_name="passiveBonus2"),
            # Module C (type 300): 1 overload effect
            _make_effect_row(300, effect_id=5, effect_category_id=5),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [100, 200, 300], simulation_mode=True,
            module_flags=[19, 20, 27], flag_states={19: "offline", 20: "online", 27: "overheated"},
        )
        mod_100 = [(t, m) for t, m in result if t == 100]
        mod_200 = [(t, m) for t, m in result if t == 200]
        mod_300 = [(t, m) for t, m in result if t == 300]
        # Module A (flag 19) offline → 0
        assert len(mod_100) == 0
        # Module B (flag 20) online → 2 passive effects allowed
        assert len(mod_200) == 2
        # Module C (flag 27) overheated → overload(5) = 1
        assert len(mod_300) == 1

    def test_duplicate_type_ids_different_states(self):
        """Two instances of same type_id with DIFFERENT states — the key bug fix.

        Previously, both instances got the same (highest) state because
        the conversion was lossy (type_id → state). Now each slot is
        filtered independently by its flag.
        """
        rows = [
            _make_effect_row(3831, effect_id=1, effect_category_id=0),  # passive
            _make_effect_row(3831, effect_id=2, effect_category_id=1),  # active
        ]
        engine = _make_engine_with_rows(rows)
        # Two instances of 3831: flag 19 = offline, flag 20 = active
        result = engine._load_modifiers(
            [3831, 3831], simulation_mode=True,
            module_flags=[19, 20], flag_states={19: "offline", 20: "active"},
        )
        # flag 19 offline → 0 effects, flag 20 active → 2 effects (cat 0 + cat 1)
        assert len(result) == 2

    def test_duplicate_type_ids_both_offline(self):
        """Two instances of same type_id both offline — no modifiers."""
        rows = [
            _make_effect_row(3831, effect_id=1, effect_category_id=0),
            _make_effect_row(3831, effect_id=2, effect_category_id=1),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831, 3831], simulation_mode=True,
            module_flags=[19, 20], flag_states={19: "offline", 20: "offline"},
        )
        assert len(result) == 0

    def test_duplicate_type_ids_same_state(self):
        """Two instances of same type_id, same state — both get modifiers."""
        rows = [
            _make_effect_row(3831, effect_id=1, effect_category_id=0),  # passive
            _make_effect_row(3831, effect_id=2, effect_category_id=1),  # active
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831, 3831], simulation_mode=True,
            module_flags=[19, 20], flag_states={19: "online", 20: "online"},
        )
        # online allows cat 0 → each instance gets 1 modifier → 2 total
        assert len(result) == 2

    def test_passive_effect_blocked_when_offline(self):
        """Even passive effects are blocked when module is offline."""
        rows = [
            _make_effect_row(3831, effect_id=1, effect_category_id=0),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831], simulation_mode=True,
            module_flags=[19], flag_states={19: "offline"},
        )
        assert len(result) == 0


class TestExistingFiltersStillWork:
    """Verify that ACTIVATION_REQUIRED_EFFECTS and durationAttributeID filters
    still work alongside effectCategory filtering."""

    def test_activation_required_still_filtered(self):
        """Siege module effect (4575) filtered even if effectCategory is allowed."""
        rows = [
            _make_effect_row(3831, effect_id=4575, effect_category_id=0),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831], simulation_mode=True,
            module_flags=[19], flag_states={19: "active"},
        )
        assert len(result) == 0

    def test_duration_attr_filter_still_works_non_simulation(self):
        """In non-simulation mode, active effects (with durationAttributeID) still filtered."""
        rows = [
            _make_effect_row(3831, effect_id=100, effect_category_id=1,
                             duration_attr_id=73),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831], simulation_mode=False,
            module_flags=[19], flag_states={19: "active"},
        )
        assert len(result) == 0


class TestEffectCategoryDerived:
    """Test that effect_category is derived and stored on DogmaModifier."""

    def test_passive_effect_derives_category_0(self):
        """Effect without durationAttr and without 'overload' → category 0."""
        rows = [
            _make_effect_row(3831, effect_id=1, effect_category_id=0),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers([3831], simulation_mode=True)
        assert len(result) == 1
        _, mod = result[0]
        assert mod.effect_category == 0

    def test_active_effect_derives_category_1(self):
        """Effect with durationAttributeID → category 1."""
        rows = [
            _make_effect_row(3831, effect_id=1, effect_category_id=1),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers([3831], simulation_mode=True)
        assert len(result) == 1
        _, mod = result[0]
        assert mod.effect_category == 1

    def test_overload_effect_derives_category_5(self):
        """Effect with 'overload' in name → category 5 (only passes when overheated)."""
        rows = [
            _make_effect_row(3831, effect_id=1, effect_category_id=5),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831], simulation_mode=True,
            module_flags=[19], flag_states={19: "overheated"},
        )
        assert len(result) == 1
        _, mod = result[0]
        assert mod.effect_category == 5

    def test_online_effect_derives_category_4(self):
        """Effect with 'online' in name → category 4 (excluded when offline)."""
        rows = [
            _make_effect_row(3831, effect_id=1, effect_category_id=4),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831], simulation_mode=True,
            module_flags=[19], flag_states={19: "active"},
        )
        assert len(result) == 1
        _, mod = result[0]
        assert mod.effect_category == 4

    def test_online_effect_blocked_when_offline(self):
        """Online (cat 4) effects excluded when module is offline."""
        rows = [
            _make_effect_row(3831, effect_id=1, effect_category_id=4),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3831], simulation_mode=True,
            module_flags=[19], flag_states={19: "offline"},
        )
        assert len(result) == 0


class TestLargeShieldExtenderScenario:
    """Regression test: LSE toggling must change shield HP.

    LSE effects have 'Online' suffix in their effectName (e.g.,
    shieldCapacityBonusOnline) → derived as category 4. When offline,
    category 4 is excluded → no shield HP bonus.
    """

    def test_lse_active_produces_modifier(self):
        """LSE online effect (cat 4) included when active."""
        rows = [
            _make_effect_row(3841, effect_id=21,
                             effect_name="shieldCapacityBonusOnline"),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3841], simulation_mode=True,
            module_flags=[19], flag_states={19: "active"},
        )
        assert len(result) == 1
        _, mod = result[0]
        assert mod.effect_category == 4

    def test_lse_offline_produces_no_modifier(self):
        """LSE online effect (cat 4) excluded when offline."""
        rows = [
            _make_effect_row(3841, effect_id=21,
                             effect_name="shieldCapacityBonusOnline"),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3841], simulation_mode=True,
            module_flags=[19], flag_states={19: "offline"},
        )
        assert len(result) == 0

    def test_lse_online_state_includes_effect(self):
        """LSE online effect (cat 4) included when module state is 'online'."""
        rows = [
            _make_effect_row(3841, effect_id=21,
                             effect_name="shieldCapacityBonusOnline"),
        ]
        engine = _make_engine_with_rows(rows)
        result = engine._load_modifiers(
            [3841], simulation_mode=True,
            module_flags=[19], flag_states={19: "online"},
        )
        assert len(result) == 1


class TestFittingStatsRequestModuleStates:
    """Test module_states field on FittingStatsRequest."""

    def test_module_states_field_exists(self):
        from app.services.fitting_stats.models import FittingStatsRequest
        from app.services.fitting_service import FittingItem
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[FittingItem(type_id=3170, flag=19, quantity=1)],
            module_states={19: "offline"},
        )
        assert req.module_states == {19: "offline"}

    def test_module_states_defaults_to_none(self):
        from app.services.fitting_stats.models import FittingStatsRequest
        req = FittingStatsRequest(ship_type_id=24698, items=[])
        assert req.module_states is None

    def test_module_states_multiple_flags(self):
        from app.services.fitting_stats.models import FittingStatsRequest
        from app.services.fitting_service import FittingItem
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[
                FittingItem(type_id=3170, flag=19, quantity=1),
                FittingItem(type_id=3841, flag=20, quantity=1),
            ],
            module_states={19: "overheated", 20: "offline"},
        )
        assert req.module_states[19] == "overheated"
        assert req.module_states[20] == "offline"

    def test_module_states_accepts_all_valid_states(self):
        from app.services.fitting_stats.models import FittingStatsRequest
        req = FittingStatsRequest(
            ship_type_id=24698,
            items=[],
            module_states={19: "offline", 20: "online", 21: "active", 27: "overheated"},
        )
        assert req.module_states[19] == "offline"
        assert req.module_states[27] == "overheated"


class TestOfflineModuleExclusion:
    """Test that offline/online modules are correctly excluded from calculations."""

    def test_is_module_active_with_none_states(self):
        """When module_states is None, all modules are active."""
        from app.services.fitting_stats.service import FittingStatsService
        assert FittingStatsService._is_module_active(19, None) is True

    def test_is_module_active_with_active_state(self):
        from app.services.fitting_stats.service import FittingStatsService
        assert FittingStatsService._is_module_active(19, {19: "active"}) is True

    def test_is_module_active_with_overheated_state(self):
        from app.services.fitting_stats.service import FittingStatsService
        assert FittingStatsService._is_module_active(19, {19: "overheated"}) is True

    def test_is_module_active_with_offline_state(self):
        from app.services.fitting_stats.service import FittingStatsService
        assert FittingStatsService._is_module_active(19, {19: "offline"}) is False

    def test_is_module_active_with_online_state(self):
        from app.services.fitting_stats.service import FittingStatsService
        assert FittingStatsService._is_module_active(19, {19: "online"}) is False

    def test_is_module_online_with_offline_state(self):
        from app.services.fitting_stats.service import FittingStatsService
        assert FittingStatsService._is_module_online(19, {19: "offline"}) is False

    def test_is_module_online_with_online_state(self):
        from app.services.fitting_stats.service import FittingStatsService
        assert FittingStatsService._is_module_online(19, {19: "online"}) is True

    def test_is_module_active_defaults_active_for_missing_flag(self):
        """Modules not in module_states dict default to active."""
        from app.services.fitting_stats.service import FittingStatsService
        assert FittingStatsService._is_module_active(19, {20: "offline"}) is True
