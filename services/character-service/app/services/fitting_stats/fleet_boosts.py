"""Fleet boost (Command Burst) buff definitions and application.

Command Bursts provide fleet-wide buffs. Instead of modeling the full burst
calculation (which requires fleet composition), we accept pre-calculated buff
values as input. Each buff has a buff_id (warfareBuffID from SDE) and a value
(percentage).
"""

# warfareBuffID -> attribute mapping
# Operation types:
#   "postPercent": attr *= (1 + value/100)
#   "resist_add": attr *= (1 - value/100)  (reduces pass-through = increases resist)
BUFF_DEFINITIONS = {
    # Shield Command
    10: {"name": "Shield HP", "attributes": [263], "operation": "postPercent"},
    11: {"name": "Shield Resist", "attributes": [271, 272, 273, 274], "operation": "resist_add"},
    12: {"name": "Shield Repair", "attributes": [68], "operation": "postPercent"},
    # Armor Command
    13: {"name": "Armor HP", "attributes": [265], "operation": "postPercent"},
    14: {"name": "Armor Resist", "attributes": [267, 268, 269, 270], "operation": "resist_add"},
    15: {"name": "Armor Repair Duration", "attributes": [73], "operation": "postPercent"},
    # Skirmish Command
    33: {"name": "Agility", "attributes": [70], "operation": "postPercent"},
    34: {"name": "Tackle Range", "attributes": [103], "operation": "postPercent"},
    35: {"name": "Speed", "attributes": [37], "operation": "postPercent"},
    # Information Command
    36: {"name": "Signature Radius", "attributes": [552], "operation": "postPercent"},
    37: {"name": "Lock Range", "attributes": [76], "operation": "postPercent"},
    38: {"name": "Scan Resolution", "attributes": [564], "operation": "postPercent"},
    39: {"name": "EWAR Resist", "attributes": [2112, 2113], "operation": "postPercent"},
    # Mining Foreman
    43: {"name": "Mining Yield", "attributes": [77], "operation": "postPercent"},
    44: {"name": "Mining Crystal Volatility", "attributes": [2699], "operation": "postPercent"},
    45: {"name": "Mining Cycle Time", "attributes": [73], "operation": "postPercent"},
}

BOOST_PRESETS = {
    "shield_t2_max": [
        {"buff_id": 10, "value": 25.88},
        {"buff_id": 11, "value": 12.94},
        {"buff_id": 12, "value": 25.88},
    ],
    "armor_t2_max": [
        {"buff_id": 13, "value": 25.88},
        {"buff_id": 14, "value": 12.94},
        {"buff_id": 15, "value": -25.88},
    ],
    "skirmish_t2_max": [
        {"buff_id": 33, "value": -25.88},
        {"buff_id": 34, "value": 25.88},
        {"buff_id": 35, "value": 25.88},
    ],
    "info_t2_max": [
        {"buff_id": 36, "value": -25.88},
        {"buff_id": 37, "value": 25.88},
        {"buff_id": 38, "value": 25.88},
    ],
}


def apply_fleet_boosts(ship_attrs: dict, boosts: list) -> dict:
    """Apply fleet boost buffs to ship attributes.

    Returns NEW dict (does not mutate input).

    Args:
        ship_attrs: Current ship attribute dict {attr_id: value}.
        boosts: List of boost dicts or FleetBoostInput objects
                with buff_id and value fields.

    Returns:
        New dict with boosted attribute values.
    """
    if not boosts:
        return ship_attrs

    result = dict(ship_attrs)

    for boost in boosts:
        buff_id = boost["buff_id"] if isinstance(boost, dict) else boost.buff_id
        value = boost["value"] if isinstance(boost, dict) else boost.value

        defn = BUFF_DEFINITIONS.get(buff_id)
        if not defn:
            continue

        for attr_id in defn["attributes"]:
            if attr_id not in result:
                continue

            if defn["operation"] == "postPercent":
                result[attr_id] = result[attr_id] * (1.0 + value / 100.0)
            elif defn["operation"] == "resist_add":
                result[attr_id] = result[attr_id] * (1.0 - value / 100.0)

    return result
