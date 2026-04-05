"""Fighter DPS calculation and SDE loading functions."""

from psycopg2.extras import RealDictCursor

from .constants import (
    ATTR_SQUADRON_SIZE, ATTR_RATE_OF_FIRE, ATTR_DAMAGE_MULT,
    ATTR_EM_DAMAGE, ATTR_THERMAL_DAMAGE, ATTR_KINETIC_DAMAGE, ATTR_EXPLOSIVE_DAMAGE,
)


def calculate_fighter_dps(fighter_attrs: dict, squadrons: int = 1) -> dict:
    """Calculate DPS for a fighter type.

    DPS formula: squadron_size * damage_mult * (em + th + kin + exp) / cycle_time_s

    Args:
        fighter_attrs: dict of {attr_id: value} for the fighter type
        squadrons: number of squadrons of this fighter type

    Returns:
        {"dps_per_squadron", "total_dps", "damage_type", "squadron_size"}
    """
    squadron_size = int(fighter_attrs.get(ATTR_SQUADRON_SIZE, 1))
    cycle_time_ms = fighter_attrs.get(ATTR_RATE_OF_FIRE, 0)
    damage_mult = fighter_attrs.get(ATTR_DAMAGE_MULT, 1.0)

    em = fighter_attrs.get(ATTR_EM_DAMAGE, 0)
    thermal = fighter_attrs.get(ATTR_THERMAL_DAMAGE, 0)
    kinetic = fighter_attrs.get(ATTR_KINETIC_DAMAGE, 0)
    explosive = fighter_attrs.get(ATTR_EXPLOSIVE_DAMAGE, 0)

    total_damage = em + thermal + kinetic + explosive

    # Handle zero cycle time gracefully
    if cycle_time_ms <= 0 or total_damage <= 0:
        return {
            "dps_per_squadron": 0.0,
            "total_dps": 0.0,
            "damage_type": "unknown",
            "squadron_size": squadron_size,
        }

    cycle_time_s = cycle_time_ms / 1000.0
    dps_per_squadron = squadron_size * damage_mult * total_damage / cycle_time_s
    total_dps = dps_per_squadron * squadrons

    # Determine primary damage type
    damage_map = {
        "em": em,
        "thermal": thermal,
        "kinetic": kinetic,
        "explosive": explosive,
    }
    damage_type = max(damage_map, key=damage_map.get) if total_damage > 0 else "unknown"

    return {
        "dps_per_squadron": round(dps_per_squadron, 1),
        "total_dps": round(total_dps, 1),
        "damage_type": damage_type,
        "squadron_size": squadron_size,
    }


def load_fighter_data(db, fighter_inputs: list) -> list:
    """Load fighter type info and attributes from SDE.

    Args:
        db: database connection (with .cursor() context manager)
        fighter_inputs: [{"type_id": int, "quantity": int}]

    Returns:
        [{"type_id", "type_name", "group_id", "attrs": {attr_id: value}, "quantity"}]
    """
    if not fighter_inputs:
        return []

    type_ids = [f["type_id"] for f in fighter_inputs]
    quantity_map = {f["type_id"]: f["quantity"] for f in fighter_inputs}

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # 1. Load type info from invTypes
        cur.execute("""
            SELECT "typeID", "typeName", "groupID"
            FROM "invTypes"
            WHERE "typeID" = ANY(%s)
        """, (type_ids,))
        type_info = {row["typeID"]: row for row in cur.fetchall()}

        # 2. Load attributes from dgmTypeAttributes
        cur.execute("""
            SELECT "typeID", "attributeID",
                   COALESCE("valueFloat", "valueInt"::double precision) as value
            FROM "dgmTypeAttributes"
            WHERE "typeID" = ANY(%s)
        """, (type_ids,))
        type_attrs = {}
        for row in cur.fetchall():
            tid = row["typeID"]
            if tid not in type_attrs:
                type_attrs[tid] = {}
            type_attrs[tid][row["attributeID"]] = row["value"]

    # Build result list
    result = []
    for type_id in type_ids:
        info = type_info.get(type_id)
        if not info:
            continue
        result.append({
            "type_id": type_id,
            "type_name": info["typeName"],
            "group_id": info["groupID"],
            "attrs": type_attrs.get(type_id, {}),
            "quantity": quantity_map.get(type_id, 1),
        })

    return result


def apply_ship_fighter_bonus(base_dps: float, ship_bonus_mult: float) -> float:
    """Apply ship's fighter damage bonus multiplier to base DPS.

    Args:
        base_dps: base fighter DPS before ship bonuses
        ship_bonus_mult: combined multiplier from ship role/per-level bonuses
                         (e.g., 1.25 = +25% bonus)

    Returns:
        Rounded DPS after applying the bonus.
    """
    return round(base_dps * ship_bonus_mult, 1)
