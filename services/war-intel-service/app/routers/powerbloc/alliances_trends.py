"""Power Bloc alliance trends endpoint."""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from ._shared import _get_coalition_members
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{leader_id}/alliances-trends")
@handle_endpoint_errors()
def get_powerbloc_alliances_trends(
    leader_id: int,
    days: int = Query(30, ge=7, le=90)
) -> List[Dict[str, Any]]:
    """Get 7-day performance trends for each member alliance."""
    with db_cursor() as cur:
        member_ids, coalition_name, name_map, ticker_map = _get_coalition_members(leader_id, cur)
        if not member_ids:
            return []

        cur.execute("""
            WITH daily_alliance_stats AS (
                SELECT
                    COALESCE(ka.alliance_id, km.victim_alliance_id) AS alliance_id,
                    DATE(km.killmail_time) AS day,
                    COUNT(DISTINCT CASE WHEN ka.alliance_id = ANY(%(member_ids)s) THEN km.killmail_id END) AS kills,
                    COUNT(CASE WHEN km.victim_alliance_id = ANY(%(member_ids)s) THEN 1 END) AS deaths
                FROM killmails km
                LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                    AND ka.alliance_id = ANY(%(member_ids)s)
                WHERE (ka.alliance_id = ANY(%(member_ids)s) OR km.victim_alliance_id = ANY(%(member_ids)s))
                    AND km.killmail_time >= NOW() - INTERVAL '7 days'
                GROUP BY COALESCE(ka.alliance_id, km.victim_alliance_id), DATE(km.killmail_time)
            ),
            alliance_trends AS (
                SELECT
                    alliance_id,
                    day,
                    ROUND(100.0 * kills / NULLIF(kills + deaths, 0), 1) AS efficiency,
                    kills + deaths AS activity
                FROM daily_alliance_stats
            )
            SELECT alliance_id, day, efficiency, activity
            FROM alliance_trends
            WHERE activity > 0
                AND alliance_id = ANY(%(member_ids)s)
            ORDER BY alliance_id, day;
        """, {"member_ids": member_ids})

        return [
            {
                "alliance_id": row["alliance_id"],
                "alliance_name": name_map.get(row["alliance_id"], f"Alliance {row['alliance_id']}"),
                "day": row["day"].isoformat() if row["day"] else None,
                "efficiency": float(row["efficiency"] or 0),
                "activity": row["activity"] or 0
            }
            for row in cur.fetchall()
        ]
