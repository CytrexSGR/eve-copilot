"""Triglavian spool-up DPS calculations.

Triglavian Entropic Disintegrators ramp up damage over consecutive firing cycles.
SDE attributes:
  - 2733 (damageMultiplierBonusPerCycle): e.g. 0.05 = 5% per cycle
  - 2734 (damageMultiplierBonusMax): e.g. 1.5 = +150% at max spool

Formula: effectiveMult = baseMult * (1 + min(cycle * bonusPerCycle, maxBonus))
Cycles to max: ceil(maxBonus / bonusPerCycle)
"""

from math import ceil

# SDE attribute IDs for spool-up
ATTR_SPOOL_BONUS_PER_CYCLE = 2733  # damageMultiplierBonusPerCycle
ATTR_SPOOL_MAX_BONUS = 2734        # damageMultiplierBonusMax


def calculate_spool_dps(
    base_dps: float,
    bonus_per_cycle: float,
    max_bonus: float,
    cycle_time_ms: float = 0.0,
) -> dict:
    """Calculate spool-up DPS variants for Triglavian weapons.

    Args:
        base_dps: Base weapon DPS (at cycle 0, no spool).
        bonus_per_cycle: Damage multiplier bonus per cycle (e.g. 0.05 for 5%).
        max_bonus: Maximum cumulative damage bonus (e.g. 1.5 for +150%).
        cycle_time_ms: Weapon cycle time in milliseconds (for time_to_max calculation).

    Returns:
        Dict with keys: min_dps, max_dps, avg_dps, cycles_to_max, time_to_max_s.
    """
    # No spool if either bonus parameter is zero/missing
    if not bonus_per_cycle or not max_bonus:
        return {
            "min_dps": base_dps,
            "max_dps": base_dps,
            "avg_dps": base_dps,
            "cycles_to_max": 0,
            "time_to_max_s": 0.0,
        }

    min_dps = base_dps
    max_dps = base_dps * (1.0 + max_bonus)
    avg_dps = (min_dps + max_dps) / 2.0
    cycles_to_max = ceil(max_bonus / bonus_per_cycle)
    cycle_time_s = cycle_time_ms / 1000.0 if cycle_time_ms > 0 else 0.0
    time_to_max_s = cycles_to_max * cycle_time_s

    return {
        "min_dps": min_dps,
        "max_dps": max_dps,
        "avg_dps": avg_dps,
        "cycles_to_max": cycles_to_max,
        "time_to_max_s": time_to_max_s,
    }


def is_spool_weapon(module_attrs: dict) -> bool:
    """Check if a module has Triglavian spool-up attributes.

    Args:
        module_attrs: Dict of {attribute_id: value} for the module.

    Returns:
        True if the module has both spool attributes with non-zero values.
    """
    bonus_per_cycle = module_attrs.get(ATTR_SPOOL_BONUS_PER_CYCLE)
    max_bonus = module_attrs.get(ATTR_SPOOL_MAX_BONUS)

    if bonus_per_cycle is None or max_bonus is None:
        return False

    return bool(bonus_per_cycle) and bool(max_bonus)
