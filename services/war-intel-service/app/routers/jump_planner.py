"""
Jump Planner Router - Jump Range, Fatigue, and Route Planning

Provides endpoints for:
- Jump range calculations for capital ships
- Jump fatigue calculations
- JF route planning with cyno placement
"""

import logging
import math
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query

from app.models.base import CamelModel
from app.database import db_cursor

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# Ship Data
# ==============================================================================

# Jump capable ships with base jump ranges (in light years)
JUMP_SHIPS = {
    # Jump Freighters (JF skill)
    "Anshar": {"base_range": 5.0, "fuel_type": 16274, "fuel_per_ly": 750, "skill": "jump_freighters"},
    "Ark": {"base_range": 5.0, "fuel_type": 16272, "fuel_per_ly": 750, "skill": "jump_freighters"},
    "Nomad": {"base_range": 5.0, "fuel_type": 16273, "fuel_per_ly": 750, "skill": "jump_freighters"},
    "Rhea": {"base_range": 5.0, "fuel_type": 16275, "fuel_per_ly": 750, "skill": "jump_freighters"},

    # Carriers
    "Archon": {"base_range": 6.5, "fuel_type": 16272, "fuel_per_ly": 1000, "skill": "jump_drive_calibration"},
    "Chimera": {"base_range": 6.5, "fuel_type": 16275, "fuel_per_ly": 1000, "skill": "jump_drive_calibration"},
    "Nidhoggur": {"base_range": 6.5, "fuel_type": 16273, "fuel_per_ly": 1000, "skill": "jump_drive_calibration"},
    "Thanatos": {"base_range": 6.5, "fuel_type": 16274, "fuel_per_ly": 1000, "skill": "jump_drive_calibration"},

    # Supercarriers
    "Aeon": {"base_range": 6.0, "fuel_type": 16272, "fuel_per_ly": 2500, "skill": "jump_drive_calibration"},
    "Hel": {"base_range": 6.0, "fuel_type": 16273, "fuel_per_ly": 2500, "skill": "jump_drive_calibration"},
    "Nyx": {"base_range": 6.0, "fuel_type": 16274, "fuel_per_ly": 2500, "skill": "jump_drive_calibration"},
    "Wyvern": {"base_range": 6.0, "fuel_type": 16275, "fuel_per_ly": 2500, "skill": "jump_drive_calibration"},

    # Titans
    "Avatar": {"base_range": 6.0, "fuel_type": 16272, "fuel_per_ly": 5000, "skill": "jump_drive_calibration"},
    "Erebus": {"base_range": 6.0, "fuel_type": 16274, "fuel_per_ly": 5000, "skill": "jump_drive_calibration"},
    "Leviathan": {"base_range": 6.0, "fuel_type": 16275, "fuel_per_ly": 5000, "skill": "jump_drive_calibration"},
    "Ragnarok": {"base_range": 6.0, "fuel_type": 16273, "fuel_per_ly": 5000, "skill": "jump_drive_calibration"},

    # Dreadnoughts
    "Moros": {"base_range": 5.0, "fuel_type": 16274, "fuel_per_ly": 1000, "skill": "jump_drive_calibration"},
    "Naglfar": {"base_range": 5.0, "fuel_type": 16273, "fuel_per_ly": 1000, "skill": "jump_drive_calibration"},
    "Phoenix": {"base_range": 5.0, "fuel_type": 16275, "fuel_per_ly": 1000, "skill": "jump_drive_calibration"},
    "Revelation": {"base_range": 5.0, "fuel_type": 16272, "fuel_per_ly": 1000, "skill": "jump_drive_calibration"},

    # Force Auxiliaries (FAX)
    "Apostle": {"base_range": 5.0, "fuel_type": 16272, "fuel_per_ly": 1000, "skill": "jump_drive_calibration"},
    "Lif": {"base_range": 5.0, "fuel_type": 16273, "fuel_per_ly": 1000, "skill": "jump_drive_calibration"},
    "Minokawa": {"base_range": 5.0, "fuel_type": 16275, "fuel_per_ly": 1000, "skill": "jump_drive_calibration"},
    "Ninazu": {"base_range": 5.0, "fuel_type": 16274, "fuel_per_ly": 1000, "skill": "jump_drive_calibration"},

    # Black Ops
    "Panther": {"base_range": 3.5, "fuel_type": 16273, "fuel_per_ly": 400, "skill": "jump_drive_calibration"},
    "Redeemer": {"base_range": 3.5, "fuel_type": 16272, "fuel_per_ly": 400, "skill": "jump_drive_calibration"},
    "Sin": {"base_range": 3.5, "fuel_type": 16274, "fuel_per_ly": 400, "skill": "jump_drive_calibration"},
    "Widow": {"base_range": 3.5, "fuel_type": 16275, "fuel_per_ly": 400, "skill": "jump_drive_calibration"},
    "Marshal": {"base_range": 3.5, "fuel_type": 16275, "fuel_per_ly": 400, "skill": "jump_drive_calibration"},

    # Rorqual
    "Rorqual": {"base_range": 5.0, "fuel_type": 16275, "fuel_per_ly": 1000, "skill": "jump_drive_calibration"},
}

# Fuel types
FUEL_TYPES = {
    16272: "Amarr (Helium Isotopes)",
    16273: "Minmatar (Hydrogen Isotopes)",
    16274: "Gallente (Oxygen Isotopes)",
    16275: "Caldari (Nitrogen Isotopes)",
}


# ==============================================================================
# Models
# ==============================================================================

class JumpRange(CamelModel):
    """Jump range for a ship."""
    ship_name: str
    base_range: float
    jdc_level: int  # Jump Drive Calibration skill level
    jf_level: Optional[int] = None  # Jump Freighters skill level
    effective_range: float
    fuel_type: str
    fuel_per_ly: int


class FatigueCalculation(CamelModel):
    """Jump fatigue calculation result."""
    distance_ly: float
    current_fatigue_minutes: float
    new_fatigue_minutes: float
    blue_timer_minutes: float  # Jump activation cooldown
    red_timer_minutes: float  # Total fatigue
    fatigue_capped: bool
    time_until_jump: str  # Human readable
    time_until_fatigue_clear: str


class SystemInfo(CamelModel):
    """Solar system info for route planning."""
    system_id: int
    system_name: str
    region_id: int
    region_name: str
    security: float
    x: float
    y: float
    z: float


class RouteWaypoint(CamelModel):
    """A waypoint in a jump route."""
    system: SystemInfo
    distance_from_prev: Optional[float] = None
    cumulative_distance: float
    fuel_required: int
    fatigue_after_jump: float
    blue_timer: float
    wait_time_minutes: float  # Time to wait before next jump
    is_midpoint: bool = False
    jammed: bool = False


class JumpRoute(CamelModel):
    """Complete jump route."""
    origin: SystemInfo
    destination: SystemInfo
    ship_name: str
    effective_range: float
    waypoints: List[RouteWaypoint]
    total_jumps: int
    total_distance: float
    total_fuel: int
    total_time_minutes: float
    route_possible: bool
    error_message: Optional[str] = None


# ==============================================================================
# Calculation Functions
# ==============================================================================

def calculate_jump_range(ship_name: str, jdc_level: int = 5, jf_level: int = 5) -> float:
    """
    Calculate effective jump range for a ship.

    Formula: base_range * (1 + skill_level * 0.25)
    - JDC (Jump Drive Calibration) gives +25% per level to all jump ships
    - JF (Jump Freighters) gives additional +25% per level to JFs only
    """
    if ship_name not in JUMP_SHIPS:
        raise ValueError(f"Unknown jump ship: {ship_name}")

    ship = JUMP_SHIPS[ship_name]
    base = ship["base_range"]

    # JDC bonus (all jump ships)
    jdc_bonus = 1 + (jdc_level * 0.25)

    # JF bonus (jump freighters only)
    if ship["skill"] == "jump_freighters":
        jf_bonus = 1 + (jf_level * 0.25)
        return base * jdc_bonus * jf_bonus
    else:
        return base * jdc_bonus


def calculate_fatigue(distance_ly: float, current_fatigue: float = 0) -> dict:
    """
    Calculate jump fatigue.

    Formula:
    - Blue timer (cooldown) = max(1, (1 + distance) * fatigue_multiplier)
    - Red timer (fatigue) = current_fatigue * (1 + distance)
    - If no fatigue: new_fatigue = 1 + distance
    - Max fatigue cap: 300 minutes (5 hours)
    """
    if current_fatigue == 0:
        current_fatigue = 1  # Minimum base fatigue

    # Calculate new fatigue
    fatigue_multiplier = 1 + distance_ly
    new_fatigue = current_fatigue * fatigue_multiplier

    # Cap at 5 hours (300 minutes)
    capped = new_fatigue > 300
    new_fatigue = min(new_fatigue, 300)

    # Blue timer (jump activation cooldown) - minimum 1 minute
    blue_timer = max(1.0, fatigue_multiplier)

    # Time until fatigue clears (fatigue decays 1:1 with real time when not jumping)
    time_to_clear = new_fatigue

    return {
        "distance_ly": distance_ly,
        "current_fatigue_minutes": current_fatigue,
        "new_fatigue_minutes": new_fatigue,
        "blue_timer_minutes": blue_timer,
        "red_timer_minutes": new_fatigue,
        "fatigue_capped": capped,
        "time_until_jump": f"{int(blue_timer)}m {int((blue_timer % 1) * 60)}s",
        "time_until_fatigue_clear": f"{int(time_to_clear / 60)}h {int(time_to_clear % 60)}m",
    }


def calculate_distance(sys1: dict, sys2: dict) -> float:
    """Calculate distance between two systems in light years."""
    # EVE coordinates are in meters, 1 LY = 9.4607e15 meters
    METERS_PER_LY = 9.4607e15

    dx = sys2["x"] - sys1["x"]
    dy = sys2["y"] - sys1["y"]
    dz = sys2["z"] - sys1["z"]

    distance_meters = math.sqrt(dx**2 + dy**2 + dz**2)
    return distance_meters / METERS_PER_LY


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get("/ships")
def get_jump_ships():
    """Get list of all jump-capable ships with their base stats."""
    ships = []
    for name, data in JUMP_SHIPS.items():
        ships.append({
            "name": name,
            "base_range": data["base_range"],
            "fuel_type": FUEL_TYPES.get(data["fuel_type"], "Unknown"),
            "fuel_per_ly": data["fuel_per_ly"],
            "skill_type": data["skill"]
        })
    return {"ships": ships}


@router.get("/range/{ship_name}", response_model=JumpRange)
def get_jump_range(
    ship_name: str,
    jdc_level: int = Query(5, ge=0, le=5, description="Jump Drive Calibration skill level"),
    jf_level: int = Query(5, ge=0, le=5, description="Jump Freighters skill level (JF only)")
):
    """Calculate effective jump range for a ship."""
    if ship_name not in JUMP_SHIPS:
        raise HTTPException(status_code=404, detail=f"Unknown ship: {ship_name}")

    ship = JUMP_SHIPS[ship_name]
    effective_range = calculate_jump_range(ship_name, jdc_level, jf_level)

    return JumpRange(
        ship_name=ship_name,
        base_range=ship["base_range"],
        jdc_level=jdc_level,
        jf_level=jf_level if ship["skill"] == "jump_freighters" else None,
        effective_range=round(effective_range, 2),
        fuel_type=FUEL_TYPES.get(ship["fuel_type"], "Unknown"),
        fuel_per_ly=ship["fuel_per_ly"]
    )


@router.get("/fatigue", response_model=FatigueCalculation)
def calculate_jump_fatigue(
    distance_ly: float = Query(..., description="Jump distance in light years"),
    current_fatigue: float = Query(0, ge=0, le=300, description="Current fatigue in minutes")
):
    """Calculate jump fatigue for a given distance."""
    result = calculate_fatigue(distance_ly, current_fatigue)
    return FatigueCalculation(**result)


@router.get("/distance")
def get_system_distance(
    origin_id: int = Query(..., description="Origin system ID"),
    destination_id: int = Query(..., description="Destination system ID")
):
    """Calculate distance between two systems."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT m."solarSystemID" as solar_system_id,
                   m."solarSystemName" as solar_system_name,
                   r.region_id, r.region_name,
                   m.security as security_status,
                   m.x, m.y, m.z
            FROM "mapSolarSystems" m
            JOIN system_region_map r ON m."solarSystemID" = r.solar_system_id
            WHERE m."solarSystemID" IN (%s, %s)
        """, (origin_id, destination_id))
        rows = cur.fetchall()

    if len(rows) < 2:
        raise HTTPException(status_code=404, detail="One or both systems not found")

    systems = {row['solar_system_id']: row for row in rows}
    origin = systems.get(origin_id)
    destination = systems.get(destination_id)

    if not origin or not destination:
        raise HTTPException(status_code=404, detail="One or both systems not found")

    distance = calculate_distance(
        {"x": origin['x'], "y": origin['y'], "z": origin['z']},
        {"x": destination['x'], "y": destination['y'], "z": destination['z']}
    )

    return {
        "origin": {
            "system_id": origin_id,
            "system_name": origin['solar_system_name'],
            "region_name": origin['region_name']
        },
        "destination": {
            "system_id": destination_id,
            "system_name": destination['solar_system_name'],
            "region_name": destination['region_name']
        },
        "distance_ly": round(distance, 2)
    }


@router.get("/route", response_model=JumpRoute)
def calculate_jump_route(
    origin_id: int = Query(..., description="Origin system ID"),
    destination_id: int = Query(..., description="Destination system ID"),
    ship_name: str = Query("Rhea", description="Jump ship name"),
    jdc_level: int = Query(5, ge=0, le=5),
    jf_level: int = Query(5, ge=0, le=5),
    avoid_jammed: bool = Query(True, description="Avoid cyno jammed systems")
):
    """
    Calculate a jump route between two systems.

    This uses a simplified direct route - for complex routes with midpoints,
    see /route/optimized endpoint.
    """
    if ship_name not in JUMP_SHIPS:
        raise HTTPException(status_code=404, detail=f"Unknown ship: {ship_name}")

    ship = JUMP_SHIPS[ship_name]
    effective_range = calculate_jump_range(ship_name, jdc_level, jf_level)

    # Get system info
    with db_cursor() as cur:
        cur.execute("""
            SELECT m."solarSystemID" as solar_system_id,
                   m."solarSystemName" as solar_system_name,
                   r.region_id, r.region_name,
                   m.security as security_status,
                   m.x, m.y, m.z
            FROM "mapSolarSystems" m
            JOIN system_region_map r ON m."solarSystemID" = r.solar_system_id
            WHERE m."solarSystemID" IN (%s, %s)
        """, (origin_id, destination_id))
        rows = cur.fetchall()

    if len(rows) < 2:
        raise HTTPException(status_code=404, detail="One or both systems not found")

    systems = {row['solar_system_id']: row for row in rows}
    origin = systems.get(origin_id)
    destination = systems.get(destination_id)

    if not origin or not destination:
        raise HTTPException(status_code=404, detail="System not found")

    # Check if destination is jammed
    jammed_systems = set()
    if avoid_jammed:
        with db_cursor() as cur:
            cur.execute("SELECT solar_system_id FROM intel_cyno_jammers")
            jammed_systems = {row['solar_system_id'] for row in cur.fetchall()}

    origin_info = SystemInfo(
        system_id=origin_id,
        system_name=origin['solar_system_name'],
        region_id=origin['region_id'],
        region_name=origin['region_name'],
        security=origin['security_status'],
        x=origin['x'], y=origin['y'], z=origin['z']
    )

    dest_info = SystemInfo(
        system_id=destination_id,
        system_name=destination['solar_system_name'],
        region_id=destination['region_id'],
        region_name=destination['region_name'],
        security=destination['security_status'],
        x=destination['x'], y=destination['y'], z=destination['z']
    )

    # Calculate direct distance
    direct_distance = calculate_distance(
        {"x": origin['x'], "y": origin['y'], "z": origin['z']},
        {"x": destination['x'], "y": destination['y'], "z": destination['z']}
    )

    # Check if direct jump is possible
    if direct_distance <= effective_range:
        # Single jump route
        if destination_id in jammed_systems:
            return JumpRoute(
                origin=origin_info,
                destination=dest_info,
                ship_name=ship_name,
                effective_range=effective_range,
                waypoints=[],
                total_jumps=0,
                total_distance=direct_distance,
                total_fuel=0,
                total_time_minutes=0,
                route_possible=False,
                error_message="Destination system is cyno jammed"
            )

        fatigue = calculate_fatigue(direct_distance, 0)
        fuel = int(math.ceil(direct_distance * ship["fuel_per_ly"]))

        waypoint = RouteWaypoint(
            system=dest_info,
            distance_from_prev=direct_distance,
            cumulative_distance=direct_distance,
            fuel_required=fuel,
            fatigue_after_jump=fatigue["new_fatigue_minutes"],
            blue_timer=fatigue["blue_timer_minutes"],
            wait_time_minutes=0,
            is_midpoint=False,
            jammed=False
        )

        return JumpRoute(
            origin=origin_info,
            destination=dest_info,
            ship_name=ship_name,
            effective_range=effective_range,
            waypoints=[waypoint],
            total_jumps=1,
            total_distance=round(direct_distance, 2),
            total_fuel=fuel,
            total_time_minutes=fatigue["blue_timer_minutes"],
            route_possible=True
        )

    # Multi-jump route needed - find midpoints
    # For now, return that route needs midpoints
    return JumpRoute(
        origin=origin_info,
        destination=dest_info,
        ship_name=ship_name,
        effective_range=effective_range,
        waypoints=[],
        total_jumps=0,
        total_distance=round(direct_distance, 2),
        total_fuel=0,
        total_time_minutes=0,
        route_possible=False,
        error_message=f"Distance {direct_distance:.1f} LY exceeds jump range {effective_range:.1f} LY. Use /route/midpoints to find cyno placement."
    )


@router.get("/route/midpoints")
def find_midpoint_systems(
    origin_id: int = Query(..., description="Origin system ID"),
    destination_id: int = Query(..., description="Destination system ID"),
    ship_name: str = Query("Rhea", description="Jump ship name"),
    jdc_level: int = Query(5, ge=0, le=5),
    jf_level: int = Query(5, ge=0, le=5),
    avoid_jammed: bool = Query(True),
    max_security: float = Query(0.0, description="Max security (negative for null only)")
):
    """
    Find potential midpoint systems for a multi-jump route.

    Returns systems that are within jump range of both origin and destination.
    """
    if ship_name not in JUMP_SHIPS:
        raise HTTPException(status_code=404, detail=f"Unknown ship: {ship_name}")

    effective_range = calculate_jump_range(ship_name, jdc_level, jf_level)

    # Get origin and destination
    with db_cursor() as cur:
        cur.execute("""
            SELECT m."solarSystemID" as solar_system_id,
                   m."solarSystemName" as solar_system_name,
                   r.region_id, r.region_name,
                   m.security as security_status,
                   m.x, m.y, m.z
            FROM "mapSolarSystems" m
            JOIN system_region_map r ON m."solarSystemID" = r.solar_system_id
            WHERE m."solarSystemID" IN (%s, %s)
        """, (origin_id, destination_id))
        rows = cur.fetchall()

    systems = {row['solar_system_id']: row for row in rows}
    origin = systems.get(origin_id)
    destination = systems.get(destination_id)

    if not origin or not destination:
        raise HTTPException(status_code=404, detail="System not found")

    # Get jammed systems
    jammed_systems = set()
    if avoid_jammed:
        with db_cursor() as cur:
            cur.execute("SELECT solar_system_id FROM intel_cyno_jammers")
            jammed_systems = {row['solar_system_id'] for row in cur.fetchall()}

    # Find systems in range of both - using bounding box for efficiency
    range_meters = effective_range * 9.4607e15

    with db_cursor() as cur:
        cur.execute("""
            SELECT m."solarSystemID" as solar_system_id,
                   m."solarSystemName" as solar_system_name,
                   r.region_id, r.region_name,
                   m.security as security_status,
                   m.x, m.y, m.z
            FROM "mapSolarSystems" m
            JOIN system_region_map r ON m."solarSystemID" = r.solar_system_id
            WHERE m.security <= %s
              AND m."solarSystemID" NOT IN (%s, %s)
        """, (max_security, origin_id, destination_id))
        candidates = cur.fetchall()

    # Filter by actual distance
    valid_midpoints = []
    for sys in candidates:
        if sys['solar_system_id'] in jammed_systems:
            continue

        dist_from_origin = calculate_distance(
            {"x": origin['x'], "y": origin['y'], "z": origin['z']},
            {"x": sys['x'], "y": sys['y'], "z": sys['z']}
        )
        dist_to_dest = calculate_distance(
            {"x": sys['x'], "y": sys['y'], "z": sys['z']},
            {"x": destination['x'], "y": destination['y'], "z": destination['z']}
        )

        if dist_from_origin <= effective_range and dist_to_dest <= effective_range:
            valid_midpoints.append({
                "system_id": sys['solar_system_id'],
                "system_name": sys['solar_system_name'],
                "region_name": sys['region_name'],
                "security": round(sys['security_status'], 2),
                "distance_from_origin": round(dist_from_origin, 2),
                "distance_to_destination": round(dist_to_dest, 2),
                "total_distance": round(dist_from_origin + dist_to_dest, 2)
            })

    # Sort by total distance
    valid_midpoints.sort(key=lambda x: x["total_distance"])

    return {
        "origin": {"system_id": origin_id, "system_name": origin['solar_system_name']},
        "destination": {"system_id": destination_id, "system_name": destination['solar_system_name']},
        "ship_name": ship_name,
        "effective_range": effective_range,
        "midpoints": valid_midpoints[:50],  # Return top 50
        "total_found": len(valid_midpoints)
    }


@router.get("/cyno-alts")
def plan_cyno_alt_positions(
    origin_id: int = Query(..., description="Origin system ID"),
    destination_id: int = Query(..., description="Destination system ID"),
    ship_name: str = Query("Rhea", description="Jump ship name"),
    jdc_level: int = Query(5, ge=0, le=5),
    jf_level: int = Query(5, ge=0, le=5),
    prefer_stations: bool = Query(True, description="Prefer systems with NPC stations"),
    max_security: float = Query(0.45, description="Max security status"),
    min_security: float = Query(-1.0, description="Min security status")
):
    """
    Plan optimal cyno alt positions for a complete jump route.

    This endpoint:
    1. Calculates the complete route from origin to destination
    2. Suggests optimal cyno alt positions for each jump
    3. Considers: cynojammer status, NPC stations, security, distance optimization
    4. Returns fuel, fatigue, and timing estimates

    Combines Jump Range Calculator + Cynojammer Map for strategic capital movement.
    """
    if ship_name not in JUMP_SHIPS:
        raise HTTPException(status_code=404, detail=f"Unknown ship: {ship_name}")

    ship = JUMP_SHIPS[ship_name]
    effective_range = calculate_jump_range(ship_name, jdc_level, jf_level)

    # Get origin and destination info
    with db_cursor() as cur:
        cur.execute("""
            SELECT m."solarSystemID" as solar_system_id,
                   m."solarSystemName" as solar_system_name,
                   r.region_id, r.region_name,
                   m.security as security_status,
                   m.x, m.y, m.z
            FROM "mapSolarSystems" m
            JOIN system_region_map r ON m."solarSystemID" = r.solar_system_id
            WHERE m."solarSystemID" IN (%s, %s)
        """, (origin_id, destination_id))
        rows = cur.fetchall()

    systems = {row['solar_system_id']: row for row in rows}
    origin = systems.get(origin_id)
    destination = systems.get(destination_id)

    if not origin or not destination:
        raise HTTPException(status_code=404, detail="System not found")

    direct_distance = calculate_distance(
        {"x": origin['x'], "y": origin['y'], "z": origin['z']},
        {"x": destination['x'], "y": destination['y'], "z": destination['z']}
    )

    # Get jammed systems
    with db_cursor() as cur:
        cur.execute("SELECT solar_system_id FROM intel_cyno_jammers")
        jammed_systems = {row['solar_system_id'] for row in cur.fetchall()}

    # Get systems with NPC stations (for safe docking)
    station_systems = set()
    if prefer_stations:
        with db_cursor() as cur:
            cur.execute("""
                SELECT DISTINCT "solarSystemID"
                FROM "staStations"
                WHERE "stationID" < 61000000
            """)
            station_systems = {row['solarSystemID'] for row in cur.fetchall()}

    # Check if direct jump is possible
    if direct_distance <= effective_range and destination_id not in jammed_systems:
        fatigue = calculate_fatigue(direct_distance, 0)
        fuel = int(math.ceil(direct_distance * ship["fuel_per_ly"]))

        return {
            "route_type": "direct",
            "origin": {
                "system_id": origin_id,
                "system_name": origin['solar_system_name'],
                "region": origin['region_name']
            },
            "destination": {
                "system_id": destination_id,
                "system_name": destination['solar_system_name'],
                "region": destination['region_name'],
                "jammed": destination_id in jammed_systems
            },
            "ship": ship_name,
            "effective_range": effective_range,
            "total_distance": round(direct_distance, 2),
            "total_fuel": fuel,
            "total_fatigue_minutes": round(fatigue["new_fatigue_minutes"], 1),
            "cyno_positions": [{
                "waypoint": 1,
                "system_id": destination_id,
                "system_name": destination['solar_system_name'],
                "region": destination['region_name'],
                "security": round(destination['security_status'], 2),
                "distance_ly": round(direct_distance, 2),
                "fuel_required": fuel,
                "jammed": False,
                "has_station": destination_id in station_systems,
                "recommendation": "Final destination"
            }],
            "warnings": []
        }

    # Multi-jump route needed - find best cyno positions
    # Get all candidate systems
    with db_cursor() as cur:
        cur.execute("""
            SELECT m."solarSystemID" as solar_system_id,
                   m."solarSystemName" as solar_system_name,
                   r.region_id, r.region_name,
                   m.security as security_status,
                   m.x, m.y, m.z
            FROM "mapSolarSystems" m
            JOIN system_region_map r ON m."solarSystemID" = r.solar_system_id
            WHERE m.security BETWEEN %s AND %s
              AND m."solarSystemID" NOT IN (%s, %s)
        """, (min_security, max_security, origin_id, destination_id))
        all_systems = cur.fetchall()

    # Build route using greedy algorithm
    current_pos = {"x": origin['x'], "y": origin['y'], "z": origin['z']}
    current_system = origin
    cyno_positions = []
    total_fuel = 0
    total_fatigue = 0
    warnings = []

    max_iterations = 20  # Safety limit

    for iteration in range(max_iterations):
        # Find systems reachable from current position that get us closer to dest
        candidates = []

        for sys in all_systems:
            if sys['solar_system_id'] in jammed_systems:
                continue

            dist_from_current = calculate_distance(
                current_pos,
                {"x": sys['x'], "y": sys['y'], "z": sys['z']}
            )

            if dist_from_current > effective_range:
                continue

            dist_to_dest = calculate_distance(
                {"x": sys['x'], "y": sys['y'], "z": sys['z']},
                {"x": destination['x'], "y": destination['y'], "z": destination['z']}
            )

            # Score the system
            score = 0
            score -= dist_to_dest * 10  # Closer to dest = better
            if sys['solar_system_id'] in station_systems:
                score += 50  # Bonus for NPC station
            if sys['security_status'] < 0:
                score += 20  # Prefer nullsec for cyno

            candidates.append({
                "system": sys,
                "dist_from_current": dist_from_current,
                "dist_to_dest": dist_to_dest,
                "score": score
            })

        if not candidates:
            warnings.append(f"No valid cyno systems found from {current_system['solar_system_name']}")
            break

        # Check if we can reach destination directly
        dest_dist = calculate_distance(
            current_pos,
            {"x": destination['x'], "y": destination['y'], "z": destination['z']}
        )

        if dest_dist <= effective_range and destination_id not in jammed_systems:
            # Final jump to destination
            fatigue = calculate_fatigue(dest_dist, total_fatigue)
            fuel = int(math.ceil(dest_dist * ship["fuel_per_ly"]))

            cyno_positions.append({
                "waypoint": len(cyno_positions) + 1,
                "system_id": destination_id,
                "system_name": destination['solar_system_name'],
                "region": destination['region_name'],
                "security": round(destination['security_status'], 2),
                "distance_ly": round(dest_dist, 2),
                "fuel_required": fuel,
                "jammed": False,
                "has_station": destination_id in station_systems,
                "recommendation": "Final destination"
            })
            total_fuel += fuel
            total_fatigue = fatigue["new_fatigue_minutes"]
            break

        # Select best candidate
        candidates.sort(key=lambda x: x["score"], reverse=True)
        best = candidates[0]

        fatigue = calculate_fatigue(best["dist_from_current"], total_fatigue)
        fuel = int(math.ceil(best["dist_from_current"] * ship["fuel_per_ly"]))

        recommendation = "Midpoint cyno"
        if best["system"]["solar_system_id"] in station_systems:
            recommendation = "Midpoint with NPC station (safe dock)"

        cyno_positions.append({
            "waypoint": len(cyno_positions) + 1,
            "system_id": best["system"]["solar_system_id"],
            "system_name": best["system"]["solar_system_name"],
            "region": best["system"]["region_name"],
            "security": round(best["system"]["security_status"], 2),
            "distance_ly": round(best["dist_from_current"], 2),
            "fuel_required": fuel,
            "jammed": False,
            "has_station": best["system"]["solar_system_id"] in station_systems,
            "recommendation": recommendation
        })

        total_fuel += fuel
        total_fatigue = fatigue["new_fatigue_minutes"]
        current_pos = {"x": best["system"]['x'], "y": best["system"]['y'], "z": best["system"]['z']}
        current_system = best["system"]

    # Check if destination is jammed
    if destination_id in jammed_systems:
        warnings.append(f"WARNING: Destination {destination['solar_system_name']} has an active cyno jammer!")

    return {
        "route_type": "multi-jump",
        "origin": {
            "system_id": origin_id,
            "system_name": origin['solar_system_name'],
            "region": origin['region_name']
        },
        "destination": {
            "system_id": destination_id,
            "system_name": destination['solar_system_name'],
            "region": destination['region_name'],
            "jammed": destination_id in jammed_systems
        },
        "ship": ship_name,
        "effective_range": effective_range,
        "total_distance": round(direct_distance, 2),
        "total_jumps": len(cyno_positions),
        "total_fuel": total_fuel,
        "total_fatigue_minutes": round(total_fatigue, 1),
        "fatigue_clear_time": f"{int(total_fatigue / 60)}h {int(total_fatigue % 60)}m",
        "cyno_positions": cyno_positions,
        "warnings": warnings,
        "cyno_alt_checklist": [
            f"Position cyno alt in {pos['system_name']} ({pos['region']})"
            + (" - has NPC station" if pos['has_station'] else "")
            for pos in cyno_positions
        ]
    }
