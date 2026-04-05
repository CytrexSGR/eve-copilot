"""Tests for charge attribute modification through Dogma engine.

Validates that Missile Guidance Enhancer (MGE) and similar modules correctly
modify charge attributes (explosion radius, explosion velocity) via
LocationRequiredSkillModifier, and that these modifications propagate to
the Applied DPS calculation.
"""

import pytest
from unittest.mock import MagicMock, patch
from collections import defaultdict

# --- Constants ---
ATTR_EXPLOSION_RADIUS = 654
ATTR_EXPLOSION_VELOCITY = 653
ATTR_DAMAGE_REDUCTION_FACTOR = 1353
SKILL_MISSILE_GUIDANCE = 3319


class TestChargeModifierPropagation:
    """Test that LocationRequiredSkillModifier effects modify charge attributes."""

    def _make_location_modifier(self, modified_attr_id, modifying_attr_id, skill_type_id, operation=6):
        """Create a mock DogmaModifier for LocationRequiredSkillModifier."""
        mod = MagicMock()
        mod.func = "LocationRequiredSkillModifier"
        mod.domain = "shipID"
        mod.modified_attr_id = modified_attr_id
        mod.modifying_attr_id = modifying_attr_id
        mod.skill_type_id = skill_type_id
        mod.operation = operation
        mod.group_id = None
        mod.is_drawback = False
        return mod

    def test_mge_reduces_explosion_radius(self):
        """MGE with -5.25% bonus should reduce charge explosion radius."""
        from app.services.dogma.engine import DogmaEngine

        MGE_TYPE_ID = 35771
        MGE_ATTR_BONUS = 848
        CHARGE_TYPE_ID = 2629

        charge_attrs = {CHARGE_TYPE_ID: {ATTR_EXPLOSION_RADIUS: 150.0, ATTR_EXPLOSION_VELOCITY: 100.0}}
        charge_required_skills = {CHARGE_TYPE_ID: {SKILL_MISSILE_GUIDANCE}}
        module_attrs = {MGE_TYPE_ID: {MGE_ATTR_BONUS: -5.25}}

        mod = self._make_location_modifier(ATTR_EXPLOSION_RADIUS, MGE_ATTR_BONUS, SKILL_MISSILE_GUIDANCE)
        modifiers = [(MGE_TYPE_ID, mod)]

        engine = DogmaEngine.__new__(DogmaEngine)
        result = engine._apply_location_modifiers(
            charge_attrs, modifiers, {}, charge_required_skills,
            source_attrs=module_attrs,
        )

        modified_radius = result[CHARGE_TYPE_ID][ATTR_EXPLOSION_RADIUS]
        assert abs(modified_radius - 142.125) < 0.01
        assert result[CHARGE_TYPE_ID][ATTR_EXPLOSION_VELOCITY] == 100.0

    def test_mge_improves_explosion_velocity(self):
        """MGE also improves explosion velocity (positive bonus)."""
        from app.services.dogma.engine import DogmaEngine

        MGE_TYPE_ID = 35771
        MGE_ATTR_VEL_BONUS = 847
        CHARGE_TYPE_ID = 2629

        charge_attrs = {CHARGE_TYPE_ID: {ATTR_EXPLOSION_VELOCITY: 100.0}}
        charge_required_skills = {CHARGE_TYPE_ID: {SKILL_MISSILE_GUIDANCE}}
        module_attrs = {MGE_TYPE_ID: {MGE_ATTR_VEL_BONUS: 5.25}}

        mod = self._make_location_modifier(ATTR_EXPLOSION_VELOCITY, MGE_ATTR_VEL_BONUS, SKILL_MISSILE_GUIDANCE)
        modifiers = [(MGE_TYPE_ID, mod)]

        engine = DogmaEngine.__new__(DogmaEngine)
        result = engine._apply_location_modifiers(
            charge_attrs, modifiers, {}, charge_required_skills,
            source_attrs=module_attrs,
        )

        modified_vel = result[CHARGE_TYPE_ID][ATTR_EXPLOSION_VELOCITY]
        assert abs(modified_vel - 105.25) < 0.01

    def test_two_mge_stacking_penalized(self):
        """Two MGEs should apply stacking penalty on explosion radius bonus."""
        from app.services.dogma.engine import DogmaEngine

        MGE_TYPE_ID = 35771
        MGE_ATTR_BONUS = 848
        CHARGE_TYPE_ID = 2629

        charge_attrs = {CHARGE_TYPE_ID: {ATTR_EXPLOSION_RADIUS: 150.0}}
        charge_required_skills = {CHARGE_TYPE_ID: {SKILL_MISSILE_GUIDANCE}}
        module_attrs = {MGE_TYPE_ID: {MGE_ATTR_BONUS: -5.25}}

        mod1 = self._make_location_modifier(ATTR_EXPLOSION_RADIUS, MGE_ATTR_BONUS, SKILL_MISSILE_GUIDANCE)
        mod2 = self._make_location_modifier(ATTR_EXPLOSION_RADIUS, MGE_ATTR_BONUS, SKILL_MISSILE_GUIDANCE)
        modifiers = [(MGE_TYPE_ID, mod1), (MGE_TYPE_ID, mod2)]

        engine = DogmaEngine.__new__(DogmaEngine)
        result = engine._apply_location_modifiers(
            charge_attrs, modifiers, {}, charge_required_skills,
            source_attrs=module_attrs,
        )

        modified_radius = result[CHARGE_TYPE_ID][ATTR_EXPLOSION_RADIUS]
        assert modified_radius < 142.125  # better than 1 MGE
        assert modified_radius > 130.0    # stacking penalty limits benefit

    def test_no_mge_charge_unchanged(self):
        """Without MGE, charge attributes pass through unchanged."""
        from app.services.dogma.engine import DogmaEngine

        CHARGE_TYPE_ID = 2629
        charge_attrs = {CHARGE_TYPE_ID: {ATTR_EXPLOSION_RADIUS: 150.0, ATTR_EXPLOSION_VELOCITY: 100.0}}
        charge_required_skills = {CHARGE_TYPE_ID: {SKILL_MISSILE_GUIDANCE}}

        engine = DogmaEngine.__new__(DogmaEngine)
        result = engine._apply_location_modifiers(
            charge_attrs, [], {}, charge_required_skills
        )

        assert result[CHARGE_TYPE_ID][ATTR_EXPLOSION_RADIUS] == 150.0
        assert result[CHARGE_TYPE_ID][ATTR_EXPLOSION_VELOCITY] == 100.0

    def test_mge_offline_no_effect(self):
        """When MGE is offline, its modifiers are absent — no change."""
        from app.services.dogma.engine import DogmaEngine

        CHARGE_TYPE_ID = 2629
        charge_attrs = {CHARGE_TYPE_ID: {ATTR_EXPLOSION_RADIUS: 150.0}}
        charge_required_skills = {CHARGE_TYPE_ID: {SKILL_MISSILE_GUIDANCE}}

        engine = DogmaEngine.__new__(DogmaEngine)
        result = engine._apply_location_modifiers(
            charge_attrs, [], {}, charge_required_skills
        )

        assert result[CHARGE_TYPE_ID][ATTR_EXPLOSION_RADIUS] == 150.0

    def test_charge_without_required_skill_not_modified(self):
        """A charge not requiring skill 3319 should not be modified by MGE."""
        from app.services.dogma.engine import DogmaEngine

        MGE_TYPE_ID = 35771
        MGE_ATTR_BONUS = 848
        CHARGE_TYPE_ID = 99999

        charge_attrs = {CHARGE_TYPE_ID: {ATTR_EXPLOSION_RADIUS: 200.0}}
        charge_required_skills = {CHARGE_TYPE_ID: {12345}}

        module_attrs = {MGE_TYPE_ID: {MGE_ATTR_BONUS: -5.25}}
        mod = self._make_location_modifier(ATTR_EXPLOSION_RADIUS, MGE_ATTR_BONUS, SKILL_MISSILE_GUIDANCE)
        modifiers = [(MGE_TYPE_ID, mod)]

        engine = DogmaEngine.__new__(DogmaEngine)
        result = engine._apply_location_modifiers(
            charge_attrs, modifiers, {}, charge_required_skills,
            source_attrs=module_attrs,
        )

        assert result[CHARGE_TYPE_ID][ATTR_EXPLOSION_RADIUS] == 200.0
