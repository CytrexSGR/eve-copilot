"""Alliance Capsuleer Intelligence Endpoints."""

import logging
from typing import Dict, Any, Optional
from collections import defaultdict
from fastapi import APIRouter, Query, HTTPException

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/fast/{alliance_id}/capsuleers")
@handle_endpoint_errors()
def get_alliance_capsuleers(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """
    Get capsuleer statistics for an alliance grouped by corporations.

    Returns:
    - Summary: total/active pilots, kills/deaths, efficiency
    - Corps: ranked by kills with stats
    - Top pilots: ranked by kills with individual stats
    """
    with db_cursor() as cur:
        # Active pilots = attackers + victims (all PvP participants)
        cur.execute("""
            SELECT COUNT(DISTINCT character_id) as active_pilots
            FROM (
                SELECT ka.character_id
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = %(aid)s
                  AND k.killmail_time > NOW() - make_interval(days => %(days)s)
                  AND ka.character_id IS NOT NULL
                UNION
                SELECT k.victim_character_id
                FROM killmails k
                WHERE k.victim_alliance_id = %(aid)s
                  AND k.killmail_time > NOW() - make_interval(days => %(days)s)
                  AND k.victim_character_id IS NOT NULL
            ) all_pilots
        """, {"aid": alliance_id, "days": days})
        active_pilots = cur.fetchone()["active_pilots"] or 0

        # Total pilots from ESI member count
        cur.execute("""
            SELECT COALESCE(SUM(member_count), 0) as total_pilots
            FROM corporations WHERE alliance_id = %s
        """, (alliance_id,))
        total_pilots = cur.fetchone()["total_pilots"] or 0

        # Kill stats (deduplicated by killmail_id for correct ISK)
        cur.execute("""
            WITH unique_kills AS (
                SELECT DISTINCT ka.killmail_id, k.ship_value
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = %(aid)s
                  AND k.killmail_time > NOW() - make_interval(days => %(days)s)
                  AND ka.character_id IS NOT NULL
            )
            SELECT COUNT(*) as total_kills,
                   COALESCE(SUM(ship_value), 0) as total_isk_destroyed
            FROM unique_kills
        """, {"aid": alliance_id, "days": days})
        attack_summary = cur.fetchone()

        cur.execute("""
            SELECT
                COUNT(*) as total_deaths,
                SUM(ship_value) as total_isk_lost,
                COUNT(*) FILTER (WHERE ship_type_id = 670) as pod_deaths
            FROM killmails
            WHERE victim_alliance_id = %s
              AND killmail_time > NOW() - INTERVAL '%s days'
        """, (alliance_id, days))
        death_summary = cur.fetchone()

        total_kills = attack_summary['total_kills'] or 0
        total_deaths = death_summary['total_deaths'] or 0
        total_isk_destroyed = float(attack_summary['total_isk_destroyed'] or 0)
        total_isk_lost = float(death_summary['total_isk_lost'] or 0)
        pod_deaths = death_summary['pod_deaths'] or 0
        ship_deaths = total_deaths - pod_deaths

        efficiency = 0
        if total_isk_destroyed + total_isk_lost > 0:
            efficiency = round(total_isk_destroyed / (total_isk_destroyed + total_isk_lost) * 100, 1)

        # Pod survival rate: how often pilots escape their pod after losing a ship
        pod_survival_rate = 0.0
        if ship_deaths > 0:
            pod_survival_rate = round((1 - pod_deaths / ship_deaths) * 100, 1)
            pod_survival_rate = max(0.0, min(100.0, pod_survival_rate))

        summary = {
            "total_pilots": total_pilots,
            "active_pilots": active_pilots,
            "total_kills": total_kills,
            "total_deaths": total_deaths,
            "efficiency": efficiency,
            "pod_deaths": pod_deaths,
            "ship_deaths": ship_deaths,
            "pod_survival_rate": pod_survival_rate
        }

        # Corp stats — use DISTINCT to deduplicate killmails (multiple attackers per kill)
        cur.execute("""
            WITH unique_kills AS (
                SELECT DISTINCT ka.corporation_id, ka.killmail_id, k.ship_value
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = %s
                  AND k.killmail_time > NOW() - INTERVAL '%s days'
                  AND ka.character_id IS NOT NULL
            ),
            corp_kills AS (
                SELECT corporation_id,
                       COUNT(*) as kills,
                       SUM(ship_value) as isk_destroyed
                FROM unique_kills
                GROUP BY corporation_id
            ),
            corp_pilots AS (
                SELECT ka.corporation_id,
                       COUNT(DISTINCT ka.character_id) as active_pilots
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = %s
                  AND k.killmail_time > NOW() - INTERVAL '%s days'
                  AND ka.character_id IS NOT NULL
                GROUP BY ka.corporation_id
            ),
            victim_stats AS (
                SELECT
                    victim_corporation_id as corporation_id,
                    COUNT(*) as deaths,
                    SUM(ship_value) as isk_lost
                FROM killmails
                WHERE victim_alliance_id = %s
                  AND killmail_time > NOW() - INTERVAL '%s days'
                GROUP BY victim_corporation_id
            )
            SELECT
                ck.corporation_id as corp_id,
                c.corporation_name as corp_name,
                c.ticker,
                COALESCE(cp.active_pilots, 0) as active_pilots,
                ck.kills,
                COALESCE(v.deaths, 0) as deaths,
                ck.isk_destroyed,
                COALESCE(v.isk_lost, 0) as isk_lost,
                ROUND(ck.isk_destroyed::numeric / NULLIF(ck.isk_destroyed + COALESCE(v.isk_lost, 0), 0) * 100, 1) as efficiency
            FROM corp_kills ck
            LEFT JOIN corp_pilots cp ON ck.corporation_id = cp.corporation_id
            LEFT JOIN victim_stats v ON ck.corporation_id = v.corporation_id
            LEFT JOIN corporations c ON ck.corporation_id = c.corporation_id
            WHERE ck.corporation_id IS NOT NULL
            ORDER BY ck.kills DESC
            LIMIT 20
        """, (alliance_id, days, alliance_id, days, alliance_id, days))

        corps_raw = cur.fetchall()
        total_alliance_kills = total_kills if total_kills > 0 else 1

        corps = []
        for row in corps_raw:
            corps.append({
                "corp_id": row["corp_id"],
                "corp_name": row["corp_name"] or f"Corp {row['corp_id']}",
                "ticker": row["ticker"] or "???",
                "active_pilots": row["active_pilots"] or 0,
                "kills": row["kills"] or 0,
                "deaths": row["deaths"] or 0,
                "efficiency": float(row["efficiency"]) if row["efficiency"] else 0,
                "isk_destroyed": float(row["isk_destroyed"] or 0),
                "activity_share": round((row["kills"] or 0) / total_alliance_kills * 100, 1)
            })

        # Top pilots — use DISTINCT to deduplicate (characters can appear multiple times per killmail)
        cur.execute("""
            WITH unique_pilot_kills AS (
                SELECT DISTINCT ka.character_id, ka.corporation_id, ka.killmail_id,
                       k.ship_value,
                       ka.is_final_blow,
                       ka.damage_done
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = %s
                  AND k.killmail_time > NOW() - INTERVAL '%s days'
                  AND ka.character_id IS NOT NULL
            ),
            attacker_stats AS (
                SELECT
                    character_id,
                    corporation_id,
                    COUNT(*) as kills,
                    SUM(CASE WHEN is_final_blow THEN 1 ELSE 0 END) as final_blows,
                    SUM(damage_done) as total_damage,
                    SUM(ship_value) as isk_destroyed
                FROM unique_pilot_kills
                GROUP BY character_id, corporation_id
            ),
            victim_stats AS (
                SELECT
                    victim_character_id as character_id,
                    COUNT(*) as deaths,
                    SUM(ship_value) as isk_lost
                FROM killmails
                WHERE victim_alliance_id = %s
                  AND killmail_time > NOW() - INTERVAL '%s days'
                  AND victim_character_id IS NOT NULL
                GROUP BY victim_character_id
            )
            SELECT
                a.character_id,
                COALESCE(cn.character_name, CONCAT('Pilot ', a.character_id)) as character_name,
                a.corporation_id as corp_id,
                c.corporation_name as corp_name,
                c.ticker,
                a.kills,
                a.final_blows,
                COALESCE(v.deaths, 0) as deaths,
                a.isk_destroyed,
                COALESCE(v.isk_lost, 0) as isk_lost,
                ROUND(a.isk_destroyed::numeric / NULLIF(a.isk_destroyed + COALESCE(v.isk_lost, 0), 0) * 100, 1) as efficiency,
                ROUND(a.total_damage::numeric / NULLIF(a.kills, 0), 0) as avg_damage
            FROM attacker_stats a
            LEFT JOIN victim_stats v ON a.character_id = v.character_id
            LEFT JOIN corporations c ON a.corporation_id = c.corporation_id
            LEFT JOIN character_name_cache cn ON a.character_id = cn.character_id
            ORDER BY a.kills DESC
            LIMIT 50
        """, (alliance_id, days, alliance_id, days))

        pilots_raw = cur.fetchall()

        top_pilots = []
        # Get skill estimates for pilots
        pilot_ids = [row["character_id"] for row in pilots_raw]
        skill_estimates = {}
        if pilot_ids:
            cur.execute("""
                SELECT character_id, min_sp, ships_analyzed, modules_analyzed
                FROM pilot_skill_estimates
                WHERE character_id = ANY(%s)
            """, (pilot_ids,))
            for r in cur.fetchall():
                skill_estimates[r["character_id"]] = {
                    "min_sp": r["min_sp"] or 0,
                    "ships_analyzed": r["ships_analyzed"] or 0,
                    "modules_analyzed": r["modules_analyzed"] or 0
                }

        for row in pilots_raw:
            char_id = row["character_id"]
            skill_data = skill_estimates.get(char_id, {"min_sp": 0, "ships_analyzed": 0, "modules_analyzed": 0})
            top_pilots.append({
                "character_id": char_id,
                "character_name": row["character_name"] or f"Pilot {char_id}",
                "corp_id": row["corp_id"],
                "corp_name": row["corp_name"] or f"Corp {row['corp_id']}",
                "ticker": row["ticker"] or "???",
                "kills": row["kills"] or 0,
                "final_blows": row["final_blows"] or 0,
                "deaths": row["deaths"] or 0,
                "efficiency": float(row["efficiency"]) if row["efficiency"] else 0,
                "isk_destroyed": float(row["isk_destroyed"] or 0),
                "avg_damage": int(row["avg_damage"]) if row["avg_damage"] else 0,
                "min_sp": skill_data["min_sp"],
                "ships_analyzed": skill_data["ships_analyzed"],
                "modules_analyzed": skill_data["modules_analyzed"]
            })

        return {
            "alliance_id": alliance_id,
            "period_days": days,
            "summary": summary,
            "corps": corps,
            "top_pilots": top_pilots
        }

@router.get("/fast/{alliance_id}/capsuleers/{character_id}")
@handle_endpoint_errors()
def get_capsuleer_detail(
    alliance_id: int,
    character_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """
    Get detailed statistics for a specific capsuleer.

    Returns:
    - Basic info: name, corp
    - Combat stats: kills, final blows, deaths, efficiency, ISK
    - Top ships flown
    - Activity pattern: peak hours, timezone
    - Top victim alliances
    """
    with db_cursor() as cur:
        # Basic info and attack stats
        cur.execute("""
            SELECT
                COALESCE(cn.character_name, CONCAT('Pilot ', ka.character_id)) as character_name,
                ka.corporation_id as corp_id,
                c.corporation_name as corp_name,
                c.ticker,
                COUNT(*) as kills,
                SUM(CASE WHEN ka.is_final_blow THEN 1 ELSE 0 END) as final_blows,
                SUM(ka.damage_done) as total_damage,
                SUM(k.ship_value) as isk_destroyed,
                COUNT(CASE WHEN NOT EXISTS (
                    SELECT 1 FROM killmail_attackers ka2
                    WHERE ka2.killmail_id = k.killmail_id
                      AND ka2.character_id != %s
                      AND ka2.character_id IS NOT NULL
                ) THEN 1 END) as solo_kills
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            LEFT JOIN corporations c ON ka.corporation_id = c.corporation_id
            LEFT JOIN character_name_cache cn ON ka.character_id = cn.character_id
            WHERE ka.character_id = %s
              AND ka.alliance_id = %s
              AND k.killmail_time > NOW() - INTERVAL '%s days'
            GROUP BY cn.character_name, ka.character_id, ka.corporation_id, c.corporation_name, c.ticker
        """, (character_id, character_id, alliance_id, days))
        attack_row = cur.fetchone()
        victim_info = None

        # If no attack data, resolve basic info from victim killmails
        if not attack_row:
            cur.execute("""
                SELECT
                    COALESCE(cn.character_name, CONCAT('Pilot ', %s)) as character_name,
                    k.victim_corporation_id as corp_id,
                    c.corporation_name as corp_name,
                    c.ticker
                FROM killmails k
                LEFT JOIN corporations c ON k.victim_corporation_id = c.corporation_id
                LEFT JOIN character_name_cache cn ON k.victim_character_id = cn.character_id
                WHERE k.victim_character_id = %s
                  AND k.victim_alliance_id = %s
                  AND k.killmail_time > NOW() - INTERVAL '%s days'
                ORDER BY k.killmail_time DESC
                LIMIT 1
            """, (character_id, character_id, alliance_id, days))
            victim_info = cur.fetchone()

            if not victim_info:
                return {
                    "character_id": character_id,
                    "character_name": "Unknown",
                    "corp_id": None,
                    "corp_name": "Unknown",
                    "ticker": "???",
                    "stats": {
                        "kills": 0, "final_blows": 0, "deaths": 0,
                        "efficiency": 0, "isk_destroyed": 0, "isk_lost": 0,
                        "avg_damage": 0, "solo_kills": 0
                    },
                    "top_ships": [],
                    "activity": None,
                    "top_victims": [],
                    "skill_estimate": None
                }

        # Death stats
        cur.execute("""
            SELECT
                COUNT(*) as deaths,
                SUM(ship_value) as isk_lost
            FROM killmails
            WHERE victim_character_id = %s
              AND victim_alliance_id = %s
              AND killmail_time > NOW() - INTERVAL '%s days'
        """, (character_id, alliance_id, days))
        death_row = cur.fetchone()

        kills = (attack_row['kills'] or 0) if attack_row else 0
        deaths = death_row['deaths'] or 0
        isk_destroyed = float(attack_row['isk_destroyed'] or 0) if attack_row else 0.0
        isk_lost = float(death_row['isk_lost'] or 0)

        efficiency = 0
        if isk_destroyed + isk_lost > 0:
            efficiency = round(isk_destroyed / (isk_destroyed + isk_lost) * 100, 1)

        avg_damage = 0
        if attack_row and kills > 0 and attack_row['total_damage']:
            avg_damage = int(attack_row['total_damage'] / kills)

        stats = {
            "kills": kills,
            "final_blows": (attack_row['final_blows'] or 0) if attack_row else 0,
            "deaths": deaths,
            "efficiency": efficiency,
            "isk_destroyed": isk_destroyed,
            "isk_lost": isk_lost,
            "avg_damage": avg_damage,
            "solo_kills": (attack_row['solo_kills'] or 0) if attack_row else 0
        }

        # Top ships flown (only if they have attack data)
        top_ships = []
        activity = None
        top_victims = []

        if attack_row:
            cur.execute("""
                SELECT
                    ka.ship_type_id,
                    t."typeName" as ship_name,
                    COUNT(*) as uses
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                LEFT JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
                WHERE ka.character_id = %s
                  AND ka.alliance_id = %s
                  AND k.killmail_time > NOW() - INTERVAL '%s days'
                  AND ka.ship_type_id IS NOT NULL
                  AND ka.ship_type_id > 0
                GROUP BY ka.ship_type_id, t."typeName"
                ORDER BY uses DESC
                LIMIT 5
            """, (character_id, alliance_id, days))
            ships_raw = cur.fetchall()

            total_uses = sum(r['uses'] for r in ships_raw) if ships_raw else 1
            top_ships = [
                {
                    "ship_type_id": row["ship_type_id"],
                    "ship_name": row["ship_name"] or "Unknown",
                    "uses": row["uses"],
                    "percentage": round(row["uses"] / total_uses * 100, 1)
                }
                for row in ships_raw
            ]

            # Activity pattern
            cur.execute("""
                SELECT
                    EXTRACT(HOUR FROM k.killmail_time) as hour,
                    COUNT(*) as kills
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.character_id = %s
                  AND ka.alliance_id = %s
                  AND k.killmail_time > NOW() - INTERVAL '%s days'
                GROUP BY EXTRACT(HOUR FROM k.killmail_time)
                ORDER BY kills DESC
            """, (character_id, alliance_id, days))
            hour_rows = cur.fetchall()

            peak_hour = int(hour_rows[0]['hour']) if hour_rows else 0

            # Determine timezone based on peak hour
            if 14 <= peak_hour <= 22:
                timezone = "US"
            elif 17 <= peak_hour <= 23 or 0 <= peak_hour <= 2:
                timezone = "EU"
            elif 6 <= peak_hour <= 14:
                timezone = "AU"
            else:
                timezone = "Mixed"

            # Peak day
            cur.execute("""
                SELECT
                    EXTRACT(DOW FROM k.killmail_time) as dow,
                    COUNT(*) as kills
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.character_id = %s
                  AND ka.alliance_id = %s
                  AND k.killmail_time > NOW() - INTERVAL '%s days'
                GROUP BY EXTRACT(DOW FROM k.killmail_time)
                ORDER BY kills DESC
            """, (character_id, alliance_id, days))
            dow_rows = cur.fetchall()

            days_of_week = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            peak_day = days_of_week[int(dow_rows[0]['dow'])] if dow_rows else "Unknown"

            # Active days
            cur.execute("""
                SELECT COUNT(DISTINCT DATE(k.killmail_time)) as active_days
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.character_id = %s
                  AND ka.alliance_id = %s
                  AND k.killmail_time > NOW() - INTERVAL '%s days'
            """, (character_id, alliance_id, days))
            active_days_row = cur.fetchone()

            activity = {
                "peak_hour": peak_hour,
                "peak_day": peak_day,
                "timezone": timezone,
                "active_days": active_days_row['active_days'] if active_days_row else 0
            }

            # Top victims (alliances)
            cur.execute("""
                SELECT
                    k.victim_alliance_id as alliance_id,
                    a.alliance_name,
                    COUNT(*) as kills
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                LEFT JOIN alliance_name_cache a ON k.victim_alliance_id = a.alliance_id
                WHERE ka.character_id = %s
                  AND ka.alliance_id = %s
                  AND k.killmail_time > NOW() - INTERVAL '%s days'
                  AND k.victim_alliance_id IS NOT NULL
                GROUP BY k.victim_alliance_id, a.alliance_name
                ORDER BY kills DESC
                LIMIT 5
            """, (character_id, alliance_id, days))
            victims_raw = cur.fetchall()

            top_victims = [
                {
                    "alliance_id": row["alliance_id"],
                    "alliance_name": row["alliance_name"] or f"Alliance {row['alliance_id']}",
                    "kills": row["kills"]
                }
                for row in victims_raw
            ]

        # Get skill estimates
        cur.execute("""
            SELECT min_sp, skill_breakdown, ships_analyzed, modules_analyzed
            FROM pilot_skill_estimates
            WHERE character_id = %s
        """, (character_id,))
        skill_row = cur.fetchone()

        skill_estimate = None
        if skill_row:
            skill_estimate = {
                "min_sp": skill_row["min_sp"] or 0,
                "skill_breakdown": skill_row["skill_breakdown"] or {},
                "ships_analyzed": skill_row["ships_analyzed"] or 0,
                "modules_analyzed": skill_row["modules_analyzed"] or 0
            }

        # Use attack_row for name/corp, fall back to victim_info
        info_row = attack_row or victim_info

        return {
            "character_id": character_id,
            "character_name": (info_row['character_name'] if info_row else None) or f"Pilot {character_id}",
            "corp_id": info_row['corp_id'] if info_row else None,
            "corp_name": (info_row['corp_name'] if info_row else None) or "Unknown",
            "ticker": (info_row['ticker'] if info_row else None) or "???",
            "stats": stats,
            "top_ships": top_ships,
            "activity": activity,
            "top_victims": top_victims,
            "skill_estimate": skill_estimate
        }

@router.get("/fast/{alliance_id}/pilot-intel")
@handle_endpoint_errors()
def get_alliance_pilot_intel(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Alliance-level pilot intelligence — same as corp pilot-intel but aggregated across all corps."""
    with db_cursor(cursor_factory=None) as cur:
        sql_base = """
            WITH pilot_base AS (
                SELECT
                    COALESCE(ka.character_id, km.victim_character_id) AS character_id,
                    cn.character_name,
                    COUNT(CASE WHEN ka.character_id IS NOT NULL THEN 1 END) AS kills,
                    COUNT(CASE WHEN km.victim_character_id = COALESCE(ka.character_id, km.victim_character_id)
                                AND km.victim_alliance_id = %(alliance_id)s THEN 1 END) AS deaths,
                    SUM(CASE WHEN ka.character_id IS NOT NULL THEN km.ship_value ELSE 0 END) AS isk_killed,
                    SUM(CASE WHEN km.victim_character_id = COALESCE(ka.character_id, km.victim_character_id)
                              AND km.victim_alliance_id = %(alliance_id)s THEN km.ship_value ELSE 0 END) AS isk_lost,
                    COUNT(DISTINCT DATE(km.killmail_time)) AS active_days,
                    MAX(km.killmail_time) AS last_active
                FROM killmails km
                LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                    AND ka.alliance_id = %(alliance_id)s
                LEFT JOIN character_name_cache cn ON COALESCE(ka.character_id, km.victim_character_id) = cn.character_id
                WHERE (ka.alliance_id = %(alliance_id)s OR km.victim_alliance_id = %(alliance_id)s)
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
                WHERE ka.alliance_id = %(alliance_id)s
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
                WHERE km.victim_alliance_id = %(alliance_id)s
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
                    WHERE ka.alliance_id = %(alliance_id)s
                        AND km.killmail_time >= NOW() - make_interval(days => 14)
                    UNION ALL
                    SELECT km.victim_character_id, km.killmail_time
                    FROM killmails km
                    WHERE km.victim_alliance_id = %(alliance_id)s
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
                COALESCE(pc.solo_kills, 0) AS solo_kills,
                COALESCE(pc.fleet_kills, 0) AS fleet_kills,
                ROUND(100.0 * COALESCE(pc.fleet_kills, 0) / NULLIF(pb.kills, 0), 1) AS fleet_participation_pct,
                ROUND(COALESCE(pc.avg_fleet_size, 0), 1) AS avg_fleet_size,
                COALESCE(pc.capital_usage, false) AS capital_usage,
                COALESCE(pl.solo_deaths, 0) AS solo_deaths,
                ROUND(COALESCE(pl.avg_loss_value, 0), 0) AS avg_loss_value,
                COALESCE(pl.expensive_losses, 0) AS expensive_losses,
                COALESCE(pt.activity_7d, 0) AS activity_7d,
                COALESCE(pt.activity_prev_7d, 0) AS activity_prev_7d
            FROM pilot_base pb
            LEFT JOIN pilot_combat pc ON pb.character_id = pc.character_id
            LEFT JOIN pilot_losses pl ON pb.character_id = pl.character_id
            LEFT JOIN pilot_trends pt ON pb.character_id = pt.character_id
            WHERE pb.kills > 0 OR pb.deaths > 0
            ORDER BY pb.kills DESC, pb.isk_killed DESC
        """
        cur.execute(sql_base, {"alliance_id": alliance_id, "days": days})

        pilots = _build_pilots_from_rows(cur.fetchall(), days)

        # Activity timeline
        cur.execute("""
            SELECT ka.character_id, DATE(km.killmail_time) AS day, COUNT(*) AS kills
            FROM killmail_attackers ka
            JOIN killmails km ON ka.killmail_id = km.killmail_id
            WHERE ka.alliance_id = %(alliance_id)s
                AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
            GROUP BY ka.character_id, DATE(km.killmail_time)
            ORDER BY ka.character_id, day
        """, {"alliance_id": alliance_id, "days": days})

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
                WHERE ka.alliance_id = %(alliance_id)s
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                    AND ka.character_id IS NOT NULL
                UNION ALL
                SELECT DATE(km.killmail_time), km.victim_character_id
                FROM killmails km
                WHERE km.victim_alliance_id = %(alliance_id)s
                    AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                    AND km.victim_character_id IS NOT NULL
            ) engagements
            GROUP BY day
            ORDER BY day
        """, {"alliance_id": alliance_id, "days": days})

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
                    WHERE ka.alliance_id = %(alliance_id)s
                        AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                        AND ka.character_id IS NOT NULL
                    UNION ALL
                    SELECT km.victim_character_id, DATE(km.killmail_time)
                    FROM killmails km
                    WHERE km.victim_alliance_id = %(alliance_id)s
                        AND km.killmail_time >= NOW() - make_interval(days => %(days)s)
                        AND km.victim_character_id IS NOT NULL
                ) engagements
                GROUP BY character_id
            ) first_seen
            GROUP BY first_day
            ORDER BY first_day
        """, {"alliance_id": alliance_id, "days": days})

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

def _build_pilots_from_rows(rows, days):
    """Convert raw SQL rows into pilot dicts with morale scores."""
    pilots = []
    for row in rows:
        activity_consistency = (float(row[6]) / days) * 100
        efficiency = float(row[8] or 0)
        activity_7d = int(row[18] if len(row) > 18 else 0)
        activity_prev_7d = int(row[19] if len(row) > 19 else 0)
        trend_factor = (activity_7d / max(activity_prev_7d, 1)) * 100 if activity_prev_7d > 0 else 100
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
            "efficiency": efficiency,
            "kd_ratio": float(row[9]) if row[9] else 0.0,
            "solo_kills": row[10],
            "fleet_kills": row[11],
            "fleet_participation_pct": float(row[12] or 0),
            "avg_fleet_size": float(row[13] or 0),
            "capital_usage": row[14],
            "solo_deaths": row[15],
            "avg_loss_value": float(row[16] or 0),
            "expensive_losses": row[17],
            "primary_ship_class": "Unknown",
            "ship_diversity": 0,
            "primary_region": "Unknown",
            "system_diversity": 0,
            "activity_7d": activity_7d,
            "activity_prev_7d": activity_prev_7d,
            "morale_score": round(morale_score, 1)
        })
    return pilots


def _build_fleet_overview(pilots, days, active_pilots_daily=None):
    """Build fleet overview summary from pilot list."""
    total_pilots = len(pilots)
    active_7d = sum(1 for p in pilots if p["activity_7d"] > 0)
    avg_activity = sum(p["kills"] + p["deaths"] for p in pilots) / total_pilots if total_pilots > 0 else 0
    avg_morale = sum(p["morale_score"] for p in pilots) / total_pilots if total_pilots > 0 else 0
    avg_participation = sum(p["fleet_participation_pct"] for p in pilots) / total_pilots if total_pilots > 0 else 0
    elite_count = sum(1 for p in pilots if p["morale_score"] >= 70 and p["efficiency"] >= 70)
    avg_daily_active = round(sum(d["active_pilots"] for d in active_pilots_daily) / len(active_pilots_daily), 1) if active_pilots_daily else 0
    return {
        "total_pilots": total_pilots,
        "active_7d": active_7d,
        "avg_activity": round(avg_activity, 1),
        "avg_daily_active": avg_daily_active,
        "avg_morale": round(avg_morale, 1),
        "avg_participation": round(avg_participation, 1),
        "elite_count": elite_count
    }
