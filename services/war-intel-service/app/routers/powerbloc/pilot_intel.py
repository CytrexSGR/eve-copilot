"""Power Bloc pilot intelligence endpoint."""

import logging
from typing import Dict, Any
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from app.services.intelligence.esi_utils import batch_resolve_alliance_info
from app.routers.intelligence.capsuleers import _build_pilots_from_rows, _build_fleet_overview
from ._shared import _get_coalition_members
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/{leader_id}/pilot-intel")
@handle_endpoint_errors()
def get_powerbloc_pilot_intel(
    leader_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """PowerBloc-level pilot intelligence — aggregated across all coalition alliances."""
    # _get_coalition_members needs dict cursor (RealDictCursor)
    with db_cursor() as dict_cur:
        member_ids, coalition_name, name_map, ticker_map = _get_coalition_members(leader_id, dict_cur)

    # Pilot intel queries use tuple cursor for _build_pilots_from_rows
    with db_cursor(cursor_factory=None) as cur:
        sql_base = """
            WITH pilot_base AS (
                SELECT
                    COALESCE(ka.character_id, km.victim_character_id) AS character_id,
                    cn.character_name,
                    COUNT(CASE WHEN ka.character_id IS NOT NULL THEN 1 END) AS kills,
                    COUNT(CASE WHEN km.victim_character_id = COALESCE(ka.character_id, km.victim_character_id)
                                AND km.victim_alliance_id = ANY(%(member_ids)s) THEN 1 END) AS deaths,
                    SUM(CASE WHEN ka.character_id IS NOT NULL THEN km.ship_value ELSE 0 END) AS isk_killed,
                    SUM(CASE WHEN km.victim_character_id = COALESCE(ka.character_id, km.victim_character_id)
                              AND km.victim_alliance_id = ANY(%(member_ids)s) THEN km.ship_value ELSE 0 END) AS isk_lost,
                    COUNT(DISTINCT DATE(km.killmail_time)) AS active_days,
                    MAX(km.killmail_time) AS last_active
                FROM killmails km
                LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                    AND ka.alliance_id = ANY(%(member_ids)s)
                LEFT JOIN character_name_cache cn ON COALESCE(ka.character_id, km.victim_character_id) = cn.character_id
                WHERE (ka.alliance_id = ANY(%(member_ids)s) OR km.victim_alliance_id = ANY(%(member_ids)s))
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                GROUP BY COALESCE(ka.character_id, km.victim_character_id), cn.character_name
            ),
            pilot_combat AS (
                SELECT
                    ka.character_id,
                    COUNT(CASE WHEN km.attacker_count <= 3 THEN 1 END) AS solo_kills,
                    COUNT(CASE WHEN km.attacker_count >= 10 THEN 1 END) AS fleet_kills,
                    AVG(km.attacker_count) AS avg_fleet_size,
                    BOOL_OR(ig."groupName" IN ('Carrier', 'Dreadnought', 'Supercarrier', 'Titan', 'Force Auxiliary', 'Lancer Dreadnought')) AS capital_usage
                FROM killmail_attackers ka
                JOIN killmails km ON ka.killmail_id = km.killmail_id
                LEFT JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
                LEFT JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE ka.alliance_id = ANY(%(member_ids)s)
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                GROUP BY ka.character_id
            ),
            pilot_losses AS (
                SELECT
                    km.victim_character_id AS character_id,
                    COUNT(CASE WHEN ka_cnt.cnt <= 3 THEN 1 END) AS solo_deaths,
                    COALESCE(AVG(km.ship_value), 0) AS avg_loss_value,
                    COUNT(CASE WHEN km.ship_value > 1000000000 THEN 1 END) AS expensive_losses
                FROM killmails km
                LEFT JOIN (
                    SELECT killmail_id, COUNT(*) AS cnt
                    FROM killmail_attackers GROUP BY killmail_id
                ) ka_cnt ON km.killmail_id = ka_cnt.killmail_id
                WHERE km.victim_alliance_id = ANY(%(member_ids)s)
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                GROUP BY km.victim_character_id
            ),
            pilot_trends AS (
                SELECT
                    character_id,
                    COUNT(CASE WHEN killmail_time >= NOW() - make_interval(days => 7) THEN 1 END) AS activity_7d,
                    COUNT(CASE WHEN killmail_time >= NOW() - make_interval(days => 14)
                               AND killmail_time < NOW() - make_interval(days => 7) THEN 1 END) AS activity_prev_7d
                FROM (
                    SELECT ka.character_id, km.killmail_time
                    FROM killmail_attackers ka
                    JOIN killmails km ON ka.killmail_id = km.killmail_id
                    WHERE ka.alliance_id = ANY(%(member_ids)s)
                        AND km.killmail_time >= NOW() - make_interval(days => 14)
                    UNION ALL
                    SELECT km.victim_character_id, km.killmail_time
                    FROM killmails km
                    WHERE km.victim_alliance_id = ANY(%(member_ids)s)
                        AND km.killmail_time >= NOW() - make_interval(days => 14)
                        AND km.victim_character_id IS NOT NULL
                ) engagements
                GROUP BY character_id
            )
            SELECT
                pb.character_id, pb.character_name,
                pb.kills, pb.deaths, pb.isk_killed, pb.isk_lost,
                pb.active_days, pb.last_active,
                ROUND(100.0 * pb.kills / NULLIF(pb.kills + pb.deaths, 0), 1) AS efficiency,
                ROUND(pb.kills::NUMERIC / NULLIF(pb.deaths, 0), 2) AS kd_ratio,
                COALESCE(pc.solo_kills, 0), COALESCE(pc.fleet_kills, 0),
                ROUND(100.0 * COALESCE(pc.fleet_kills, 0) / NULLIF(pb.kills, 0), 1),
                ROUND(COALESCE(pc.avg_fleet_size, 0), 1),
                COALESCE(pc.capital_usage, false),
                COALESCE(pl.solo_deaths, 0),
                ROUND(COALESCE(pl.avg_loss_value, 0), 0),
                COALESCE(pl.expensive_losses, 0),
                COALESCE(pt.activity_7d, 0), COALESCE(pt.activity_prev_7d, 0)
            FROM pilot_base pb
            LEFT JOIN pilot_combat pc ON pb.character_id = pc.character_id
            LEFT JOIN pilot_losses pl ON pb.character_id = pl.character_id
            LEFT JOIN pilot_trends pt ON pb.character_id = pt.character_id
            WHERE pb.kills > 0 OR pb.deaths > 0
            ORDER BY pb.kills DESC, pb.isk_killed DESC
        """
        cur.execute(sql_base, {"member_ids": member_ids, "days": days})

        # Reuse helpers from capsuleers module

        pilots = _build_pilots_from_rows(cur.fetchall(), days)

        # Activity timeline
        cur.execute("""
            SELECT ka.character_id, DATE(km.killmail_time) AS day, COUNT(*) AS kills
            FROM killmail_attackers ka
            JOIN killmails km ON ka.killmail_id = km.killmail_id
            WHERE ka.alliance_id = ANY(%(member_ids)s)
                AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
            GROUP BY ka.character_id, DATE(km.killmail_time)
            ORDER BY ka.character_id, day
        """, {"member_ids": member_ids, "days": days})

        timeline_data = defaultdict(list)
        for char_id, day, kills in cur.fetchall():
            timeline_data[char_id].append({"day": day.isoformat(), "kills": kills})

        # Daily active pilots timeline (attackers + victims)
        cur.execute("""
            SELECT day, COUNT(DISTINCT character_id) AS active_pilots
            FROM (
                SELECT DATE(km.killmail_time) AS day, ka.character_id
                FROM killmail_attackers ka
                JOIN killmails km ON ka.killmail_id = km.killmail_id
                WHERE ka.alliance_id = ANY(%(member_ids)s)
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                    AND ka.character_id IS NOT NULL
                UNION ALL
                SELECT DATE(km.killmail_time), km.victim_character_id
                FROM killmails km
                WHERE km.victim_alliance_id = ANY(%(member_ids)s)
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                    AND km.victim_character_id IS NOT NULL
            ) engagements
            GROUP BY day
            ORDER BY day
        """, {"member_ids": member_ids, "days": days})

        active_pilots_daily = [
            {"day": row[0], "active_pilots": row[1]}
            for row in cur.fetchall()
        ]

        # New unique pilots per day (first appearance in period)
        cur.execute("""
            SELECT first_day, COUNT(*) AS new_pilots
            FROM (
                SELECT character_id, MIN(day) AS first_day
                FROM (
                    SELECT ka.character_id, DATE(km.killmail_time) AS day
                    FROM killmail_attackers ka
                    JOIN killmails km ON ka.killmail_id = km.killmail_id
                    WHERE ka.alliance_id = ANY(%(member_ids)s)
                        AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                        AND ka.character_id IS NOT NULL
                    UNION ALL
                    SELECT km.victim_character_id, DATE(km.killmail_time)
                    FROM killmails km
                    WHERE km.victim_alliance_id = ANY(%(member_ids)s)
                        AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                        AND km.victim_character_id IS NOT NULL
                ) engagements
                GROUP BY character_id
            ) first_seen
            GROUP BY first_day
            ORDER BY first_day
        """, {"member_ids": member_ids, "days": days})

        new_pilots_by_day = {row[0]: row[1] for row in cur.fetchall()}
        cumulative = 0
        for entry in active_pilots_daily:
            new = new_pilots_by_day.get(entry["day"], 0)
            cumulative += new
            entry["new_pilots"] = new
            entry["cumulative"] = cumulative

        fleet_overview = _build_fleet_overview(pilots, days, active_pilots_daily)

        return {
            "fleet_overview": fleet_overview,
            "pilots": pilots,
            "timeline": dict(timeline_data),
            "active_pilots_timeline": active_pilots_daily
        }
