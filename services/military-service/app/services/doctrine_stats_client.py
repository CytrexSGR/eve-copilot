"""HTTP client for character-service Doctrine Engine API.

Provides cached access to Dogma-powered doctrine stats (DPS, EHP, tank).
Falls back gracefully when character-service is unreachable.

Adapted for military-service split-DB architecture:
- fleet_doctrines -> military DB (db_cursor)
- invTypes -> SDE DB (sde_cursor)
"""

import logging
import os
from typing import Optional

import httpx

from app.database import db_cursor, sde_cursor

logger = logging.getLogger(__name__)

CHARACTER_SERVICE_URL = os.environ.get(
    "CHARACTER_SERVICE_URL", "http://character-service:8000"
)

_stats_cache: dict[int, dict] = {}


async def get_doctrine_stats(doctrine_id: int) -> Optional[dict]:
    """Fetch full doctrine stats from character-service.

    Returns dict with keys: dps, ehp, tank_type, cap_stable, weapon_dps, drone_dps.
    Returns None on failure.
    """
    if doctrine_id in _stats_cache:
        return _stats_cache[doctrine_id]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{CHARACTER_SERVICE_URL}/api/doctrines/{doctrine_id}/stats"
            )
        if resp.status_code != 200:
            logger.warning("Doctrine stats %s returned %s", doctrine_id, resp.status_code)
            return None

        data = resp.json()
        result = {
            "dps": data.get("offense", {}).get("total_dps", 0),
            "ehp": data.get("defense", {}).get("total_ehp", 0),
            "tank_type": data.get("defense", {}).get("tank_type", "unknown"),
            "cap_stable": data.get("capacitor", {}).get("stable", False),
            "weapon_dps": data.get("offense", {}).get("weapon_dps", 0),
            "drone_dps": data.get("offense", {}).get("drone_dps", 0),
        }
        _stats_cache[doctrine_id] = result
        return result
    except Exception as e:
        logger.warning("Failed to fetch doctrine stats %s: %s", doctrine_id, e)
        return None


async def get_doctrine_dps(doctrine_id: int) -> Optional[float]:
    """Fetch just the DPS for a doctrine."""
    stats = await get_doctrine_stats(doctrine_id)
    return stats["dps"] if stats else None


def resolve_doctrine_id(ship_name: str) -> Optional[int]:
    """Find a fleet_doctrines ID by ship name pattern.

    Split-DB version: queries military DB for fleet_doctrines
    and SDE DB for invTypes separately.
    """
    # First, look up matching typeIDs from SDE
    matching_type_ids = []
    with sde_cursor() as cur:
        cur.execute(
            """SELECT "typeID" FROM "invTypes" WHERE "typeName" ILIKE %s""",
            (f"%{ship_name}%",),
        )
        matching_type_ids = [row["typeID"] for row in cur.fetchall()]

    # Now search fleet_doctrines in military DB
    with db_cursor() as cur:
        if matching_type_ids:
            cur.execute(
                """
                SELECT id FROM fleet_doctrines
                WHERE is_active = TRUE
                  AND (name ILIKE %s OR ship_type_id = ANY(%s))
                ORDER BY id
                LIMIT 1
                """,
                (f"%{ship_name}%", matching_type_ids),
            )
        else:
            cur.execute(
                """
                SELECT id FROM fleet_doctrines
                WHERE is_active = TRUE
                  AND name ILIKE %s
                ORDER BY id
                LIMIT 1
                """,
                (f"%{ship_name}%",),
            )
        row = cur.fetchone()
    return row["id"] if row else None


def clear_cache():
    """Clear in-memory stats cache."""
    _stats_cache.clear()
