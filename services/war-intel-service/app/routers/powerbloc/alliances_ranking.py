"""Power Bloc alliance ranking endpoint."""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from ._shared import _get_coalition_members
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{leader_id}/alliances-ranking")
@handle_endpoint_errors()
def get_powerbloc_alliances_ranking(
    leader_id: int,
    days: int = Query(30, ge=1, le=90)
) -> List[Dict[str, Any]]:
    """Get member alliance ranking with activity share and efficiency."""
    with db_cursor() as cur:
        member_ids, coalition_name, name_map, ticker_map = _get_coalition_members(leader_id, cur)
        if not member_ids:
            return []

        cur.execute("""
            WITH unique_kills AS (
                SELECT DISTINCT ka.alliance_id, km.killmail_id, km.ship_value
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.alliance_id = ANY(%(member_ids)s)
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
            ),
            alliance_kills AS (
                SELECT uk.alliance_id,
                       COUNT(*) AS kills,
                       SUM(uk.ship_value) AS isk_killed
                FROM unique_kills uk
                GROUP BY uk.alliance_id
            ),
            alliance_pilots AS (
                SELECT ka.alliance_id,
                       COUNT(DISTINCT ka.character_id) AS active_pilots
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.alliance_id = ANY(%(member_ids)s)
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                GROUP BY ka.alliance_id
            ),
            alliance_deaths AS (
                SELECT km.victim_alliance_id AS alliance_id,
                       COUNT(*) AS deaths,
                       SUM(km.ship_value) AS isk_lost
                FROM killmails km
                WHERE km.victim_alliance_id = ANY(%(member_ids)s)
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                GROUP BY km.victim_alliance_id
            ),
            combined AS (
                SELECT COALESCE(k.alliance_id, d.alliance_id) AS alliance_id,
                       COALESCE(k.kills, 0) AS kills,
                       COALESCE(d.deaths, 0) AS deaths,
                       COALESCE(k.isk_killed, 0) AS isk_killed,
                       COALESCE(d.isk_lost, 0) AS isk_lost,
                       COALESCE(p.active_pilots, 0) AS active_pilots
                FROM alliance_kills k
                FULL OUTER JOIN alliance_deaths d ON k.alliance_id = d.alliance_id
                LEFT JOIN alliance_pilots p ON COALESCE(k.alliance_id, d.alliance_id) = p.alliance_id
            ),
            total AS (SELECT SUM(kills + deaths) AS total_activity FROM combined)
            SELECT c.alliance_id, c.kills::INT, c.deaths::INT, c.isk_killed, c.isk_lost,
                   c.active_pilots,
                   ROUND(100.0 * (c.kills + c.deaths) / NULLIF(t.total_activity, 0), 1) AS activity_share_pct,
                   ROUND(100.0 * c.kills / NULLIF(c.kills + c.deaths, 0), 1) AS efficiency,
                   ROUND(c.deaths::numeric / NULLIF(c.active_pilots, 0), 1) AS deaths_per_pilot
            FROM combined c CROSS JOIN total t
            WHERE c.kills + c.deaths > 0
            ORDER BY activity_share_pct DESC;
        """, {"member_ids": member_ids, "days": days})

        return [
            {
                "alliance_id": row["alliance_id"],
                "alliance_name": name_map.get(row["alliance_id"], f"Alliance {row['alliance_id']}"),
                "ticker": ticker_map.get(row["alliance_id"], ""),
                "kills": row["kills"] or 0,
                "deaths": row["deaths"] or 0,
                "isk_killed": float(row["isk_killed"] or 0),
                "isk_lost": float(row["isk_lost"] or 0),
                "activity_share_pct": float(row["activity_share_pct"] or 0),
                "efficiency": float(row["efficiency"] or 0),
                "active_pilots": row["active_pilots"] or 0,
                "deaths_per_pilot": float(row["deaths_per_pilot"] or 0)
            }
            for row in cur.fetchall()
        ]
