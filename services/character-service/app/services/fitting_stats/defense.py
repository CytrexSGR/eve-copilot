"""Defense calculation — EHP from Dogma-modified ship attributes."""

from .models import DefenseStats, ResistProfile
from .constants import (
    ATTR_SHIELD_HP, ATTR_ARMOR_HP, ATTR_HULL_HP,
    ATTR_SHIELD_EM_RESIST, ATTR_SHIELD_THERMAL_RESIST,
    ATTR_SHIELD_KINETIC_RESIST, ATTR_SHIELD_EXPLOSIVE_RESIST,
    ATTR_ARMOR_EM_RESIST, ATTR_ARMOR_THERMAL_RESIST,
    ATTR_ARMOR_KINETIC_RESIST, ATTR_ARMOR_EXPLOSIVE_RESIST,
    ATTR_HULL_EM_RESIST, ATTR_HULL_THERMAL_RESIST,
    ATTR_HULL_KINETIC_RESIST, ATTR_HULL_EXPLOSIVE_RESIST,
)


class DefenseMixin:
    """Mixin providing _calc_defense_local."""

    def _calc_defense_local(self, modified_ship_attrs: dict) -> DefenseStats:
        """Calculate EHP from Dogma-modified ship attributes (local, no httpx)."""
        SHIELD_RESISTS = {
            ATTR_SHIELD_EM_RESIST: "em",
            ATTR_SHIELD_THERMAL_RESIST: "thermal",
            ATTR_SHIELD_KINETIC_RESIST: "kinetic",
            ATTR_SHIELD_EXPLOSIVE_RESIST: "explosive",
        }
        ARMOR_RESISTS = {
            ATTR_ARMOR_EM_RESIST: "em",
            ATTR_ARMOR_THERMAL_RESIST: "thermal",
            ATTR_ARMOR_KINETIC_RESIST: "kinetic",
            ATTR_ARMOR_EXPLOSIVE_RESIST: "explosive",
        }
        HULL_RESISTS = {
            ATTR_HULL_EM_RESIST: "em",
            ATTR_HULL_THERMAL_RESIST: "thermal",
            ATTR_HULL_KINETIC_RESIST: "kinetic",
            ATTR_HULL_EXPLOSIVE_RESIST: "explosive",
        }

        shield_hp = modified_ship_attrs.get(ATTR_SHIELD_HP, 0)
        armor_hp = modified_ship_attrs.get(ATTR_ARMOR_HP, 0)
        hull_hp = modified_ship_attrs.get(ATTR_HULL_HP, 0)

        def calc_layer(hp, resist_map):
            resists = {}
            for attr_id, name in resist_map.items():
                mult = modified_ship_attrs.get(attr_id, 1.0)
                resists[name] = round((1 - mult) * 100, 1)
            avg_mult = sum(modified_ship_attrs.get(a, 1.0) for a in resist_map) / 4
            ehp = hp / max(avg_mult, 0.001)
            return ehp, ResistProfile(**resists)

        shield_ehp, shield_r = calc_layer(shield_hp, SHIELD_RESISTS)
        armor_ehp, armor_r = calc_layer(armor_hp, ARMOR_RESISTS)
        hull_ehp, hull_r = calc_layer(hull_hp, HULL_RESISTS)
        total_ehp = shield_ehp + armor_ehp + hull_ehp

        tank = "shield" if shield_ehp > armor_ehp * 1.5 else \
               "armor" if armor_ehp > shield_ehp * 1.5 else "balanced"

        return DefenseStats(
            total_ehp=round(total_ehp),
            shield_ehp=round(shield_ehp),
            armor_ehp=round(armor_ehp),
            hull_ehp=round(hull_ehp),
            shield_hp=round(shield_hp),
            armor_hp=round(armor_hp),
            hull_hp=round(hull_hp),
            shield_resists=shield_r,
            armor_resists=armor_r,
            hull_resists=hull_r,
            tank_type=tank,
        )
