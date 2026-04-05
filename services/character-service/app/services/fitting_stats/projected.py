"""Projected effects: webs, target painters, energy neutralizers, remote reps.

Projected effects are remote modules applied by other ships. They are modeled
as pre-calculated values — the caller provides effect type and strength.

Stacking penalty formula: e^(-((n/2.67)^2)) where n is 0-indexed.
"""

import math

STACKING_PENALTIES = [1.0, 0.8691, 0.5706, 0.2830, 0.1059, 0.0300]

PROJECTED_DEFINITIONS = {
    "web": {
        "attribute": 37,       # maxVelocity
        "operation": "reduce_percent",
        "stacking_penalized": True,
    },
    "paint": {
        "attribute": 552,      # signatureRadius
        "operation": "increase_percent",
        "stacking_penalized": True,
    },
    "neut": {
        "attribute": None,
        "operation": "cap_drain",
        "stacking_penalized": False,
        "default_cycle_time_s": 12.0,
    },
    "remote_shield": {
        "attribute": None,
        "operation": "incoming_rep",
        "stacking_penalized": False,
        "default_cycle_time_s": 5.0,
    },
    "remote_armor": {
        "attribute": None,
        "operation": "incoming_rep",
        "stacking_penalized": False,
        "default_cycle_time_s": 5.0,
    },
}

PROJECTED_PRESETS = {
    "single_web": [{"effect_type": "web", "strength": 60.0, "count": 1}],
    "double_web": [{"effect_type": "web", "strength": 60.0, "count": 2}],
    "web_paint": [
        {"effect_type": "web", "strength": 60.0, "count": 1},
        {"effect_type": "paint", "strength": 30.0, "count": 1},
    ],
    "heavy_neut": [{"effect_type": "neut", "strength": 600.0, "count": 1}],
    "double_paint": [{"effect_type": "paint", "strength": 30.0, "count": 2}],
    "logi_shield": [{"effect_type": "remote_shield", "strength": 350.0, "count": 2}],
    "logi_armor": [{"effect_type": "remote_armor", "strength": 350.0, "count": 2}],
}


def _stacking_penalty(n: int) -> float:
    """Return the stacking penalty coefficient for the nth application (0-indexed)."""
    if n < len(STACKING_PENALTIES):
        return STACKING_PENALTIES[n]
    return math.exp(-((n / 2.67) ** 2))


def apply_projected_effects(ship_attrs: dict, effects: list) -> dict:
    """Apply projected effects to ship attributes.

    Args:
        ship_attrs: Ship attribute dict {attr_id: value}. NOT mutated.
        effects: List of dicts with effect_type, strength, count fields.

    Returns:
        dict with keys:
        - modified_attrs: dict — copy of ship_attrs with modifications applied
        - cap_drain_per_s: float — total external cap drain in GJ/s
        - incoming_rep_shield: float — total incoming shield rep in HP/s
        - incoming_rep_armor: float — total incoming armor rep in HP/s
        - summary: list of dicts describing each applied effect
    """
    modified = dict(ship_attrs)
    cap_drain_per_s = 0.0
    incoming_rep_shield = 0.0
    incoming_rep_armor = 0.0
    summary = []

    # Track stacking counters per effect type (for stacking penalized effects)
    stacking_counters = {}

    for effect in effects:
        effect_type = effect.get("effect_type") if isinstance(effect, dict) else effect.effect_type
        strength = effect.get("strength", 0) if isinstance(effect, dict) else effect.strength
        count = effect.get("count", 1) if isinstance(effect, dict) else effect.count

        defn = PROJECTED_DEFINITIONS.get(effect_type)
        if not defn:
            continue

        operation = defn["operation"]
        attr_id = defn["attribute"]
        stacking = defn["stacking_penalized"]

        if operation == "reduce_percent":
            # Web: reduce attribute by strength% per application, stacking penalized
            if attr_id is not None and attr_id in modified:
                for _ in range(count):
                    n = stacking_counters.get(effect_type, 0)
                    penalty = _stacking_penalty(n) if stacking else 1.0
                    effective_strength = strength * penalty
                    modified[attr_id] *= (1.0 - effective_strength / 100.0)
                    stacking_counters[effect_type] = n + 1

                summary.append({
                    "effect_type": effect_type,
                    "strength": strength,
                    "count": count,
                    "stacking_penalized": stacking,
                })

        elif operation == "increase_percent":
            # Paint: increase attribute by strength% per application, stacking penalized
            if attr_id is not None and attr_id in modified:
                for _ in range(count):
                    n = stacking_counters.get(effect_type, 0)
                    penalty = _stacking_penalty(n) if stacking else 1.0
                    effective_strength = strength * penalty
                    modified[attr_id] *= (1.0 + effective_strength / 100.0)
                    stacking_counters[effect_type] = n + 1

                summary.append({
                    "effect_type": effect_type,
                    "strength": strength,
                    "count": count,
                    "stacking_penalized": stacking,
                })

        elif operation == "cap_drain":
            # Neut: not stacking penalized, strength = GJ per cycle
            cycle_time_s = defn.get("default_cycle_time_s", 12.0)
            drain = (strength / cycle_time_s) * count
            cap_drain_per_s += drain

            summary.append({
                "effect_type": effect_type,
                "strength": strength,
                "count": count,
                "cap_drain_per_s": drain,
                "stacking_penalized": stacking,
            })

        elif operation == "incoming_rep":
            # Remote rep: not stacking penalized, strength = HP per cycle
            cycle_time_s = defn.get("default_cycle_time_s", 5.0)
            hp_per_s = (strength / cycle_time_s) * count

            if effect_type == "remote_shield":
                incoming_rep_shield += hp_per_s
            elif effect_type == "remote_armor":
                incoming_rep_armor += hp_per_s

            summary.append({
                "effect_type": effect_type,
                "strength": strength,
                "count": count,
                "hp_per_s": hp_per_s,
                "stacking_penalized": stacking,
            })

    return {
        "modified_attrs": modified,
        "cap_drain_per_s": cap_drain_per_s,
        "incoming_rep_shield": incoming_rep_shield,
        "incoming_rep_armor": incoming_rep_armor,
        "summary": summary,
    }
