"""Power Bloc alliance ship specialization endpoint."""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from ._shared import _get_coalition_members
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{leader_id}/alliances-ships")
@handle_endpoint_errors()
def get_powerbloc_alliances_ships(
    leader_id: int,
    days: int = Query(30, ge=1, le=90)
) -> List[Dict[str, Any]]:
    """Get ship class specialization for each member alliance."""
    with db_cursor() as cur:
        member_ids, coalition_name, name_map, ticker_map = _get_coalition_members(leader_id, cur)
        if not member_ids:
            return []

        cur.execute("""
            WITH alliance_ship_raw AS (
                SELECT
                    ka.alliance_id,
                    CASE
                        WHEN ig."groupName" IN ('Frigate', 'Assault Frigate', 'Interceptor', 'Covert Ops', 'Electronic Attack Ship', 'Expedition Frigate', 'Logistics Frigate', 'Prototype Exploration Ship', 'Rookie ship') THEN 'Frigate'
                        WHEN ig."groupName" IN ('Destroyer', 'Interdictor', 'Command Destroyer', 'Tactical Destroyer') THEN 'Destroyer'
                        WHEN ig."groupName" IN ('Cruiser', 'Heavy Assault Cruiser', 'Strategic Cruiser', 'Recon Ship', 'Heavy Interdiction Cruiser', 'Logistics', 'Combat Recon Ship', 'Force Recon Ship') THEN 'Cruiser'
                        WHEN ig."groupName" IN ('Battlecruiser', 'Command Ship', 'Attack Battlecruiser') THEN 'Battlecruiser'
                        WHEN ig."groupName" IN ('Battleship', 'Black Ops', 'Marauder', 'Elite Battleship') THEN 'Battleship'
                        WHEN ig."groupName" IN ('Carrier', 'Dreadnought', 'Force Auxiliary', 'Supercarrier', 'Titan', 'Capital Industrial Ship', 'Jump Freighter') THEN 'Capital'
                        ELSE 'Other'
                    END AS ship_class
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE ka.alliance_id = ANY(%(member_ids)s)
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
            ),
            alliance_ships AS (
                SELECT alliance_id, ship_class, COUNT(*) AS count
                FROM alliance_ship_raw
                GROUP BY alliance_id, ship_class
            ),
            alliance_totals AS (
                SELECT alliance_id, SUM(count) AS total_count
                FROM alliance_ships
                GROUP BY alliance_id
            )
            SELECT
                s.alliance_id,
                s.ship_class,
                s.count,
                ROUND(100.0 * s.count / NULLIF(t.total_count, 0), 1) AS percentage
            FROM alliance_ships s
            JOIN alliance_totals t ON s.alliance_id = t.alliance_id
            ORDER BY s.alliance_id, s.count DESC;
        """, {"member_ids": member_ids, "days": days})

        return [
            {
                "alliance_id": row["alliance_id"],
                "alliance_name": name_map.get(row["alliance_id"], f"Alliance {row['alliance_id']}"),
                "ship_class": row["ship_class"],
                "count": row["count"] or 0,
                "percentage": float(row["percentage"] or 0)
            }
            for row in cur.fetchall()
        ]
