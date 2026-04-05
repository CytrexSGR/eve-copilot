"""Tests for projected effects system (webs, paints, neuts, remote reps).

Covers:
- ProjectedEffectInput model validation
- Stacking penalty formula
- Single web reduces speed by 60%
- Two webs with stacking penalty (1st 100%, 2nd 86.9%)
- Single paint increases sig by 30%
- Two paints with stacking penalty
- Neut reports cap drain per second
- Remote shield/armor rep reports incoming rep per second
- Empty effects no change
- Original attrs not mutated
- Unknown effect type ignored
- Preset validation
- Target projected affects applied DPS (target velocity/sig)
"""

import math
import pytest

from app.services.fitting_stats.projected import (
    STACKING_PENALTIES,
    PROJECTED_DEFINITIONS,
    PROJECTED_PRESETS,
    _stacking_penalty,
    apply_projected_effects,
)
from app.services.fitting_stats.models import ProjectedEffectInput


# ---------------------------------------------------------------------------
# ProjectedEffectInput model
# ---------------------------------------------------------------------------

class TestProjectedEffectInputModel:
    """Tests for the ProjectedEffectInput Pydantic model."""

    def test_valid_web(self):
        """Create a valid web effect."""
        effect = ProjectedEffectInput(effect_type="web", strength=60.0)
        assert effect.effect_type == "web"
        assert effect.strength == 60.0
        assert effect.count == 1

    def test_valid_paint(self):
        """Create a valid paint effect."""
        effect = ProjectedEffectInput(effect_type="paint", strength=30.0)
        assert effect.effect_type == "paint"
        assert effect.strength == 30.0

    def test_valid_neut(self):
        """Create a valid neut effect."""
        effect = ProjectedEffectInput(effect_type="neut", strength=600.0, count=2)
        assert effect.effect_type == "neut"
        assert effect.strength == 600.0
        assert effect.count == 2

    def test_valid_remote_shield(self):
        """Create a valid remote shield rep effect."""
        effect = ProjectedEffectInput(effect_type="remote_shield", strength=350.0)
        assert effect.effect_type == "remote_shield"
        assert effect.strength == 350.0

    def test_valid_remote_armor(self):
        """Create a valid remote armor rep effect."""
        effect = ProjectedEffectInput(effect_type="remote_armor", strength=350.0)
        assert effect.effect_type == "remote_armor"
        assert effect.strength == 350.0

    def test_default_count_is_one(self):
        """Default count should be 1."""
        effect = ProjectedEffectInput(effect_type="web", strength=60.0)
        assert effect.count == 1

    def test_custom_count(self):
        """Custom count can be set."""
        effect = ProjectedEffectInput(effect_type="web", strength=60.0, count=3)
        assert effect.count == 3

    def test_zero_strength(self):
        """Zero strength is valid (no effect)."""
        effect = ProjectedEffectInput(effect_type="web", strength=0.0)
        assert effect.strength == 0.0


# ---------------------------------------------------------------------------
# Stacking penalty formula
# ---------------------------------------------------------------------------

class TestStackingPenalty:
    """Tests for EVE stacking penalty formula."""

    def test_first_application_full(self):
        """First application (n=0) has 100% effectiveness."""
        assert _stacking_penalty(0) == pytest.approx(1.0, rel=1e-4)

    def test_second_application(self):
        """Second application (n=1) has ~86.9% effectiveness."""
        assert _stacking_penalty(1) == pytest.approx(0.8691, rel=1e-4)

    def test_third_application(self):
        """Third application (n=2) has ~57.1% effectiveness."""
        assert _stacking_penalty(2) == pytest.approx(0.5706, rel=1e-3)

    def test_fourth_application(self):
        """Fourth application (n=3) has ~28.3% effectiveness."""
        assert _stacking_penalty(3) == pytest.approx(0.2830, rel=1e-3)

    def test_fifth_application(self):
        """Fifth application (n=4) has ~10.6% effectiveness."""
        assert _stacking_penalty(4) == pytest.approx(0.1059, rel=1e-3)

    def test_sixth_application(self):
        """Sixth application (n=5) has ~3.0% effectiveness."""
        assert _stacking_penalty(5) == pytest.approx(0.0300, rel=1e-3)

    def test_beyond_table_uses_formula(self):
        """Beyond the lookup table, the formula is used."""
        n = 6
        expected = math.exp(-((n / 2.67) ** 2))
        assert _stacking_penalty(n) == pytest.approx(expected, rel=1e-6)

    def test_penalty_decreases_monotonically(self):
        """Stacking penalties should always decrease."""
        for i in range(10):
            assert _stacking_penalty(i) >= _stacking_penalty(i + 1)

    def test_penalties_are_positive(self):
        """All penalties should be positive."""
        for i in range(20):
            assert _stacking_penalty(i) > 0


# ---------------------------------------------------------------------------
# apply_projected_effects — web
# ---------------------------------------------------------------------------

class TestApplyWeb:
    """Tests for web (velocity reduction) projected effect."""

    def test_single_web_60_percent(self):
        """Single 60% web reduces maxVelocity by 60%."""
        attrs = {37: 1000.0}  # maxVelocity
        result = apply_projected_effects(attrs, [
            {"effect_type": "web", "strength": 60.0, "count": 1}
        ])
        # 1st application: 60% * 1.0 penalty = 60% reduction
        expected = 1000.0 * (1.0 - 60.0 / 100.0)
        assert result["modified_attrs"][37] == pytest.approx(expected, rel=1e-4)

    def test_single_web_90_percent(self):
        """Single 90% web (officer) reduces maxVelocity by 90%."""
        attrs = {37: 500.0}
        result = apply_projected_effects(attrs, [
            {"effect_type": "web", "strength": 90.0, "count": 1}
        ])
        expected = 500.0 * (1.0 - 90.0 / 100.0)
        assert result["modified_attrs"][37] == pytest.approx(expected, rel=1e-4)

    def test_two_webs_stacking_penalized(self):
        """Two 60% webs: 1st full, 2nd stacking penalized."""
        attrs = {37: 1000.0}
        result = apply_projected_effects(attrs, [
            {"effect_type": "web", "strength": 60.0, "count": 2}
        ])
        # 1st web: 60% * 1.0 = 60% reduction
        # 2nd web: 60% * 0.8691 = 52.146% reduction
        vel = 1000.0
        vel *= (1.0 - 60.0 * 1.0 / 100.0)        # 400.0
        vel *= (1.0 - 60.0 * 0.8691 / 100.0)      # 400 * (1 - 0.52146) = ~191.42
        assert result["modified_attrs"][37] == pytest.approx(vel, rel=1e-3)

    def test_three_webs_stacking_penalized(self):
        """Three webs with diminishing returns."""
        attrs = {37: 1000.0}
        result = apply_projected_effects(attrs, [
            {"effect_type": "web", "strength": 60.0, "count": 3}
        ])
        vel = 1000.0
        vel *= (1.0 - 60.0 * STACKING_PENALTIES[0] / 100.0)
        vel *= (1.0 - 60.0 * STACKING_PENALTIES[1] / 100.0)
        vel *= (1.0 - 60.0 * STACKING_PENALTIES[2] / 100.0)
        assert result["modified_attrs"][37] == pytest.approx(vel, rel=1e-3)

    def test_web_zero_strength(self):
        """Web with 0 strength does nothing."""
        attrs = {37: 1000.0}
        result = apply_projected_effects(attrs, [
            {"effect_type": "web", "strength": 0.0, "count": 1}
        ])
        assert result["modified_attrs"][37] == pytest.approx(1000.0, rel=1e-6)

    def test_web_summary_entry(self):
        """Web effect should produce a summary entry."""
        attrs = {37: 1000.0}
        result = apply_projected_effects(attrs, [
            {"effect_type": "web", "strength": 60.0, "count": 1}
        ])
        assert len(result["summary"]) == 1
        summary = result["summary"][0]
        assert summary["effect_type"] == "web"
        assert summary["count"] == 1
        assert summary["strength"] == 60.0


# ---------------------------------------------------------------------------
# apply_projected_effects — paint
# ---------------------------------------------------------------------------

class TestApplyPaint:
    """Tests for target painter (signature radius increase) projected effect."""

    def test_single_paint_30_percent(self):
        """Single 30% paint increases signatureRadius by 30%."""
        attrs = {552: 150.0}  # signatureRadius
        result = apply_projected_effects(attrs, [
            {"effect_type": "paint", "strength": 30.0, "count": 1}
        ])
        expected = 150.0 * (1.0 + 30.0 / 100.0)
        assert result["modified_attrs"][552] == pytest.approx(expected, rel=1e-4)

    def test_two_paints_stacking_penalized(self):
        """Two 30% paints with stacking penalty."""
        attrs = {552: 150.0}
        result = apply_projected_effects(attrs, [
            {"effect_type": "paint", "strength": 30.0, "count": 2}
        ])
        sig = 150.0
        sig *= (1.0 + 30.0 * STACKING_PENALTIES[0] / 100.0)
        sig *= (1.0 + 30.0 * STACKING_PENALTIES[1] / 100.0)
        assert result["modified_attrs"][552] == pytest.approx(sig, rel=1e-3)

    def test_paint_summary_entry(self):
        """Paint effect should produce a summary entry."""
        attrs = {552: 150.0}
        result = apply_projected_effects(attrs, [
            {"effect_type": "paint", "strength": 30.0, "count": 2}
        ])
        assert len(result["summary"]) == 1
        summary = result["summary"][0]
        assert summary["effect_type"] == "paint"
        assert summary["count"] == 2


# ---------------------------------------------------------------------------
# apply_projected_effects — neut
# ---------------------------------------------------------------------------

class TestApplyNeut:
    """Tests for energy neutralizer projected effect."""

    def test_single_neut(self):
        """Single neut reports cap drain per second."""
        attrs = {37: 1000.0}
        result = apply_projected_effects(attrs, [
            {"effect_type": "neut", "strength": 600.0, "count": 1}
        ])
        # 600 GJ / 12s default cycle time = 50 GJ/s
        assert result["cap_drain_per_s"] == pytest.approx(50.0, rel=1e-4)

    def test_two_neuts(self):
        """Two neuts double the cap drain."""
        attrs = {}
        result = apply_projected_effects(attrs, [
            {"effect_type": "neut", "strength": 600.0, "count": 2}
        ])
        # 2 * 600 / 12 = 100 GJ/s
        assert result["cap_drain_per_s"] == pytest.approx(100.0, rel=1e-4)

    def test_neut_not_stacking_penalized(self):
        """Neuts are NOT stacking penalized — 3 neuts = 3x drain."""
        attrs = {}
        result = apply_projected_effects(attrs, [
            {"effect_type": "neut", "strength": 600.0, "count": 3}
        ])
        # 3 * 600 / 12 = 150 GJ/s
        assert result["cap_drain_per_s"] == pytest.approx(150.0, rel=1e-4)

    def test_neut_does_not_modify_attrs(self):
        """Neut should not modify any ship attributes."""
        attrs = {37: 1000.0, 552: 150.0}
        result = apply_projected_effects(attrs, [
            {"effect_type": "neut", "strength": 600.0, "count": 1}
        ])
        assert result["modified_attrs"][37] == 1000.0
        assert result["modified_attrs"][552] == 150.0

    def test_neut_summary(self):
        """Neut summary shows drain per second."""
        attrs = {}
        result = apply_projected_effects(attrs, [
            {"effect_type": "neut", "strength": 600.0, "count": 1}
        ])
        summary = result["summary"][0]
        assert summary["effect_type"] == "neut"
        assert summary["cap_drain_per_s"] == pytest.approx(50.0, rel=1e-4)


# ---------------------------------------------------------------------------
# apply_projected_effects — remote reps
# ---------------------------------------------------------------------------

class TestApplyRemoteRep:
    """Tests for remote repair projected effects."""

    def test_remote_shield_rep(self):
        """Remote shield rep reports incoming HP per second."""
        attrs = {}
        result = apply_projected_effects(attrs, [
            {"effect_type": "remote_shield", "strength": 350.0, "count": 1}
        ])
        # 350 HP / 5s default cycle time = 70 HP/s
        assert result["incoming_rep_shield"] == pytest.approx(70.0, rel=1e-4)
        assert result["incoming_rep_armor"] == pytest.approx(0.0, rel=1e-6)

    def test_remote_armor_rep(self):
        """Remote armor rep reports incoming HP per second."""
        attrs = {}
        result = apply_projected_effects(attrs, [
            {"effect_type": "remote_armor", "strength": 350.0, "count": 1}
        ])
        assert result["incoming_rep_armor"] == pytest.approx(70.0, rel=1e-4)
        assert result["incoming_rep_shield"] == pytest.approx(0.0, rel=1e-6)

    def test_two_remote_shield_reps(self):
        """Two remote shield reps stack linearly (no stacking penalty)."""
        attrs = {}
        result = apply_projected_effects(attrs, [
            {"effect_type": "remote_shield", "strength": 350.0, "count": 2}
        ])
        # 2 * 350 / 5 = 140 HP/s
        assert result["incoming_rep_shield"] == pytest.approx(140.0, rel=1e-4)

    def test_mixed_remote_reps(self):
        """Shield and armor remote reps are tracked separately."""
        attrs = {}
        result = apply_projected_effects(attrs, [
            {"effect_type": "remote_shield", "strength": 350.0, "count": 2},
            {"effect_type": "remote_armor", "strength": 300.0, "count": 1},
        ])
        assert result["incoming_rep_shield"] == pytest.approx(140.0, rel=1e-4)
        assert result["incoming_rep_armor"] == pytest.approx(60.0, rel=1e-4)

    def test_remote_rep_summary(self):
        """Remote rep summary shows HP per second."""
        attrs = {}
        result = apply_projected_effects(attrs, [
            {"effect_type": "remote_shield", "strength": 350.0, "count": 2}
        ])
        summary = result["summary"][0]
        assert summary["effect_type"] == "remote_shield"
        assert summary["hp_per_s"] == pytest.approx(140.0, rel=1e-4)


# ---------------------------------------------------------------------------
# apply_projected_effects — edge cases
# ---------------------------------------------------------------------------

class TestApplyProjectedEdgeCases:
    """Edge cases for apply_projected_effects."""

    def test_empty_effects_no_change(self):
        """Empty effects list returns original attrs unchanged."""
        attrs = {37: 1000.0, 552: 150.0}
        result = apply_projected_effects(attrs, [])
        assert result["modified_attrs"][37] == 1000.0
        assert result["modified_attrs"][552] == 150.0
        assert result["cap_drain_per_s"] == 0.0
        assert result["incoming_rep_shield"] == 0.0
        assert result["incoming_rep_armor"] == 0.0
        assert result["summary"] == []

    def test_original_attrs_not_mutated(self):
        """apply_projected_effects MUST NOT mutate the input dict."""
        attrs = {37: 1000.0, 552: 150.0}
        original_vel = attrs[37]
        original_sig = attrs[552]
        result = apply_projected_effects(attrs, [
            {"effect_type": "web", "strength": 60.0, "count": 1},
            {"effect_type": "paint", "strength": 30.0, "count": 1},
        ])
        # Input unchanged
        assert attrs[37] == original_vel
        assert attrs[552] == original_sig
        # Result changed
        assert result["modified_attrs"][37] != original_vel
        assert result["modified_attrs"][552] != original_sig

    def test_unknown_effect_type_ignored(self):
        """Unknown effect types are silently ignored."""
        attrs = {37: 1000.0}
        result = apply_projected_effects(attrs, [
            {"effect_type": "warp_disrupt", "strength": 1.0, "count": 1}
        ])
        assert result["modified_attrs"][37] == 1000.0
        assert result["summary"] == []

    def test_missing_attribute_in_ship(self):
        """Web on ship without maxVelocity attribute is handled gracefully."""
        attrs = {552: 150.0}  # No attr 37
        result = apply_projected_effects(attrs, [
            {"effect_type": "web", "strength": 60.0, "count": 1}
        ])
        # Paint on sig should still work
        assert 37 not in result["modified_attrs"]
        assert result["modified_attrs"][552] == 150.0

    def test_combined_web_and_paint(self):
        """Web and paint together modify different attributes."""
        attrs = {37: 1000.0, 552: 150.0}
        result = apply_projected_effects(attrs, [
            {"effect_type": "web", "strength": 60.0, "count": 1},
            {"effect_type": "paint", "strength": 30.0, "count": 1},
        ])
        assert result["modified_attrs"][37] == pytest.approx(400.0, rel=1e-4)
        assert result["modified_attrs"][552] == pytest.approx(195.0, rel=1e-4)

    def test_combined_all_types(self):
        """All effect types in one call."""
        attrs = {37: 1000.0, 552: 150.0}
        result = apply_projected_effects(attrs, [
            {"effect_type": "web", "strength": 60.0, "count": 1},
            {"effect_type": "paint", "strength": 30.0, "count": 1},
            {"effect_type": "neut", "strength": 600.0, "count": 1},
            {"effect_type": "remote_shield", "strength": 350.0, "count": 1},
            {"effect_type": "remote_armor", "strength": 300.0, "count": 1},
        ])
        assert result["modified_attrs"][37] == pytest.approx(400.0, rel=1e-4)
        assert result["modified_attrs"][552] == pytest.approx(195.0, rel=1e-4)
        assert result["cap_drain_per_s"] == pytest.approx(50.0, rel=1e-4)
        assert result["incoming_rep_shield"] == pytest.approx(70.0, rel=1e-4)
        assert result["incoming_rep_armor"] == pytest.approx(60.0, rel=1e-4)
        assert len(result["summary"]) == 5

    def test_web_and_paint_stacking_independent(self):
        """Webs and paints have separate stacking penalty counters."""
        attrs = {37: 1000.0, 552: 150.0}
        result = apply_projected_effects(attrs, [
            {"effect_type": "web", "strength": 60.0, "count": 2},
            {"effect_type": "paint", "strength": 30.0, "count": 2},
        ])
        # Webs: independent stacking counter
        vel = 1000.0
        vel *= (1.0 - 60.0 * STACKING_PENALTIES[0] / 100.0)
        vel *= (1.0 - 60.0 * STACKING_PENALTIES[1] / 100.0)
        # Paints: independent stacking counter
        sig = 150.0
        sig *= (1.0 + 30.0 * STACKING_PENALTIES[0] / 100.0)
        sig *= (1.0 + 30.0 * STACKING_PENALTIES[1] / 100.0)
        assert result["modified_attrs"][37] == pytest.approx(vel, rel=1e-3)
        assert result["modified_attrs"][552] == pytest.approx(sig, rel=1e-3)


# ---------------------------------------------------------------------------
# PROJECTED_DEFINITIONS structure validation
# ---------------------------------------------------------------------------

class TestProjectedDefinitions:
    """Validate PROJECTED_DEFINITIONS structure."""

    def test_web_definition(self):
        """Web definition exists and targets maxVelocity."""
        defn = PROJECTED_DEFINITIONS["web"]
        assert defn["attribute"] == 37
        assert defn["operation"] == "reduce_percent"
        assert defn["stacking_penalized"] is True

    def test_paint_definition(self):
        """Paint definition exists and targets signatureRadius."""
        defn = PROJECTED_DEFINITIONS["paint"]
        assert defn["attribute"] == 552
        assert defn["operation"] == "increase_percent"
        assert defn["stacking_penalized"] is True

    def test_neut_definition(self):
        """Neut definition exists and is not stacking penalized."""
        defn = PROJECTED_DEFINITIONS["neut"]
        assert defn["attribute"] is None
        assert defn["operation"] == "cap_drain"
        assert defn["stacking_penalized"] is False

    def test_remote_shield_definition(self):
        """Remote shield rep definition exists."""
        defn = PROJECTED_DEFINITIONS["remote_shield"]
        assert defn["operation"] == "incoming_rep"
        assert defn["stacking_penalized"] is False

    def test_remote_armor_definition(self):
        """Remote armor rep definition exists."""
        defn = PROJECTED_DEFINITIONS["remote_armor"]
        assert defn["operation"] == "incoming_rep"
        assert defn["stacking_penalized"] is False

    def test_all_definitions_have_required_keys(self):
        """All definitions must have attribute, operation, stacking_penalized."""
        for name, defn in PROJECTED_DEFINITIONS.items():
            assert "attribute" in defn, f"{name} missing 'attribute'"
            assert "operation" in defn, f"{name} missing 'operation'"
            assert "stacking_penalized" in defn, f"{name} missing 'stacking_penalized'"


# ---------------------------------------------------------------------------
# PROJECTED_PRESETS validation
# ---------------------------------------------------------------------------

class TestProjectedPresets:
    """Validate PROJECTED_PRESETS structure."""

    def test_single_web_preset(self):
        """single_web preset has one 60% web."""
        preset = PROJECTED_PRESETS["single_web"]
        assert len(preset) == 1
        assert preset[0]["effect_type"] == "web"
        assert preset[0]["strength"] == 60.0
        assert preset[0]["count"] == 1

    def test_double_web_preset(self):
        """double_web preset has two 60% webs."""
        preset = PROJECTED_PRESETS["double_web"]
        assert len(preset) == 1
        assert preset[0]["count"] == 2

    def test_web_paint_preset(self):
        """web_paint preset has one web and one paint."""
        preset = PROJECTED_PRESETS["web_paint"]
        assert len(preset) == 2
        types = [p["effect_type"] for p in preset]
        assert "web" in types
        assert "paint" in types

    def test_heavy_neut_preset(self):
        """heavy_neut preset has one 600 GJ neut."""
        preset = PROJECTED_PRESETS["heavy_neut"]
        assert len(preset) == 1
        assert preset[0]["effect_type"] == "neut"
        assert preset[0]["strength"] == 600.0

    def test_logi_shield_preset(self):
        """logi_shield preset has 2 remote shield reps."""
        preset = PROJECTED_PRESETS["logi_shield"]
        assert len(preset) == 1
        assert preset[0]["effect_type"] == "remote_shield"
        assert preset[0]["count"] == 2

    def test_logi_armor_preset(self):
        """logi_armor preset has 2 remote armor reps."""
        preset = PROJECTED_PRESETS["logi_armor"]
        assert len(preset) == 1
        assert preset[0]["effect_type"] == "remote_armor"
        assert preset[0]["count"] == 2

    def test_all_presets_reference_valid_effect_types(self):
        """All presets reference effect types defined in PROJECTED_DEFINITIONS."""
        for name, effects in PROJECTED_PRESETS.items():
            for e in effects:
                assert e["effect_type"] in PROJECTED_DEFINITIONS, (
                    f"Preset '{name}' references unknown effect_type '{e['effect_type']}'"
                )

    def test_preset_count(self):
        """Should have exactly 7 presets."""
        assert len(PROJECTED_PRESETS) == 7


# ---------------------------------------------------------------------------
# STACKING_PENALTIES table
# ---------------------------------------------------------------------------

class TestStackingPenaltiesTable:
    """Validate the STACKING_PENALTIES lookup table."""

    def test_table_length(self):
        """Table should have 6 entries."""
        assert len(STACKING_PENALTIES) == 6

    def test_first_entry_is_one(self):
        """First entry must be 1.0 (100%)."""
        assert STACKING_PENALTIES[0] == 1.0

    def test_entries_are_decreasing(self):
        """Entries must be monotonically decreasing."""
        for i in range(len(STACKING_PENALTIES) - 1):
            assert STACKING_PENALTIES[i] > STACKING_PENALTIES[i + 1]

    def test_all_positive(self):
        """All entries must be positive."""
        for p in STACKING_PENALTIES:
            assert p > 0
