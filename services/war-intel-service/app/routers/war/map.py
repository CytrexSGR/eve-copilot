"""
Map and navigation endpoints for War Intel API.

Provides endpoints for 2D map rendering and system positions.
"""

import logging

from fastapi import APIRouter, HTTPException

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/map/systems")
@handle_endpoint_errors()
def get_map_systems():
    """Get all solar system positions for 2D map rendering."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                ms."solarSystemID" as system_id,
                ms."solarSystemName" as system_name,
                ms."regionID" as region_id,
                mr."regionName" as region_name,
                ms.x,
                ms.z,
                ms.security
            FROM "mapSolarSystems" ms
            JOIN "mapRegions" mr ON mr."regionID" = ms."regionID"
            ORDER BY ms."solarSystemID"
        """)
        rows = cur.fetchall()

    return {
        "systems": [{
            "system_id": row["system_id"],
            "system_name": row["system_name"],
            "region_id": row["region_id"],
            "region_name": row["region_name"],
            "x": float(row["x"]) if row.get("x") else 0.0,
            "z": float(row["z"]) if row.get("z") else 0.0,
            "security": float(row["security"]) if row.get("security") else 0.0
        } for row in rows],
        "total": len(rows)
    }
