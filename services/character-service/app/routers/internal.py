"""Internal endpoints for scheduler-triggered jobs.

These endpoints are called by the scheduler-service to execute
background tasks. Not exposed via api-gateway.
"""

import asyncio
import logging
from typing import Dict, Any

import httpx
from fastapi import APIRouter, Request
from psycopg2.extras import RealDictCursor

from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()

# ESI constants
ESI_BASE_URL = "https://esi.evetech.net/latest"
ESI_USER_AGENT = "EVE-CoPilot/1.0"

# Logistics ship group IDs
LOGISTICS_SHIP_GROUPS = {
    28: "Industrial",
    380: "Deep Space Transport",
    381: "Industrial Command Ship",
    513: "Freighter",
    902: "Jump Freighter",
    1022: "Blockade Runner",
    941: "Industrial Command Ship (ORE)",
    31: "Shuttle",
}


def _get_ship_type_ids(db) -> set:
    """Get all ship type IDs from logistics groups."""
    group_ids = list(LOGISTICS_SHIP_GROUPS.keys())
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            'SELECT "typeID" FROM "invTypes" WHERE "groupID" = ANY(%s) AND published = 1',
            (group_ids,),
        )
        return {row["typeID"] for row in cur.fetchall()}


def _get_ship_info(db, type_id: int) -> Dict[str, Any]:
    """Get ship name and group from SDE."""
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
            (type_id,),
        )
        row = cur.fetchone()
        return {"type_name": row["typeName"] if row else f"Unknown ({type_id})"}


def _get_ship_skill_requirements(db, type_id: int) -> list:
    """Get skill requirements for a ship."""
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT
                dta_skill."valueFloat" as skill_id,
                dta_level."valueFloat" as level
            FROM "dgmTypeAttributes" dta_skill
            JOIN "dgmTypeAttributes" dta_level
                ON dta_skill."typeID" = dta_level."typeID"
            WHERE dta_skill."typeID" = %s
              AND dta_skill."attributeID" IN (182, 183, 184)
              AND dta_level."attributeID" = dta_skill."attributeID" + 95
        """, (type_id,))
        return cur.fetchall()


def _get_cargo_capacity(db, type_id: int) -> float:
    """Get ship cargo capacity from SDE."""
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            'SELECT capacity FROM "invTypes" WHERE "typeID" = %s',
            (type_id,),
        )
        row = cur.fetchone()
        return float(row["capacity"]) if row and row["capacity"] else 0.0


def _resolve_location(db, location_id: int) -> str:
    """Resolve location ID to name."""
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            'SELECT "stationName" FROM "staStations" WHERE "stationID" = %s',
            (location_id,),
        )
        row = cur.fetchone()
        if row:
            return row["stationName"]

        cur.execute(
            'SELECT "solarSystemName" FROM "mapSolarSystems" WHERE "solarSystemID" = %s',
            (location_id,),
        )
        row = cur.fetchone()
        if row:
            return row["solarSystemName"]

    return f"Location {location_id}"


def _get_ship_group_name(db, type_id: int) -> str:
    """Get the ship group name from SDE."""
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT g."groupName"
            FROM "invTypes" t
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE t."typeID" = %s
        """, (type_id,))
        row = cur.fetchone()
        return row["groupName"] if row else "Unknown"


def sync_capabilities(db, auth_service_url: str) -> dict:
    """Sync ship capabilities for all authenticated characters.

    Args:
        db: Database connection pool
        auth_service_url: URL for auth-service

    Returns:
        Dict with sync statistics.
    """
    # Get authenticated characters from auth-service
    try:
        resp = httpx.get(f"{auth_service_url}/api/auth/characters", timeout=10)
        resp.raise_for_status()
        characters = resp.json().get("characters", [])
    except Exception as e:
        return {"error": f"Failed to get characters: {e}"}

    if not characters:
        return {"characters": 0, "total_synced": 0}

    # Get ship type IDs
    ship_type_ids = _get_ship_type_ids(db)
    logger.info(f"Tracking {len(ship_type_ids)} ship types across {len(characters)} characters")

    total_synced = 0
    errors = 0

    for char in characters:
        char_id = char["character_id"]
        char_name = char.get("character_name", str(char_id))

        try:
            # Get character assets via ESI (through character-service itself)
            # We use the internal DB directly since we're in the same service
            with db.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT item_id, type_id, location_id
                       FROM character_assets
                       WHERE character_id = %s AND type_id = ANY(%s)""",
                    (char_id, list(ship_type_ids)),
                )
                ships = cur.fetchall()

            if not ships:
                continue

            # Get character skills
            with db.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT skill_id, trained_skill_level
                       FROM character_skills
                       WHERE character_id = %s""",
                    (char_id,),
                )
                skills = {
                    row["skill_id"]: row["trained_skill_level"]
                    for row in cur.fetchall()
                }

            synced = 0
            for ship in ships:
                type_id = ship["type_id"]
                location_id = ship.get("location_id", 0)

                ship_info = _get_ship_info(db, type_id)
                ship_name = ship_info["type_name"]
                ship_group = _get_ship_group_name(db, type_id)
                cargo = _get_cargo_capacity(db, type_id)
                location_name = _resolve_location(db, location_id)

                # Check skill requirements (simplified -- just check can_fly)
                reqs = _get_ship_skill_requirements(db, type_id)
                can_fly = True
                missing = []
                for req in reqs:
                    skill_id = int(req.get("skill_id", 0))
                    required_level = int(req.get("level", 0))
                    current_level = skills.get(skill_id, 0)
                    if current_level < required_level:
                        can_fly = False
                        missing.append({"skill_id": skill_id, "required": required_level, "current": current_level})

                # Upsert capability
                with db.cursor() as cur:
                    cur.execute(
                        """INSERT INTO character_ship_capabilities
                           (character_id, character_name, type_id, ship_name,
                            ship_group, cargo_capacity, location_id, location_name,
                            can_fly, missing_skills, updated_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                           ON CONFLICT (character_id, type_id) DO UPDATE SET
                              character_name = EXCLUDED.character_name,
                              ship_name = EXCLUDED.ship_name,
                              ship_group = EXCLUDED.ship_group,
                              cargo_capacity = EXCLUDED.cargo_capacity,
                              location_id = EXCLUDED.location_id,
                              location_name = EXCLUDED.location_name,
                              can_fly = EXCLUDED.can_fly,
                              missing_skills = EXCLUDED.missing_skills,
                              updated_at = NOW()""",
                        (
                            char_id, char_name, type_id, ship_name,
                            ship_group, cargo, location_id, location_name,
                            can_fly, str(missing),
                        ),
                    )
                synced += 1

            total_synced += synced
            logger.info(f"Synced {synced} ships for {char_name}")

        except Exception as e:
            logger.error(f"Error syncing {char_name}: {e}")
            errors += 1

    return {
        "characters": len(characters),
        "total_synced": total_synced,
        "errors": errors,
    }


@router.post("/internal/sync-capabilities")
@handle_endpoint_errors("sync-capabilities")
async def api_sync_capabilities(request: Request):
    """Sync ship capabilities for all authenticated characters."""
    import os

    db = request.app.state.db
    auth_url = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:8000")
    result = await asyncio.to_thread(sync_capabilities, db, auth_url)
    if "error" in result:
        return {"status": "failed", "job": "capability-sync", "details": result}
    return {"status": "completed", "job": "capability-sync", "details": result}
