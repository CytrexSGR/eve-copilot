"""Corporation Pilot Statistics and Rankings."""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from ..corp_sql_helpers import classify_ship_group, CAPITAL_GROUPS
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/corporation/{corp_id}/top-pilots")
@handle_endpoint_errors()
def get_top_pilots(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> List[Dict[str, Any]]:
    """Get top high-value target pilots.

    Returns pilots ranked by kills or capital ship usage.
    """
    with db_cursor(cursor_factory=None) as cur:
        sql = """
            SELECT
                ka.character_id,
                cn.character_name,
                COUNT(*) AS kills,
                SUM(km.ship_value) AS isk_destroyed,
                COUNT(DISTINCT ig."groupName") FILTER (
                    WHERE ig."groupName" IN %(capital_groups)s
                ) > 0 AS has_capital_kills
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            LEFT JOIN character_name_cache cn ON ka.character_id = cn.character_id
            LEFT JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            LEFT JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE ka.corporation_id = %(corp_id)s
                AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            GROUP BY ka.character_id, cn.character_name
            ORDER BY kills DESC, isk_destroyed DESC
            LIMIT 20
        """

        cur.execute(sql, {"corp_id": corp_id, "capital_groups": CAPITAL_GROUPS, "days": days})

        pilots = []
        for char_id, char_name, kills, isk_destroyed, has_capital_kills in cur.fetchall():
            pilots.append({
                "character_id": char_id,
                "character_name": char_name,
                "kills": kills,
                "isk_destroyed": isk_destroyed or 0.0,
                "has_capital_kills": has_capital_kills,
            })
        return pilots

@router.get("/corporation/{corp_id}/doctrines")

@router.get("/corporation/{corp_id}/pilot-ranking")
@handle_endpoint_errors()
def get_pilot_ranking(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> List[Dict[str, Any]]:
    """Get individual pilot statistics ranked by kills.

    Returns top 50 pilots by kill count with efficiency, ISK, deaths.
    """
    with db_cursor(cursor_factory=None) as cur:
        sql = """
            WITH pilot_stats AS (
                SELECT
                    COALESCE(ka.character_id, km.victim_character_id) AS character_id,
                    cn.character_name,
                    COUNT(CASE WHEN ka.character_id IS NOT NULL THEN 1 END) AS kills,
                    COUNT(CASE WHEN km.victim_character_id = COALESCE(ka.character_id, km.victim_character_id)
                                AND km.victim_corporation_id = %(corp_id)s THEN 1 END) AS deaths,
                    SUM(CASE WHEN ka.character_id IS NOT NULL THEN km.ship_value ELSE 0 END) AS isk_killed,
                    SUM(CASE WHEN km.victim_character_id = COALESCE(ka.character_id, km.victim_character_id)
                              AND km.victim_corporation_id = %(corp_id)s THEN km.ship_value ELSE 0 END) AS isk_lost
                FROM killmails km
                LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                    AND ka.corporation_id = %(corp_id)s
                LEFT JOIN character_name_cache cn ON COALESCE(ka.character_id, km.victim_character_id) = cn.character_id
                WHERE (ka.corporation_id = %(corp_id)s OR km.victim_corporation_id = %(corp_id)s)
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                GROUP BY COALESCE(ka.character_id, km.victim_character_id), cn.character_name
            )
            SELECT
                character_id,
                character_name,
                kills,
                deaths,
                isk_killed,
                isk_lost,
                ROUND(100.0 * kills / NULLIF(kills + deaths, 0), 1) AS efficiency
            FROM pilot_stats
            WHERE kills > 0 OR deaths > 0
            ORDER BY kills DESC, isk_killed DESC
            LIMIT 50
        """

        cur.execute(sql, {"corp_id": corp_id, "days": days})

        pilots = []
        for char_id, char_name, kills, deaths, isk_killed, isk_lost, efficiency in cur.fetchall():
            pilots.append({
                "character_id": char_id,
                "character_name": char_name,
                "kills": kills,
                "deaths": deaths,
                "isk_killed": isk_killed or 0.0,
                "isk_lost": isk_lost or 0.0,
                "efficiency": efficiency or 0.0,
            })
        return pilots

@router.get("/corporation/{corp_id}/pilot-intel")
@handle_endpoint_errors()
def get_pilot_intel(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get comprehensive pilot intelligence for corporation members.

    Returns:
        - Fleet overview: morale score, participation rate, activity metrics
        - Pilot intelligence: engagement, activity patterns, combat style, risk profile
        - Activity timeline: 30-day kill timeline per pilot
        - Ship usage: primary ship class, diversity, doctrine adherence
    """
    with db_cursor(cursor_factory=None) as cur:
        # ============================================================================
        # CTE 1: Pilot Base Stats - Kills, Deaths, ISK, Activity Days
        # ============================================================================
        sql_base = """
            WITH pilot_base AS (
                SELECT
                    COALESCE(ka.character_id, km.victim_character_id) AS character_id,
                    cn.character_name,
                    COUNT(CASE WHEN ka.character_id IS NOT NULL THEN 1 END) AS kills,
                    COUNT(CASE WHEN km.victim_character_id = COALESCE(ka.character_id, km.victim_character_id)
                                AND km.victim_corporation_id = %(corp_id)s THEN 1 END) AS deaths,
                    SUM(CASE WHEN ka.character_id IS NOT NULL THEN km.ship_value ELSE 0 END) AS isk_killed,
                    SUM(CASE WHEN km.victim_character_id = COALESCE(ka.character_id, km.victim_character_id)
                              AND km.victim_corporation_id = %(corp_id)s THEN km.ship_value ELSE 0 END) AS isk_lost,
                    COUNT(DISTINCT DATE(km.killmail_time)) AS active_days,
                    MAX(km.killmail_time) AS last_active
                FROM killmails km
                LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                    AND ka.corporation_id = %(corp_id)s
                LEFT JOIN character_name_cache cn ON COALESCE(ka.character_id, km.victim_character_id) = cn.character_id
                WHERE (ka.corporation_id = %(corp_id)s OR km.victim_corporation_id = %(corp_id)s)
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                GROUP BY COALESCE(ka.character_id, km.victim_character_id), cn.character_name
            ),
            -- ============================================================================
            -- CTE 2: Combat Style - Solo, Fleet, Capital Usage
            -- ============================================================================
            pilot_combat AS (
                SELECT
                    ka.character_id,
                    COUNT(CASE WHEN km.attacker_count <= 3 THEN 1 END) AS solo_kills,
                    COUNT(CASE WHEN km.attacker_count >= 10 THEN 1 END) AS fleet_kills,
                    AVG(km.attacker_count) AS avg_fleet_size,
                    -- Capital usage check
                    BOOL_OR(ig."groupName" IN ('Carrier', 'Dreadnought', 'Supercarrier', 'Titan', 'Force Auxiliary', 'Lancer Dreadnought')) AS capital_usage
                FROM killmail_attackers ka
                JOIN killmails km ON ka.killmail_id = km.killmail_id
                LEFT JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
                LEFT JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE ka.corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                GROUP BY ka.character_id
            ),
            -- ============================================================================
            -- CTE 3: Loss Analysis - Solo Deaths, Expensive Losses
            -- ============================================================================
            pilot_losses AS (
                SELECT
                    km.victim_character_id AS character_id,
                    COUNT(CASE WHEN ka_cnt.cnt <= 3 THEN 1 END) AS solo_deaths,
                    COALESCE(AVG(km.ship_value), 0) AS avg_loss_value,
                    COUNT(CASE WHEN km.ship_value > 1000000000 THEN 1 END) AS expensive_losses
                FROM killmails km
                LEFT JOIN (
                    SELECT killmail_id, COUNT(*) AS cnt
                    FROM killmail_attackers
                    GROUP BY killmail_id
                ) ka_cnt ON km.killmail_id = ka_cnt.killmail_id
                WHERE km.victim_corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                GROUP BY km.victim_character_id
            ),
            -- ============================================================================
            -- CTE 4: Activity Trends - Last 7d vs Previous 7d
            -- ============================================================================
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
                    WHERE ka.corporation_id = %(corp_id)s
                        AND km.killmail_time >= NOW() - make_interval(days => 14)
                    UNION ALL
                    SELECT km.victim_character_id, km.killmail_time
                    FROM killmails km
                    WHERE km.victim_corporation_id = %(corp_id)s
                        AND km.killmail_time >= NOW() - make_interval(days => 14)
                        AND km.victim_character_id IS NOT NULL
                ) engagements
                GROUP BY character_id
            )
            -- ============================================================================
            -- Final Join: Combine All Intelligence
            -- ============================================================================
            SELECT
                pb.character_id,
                pb.character_name,
                pb.kills,
                pb.deaths,
                pb.isk_killed,
                pb.isk_lost,
                pb.active_days,
                pb.last_active,
                ROUND(100.0 * pb.kills / NULLIF(pb.kills + pb.deaths, 0), 1) AS efficiency,
                ROUND(pb.kills::NUMERIC / NULLIF(pb.deaths, 0), 2) AS kd_ratio,
                -- Combat Style
                COALESCE(pc.solo_kills, 0) AS solo_kills,
                COALESCE(pc.fleet_kills, 0) AS fleet_kills,
                ROUND(100.0 * COALESCE(pc.fleet_kills, 0) / NULLIF(pb.kills, 0), 1) AS fleet_participation_pct,
                ROUND(COALESCE(pc.avg_fleet_size, 0), 1) AS avg_fleet_size,
                COALESCE(pc.capital_usage, false) AS capital_usage,
                -- Loss Analysis
                COALESCE(pl.solo_deaths, 0) AS solo_deaths,
                ROUND(COALESCE(pl.avg_loss_value, 0), 0) AS avg_loss_value,
                COALESCE(pl.expensive_losses, 0) AS expensive_losses,
                -- Activity Trends
                COALESCE(pt.activity_7d, 0) AS activity_7d,
                COALESCE(pt.activity_prev_7d, 0) AS activity_prev_7d
            FROM pilot_base pb
            LEFT JOIN pilot_combat pc ON pb.character_id = pc.character_id
            LEFT JOIN pilot_losses pl ON pb.character_id = pl.character_id
            LEFT JOIN pilot_trends pt ON pb.character_id = pt.character_id
            WHERE pb.kills > 0 OR pb.deaths > 0
            ORDER BY pb.kills DESC, pb.isk_killed DESC
        """

        cur.execute(sql_base, {"corp_id": corp_id, "days": days})

        pilots = []
        for row in cur.fetchall():
            # Calculate morale score (0-100)
            activity_consistency = (float(row[6]) / days) * 100  # active_days / total_days
            efficiency = float(row[8] or 0)
            activity_7d = int(row[18] if len(row) > 18 else 0)
            activity_prev_7d = int(row[19] if len(row) > 19 else 0)
            trend_factor = (activity_7d / max(activity_prev_7d, 1)) * 100 if activity_prev_7d > 0 else 100  # 7d vs prev 7d
            morale_score = (activity_consistency * 0.3 + efficiency * 0.4 + min(trend_factor, 150) * 0.3)

            pilots.append({
                "character_id": row[0],
                "character_name": row[1],
                "kills": row[2],
                "deaths": row[3],
                "isk_killed": float(row[4] or 0),
                "isk_lost": float(row[5] or 0),
                "active_days": row[6],
                "last_active": row[7].isoformat() if row[7] else None,
                "efficiency": float(row[8] or 0),
                "kd_ratio": float(row[9]) if row[9] else 0.0,
                "solo_kills": row[10],
                "fleet_kills": row[11],
                "fleet_participation_pct": float(row[12] or 0),
                "avg_fleet_size": float(row[13] or 0),
                "capital_usage": row[14],
                "solo_deaths": row[15],
                "avg_loss_value": float(row[16] or 0),
                "expensive_losses": row[17],
                "primary_ship_class": "Unknown",  # Simplified - was too complex for shared memory
                "ship_diversity": 0,  # Simplified
                "primary_region": "Unknown",  # Simplified
                "system_diversity": 0,  # Simplified
                "activity_7d": row[18],
                "activity_prev_7d": row[19],
                "morale_score": round(morale_score, 1)
            })

        # ============================================================================
        # Fleet Overview Summary
        # ============================================================================
        total_pilots = len(pilots)
        active_7d = sum(1 for p in pilots if p["activity_7d"] > 0)
        avg_activity = sum(p["kills"] + p["deaths"] for p in pilots) / total_pilots if total_pilots > 0 else 0
        avg_morale = sum(p["morale_score"] for p in pilots) / total_pilots if total_pilots > 0 else 0
        avg_participation = sum(p["fleet_participation_pct"] for p in pilots) / total_pilots if total_pilots > 0 else 0
        elite_count = sum(1 for p in pilots if p["morale_score"] >= 70 and p["efficiency"] >= 70)

        # ============================================================================
        # Activity Timeline (30-day kill timeline per pilot)
        # ============================================================================
        sql_timeline = """
            SELECT
                ka.character_id,
                DATE(km.killmail_time) AS day,
                COUNT(*) AS kills
            FROM killmail_attackers ka
            JOIN killmails km ON ka.killmail_id = km.killmail_id
            WHERE ka.corporation_id = %(corp_id)s
                AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
            GROUP BY ka.character_id, DATE(km.killmail_time)
            ORDER BY ka.character_id, day
        """

        cur.execute(sql_timeline, {"corp_id": corp_id, "days": days})

        timeline_data = defaultdict(list)
        for char_id, day, kills in cur.fetchall():
            timeline_data[char_id].append({
                "day": day.isoformat(),
                "kills": kills
            })

        # Daily active pilots timeline (attackers + victims)
        cur.execute("""
            SELECT day, COUNT(DISTINCT character_id) AS active_pilots
            FROM (
                SELECT DATE(km.killmail_time) AS day, ka.character_id
                FROM killmail_attackers ka
                JOIN killmails km ON ka.killmail_id = km.killmail_id
                WHERE ka.corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                    AND ka.character_id IS NOT NULL
                UNION ALL
                SELECT DATE(km.killmail_time), km.victim_character_id
                FROM killmails km
                WHERE km.victim_corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                    AND km.victim_character_id IS NOT NULL
            ) engagements
            GROUP BY day
            ORDER BY day
        """, {"corp_id": corp_id, "days": days})

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
                    WHERE ka.corporation_id = %(corp_id)s
                        AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                        AND ka.character_id IS NOT NULL
                    UNION ALL
                    SELECT km.victim_character_id, DATE(km.killmail_time)
                    FROM killmails km
                    WHERE km.victim_corporation_id = %(corp_id)s
                        AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                        AND km.victim_character_id IS NOT NULL
                ) engagements
                GROUP BY character_id
            ) first_seen
            GROUP BY first_day
            ORDER BY first_day
        """, {"corp_id": corp_id, "days": days})

        new_pilots_by_day = {row[0]: row[1] for row in cur.fetchall()}
        cumulative = 0
        for entry in active_pilots_daily:
            new = new_pilots_by_day.get(entry["day"], 0)
            cumulative += new
            entry["new_pilots"] = new
            entry["cumulative"] = cumulative

        avg_daily_active = round(sum(d["active_pilots"] for d in active_pilots_daily) / len(active_pilots_daily), 1) if active_pilots_daily else 0

        # ── Member count history ──────────────────────────────────────
        cur.execute("""
            SELECT snapshot_date, member_count, alliance_id
            FROM corporation_member_count_history
            WHERE corporation_id = %(corp_id)s
              AND snapshot_date >= CURRENT_DATE - INTERVAL '1 day' * %(days)s
            ORDER BY snapshot_date
        """, {"corp_id": corp_id, "days": days})
        member_history = [
            {"date": str(row[0]), "member_count": row[1], "alliance_id": row[2]}
            for row in cur.fetchall()
        ]

        # Compute member change delta
        member_count_change = None
        member_count_change_pct = None
        if len(member_history) >= 2:
            oldest = member_history[0]["member_count"]
            newest = member_history[-1]["member_count"]
            member_count_change = newest - oldest
            member_count_change_pct = round(100.0 * member_count_change / oldest, 1) if oldest > 0 else 0

        return {
            "fleet_overview": {
                "total_pilots": total_pilots,
                "active_7d": active_7d,
                "avg_activity": round(avg_activity, 1),
                "avg_daily_active": avg_daily_active,
                "avg_morale": round(avg_morale, 1),
                "avg_participation": round(avg_participation, 1),
                "elite_count": elite_count,
                "member_count_change": member_count_change,
                "member_count_change_pct": member_count_change_pct,
            },
            "pilots": pilots,
            "timeline": dict(timeline_data),
            "active_pilots_timeline": active_pilots_daily,
            "member_count_history": member_history,
        }

# ============================================================================
# CAPITALS TAB - Capital Fleet Intel
# ============================================================================

