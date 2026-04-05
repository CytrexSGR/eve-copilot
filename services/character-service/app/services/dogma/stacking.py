"""EVE Online stacking penalty calculations."""

import math
from typing import List


def stacking_penalty(index: int) -> float:
    """Calculate stacking penalty effectiveness for the nth module (0-indexed).

    Formula: e^(-((index / 2.67)^2))
    """
    return math.exp(-((index / 2.67) ** 2))


def apply_stacking_penalized_multipliers(multipliers: List[float]) -> float:
    """Apply a list of multipliers with stacking penalty.

    Multipliers are sorted by distance from 1.0 (most effective first),
    then each subsequent multiplier's effectiveness is reduced by the
    stacking penalty formula.

    Returns the combined multiplier.
    """
    if not multipliers:
        return 1.0

    # Sort by distance from 1.0 (most effective first)
    sorted_mults = sorted(multipliers, key=lambda m: abs(m - 1.0), reverse=True)

    result = 1.0
    for i, mult in enumerate(sorted_mults):
        penalty = stacking_penalty(i)
        # Penalized multiplier: interpolate between 1.0 and the modifier value
        effective = 1.0 + (mult - 1.0) * penalty
        result *= effective

    return result
