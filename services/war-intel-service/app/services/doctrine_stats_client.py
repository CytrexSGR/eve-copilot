"""HTTP client for character-service Doctrine Engine API.

Provides cached access to Dogma-powered doctrine stats (DPS, EHP, tank).
Falls back gracefully when character-service is unreachable.
"""

import logging
import os
from typing import Optional

import httpx
from psycopg2.extras import RealDictCursor

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


def resolve_doctrine_id(db, ship_name: str) -> Optional[int]:
    """Find a fleet_doctrines ID by ship name pattern."""
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id FROM fleet_doctrines
            WHERE is_active = TRUE
              AND (name ILIKE %s OR ship_type_id IN (
                  SELECT "typeID" FROM "invTypes" WHERE "typeName" ILIKE %s
              ))
            ORDER BY id
            LIMIT 1
            """,
            (f"%{ship_name}%", f"%{ship_name}%"),
        )
        row = cur.fetchone()
    return row["id"] if row else None


def clear_cache():
    """Clear in-memory stats cache."""
    _stats_cache.clear()
