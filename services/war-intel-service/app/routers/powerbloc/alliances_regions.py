"""Power Bloc alliance geographic spread endpoint."""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from ._shared import _get_coalition_members
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{leader_id}/alliances-regions")
@handle_endpoint_errors()
def get_powerbloc_alliances_regions(
    leader_id: int,
    days: int = Query(30, ge=1, le=90)
) -> List[Dict[str, Any]]:
    """Get geographic spread for each member alliance."""
    with db_cursor() as cur:
        member_ids, coalition_name, name_map, ticker_map = _get_coalition_members(leader_id, cur)
        if not member_ids:
            return []

        cur.execute("""
            WITH alliance_regions AS (
                SELECT
                    ka.alliance_id,
                    ms."regionID" AS region_id,
                    mr."regionName" AS region_name,
                    COUNT(*) AS kills_in_region
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
                JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
                WHERE ka.alliance_id = ANY(%(member_ids)s)
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                GROUP BY ka.alliance_id, ms."regionID", mr."regionName"
            ),
            ranked_regions AS (
                SELECT
                    alliance_id,
                    region_name,
                    kills_in_region,
                    ROW_NUMBER() OVER (PARTITION BY alliance_id ORDER BY kills_in_region DESC) AS rank
                FROM alliance_regions
            ),
            alliance_region_summary AS (
                SELECT
                    alliance_id,
                    COUNT(DISTINCT region_name) AS region_count,
                    ARRAY_AGG(region_name ORDER BY kills_in_region DESC) FILTER (WHERE rank <= 3) AS top_regions
                FROM ranked_regions
                GROUP BY alliance_id
            )
            SELECT alliance_id, region_count, top_regions
            FROM alliance_region_summary
            ORDER BY region_count DESC;
        """, {"member_ids": member_ids, "days": days})

        return [
            {
                "alliance_id": row["alliance_id"],
                "alliance_name": name_map.get(row["alliance_id"], f"Alliance {row['alliance_id']}"),
                "region_count": row["region_count"] or 0,
                "top_regions": row["top_regions"] or []
            }
            for row in cur.fetchall()
        ]
