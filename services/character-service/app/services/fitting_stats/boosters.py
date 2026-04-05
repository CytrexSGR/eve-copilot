"""Combat booster effect parsing and application."""
from typing import Dict, List


ATTR_BOOSTERNESS = 1087  # Booster slot (1-3)
# Side effect chance attributes (1089-1093)
SIDE_EFFECT_CHANCE_ATTRS = [1089, 1090, 1091, 1092, 1093]
# Side effect penalty attribute IDs (1099-1103) -- value points to which attr gets penalized
SIDE_EFFECT_PENALTY_ATTRS = [1099, 1100, 1101, 1102, 1103]
# Side effect penalty magnitudes (1141-1151)
SIDE_EFFECT_MAGNITUDE_ATTRS = [1141, 1142, 1143, 1144, 1145, 1146, 1147, 1148, 1149, 1150, 1151]


def parse_booster_effects(
    booster_type_id: int,
    booster_attrs: Dict[int, float],
    side_effects_enabled: List[int],
) -> dict:
    """Parse booster primary bonuses and side effects.

    Args:
        booster_type_id: The type ID of the booster item.
        booster_attrs: {attr_id: value} for the booster type from SDE.
        side_effects_enabled: List of side effect indices (0-4) that are enabled.

    Returns:
        {"primary_bonuses": [...], "side_effects": [...]}
    """
    primary_bonuses = []
    side_effects = []

    # Primary bonus is typically attr 330 (boosterAttributeModifier)
    # Applied as PostPercent to a target attribute
    bonus_val = booster_attrs.get(330, 0)
    if bonus_val:
        primary_bonuses.append({"value": bonus_val, "source_attr": 330})

    # Parse side effects (up to 5)
    for i, (chance_attr, penalty_attr) in enumerate(
        zip(SIDE_EFFECT_CHANCE_ATTRS, SIDE_EFFECT_PENALTY_ATTRS)
    ):
        chance = booster_attrs.get(chance_attr, 0)
        target_attr = int(booster_attrs.get(penalty_attr, 0))
        if chance > 0 and target_attr > 0 and i in side_effects_enabled:
            # Look up magnitude by side effect index
            if i < len(SIDE_EFFECT_MAGNITUDE_ATTRS):
                magnitude = booster_attrs.get(SIDE_EFFECT_MAGNITUDE_ATTRS[i], 0)
            else:
                magnitude = 0
            side_effects.append({
                "target_attr": target_attr,
                "magnitude": magnitude,
                "chance": chance,
            })

    return {"primary_bonuses": primary_bonuses, "side_effects": side_effects}
