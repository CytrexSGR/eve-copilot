"""SDE Browser REST API.
Browse ships and modules from the EVE Static Data Export.
"""

from fastapi import APIRouter, Query, Request, HTTPException
from typing import List, Optional
from pydantic import BaseModel

from psycopg2.extras import RealDictCursor


router = APIRouter()


# --- Models ---

class ShipSummary(BaseModel):
    type_id: int
    type_name: str
    group_id: int
    group_name: str
    hi_slots: int = 0
    med_slots: int = 0
    low_slots: int = 0
    rig_slots: int = 0
    power_output: float = 0
    cpu_output: float = 0
    turret_hardpoints: int = 0
    launcher_hardpoints: int = 0
    rig_size: int = 0


class ShipDetail(ShipSummary):
    capacitor_capacity: float = 0
    capacitor_recharge: float = 0
    max_velocity: float = 0
    agility: float = 0
    signature_radius: float = 0
    shield_hp: float = 0
    armor_hp: float = 0
    hull_hp: float = 0


class ModuleSummary(BaseModel):
    type_id: int
    type_name: str
    group_id: int
    group_name: str
    slot_type: str
    cpu: float = 0
    power: float = 0
    meta_level: int = 0
    hardpoint_type: str | None = None  # "turret", "launcher", or None


class ChargeSummary(BaseModel):
    type_id: int
    name: str
    group_name: str
    em: float = 0
    thermal: float = 0
    kinetic: float = 0
    explosive: float = 0
    meta_level: int = 0


class ResolvedType(BaseModel):
    type_id: int
    type_name: str


class GroupSummary(BaseModel):
    group_id: int
    group_name: str
    count: int


class MarketGroupNode(BaseModel):
    market_group_id: int
    name: str
    has_types: bool
    child_count: int
    icon_id: int | None = None


# Market group root IDs
MARKET_ROOT_SHIPS = 4
MARKET_ROOT_MODULES = 9
MARKET_ROOT_CHARGES = 11
MARKET_ROOT_DRONES = 157
MARKET_ROOT_RIGS = 1111        # Under 955 "Ship and Module Modifications"
MARKET_ROOT_SUBSYSTEMS = 1112  # Under 955 "Ship and Module Modifications"
MARKET_ROOTS = {MARKET_ROOT_SHIPS, MARKET_ROOT_MODULES, MARKET_ROOT_CHARGES, MARKET_ROOT_DRONES}


# --- Attribute ID constants ---
ATTR_HI_SLOTS = 14
ATTR_MED_SLOTS = 13
ATTR_LOW_SLOTS = 12
ATTR_RIG_SLOTS = 1137
ATTR_POWER_OUTPUT = 11
ATTR_CPU_OUTPUT = 48
ATTR_CAP_CAPACITY = 482
ATTR_CAP_RECHARGE = 55
ATTR_MAX_VELOCITY = 37
ATTR_AGILITY = 70
ATTR_SIG_RADIUS = 552
ATTR_SHIELD_HP = 263
ATTR_ARMOR_HP = 265
ATTR_HULL_HP = 9
ATTR_CPU_NEED = 50
ATTR_POWER_NEED = 30
ATTR_META_LEVEL = 633
ATTR_DAMAGE_EM = 114
ATTR_DAMAGE_EXPLOSIVE = 116
ATTR_DAMAGE_KINETIC = 117
ATTR_DAMAGE_THERMAL = 118
ATTR_TURRET_HARDPOINTS = 102
ATTR_LAUNCHER_HARDPOINTS = 101
ATTR_RIG_SIZE = 1547
ATTR_CHARGE_SIZE = 128  # Turret weapon size: 1=Small, 2=Medium, 3=Large, 4=XL

# canFitShipGroup / canFitShipType attribute IDs (1298-1305, 1872, 1879-1881)
CAN_FIT_SHIP_GROUP_ATTRS = [1298, 1299, 1300, 1301]
CAN_FIT_SHIP_TYPE_ATTRS = [1302, 1303, 1304, 1305, 1872, 1879, 1880, 1881]
ALL_CAN_FIT_ATTRS = CAN_FIT_SHIP_GROUP_ATTRS + CAN_FIT_SHIP_TYPE_ATTRS

# Launcher group → weapon size (matches ship rig_size)
LAUNCHER_SIZE_MAP: dict[int, int] = {
    507: 1,    # Rocket
    509: 1,    # Light Missile
    511: 2,    # Rapid Light Missile
    510: 2,    # Heavy Missile
    771: 2,    # Heavy Assault Missile
    506: 3,    # Cruise Missile
    508: 3,    # Torpedo
    1245: 3,   # Rapid Heavy Missile
    1673: 3,   # Rapid Torpedo
    1674: 4,   # XL Cruise Missile
    524: 4,    # XL Torpedo
}

# Charge group attribute IDs (chargeGroup1..5)
CHARGE_GROUP_ATTR_IDS = [604, 605, 606, 609, 610]

# Effect IDs for slot determination
EFFECT_HI_POWER = 12
EFFECT_MED_POWER = 13
EFFECT_LO_POWER = 11
EFFECT_RIG_SLOT = 2663
EFFECT_TURRET_FITTED = 42
EFFECT_LAUNCHER_FITTED = 40

SLOT_EFFECT_MAP = {
    EFFECT_HI_POWER: "high",
    EFFECT_MED_POWER: "mid",
    EFFECT_LO_POWER: "low",
    EFFECT_RIG_SLOT: "rig",
}

# Ship attribute IDs to pivot
SHIP_ATTR_IDS = [
    ATTR_HI_SLOTS, ATTR_MED_SLOTS, ATTR_LOW_SLOTS, ATTR_RIG_SLOTS,
    ATTR_POWER_OUTPUT, ATTR_CPU_OUTPUT, ATTR_CAP_CAPACITY, ATTR_CAP_RECHARGE,
    ATTR_MAX_VELOCITY, ATTR_AGILITY, ATTR_SIG_RADIUS,
    ATTR_SHIELD_HP, ATTR_ARMOR_HP, ATTR_HULL_HP,
    ATTR_TURRET_HARDPOINTS, ATTR_LAUNCHER_HARDPOINTS, ATTR_RIG_SIZE,
]


def _get_attr(attrs: dict, attr_id: int, default=0):
    """Get attribute value from pivot dict."""
    val = attrs.get(attr_id)
    return val if val is not None else default


@router.get("/modes/{ship_type_id}", summary="Get T3D modes for a ship")
def get_ship_modes(request: Request, ship_type_id: int):
    """Return available T3D modes for a Tactical Destroyer.
    Returns empty list for non-T3D ships.
    Mode items are in group 1306 (Ship Modifiers) and linked via ship type name.
    T3D ships are in group 1305 (Tactical Destroyers).
    """
    db = request.app.state.db
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('''
            SELECT t."typeName", t."groupID"
            FROM "invTypes" t
            WHERE t."typeID" = %(ship_id)s
        ''', {"ship_id": ship_type_id})
        ship = cur.fetchone()
        if not ship or ship["groupID"] != 1305:
            return []

        ship_name = ship["typeName"]
        cur.execute('''
            SELECT t."typeID" as type_id, t."typeName" as name
            FROM "invTypes" t
            WHERE t."groupID" = 1306
            AND t."typeName" LIKE %(pattern)s
            ORDER BY t."typeName"
        ''', {"pattern": f"{ship_name}%"})
        return cur.fetchall()


def _fetch_ship_constraints(db, ship_type_id: int) -> dict:
    """Fetch turret/launcher hardpoints, rig_size, and groupID for a ship."""
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # Get ship groupID
        cur.execute("""
            SELECT "groupID" FROM "invTypes" WHERE "typeID" = %(ship_id)s
        """, {"ship_id": ship_type_id})
        row = cur.fetchone()
        group_id = row["groupID"] if row else 0

        cur.execute("""
            SELECT "attributeID",
                   COALESCE("valueFloat", "valueInt"::float) as value
            FROM "dgmTypeAttributes"
            WHERE "typeID" = %(ship_id)s
              AND "attributeID" IN (%(turret)s, %(launcher)s, %(rig_size)s)
        """, {
            "ship_id": ship_type_id,
            "turret": ATTR_TURRET_HARDPOINTS,
            "launcher": ATTR_LAUNCHER_HARDPOINTS,
            "rig_size": ATTR_RIG_SIZE,
        })
        attrs = {row["attributeID"]: int(row["value"]) for row in cur.fetchall()}
        return {
            "turret_hardpoints": attrs.get(ATTR_TURRET_HARDPOINTS, 0),
            "launcher_hardpoints": attrs.get(ATTR_LAUNCHER_HARDPOINTS, 0),
            "rig_size": attrs.get(ATTR_RIG_SIZE, 0),
            "group_id": group_id,
            "type_id": ship_type_id,
        }


def _build_hardpoint_filter(turret_hp: int, launcher_hp: int) -> tuple:
    """Build SQL to exclude turret/launcher modules when ship lacks those hardpoints.
    Returns (sql_fragment, params_dict). Empty string if no filter needed."""
    exclude_effects = []
    if turret_hp == 0:
        exclude_effects.append(EFFECT_TURRET_FITTED)
    if launcher_hp == 0:
        exclude_effects.append(EFFECT_LAUNCHER_FITTED)
    if not exclude_effects:
        return "", {}
    return (
        """NOT EXISTS (
            SELECT 1 FROM "dgmTypeEffects" dte_hp
            WHERE dte_hp."typeID" = t."typeID"
              AND dte_hp."effectID" = ANY(%(exclude_hp_effects)s)
        )""",
        {"exclude_hp_effects": exclude_effects},
    )


def _build_rig_size_filter(rig_size: int) -> tuple:
    """Build SQL to filter rigs by matching ship rig size.
    Returns (sql_fragment, params_dict)."""
    return (
        """EXISTS (
            SELECT 1 FROM "dgmTypeAttributes" dta_rs
            WHERE dta_rs."typeID" = t."typeID"
              AND dta_rs."attributeID" = 1547
              AND COALESCE(dta_rs."valueFloat", dta_rs."valueInt"::float) = %(ship_rig_size)s
        )""",
        {"ship_rig_size": rig_size},
    )


def _build_weapon_size_filter(rig_size: int) -> tuple:
    """Filter turrets by chargeSize and launchers by group to match ship weapon class.

    Non-weapon modules (neuts, smartbombs without chargeSize, etc.) pass through.
    Returns (sql_fragment, params_dict).
    """
    allowed_launchers = [gid for gid, size in LAUNCHER_SIZE_MAP.items() if size == rig_size]
    return (
        """(
            -- Not a turret/launcher → allow (smartbombs, neuts, etc.)
            NOT EXISTS (
                SELECT 1 FROM "dgmTypeEffects" dte_ws
                WHERE dte_ws."typeID" = t."typeID"
                  AND dte_ws."effectID" IN (%(eff_turret)s, %(eff_launcher)s)
            )
            OR
            -- Turret → chargeSize must match ship rig_size
            (EXISTS (
                SELECT 1 FROM "dgmTypeEffects" dte_ws2
                WHERE dte_ws2."typeID" = t."typeID" AND dte_ws2."effectID" = %(eff_turret)s
            ) AND EXISTS (
                SELECT 1 FROM "dgmTypeAttributes" dta_cs
                WHERE dta_cs."typeID" = t."typeID"
                  AND dta_cs."attributeID" = %(attr_charge_size)s
                  AND COALESCE(dta_cs."valueFloat", dta_cs."valueInt"::float) = %(weapon_size)s
            ))
            OR
            -- Launcher → group must be in allowed launcher groups for this ship size
            (EXISTS (
                SELECT 1 FROM "dgmTypeEffects" dte_ws3
                WHERE dte_ws3."typeID" = t."typeID" AND dte_ws3."effectID" = %(eff_launcher)s
            ) AND t."groupID" = ANY(%(allowed_launcher_groups)s))
        )""",
        {
            "eff_turret": EFFECT_TURRET_FITTED,
            "eff_launcher": EFFECT_LAUNCHER_FITTED,
            "attr_charge_size": ATTR_CHARGE_SIZE,
            "weapon_size": rig_size,
            "allowed_launcher_groups": allowed_launchers if allowed_launchers else [0],
        },
    )


def _build_can_fit_ship_filter(ship_group_id: int, ship_type_id: int) -> tuple:
    """Filter modules that have canFitShipGroup/canFitShipType restrictions.

    Modules WITH these attributes can only be fitted to specific ship groups/types.
    Modules WITHOUT these attributes pass through (no restriction).
    Returns (sql_fragment, params_dict).
    """
    return (
        """(
            -- Module has no canFit restrictions → allow
            NOT EXISTS (
                SELECT 1 FROM "dgmTypeAttributes" dta_cf
                WHERE dta_cf."typeID" = t."typeID"
                  AND dta_cf."attributeID" = ANY(%(can_fit_attrs)s)
            )
            OR
            -- Module has restrictions AND ship matches one of them
            EXISTS (
                SELECT 1 FROM "dgmTypeAttributes" dta_cf2
                WHERE dta_cf2."typeID" = t."typeID"
                  AND dta_cf2."attributeID" = ANY(%(can_fit_attrs)s)
                  AND (
                      COALESCE(dta_cf2."valueFloat", dta_cf2."valueInt"::float) = %(ship_group_for_fit)s
                      OR COALESCE(dta_cf2."valueFloat", dta_cf2."valueInt"::float) = %(ship_type_for_fit)s
                  )
            )
        )""",
        {
            "can_fit_attrs": ALL_CAN_FIT_ATTRS,
            "ship_group_for_fit": float(ship_group_id),
            "ship_type_for_fit": float(ship_type_id),
        },
    )


@router.get(
    "/ships",
    response_model=List[ShipSummary],
    summary="Browse ships",
    description="Search and filter ships from SDE. Category 6 = Ships.",
)
def get_ships(
    request: Request,
    search: Optional[str] = Query(None, description="Search by ship name"),
    group: Optional[str] = Query(None, description="Filter by group name (e.g. Battleship, Cruiser)"),
    group_id: Optional[int] = Query(None, description="Filter by exact group ID"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get ships with slot counts and PG/CPU."""
    db = request.app.state.db

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # Build WHERE clause
        conditions = [
            'c."categoryID" = 6',
            't."published" = 1',
        ]
        params = {}

        if search:
            conditions.append('t."typeName" ILIKE %(search)s')
            params["search"] = f"%{search}%"

        if group:
            conditions.append('g."groupName" ILIKE %(group)s')
            params["group"] = f"%{group}%"

        if group_id:
            conditions.append('g."groupID" = %(group_id)s')
            params["group_id"] = group_id

        where = " AND ".join(conditions)
        params["limit"] = limit
        params["offset"] = offset

        cur.execute(f"""
            SELECT t."typeID", t."typeName",
                   g."groupID", g."groupName"
            FROM "invTypes" t
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            JOIN "invCategories" c ON g."categoryID" = c."categoryID"
            WHERE {where}
            ORDER BY g."groupName", t."typeName"
            LIMIT %(limit)s OFFSET %(offset)s
        """, params)

        ships = cur.fetchall()
        if not ships:
            return []

        # Batch-fetch attributes for all ships
        type_ids = [s["typeID"] for s in ships]
        cur.execute("""
            SELECT "typeID", "attributeID",
                   COALESCE("valueFloat", "valueInt"::float) as value
            FROM "dgmTypeAttributes"
            WHERE "typeID" = ANY(%(ids)s)
              AND "attributeID" = ANY(%(attrs)s)
        """, {"ids": type_ids, "attrs": SHIP_ATTR_IDS})

        # Build attr lookup: type_id -> {attr_id -> value}
        attr_map = {}
        for row in cur.fetchall():
            tid = row["typeID"]
            if tid not in attr_map:
                attr_map[tid] = {}
            attr_map[tid][row["attributeID"]] = row["value"]

        results = []
        for s in ships:
            attrs = attr_map.get(s["typeID"], {})
            results.append(ShipSummary(
                type_id=s["typeID"],
                type_name=s["typeName"],
                group_id=s["groupID"],
                group_name=s["groupName"],
                hi_slots=int(_get_attr(attrs, ATTR_HI_SLOTS)),
                med_slots=int(_get_attr(attrs, ATTR_MED_SLOTS)),
                low_slots=int(_get_attr(attrs, ATTR_LOW_SLOTS)),
                rig_slots=int(_get_attr(attrs, ATTR_RIG_SLOTS)),
                power_output=round(_get_attr(attrs, ATTR_POWER_OUTPUT), 1),
                cpu_output=round(_get_attr(attrs, ATTR_CPU_OUTPUT), 1),
                turret_hardpoints=int(_get_attr(attrs, ATTR_TURRET_HARDPOINTS)),
                launcher_hardpoints=int(_get_attr(attrs, ATTR_LAUNCHER_HARDPOINTS)),
                rig_size=int(_get_attr(attrs, ATTR_RIG_SIZE)),
            ))

        return results


@router.get(
    "/ship-groups",
    response_model=List[GroupSummary],
    summary="List ship groups",
    description="Get all published ship groups with item counts.",
)
def get_ship_groups(request: Request):
    """Get all ship groups with counts of published ships."""
    db = request.app.state.db
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT g."groupID", g."groupName", COUNT(t."typeID") as count
            FROM "invGroups" g
            JOIN "invTypes" t ON t."groupID" = g."groupID"
            WHERE g."categoryID" = 6
              AND t."published" = 1
            GROUP BY g."groupID", g."groupName"
            HAVING COUNT(t."typeID") > 0
            ORDER BY g."groupName"
        """)
        return [
            GroupSummary(group_id=r["groupID"], group_name=r["groupName"], count=r["count"])
            for r in cur.fetchall()
        ]


@router.get(
    "/module-groups",
    response_model=List[GroupSummary],
    summary="List module groups by slot type",
    description="Get module groups for a given slot type with item counts.",
)
def get_module_groups(
    request: Request,
    slot_type: Optional[str] = Query(None, description="Filter: high, mid, low, rig"),
    category: Optional[str] = Query(None, description="Filter: module, drone"),
    ship_type_id: Optional[int] = Query(None, description="Ship type ID for compatibility filtering"),
):
    """Get module groups (Shield Hardeners, Armor Plates, etc.) with counts."""
    db = request.app.state.db

    # Determine category ID
    if category == "drone":
        cat_id = 18  # Drones
    else:
        cat_id = 7   # Modules

    # Map slot_type to effect IDs
    slot_effect_ids = None
    if slot_type and cat_id == 7:
        slot_lower = slot_type.lower()
        slot_effect_ids = [eid for eid, name in SLOT_EFFECT_MAP.items() if name == slot_lower]
        if not slot_effect_ids:
            raise HTTPException(status_code=400, detail=f"Invalid slot_type: {slot_type}")

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        if slot_effect_ids:
            # Build additional ship compatibility conditions
            ship_conditions = ""
            ship_params = {}
            if ship_type_id and cat_id == 7:
                constraints = _fetch_ship_constraints(db, ship_type_id)

                # High slot hardpoint filter
                if any(eid == EFFECT_HI_POWER for eid in slot_effect_ids):
                    hp_sql, hp_params = _build_hardpoint_filter(
                        constraints["turret_hardpoints"],
                        constraints["launcher_hardpoints"],
                    )
                    if hp_sql:
                        ship_conditions += f" AND {hp_sql}"
                        ship_params.update(hp_params)

                # Rig size filter
                if any(eid == EFFECT_RIG_SLOT for eid in slot_effect_ids):
                    rs_sql, rs_params = _build_rig_size_filter(constraints["rig_size"])
                    ship_conditions += f" AND {rs_sql}"
                    ship_params.update(rs_params)

                # canFitShipGroup/Type filter
                cf_sql, cf_params = _build_can_fit_ship_filter(constraints["group_id"], constraints["type_id"])
                ship_conditions += f" AND {cf_sql}"
                ship_params.update(cf_params)

            all_params = {"cat_id": cat_id, "effects": slot_effect_ids}
            all_params.update(ship_params)
            cur.execute(f"""
                SELECT g."groupID", g."groupName", COUNT(DISTINCT t."typeID") as count
                FROM "invGroups" g
                JOIN "invTypes" t ON t."groupID" = g."groupID"
                JOIN "dgmTypeEffects" dte ON dte."typeID" = t."typeID"
                WHERE g."categoryID" = %(cat_id)s
                  AND t."published" = 1
                  AND dte."effectID" = ANY(%(effects)s)
                  {ship_conditions}
                GROUP BY g."groupID", g."groupName"
                HAVING COUNT(DISTINCT t."typeID") > 0
                ORDER BY g."groupName"
            """, all_params)
        else:
            cur.execute("""
                SELECT g."groupID", g."groupName", COUNT(t."typeID") as count
                FROM "invGroups" g
                JOIN "invTypes" t ON t."groupID" = g."groupID"
                WHERE g."categoryID" = %(cat_id)s
                  AND t."published" = 1
                GROUP BY g."groupID", g."groupName"
                HAVING COUNT(t."typeID") > 0
                ORDER BY g."groupName"
            """, {"cat_id": cat_id})

        return [
            GroupSummary(group_id=r["groupID"], group_name=r["groupName"], count=r["count"])
            for r in cur.fetchall()
        ]


@router.get(
    "/ships/{ship_type_id}",
    response_model=ShipDetail,
    summary="Get ship details",
    description="Full ship attributes including slots, resources, navigation, HP.",
)
def get_ship_detail(request: Request, ship_type_id: int):
    """Get detailed ship attributes."""
    db = request.app.state.db

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT t."typeID", t."typeName",
                   g."groupID", g."groupName"
            FROM "invTypes" t
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            JOIN "invCategories" c ON g."categoryID" = c."categoryID"
            WHERE t."typeID" = %(id)s AND c."categoryID" = 6
        """, {"id": ship_type_id})

        ship = cur.fetchone()
        if not ship:
            raise HTTPException(status_code=404, detail="Ship not found")

        # Fetch attributes
        cur.execute("""
            SELECT "attributeID",
                   COALESCE("valueFloat", "valueInt"::float) as value
            FROM "dgmTypeAttributes"
            WHERE "typeID" = %(id)s
              AND "attributeID" = ANY(%(attrs)s)
        """, {"id": ship_type_id, "attrs": SHIP_ATTR_IDS})

        attrs = {row["attributeID"]: row["value"] for row in cur.fetchall()}

        return ShipDetail(
            type_id=ship["typeID"],
            type_name=ship["typeName"],
            group_id=ship["groupID"],
            group_name=ship["groupName"],
            hi_slots=int(_get_attr(attrs, ATTR_HI_SLOTS)),
            med_slots=int(_get_attr(attrs, ATTR_MED_SLOTS)),
            low_slots=int(_get_attr(attrs, ATTR_LOW_SLOTS)),
            rig_slots=int(_get_attr(attrs, ATTR_RIG_SLOTS)),
            power_output=round(_get_attr(attrs, ATTR_POWER_OUTPUT), 1),
            cpu_output=round(_get_attr(attrs, ATTR_CPU_OUTPUT), 1),
            turret_hardpoints=int(_get_attr(attrs, ATTR_TURRET_HARDPOINTS)),
            launcher_hardpoints=int(_get_attr(attrs, ATTR_LAUNCHER_HARDPOINTS)),
            rig_size=int(_get_attr(attrs, ATTR_RIG_SIZE)),
            capacitor_capacity=round(_get_attr(attrs, ATTR_CAP_CAPACITY), 1),
            capacitor_recharge=round(_get_attr(attrs, ATTR_CAP_RECHARGE), 1),
            max_velocity=round(_get_attr(attrs, ATTR_MAX_VELOCITY), 1),
            agility=round(_get_attr(attrs, ATTR_AGILITY), 4),
            signature_radius=round(_get_attr(attrs, ATTR_SIG_RADIUS), 1),
            shield_hp=round(_get_attr(attrs, ATTR_SHIELD_HP), 1),
            armor_hp=round(_get_attr(attrs, ATTR_ARMOR_HP), 1),
            hull_hp=round(_get_attr(attrs, ATTR_HULL_HP), 1),
        )


@router.get(
    "/modules",
    response_model=List[ModuleSummary],
    summary="Browse modules",
    description="Search modules filtered by slot type.",
)
def get_modules(
    request: Request,
    slot_type: Optional[str] = Query(None, description="Filter: high, mid, low, rig"),
    search: Optional[str] = Query(None, description="Search by module name"),
    group: Optional[str] = Query(None, description="Filter by group name"),
    group_id: Optional[int] = Query(None, description="Filter by exact group ID"),
    category: Optional[str] = Query(None, description="Category: module (default) or drone"),
    ship_type_id: Optional[int] = Query(None, description="Ship type ID for compatibility filtering"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get modules with slot type and fitting requirements."""
    db = request.app.state.db

    # Determine category ID
    if category == "drone":
        cat_id = 18  # Drones
    elif category == "fighter":
        cat_id = 87  # Fighters
    elif category == "charge":
        cat_id = 8   # Charges
    else:
        cat_id = 7   # Modules

    # Map slot_type to effect IDs (only for modules, not drones/fighters)
    slot_effect_ids = None
    if slot_type and cat_id == 7:
        slot_lower = slot_type.lower()
        slot_effect_ids = [eid for eid, name in SLOT_EFFECT_MAP.items() if name == slot_lower]
        if not slot_effect_ids:
            raise HTTPException(status_code=400, detail=f"Invalid slot_type: {slot_type}. Use high, mid, low, rig.")

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        conditions = [
            'c."categoryID" = %(cat_id)s',
            't."published" = 1',
        ]
        params = {"cat_id": cat_id}

        if search:
            conditions.append('t."typeName" ILIKE %(search)s')
            params["search"] = f"%{search}%"

        if group:
            conditions.append('g."groupName" ILIKE %(group)s')
            params["group"] = f"%{group}%"

        if group_id:
            conditions.append('g."groupID" = %(group_id)s')
            params["group_id"] = group_id

        if slot_effect_ids:
            conditions.append("""
                EXISTS (
                    SELECT 1 FROM "dgmTypeEffects" dte
                    WHERE dte."typeID" = t."typeID"
                      AND dte."effectID" = ANY(%(slot_effects)s)
                )
            """)
            params["slot_effects"] = slot_effect_ids

        # Ship compatibility filtering
        if ship_type_id and cat_id == 7:
            constraints = _fetch_ship_constraints(db, ship_type_id)

            if slot_effect_ids:
                # High slot: filter by hardpoints
                if EFFECT_HI_POWER in slot_effect_ids:
                    hp_sql, hp_params = _build_hardpoint_filter(
                        constraints["turret_hardpoints"],
                        constraints["launcher_hardpoints"],
                    )
                    if hp_sql:
                        conditions.append(hp_sql)
                        params.update(hp_params)

                # Rig slot: filter by rig size
                if EFFECT_RIG_SLOT in slot_effect_ids:
                    rs_sql, rs_params = _build_rig_size_filter(constraints["rig_size"])
                    conditions.append(rs_sql)
                    params.update(rs_params)

            # canFitShipGroup/Type filter (applies to all slot types)
            cf_sql, cf_params = _build_can_fit_ship_filter(constraints["group_id"], constraints["type_id"])
            conditions.append(cf_sql)
            params.update(cf_params)

        where = " AND ".join(conditions)
        params["limit"] = limit
        params["offset"] = offset

        cur.execute(f"""
            SELECT t."typeID", t."typeName",
                   g."groupID", g."groupName"
            FROM "invTypes" t
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            JOIN "invCategories" c ON g."categoryID" = c."categoryID"
            WHERE {where}
            ORDER BY g."groupName", t."typeName"
            LIMIT %(limit)s OFFSET %(offset)s
        """, params)

        modules = cur.fetchall()
        if not modules:
            return []

        type_ids = [m["typeID"] for m in modules]

        # Batch fetch fitting attributes (CPU, PG, meta level)
        cur.execute("""
            SELECT "typeID", "attributeID",
                   COALESCE("valueFloat", "valueInt"::float) as value
            FROM "dgmTypeAttributes"
            WHERE "typeID" = ANY(%(ids)s)
              AND "attributeID" IN (%(cpu)s, %(pg)s, %(meta)s)
        """, {
            "ids": type_ids,
            "cpu": ATTR_CPU_NEED,
            "pg": ATTR_POWER_NEED,
            "meta": ATTR_META_LEVEL,
        })

        attr_map = {}
        for row in cur.fetchall():
            tid = row["typeID"]
            if tid not in attr_map:
                attr_map[tid] = {}
            attr_map[tid][row["attributeID"]] = row["value"]

        # Batch fetch slot effects (only for modules, not drones)
        slot_map = {}
        hardpoint_map = {}
        if cat_id == 7:
            cur.execute("""
                SELECT "typeID", "effectID"
                FROM "dgmTypeEffects"
                WHERE "typeID" = ANY(%(ids)s)
                  AND "effectID" IN (%(hi)s, %(med)s, %(lo)s, %(rig)s, %(turret)s, %(launcher)s)
            """, {
                "ids": type_ids,
                "hi": EFFECT_HI_POWER,
                "med": EFFECT_MED_POWER,
                "lo": EFFECT_LO_POWER,
                "rig": EFFECT_RIG_SLOT,
                "turret": EFFECT_TURRET_FITTED,
                "launcher": EFFECT_LAUNCHER_FITTED,
            })

            for row in cur.fetchall():
                eid = row["effectID"]
                tid = row["typeID"]
                if eid in SLOT_EFFECT_MAP:
                    slot_map[tid] = SLOT_EFFECT_MAP[eid]
                if eid == EFFECT_TURRET_FITTED:
                    hardpoint_map[tid] = "turret"
                elif eid == EFFECT_LAUNCHER_FITTED:
                    hardpoint_map[tid] = "launcher"

        results = []
        for m in modules:
            attrs = attr_map.get(m["typeID"], {})
            results.append(ModuleSummary(
                type_id=m["typeID"],
                type_name=m["typeName"],
                group_id=m["groupID"],
                group_name=m["groupName"],
                slot_type="fighter" if cat_id == 87 else (slot_map.get(m["typeID"], "drone") if cat_id == 18 else slot_map.get(m["typeID"], "unknown")),
                cpu=round(_get_attr(attrs, ATTR_CPU_NEED), 1),
                power=round(_get_attr(attrs, ATTR_POWER_NEED), 1),
                meta_level=int(_get_attr(attrs, ATTR_META_LEVEL)),
                hardpoint_type=hardpoint_map.get(m["typeID"]),
            ))

        return results


@router.post(
    "/resolve-names",
    response_model=List[ResolvedType],
    summary="Resolve type names to IDs",
    description="Bulk resolve type names to type IDs for EFT import.",
)
def resolve_names(
    request: Request,
    names: List[str],
):
    """Resolve a list of type names to type IDs."""
    if not names:
        return []

    if len(names) > 500:
        raise HTTPException(status_code=400, detail="Max 500 names per request")

    db = request.app.state.db

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # Exact match first
        cur.execute("""
            SELECT "typeID", "typeName"
            FROM "invTypes"
            WHERE "typeName" = ANY(%(names)s)
              AND "published" = 1
        """, {"names": names})

        results = []
        found_names = set()
        for row in cur.fetchall():
            results.append(ResolvedType(
                type_id=row["typeID"],
                type_name=row["typeName"],
            ))
            found_names.add(row["typeName"])

        # For unresolved names, try ILIKE
        unresolved = [n for n in names if n not in found_names]
        if unresolved:
            for name in unresolved:
                cur.execute("""
                    SELECT "typeID", "typeName"
                    FROM "invTypes"
                    WHERE "typeName" ILIKE %(name)s
                      AND "published" = 1
                    LIMIT 1
                """, {"name": name})
                row = cur.fetchone()
                if row:
                    results.append(ResolvedType(
                        type_id=row["typeID"],
                        type_name=row["typeName"],
                    ))

        return results


# --- Charge Browser ---

def get_compatible_charges(db, weapon_type_id: int) -> list:
    """Return compatible charges/ammo for a given weapon module.

    Step 1: Look up chargeGroup attributes (604-610) on the weapon.
    Step 2: If no charge groups found, return [].
    Step 3: Query all published charges in those groups with damage stats
            and meta level.
    """
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # Step 1: Get charge group IDs from weapon attributes
        cur.execute("""
            SELECT COALESCE("valueFloat", "valueInt"::float)::int as group_id
            FROM "dgmTypeAttributes"
            WHERE "typeID" = %(type_id)s
              AND "attributeID" IN (604, 605, 606, 609, 610)
              AND COALESCE("valueFloat", "valueInt") IS NOT NULL
        """, {"type_id": weapon_type_id})

        group_rows = cur.fetchall()
        if not group_rows:
            return []

        group_ids = [r["group_id"] for r in group_rows]

        # Step 2: Get all charges in those groups with damage stats
        cur.execute("""
            SELECT t."typeID", t."typeName", g."groupName",
                   COALESCE(em.value, 0) as em,
                   COALESCE(th.value, 0) as thermal,
                   COALESCE(ki.value, 0) as kinetic,
                   COALESCE(ex.value, 0) as explosive,
                   COALESCE(ml.value, 0)::int as meta_level
            FROM "invTypes" t
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            LEFT JOIN LATERAL (
                SELECT COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes" WHERE "typeID" = t."typeID" AND "attributeID" = 114
            ) em ON true
            LEFT JOIN LATERAL (
                SELECT COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes" WHERE "typeID" = t."typeID" AND "attributeID" = 118
            ) th ON true
            LEFT JOIN LATERAL (
                SELECT COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes" WHERE "typeID" = t."typeID" AND "attributeID" = 117
            ) ki ON true
            LEFT JOIN LATERAL (
                SELECT COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes" WHERE "typeID" = t."typeID" AND "attributeID" = 116
            ) ex ON true
            LEFT JOIN LATERAL (
                SELECT COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes" WHERE "typeID" = t."typeID" AND "attributeID" = 633
            ) ml ON true
            WHERE t."groupID" = ANY(%(group_ids)s)
              AND t.published = 1
            ORDER BY g."groupName", COALESCE(ml.value, 0), t."typeName"
        """, {"group_ids": group_ids})

        charges = cur.fetchall()

        return [
            {
                "type_id": c["typeID"],
                "name": c["typeName"],
                "group_name": c["groupName"],
                "em": round(c["em"], 1),
                "thermal": round(c["thermal"], 1),
                "kinetic": round(c["kinetic"], 1),
                "explosive": round(c["explosive"], 1),
                "meta_level": c["meta_level"],
            }
            for c in charges
        ]


@router.get(
    "/charges",
    response_model=List[ChargeSummary],
    summary="Browse compatible charges",
    description="Get all compatible charges/ammo for a given weapon module.",
)
def get_charges(
    request: Request,
    weapon_type_id: int = Query(..., description="Type ID of the weapon module"),
):
    """Get compatible charges for a weapon."""
    db = request.app.state.db
    return get_compatible_charges(db, weapon_type_id)


# --- Market Tree Browser ---


@router.get(
    "/market-tree/children",
    response_model=List[MarketGroupNode],
    summary="Get market group children",
    description="Lazy-load children of a market group node. Without parent_id, returns children of category_root.",
)
def get_market_tree_children(
    request: Request,
    category_root: int = Query(..., description="Root market group ID (4=Ships, 9=Modules, 11=Charges, 157=Drones)"),
    parent_id: Optional[int] = Query(None, description="Parent market group ID. If omitted, returns children of category_root."),
    slot_type: Optional[str] = Query(None, description="Filter modules by slot type (high/mid/low/rig)"),
    ship_type_id: Optional[int] = Query(None, description="Ship type ID for compatibility filtering"),
):
    if category_root not in MARKET_ROOTS:
        raise HTTPException(status_code=400, detail=f"Invalid category_root: {category_root}")

    db = request.app.state.db

    # Rigs live under a different market root (1111) than Ship Equipment (9).
    # When slot_type=rig and browsing modules root, redirect to Rigs subtree.
    if slot_type == "rig" and category_root == MARKET_ROOT_MODULES and parent_id is None:
        effective_parent = MARKET_ROOT_RIGS
        slot_type = None  # All children of Rigs are rigs, no need to filter
    else:
        effective_parent = parent_id if parent_id is not None else category_root

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # If slot filtering requested, prune empty branches
        if slot_type and category_root == MARKET_ROOT_MODULES:
            slot_effect = _slot_type_to_effect(slot_type)
            if slot_effect is None:
                raise HTTPException(status_code=400, detail=f"Invalid slot_type: {slot_type}")

            # Build ship compatibility sub-conditions
            ship_filter_sql = ""
            ship_params = {}
            if ship_type_id:
                constraints = _fetch_ship_constraints(db, ship_type_id)
                if slot_effect == EFFECT_HI_POWER:
                    hp_sql, hp_params = _build_hardpoint_filter(
                        constraints["turret_hardpoints"], constraints["launcher_hardpoints"]
                    )
                    if hp_sql:
                        ship_filter_sql += f" AND {hp_sql}"
                        ship_params.update(hp_params)
                    # Weapon size filter for turrets/launchers
                    ws_sql, ws_params = _build_weapon_size_filter(constraints["rig_size"])
                    ship_filter_sql += f" AND {ws_sql}"
                    ship_params.update(ws_params)
                if slot_effect == EFFECT_RIG_SLOT:
                    rs_sql, rs_params = _build_rig_size_filter(constraints["rig_size"])
                    ship_filter_sql += f" AND {rs_sql}"
                    ship_params.update(rs_params)
                # canFitShipGroup/Type filter (applies to all slot types)
                cf_sql, cf_params = _build_can_fit_ship_filter(constraints["group_id"], constraints["type_id"])
                ship_filter_sql += f" AND {cf_sql}"
                ship_params.update(cf_params)

            params = {"parent_id": effective_parent, "slot_effect": slot_effect}
            params.update(ship_params)

            cur.execute(f"""
                WITH RECURSIVE subtree AS (
                    -- Track root_id so we know which direct child each descendant belongs to
                    SELECT mg2."marketGroupID" as root_id, mg2."marketGroupID"
                    FROM "invMarketGroups" mg2
                    WHERE mg2."parentGroupID" = %(parent_id)s
                    UNION ALL
                    SELECT st.root_id, child."marketGroupID"
                    FROM subtree st
                    JOIN "invMarketGroups" child ON child."parentGroupID" = st."marketGroupID"
                ),
                roots_with_slot_items AS (
                    SELECT DISTINCT st.root_id
                    FROM subtree st
                    JOIN "invMarketGroups" leaf ON leaf."marketGroupID" = st."marketGroupID"
                        AND leaf."hasTypes" = 1
                    JOIN "invTypes" t ON t."marketGroupID" = leaf."marketGroupID"
                        AND t.published = 1
                    JOIN "dgmTypeEffects" dte ON dte."typeID" = t."typeID"
                        AND dte."effectID" = %(slot_effect)s
                    {ship_filter_sql}
                )
                SELECT mg."marketGroupID", mg."marketGroupName",
                       CASE WHEN mg."hasTypes" = 1 THEN true ELSE false END as "hasTypes",
                       mg."iconID",
                       (SELECT COUNT(*) FROM "invMarketGroups" c
                        WHERE c."parentGroupID" = mg."marketGroupID") as child_count
                FROM "invMarketGroups" mg
                WHERE mg."parentGroupID" = %(parent_id)s
                  AND mg."marketGroupID" IN (SELECT root_id FROM roots_with_slot_items)
                ORDER BY mg."marketGroupName"
            """, params)
        elif ship_type_id and category_root == MARKET_ROOT_MODULES:
            # No slot filter but ship selected — apply ship compatibility pruning
            constraints = _fetch_ship_constraints(db, ship_type_id)
            ship_filter_sql = ""
            ship_params: dict = {}

            # Hardpoint filter (exclude turret/launcher modules if ship has 0 of that hardpoint)
            hp_sql, hp_params = _build_hardpoint_filter(
                constraints["turret_hardpoints"], constraints["launcher_hardpoints"]
            )
            if hp_sql:
                ship_filter_sql += f" AND {hp_sql}"
                ship_params.update(hp_params)

            # Weapon size filter
            ws_sql, ws_params = _build_weapon_size_filter(constraints["rig_size"])
            ship_filter_sql += f" AND {ws_sql}"
            ship_params.update(ws_params)

            # canFitShipGroup/Type
            cf_sql, cf_params = _build_can_fit_ship_filter(constraints["group_id"], constraints["type_id"])
            ship_filter_sql += f" AND {cf_sql}"
            ship_params.update(cf_params)

            params = {"parent_id": effective_parent}
            params.update(ship_params)

            cur.execute(f"""
                WITH RECURSIVE subtree AS (
                    SELECT mg."marketGroupID" as root_id, mg."marketGroupID"
                    FROM "invMarketGroups" mg
                    WHERE mg."parentGroupID" = %(parent_id)s
                    UNION ALL
                    SELECT st.root_id, child."marketGroupID"
                    FROM subtree st
                    JOIN "invMarketGroups" child ON child."parentGroupID" = st."marketGroupID"
                ),
                roots_with_compatible_items AS (
                    SELECT DISTINCT st.root_id
                    FROM subtree st
                    JOIN "invMarketGroups" leaf ON leaf."marketGroupID" = st."marketGroupID"
                        AND leaf."hasTypes" = 1
                    JOIN "invTypes" t ON t."marketGroupID" = leaf."marketGroupID"
                        AND t.published = 1
                    {ship_filter_sql}
                )
                SELECT mg."marketGroupID", mg."marketGroupName",
                       CASE WHEN mg."hasTypes" = 1 THEN true ELSE false END as "hasTypes",
                       mg."iconID",
                       (SELECT COUNT(*) FROM "invMarketGroups" c
                        WHERE c."parentGroupID" = mg."marketGroupID") as child_count
                FROM "invMarketGroups" mg
                WHERE mg."parentGroupID" = %(parent_id)s
                  AND mg."marketGroupID" IN (SELECT root_id FROM roots_with_compatible_items)
                ORDER BY mg."marketGroupName"
            """, params)
        else:
            # No filtering at all — return all children with published items
            cur.execute("""
                WITH RECURSIVE subtree AS (
                    SELECT mg."marketGroupID" as root_id, mg."marketGroupID"
                    FROM "invMarketGroups" mg
                    WHERE mg."parentGroupID" = %(parent_id)s
                    UNION ALL
                    SELECT st.root_id, child."marketGroupID"
                    FROM subtree st
                    JOIN "invMarketGroups" child ON child."parentGroupID" = st."marketGroupID"
                ),
                roots_with_items AS (
                    SELECT DISTINCT st.root_id
                    FROM subtree st
                    JOIN "invMarketGroups" leaf ON leaf."marketGroupID" = st."marketGroupID"
                        AND leaf."hasTypes" = 1
                    JOIN "invTypes" t ON t."marketGroupID" = leaf."marketGroupID"
                        AND t.published = 1
                )
                SELECT mg."marketGroupID", mg."marketGroupName",
                       CASE WHEN mg."hasTypes" = 1 THEN true ELSE false END as "hasTypes",
                       mg."iconID",
                       (SELECT COUNT(*) FROM "invMarketGroups" c
                        WHERE c."parentGroupID" = mg."marketGroupID") as child_count
                FROM "invMarketGroups" mg
                WHERE mg."parentGroupID" = %(parent_id)s
                  AND (
                    mg."marketGroupID" IN (SELECT root_id FROM roots_with_items)
                    OR (mg."hasTypes" = 1 AND EXISTS (
                        SELECT 1 FROM "invTypes" t
                        WHERE t."marketGroupID" = mg."marketGroupID"
                          AND t.published = 1
                    ))
                  )
                ORDER BY mg."marketGroupName"
            """, {"parent_id": effective_parent})

        results = [
            MarketGroupNode(
                market_group_id=r["marketGroupID"],
                name=r["marketGroupName"],
                has_types=r["hasTypes"],
                child_count=r["child_count"],
                icon_id=r["iconID"],
            )
            for r in cur.fetchall()
        ]

        # When browsing modules root without slot filter, inject Rigs + Subsystems nodes
        if category_root == MARKET_ROOT_MODULES and effective_parent == category_root and not slot_type:
            for extra_root in [MARKET_ROOT_RIGS, MARKET_ROOT_SUBSYSTEMS]:
                cur.execute("""
                    SELECT mg."marketGroupID", mg."marketGroupName",
                           CASE WHEN mg."hasTypes" = 1 THEN true ELSE false END as "hasTypes",
                           mg."iconID",
                           (SELECT COUNT(*) FROM "invMarketGroups" c
                            WHERE c."parentGroupID" = mg."marketGroupID") as child_count
                    FROM "invMarketGroups" mg
                    WHERE mg."marketGroupID" = %(mg_id)s
                """, {"mg_id": extra_root})
                row = cur.fetchone()
                if row and row["child_count"] > 0:
                    results.append(MarketGroupNode(
                        market_group_id=row["marketGroupID"],
                        name=row["marketGroupName"],
                        has_types=row["hasTypes"],
                        child_count=row["child_count"],
                        icon_id=row["iconID"],
                    ))
            results.sort(key=lambda n: n.name)

        return results


@router.get(
    "/market-tree/items",
    summary="Get items in a market group leaf",
    description="Returns items (ships/modules/charges/drones) in a leaf market group.",
)
def get_market_tree_items(
    request: Request,
    market_group_id: int = Query(..., description="Market group ID (must be a leaf with hasTypes=1)"),
    category_root: int = Query(..., description="Root category (4=Ships, 9=Modules, 11=Charges, 157=Drones)"),
    slot_type: Optional[str] = Query(None, description="Slot filter for modules"),
    ship_type_id: Optional[int] = Query(None, description="Ship for compatibility filter"),
):
    """Return items in a leaf market group. Response type depends on category_root."""
    db = request.app.state.db

    if category_root == MARKET_ROOT_SHIPS:
        return _get_market_tree_ships(db, market_group_id)
    elif category_root in (MARKET_ROOT_MODULES, MARKET_ROOT_DRONES):
        return _get_market_tree_modules(db, market_group_id, slot_type, ship_type_id, category_root)
    elif category_root == MARKET_ROOT_CHARGES:
        return _get_market_tree_charges(db, market_group_id)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid category_root: {category_root}")


def _get_market_tree_ships(db, market_group_id: int) -> List[ShipSummary]:
    """Get ships in a market group leaf."""
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT t."typeID", t."typeName", g."groupID", g."groupName"
            FROM "invTypes" t
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE t."marketGroupID" = %(mg_id)s AND t.published = 1
            ORDER BY t."typeName"
        """, {"mg_id": market_group_id})
        ships = cur.fetchall()
        if not ships:
            return []

        type_ids = [s["typeID"] for s in ships]
        cur.execute("""
            SELECT "typeID", "attributeID",
                   COALESCE("valueFloat", "valueInt"::float) as value
            FROM "dgmTypeAttributes"
            WHERE "typeID" = ANY(%(ids)s) AND "attributeID" = ANY(%(attrs)s)
        """, {"ids": type_ids, "attrs": SHIP_ATTR_IDS})

        attr_map = {}
        for row in cur.fetchall():
            attr_map.setdefault(row["typeID"], {})[row["attributeID"]] = row["value"]

        return [
            ShipSummary(
                type_id=s["typeID"], type_name=s["typeName"],
                group_id=s["groupID"], group_name=s["groupName"],
                hi_slots=int(_get_attr(attr_map.get(s["typeID"], {}), ATTR_HI_SLOTS)),
                med_slots=int(_get_attr(attr_map.get(s["typeID"], {}), ATTR_MED_SLOTS)),
                low_slots=int(_get_attr(attr_map.get(s["typeID"], {}), ATTR_LOW_SLOTS)),
                rig_slots=int(_get_attr(attr_map.get(s["typeID"], {}), ATTR_RIG_SLOTS)),
                power_output=round(_get_attr(attr_map.get(s["typeID"], {}), ATTR_POWER_OUTPUT), 1),
                cpu_output=round(_get_attr(attr_map.get(s["typeID"], {}), ATTR_CPU_OUTPUT), 1),
                turret_hardpoints=int(_get_attr(attr_map.get(s["typeID"], {}), ATTR_TURRET_HARDPOINTS)),
                launcher_hardpoints=int(_get_attr(attr_map.get(s["typeID"], {}), ATTR_LAUNCHER_HARDPOINTS)),
                rig_size=int(_get_attr(attr_map.get(s["typeID"], {}), ATTR_RIG_SIZE)),
            )
            for s in ships
        ]


def _get_market_tree_modules(db, market_group_id: int, slot_type: str | None,
                              ship_type_id: int | None, category_root: int) -> List[ModuleSummary]:
    """Get modules/drones in a market group leaf."""
    cat_id = 18 if category_root == MARKET_ROOT_DRONES else 7

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        conditions = [
            't."marketGroupID" = %(mg_id)s',
            't.published = 1',
        ]
        params: dict = {"mg_id": market_group_id}

        # Slot filter
        slot_effect_ids = None
        if slot_type and cat_id == 7:
            slot_effect_ids = [eid for eid, name in SLOT_EFFECT_MAP.items() if name == slot_type.lower()]
            if slot_effect_ids:
                conditions.append("""EXISTS (
                    SELECT 1 FROM "dgmTypeEffects" dte
                    WHERE dte."typeID" = t."typeID" AND dte."effectID" = ANY(%(slot_effects)s)
                )""")
                params["slot_effects"] = slot_effect_ids

        # Ship compatibility
        if ship_type_id and cat_id == 7:
            constraints = _fetch_ship_constraints(db, ship_type_id)
            # Hardpoint filter — always apply when ship has 0 turret/launcher hardpoints
            is_high_slot = slot_effect_ids and EFFECT_HI_POWER in slot_effect_ids
            if is_high_slot or not slot_effect_ids:
                hp_sql, hp_params = _build_hardpoint_filter(
                    constraints["turret_hardpoints"], constraints["launcher_hardpoints"]
                )
                if hp_sql:
                    conditions.append(hp_sql)
                    params.update(hp_params)
            # Rig size filter
            if slot_effect_ids and EFFECT_RIG_SLOT in slot_effect_ids:
                rs_sql, rs_params = _build_rig_size_filter(constraints["rig_size"])
                conditions.append(rs_sql)
                params.update(rs_params)
            # Weapon size filter: turrets must match chargeSize, launchers by group
            ws_sql, ws_params = _build_weapon_size_filter(constraints["rig_size"])
            conditions.append(ws_sql)
            params.update(ws_params)
            # canFitShipGroup/canFitShipType: restrict specialty modules to allowed ships
            cf_sql, cf_params = _build_can_fit_ship_filter(constraints["group_id"], constraints["type_id"])
            conditions.append(cf_sql)
            params.update(cf_params)

        where = " AND ".join(conditions)
        cur.execute(f"""
            SELECT t."typeID", t."typeName", g."groupID", g."groupName"
            FROM "invTypes" t
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE {where}
            ORDER BY t."typeName"
        """, params)

        modules = cur.fetchall()
        if not modules:
            return []

        type_ids = [m["typeID"] for m in modules]

        # Batch attrs
        cur.execute("""
            SELECT "typeID", "attributeID",
                   COALESCE("valueFloat", "valueInt"::float) as value
            FROM "dgmTypeAttributes"
            WHERE "typeID" = ANY(%(ids)s)
              AND "attributeID" IN (%(cpu)s, %(pg)s, %(meta)s)
        """, {"ids": type_ids, "cpu": ATTR_CPU_NEED, "pg": ATTR_POWER_NEED, "meta": ATTR_META_LEVEL})

        attr_map = {}
        for row in cur.fetchall():
            attr_map.setdefault(row["typeID"], {})[row["attributeID"]] = row["value"]

        # Batch effects
        slot_map = {}
        hardpoint_map = {}
        if cat_id == 7:
            cur.execute("""
                SELECT "typeID", "effectID" FROM "dgmTypeEffects"
                WHERE "typeID" = ANY(%(ids)s)
                  AND "effectID" IN (%(hi)s, %(med)s, %(lo)s, %(rig)s, %(turret)s, %(launcher)s)
            """, {
                "ids": type_ids, "hi": EFFECT_HI_POWER, "med": EFFECT_MED_POWER,
                "lo": EFFECT_LO_POWER, "rig": EFFECT_RIG_SLOT,
                "turret": EFFECT_TURRET_FITTED, "launcher": EFFECT_LAUNCHER_FITTED,
            })
            for row in cur.fetchall():
                eid, tid = row["effectID"], row["typeID"]
                if eid in SLOT_EFFECT_MAP:
                    slot_map[tid] = SLOT_EFFECT_MAP[eid]
                if eid == EFFECT_TURRET_FITTED:
                    hardpoint_map[tid] = "turret"
                elif eid == EFFECT_LAUNCHER_FITTED:
                    hardpoint_map[tid] = "launcher"

        return [
            ModuleSummary(
                type_id=m["typeID"], type_name=m["typeName"],
                group_id=m["groupID"], group_name=m["groupName"],
                slot_type=slot_map.get(m["typeID"], "drone" if cat_id == 18 else "unknown"),
                cpu=round(_get_attr(attr_map.get(m["typeID"], {}), ATTR_CPU_NEED), 1),
                power=round(_get_attr(attr_map.get(m["typeID"], {}), ATTR_POWER_NEED), 1),
                meta_level=int(_get_attr(attr_map.get(m["typeID"], {}), ATTR_META_LEVEL)),
                hardpoint_type=hardpoint_map.get(m["typeID"]),
            )
            for m in modules
        ]


def _get_market_tree_charges(db, market_group_id: int) -> List[dict]:
    """Get charges in a market group leaf."""
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT t."typeID", t."typeName", g."groupName",
                   COALESCE(em.value, 0) as em,
                   COALESCE(th.value, 0) as thermal,
                   COALESCE(ki.value, 0) as kinetic,
                   COALESCE(ex.value, 0) as explosive,
                   COALESCE(ml.value, 0)::int as meta_level
            FROM "invTypes" t
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            LEFT JOIN LATERAL (
                SELECT COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes" WHERE "typeID" = t."typeID" AND "attributeID" = 114
            ) em ON true
            LEFT JOIN LATERAL (
                SELECT COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes" WHERE "typeID" = t."typeID" AND "attributeID" = 118
            ) th ON true
            LEFT JOIN LATERAL (
                SELECT COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes" WHERE "typeID" = t."typeID" AND "attributeID" = 117
            ) ki ON true
            LEFT JOIN LATERAL (
                SELECT COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes" WHERE "typeID" = t."typeID" AND "attributeID" = 116
            ) ex ON true
            LEFT JOIN LATERAL (
                SELECT COALESCE("valueFloat", "valueInt"::float) as value
                FROM "dgmTypeAttributes" WHERE "typeID" = t."typeID" AND "attributeID" = 633
            ) ml ON true
            WHERE t."marketGroupID" = %(mg_id)s AND t.published = 1
            ORDER BY COALESCE(ml.value, 0), t."typeName"
        """, {"mg_id": market_group_id})

        return [
            {
                "type_id": c["typeID"], "name": c["typeName"],
                "group_name": c["groupName"],
                "em": round(c["em"], 1), "thermal": round(c["thermal"], 1),
                "kinetic": round(c["kinetic"], 1), "explosive": round(c["explosive"], 1),
                "meta_level": c["meta_level"],
            }
            for c in cur.fetchall()
        ]


def _slot_type_to_effect(slot_type: str) -> int | None:
    """Convert slot type string to effect ID."""
    mapping = {"high": EFFECT_HI_POWER, "mid": EFFECT_MED_POWER, "low": EFFECT_LO_POWER, "rig": EFFECT_RIG_SLOT}
    return mapping.get(slot_type.lower())
