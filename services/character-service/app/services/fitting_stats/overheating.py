"""Overheating bonus and heat damage calculations.

Overload bonuses in EVE use effectCategoryID 5 and operation 6 (postPercent).
They are self-modifying (domain: itemID, func: ItemModifier) and NOT stacking penalized.
The Dogma engine already applies these when module state is "overheated" -- this module
provides constants and helper functions for heat damage and display.
"""

# Overload bonus source attribute IDs (on the module)
ATTR_OVERLOAD_ROF_BONUS = 1205
ATTR_OVERLOAD_DURATION_BONUS = 1206
ATTR_OVERLOAD_HARDENING_BONUS = 1208
ATTR_OVERLOAD_DAMAGE_MODIFIER = 1210
ATTR_OVERLOAD_RANGE_BONUS = 1222
ATTR_OVERLOAD_SPEED_BONUS = 1223
ATTR_OVERLOAD_ECM_BONUS = 1225
ATTR_OVERLOAD_ARMOR_REP = 1230
ATTR_OVERLOAD_SHIELD_BOOST = 1231

# Heat damage
ATTR_HEAT_DAMAGE = 1211
ATTR_HEAT_GENERATION_MULT = 1213

# Thermodynamics skill type ID
SKILL_THERMODYNAMICS = 28164

# All overload bonus attrs (for quick lookup)
OVERLOAD_BONUS_ATTRS = frozenset({
    ATTR_OVERLOAD_ROF_BONUS, ATTR_OVERLOAD_DURATION_BONUS,
    ATTR_OVERLOAD_HARDENING_BONUS, ATTR_OVERLOAD_DAMAGE_MODIFIER,
    ATTR_OVERLOAD_RANGE_BONUS, ATTR_OVERLOAD_SPEED_BONUS,
    ATTR_OVERLOAD_ECM_BONUS, ATTR_OVERLOAD_ARMOR_REP,
    ATTR_OVERLOAD_SHIELD_BOOST,
})


def calculate_overload_bonus(base_value: float, overload_bonus_pct: float) -> float:
    """Apply overload bonus percentage to a base value.

    Overload bonuses use operation 6 (postPercent) -- self-modifying.
    NOT stacking penalized.
    """
    return base_value * (1.0 + overload_bonus_pct / 100.0)


def calculate_heat_damage(
    heat_damage_per_cycle: float,
    thermodynamics_level: int = 0,
) -> float:
    """Calculate actual heat damage per cycle after Thermodynamics skill.

    Thermodynamics reduces heat damage by 5% per level.
    Level 5 = 25% reduction.
    """
    if heat_damage_per_cycle <= 0:
        return 0.0
    reduction = 0.05 * thermodynamics_level
    return round(heat_damage_per_cycle * (1.0 - reduction), 2)
