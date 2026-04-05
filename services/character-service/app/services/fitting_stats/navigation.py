"""Navigation — propmod speed effects (AB/MWD)."""

from typing import List

from psycopg2.extras import RealDictCursor

from app.services.fitting_service import FittingItem
from .constants import (
    EFFECT_AFTERBURNER, EFFECT_MWD,
    ATTR_SPEED_BOOST_FACTOR, ATTR_SPEED_FACTOR,
    ATTR_MASS_ADDITION, ATTR_SIG_RADIUS_MOD,
    ATTR_MASS, ATTR_MAX_VELOCITY, ATTR_SIG_RADIUS,
    DEFAULT_FITTING_SKILL_LEVEL,
    SKILL_ACCELERATION_CONTROL,
)


class NavigationMixin:
    """Mixin providing _apply_propmod_effects."""

    def _apply_propmod_effects(self, ship_attrs: dict, items: List[FittingItem],
                               skill_levels=None) -> dict:
        """Apply AB/MWD speed effects (hardcoded, not in modifierInfo).

        EVE speed formula: velocity * (1 + speedBoostFactor/100 * thrust/mass)
        MWD additionally: +massAddition to mass.
        Only one propmod can be active at a time.

        AB and MWD share groupID 46 in SDE, so we distinguish them by effect:
        - Effect 6731 = moduleBonusAfterburner
        - Effect 6730 = moduleBonusMicrowarpdrive
        """
        # Find mid-slot items
        mid_items = [i for i in items if 19 <= i.flag <= 26]
        if not mid_items:
            return ship_attrs

        # Check which mid-slot modules are propmods (AB or MWD) via effects
        unique_mids = list(set(i.type_id for i in mid_items))
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT "typeID", "effectID"
                FROM "dgmTypeEffects"
                WHERE "typeID" = ANY(%s)
                  AND "effectID" IN (%s, %s)
            """, (unique_mids, EFFECT_AFTERBURNER, EFFECT_MWD))
            effect_map = {row["typeID"]: row["effectID"] for row in cur.fetchall()}

        # Find first propmod (only one active at a time)
        propmod_type_id = None
        propmod_effect = None
        for item in mid_items:
            eff = effect_map.get(item.type_id)
            if eff in (EFFECT_AFTERBURNER, EFFECT_MWD):
                propmod_type_id = item.type_id
                propmod_effect = eff
                break

        if propmod_type_id is None:
            return ship_attrs

        # Load propmod attributes
        prop_attr_ids = [ATTR_SPEED_BOOST_FACTOR, ATTR_SPEED_FACTOR, ATTR_MASS_ADDITION, ATTR_SIG_RADIUS_MOD]
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT "attributeID",
                       COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes"
                WHERE "typeID" = %s AND "attributeID" = ANY(%s)
            """, (propmod_type_id, prop_attr_ids))
            prop_attrs = {row["attributeID"]: row["value"] for row in cur.fetchall()}

        speed_factor = prop_attrs.get(ATTR_SPEED_BOOST_FACTOR, 0)
        thrust = prop_attrs.get(ATTR_SPEED_FACTOR, 0)
        mass = ship_attrs.get(ATTR_MASS, 1)

        if speed_factor <= 0 or thrust <= 0 or mass <= 0:
            return ship_attrs

        result = dict(ship_attrs)

        # Both AB and MWD add mass via massAddition attribute when active.
        # MWD additionally has sig radius bloom.
        mass_add = prop_attrs.get(ATTR_MASS_ADDITION, 0)
        if mass_add > 0:
            result[ATTR_MASS] = mass + mass_add
            mass = mass + mass_add

        if propmod_effect == EFFECT_MWD:
            # MWD sig bloom: moduleBonusMicrowarpdrive has NO modifierInfo,
            # so this must be applied manually. PostPercent: sig *= (1 + value/100)
            sig_mod = prop_attrs.get(ATTR_SIG_RADIUS_MOD, 0)
            if sig_mod > 0:
                result[ATTR_SIG_RADIUS] = result.get(ATTR_SIG_RADIUS, 0) * (1 + sig_mod / 100)

        # Speed formula: v * (1 + speedBoostFactor/100 * thrust/mass * ac_skill)
        # Acceleration Control: +5%/level to propmod speed boost
        ac_level = DEFAULT_FITTING_SKILL_LEVEL
        if skill_levels and SKILL_ACCELERATION_CONTROL in skill_levels:
            ac_level = skill_levels[SKILL_ACCELERATION_CONTROL]
        elif skill_levels is not None and SKILL_ACCELERATION_CONTROL not in skill_levels:
            ac_level = 0  # Character doesn't have the skill
        ac_mult = 1 + (5.0 * ac_level) / 100
        velocity = result.get(ATTR_MAX_VELOCITY, 0)
        speed_boost = speed_factor / 100.0 * thrust / mass * ac_mult
        result[ATTR_MAX_VELOCITY] = velocity * (1 + speed_boost)

        return result
