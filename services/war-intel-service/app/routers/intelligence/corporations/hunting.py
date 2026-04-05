"""Corporation Hunting Intelligence - Strike Windows and Target Analysis."""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from ..corp_sql_helpers import classify_ship_group, solo_kills_detection_case, CAPITAL_GROUPS
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/corporation/{corp_id}/hunting-overview")
@handle_endpoint_errors()
def get_hunting_overview(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get hunting overview for intelligence command.

    Returns aggregated stats for strike windows, activity patterns, threat level.
    """
    with db_cursor(cursor_factory=None) as cur:
        # Basic activity stats
        sql = """
            SELECT
                COUNT(CASE WHEN ka.corporation_id = %(corp_id)s THEN 1 END) AS kills,
                COUNT(CASE WHEN km.victim_corporation_id = %(corp_id)s THEN 1 END) AS deaths,
                COUNT(DISTINCT DATE(km.killmail_time)) AS active_days,
                COUNT(DISTINCT CASE WHEN ka.corporation_id = %(corp_id)s THEN ka.character_id END) AS unique_pilots,
                COUNT(DISTINCT ms."solarSystemID") AS unique_systems,
                AVG(CASE WHEN ka.corporation_id = %(corp_id)s THEN km.ship_value ELSE NULL END) AS avg_kill_value
            FROM killmails km
            LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
            WHERE (ka.corporation_id = %(corp_id)s OR km.victim_corporation_id = %(corp_id)s)
                AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
        """

        cur.execute(sql, {"corp_id": corp_id, "days": days})

        stats_row = cur.fetchone()
        kills_val, deaths_val, active_days, unique_pilots, unique_systems, avg_kill_value = stats_row
        avg_kill_value = float(avg_kill_value) if avg_kill_value else 0.0

        overview = {
            "kills": kills_val or 0,
            "deaths": deaths_val or 0,
            "active_days": active_days or 0,
            "unique_pilots": unique_pilots or 0,
            "unique_systems": unique_systems or 0,
            "efficiency": round(100.0 * (kills_val or 0) / ((kills_val or 0) + (deaths_val or 1)), 1),
            "avg_kill_value": avg_kill_value,
        }

        # Peak activity hour
        sql = """
            SELECT
                EXTRACT(HOUR FROM km.killmail_time AT TIME ZONE 'UTC') AS hour,
                COUNT(*) AS activity
            FROM killmails km
            LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            WHERE (ka.corporation_id = %(corp_id)s OR km.victim_corporation_id = %(corp_id)s)
                AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            GROUP BY hour
            ORDER BY activity DESC
            LIMIT 1
        """

        cur.execute(sql, {"corp_id": corp_id, "days": days})

        peak_row = cur.fetchone()
        if peak_row:
            peak_hour, _ = peak_row
            overview["peak_activity_hour"] = int(peak_hour)
        else:
            overview["peak_activity_hour"] = None

        # Primary region
        sql = """
            SELECT mr."regionName", COUNT(*) AS activity
            FROM killmails km
            LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
            JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
            WHERE (ka.corporation_id = %(corp_id)s OR km.victim_corporation_id = %(corp_id)s)
                AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            GROUP BY mr."regionName"
            ORDER BY activity DESC
            LIMIT 1
        """

        cur.execute(sql, {"corp_id": corp_id, "days": days})

        region_row = cur.fetchone()
        overview["primary_region"] = region_row[0] if region_row else None

        # Primary system
        sql = """
            SELECT ms."solarSystemName", COUNT(*) AS activity
            FROM killmails km
            LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
            WHERE (ka.corporation_id = %(corp_id)s OR km.victim_corporation_id = %(corp_id)s)
                AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
            GROUP BY ms."solarSystemName"
            ORDER BY activity DESC
            LIMIT 1
        """

        cur.execute(sql, {"corp_id": corp_id, "days": days})

        system_row = cur.fetchone()
        overview["primary_system"] = system_row[0] if system_row else None

        # Threat level calculation
        threat_score = 0

        # Scoring based on kills (max 40 points)
        if kills_val > 100:
            threat_score += 40
        elif kills_val > 30:
            threat_score += 20
        elif kills_val > 10:
            threat_score += 10

        # Scoring based on avg kill value (max 30 points)
        if avg_kill_value > 1e9:  # >1B ISK
            threat_score += 30
        elif avg_kill_value > 500e6:  # >500M ISK
            threat_score += 15
        elif avg_kill_value > 100e6:  # >100M ISK
            threat_score += 5

        # Scoring based on activity frequency (max 30 points)
        activity_rate = (active_days or 0) / days
        if activity_rate > 0.8:  # Active >80% of days
            threat_score += 30
        elif activity_rate > 0.5:  # Active >50% of days
            threat_score += 15
        elif activity_rate > 0.2:  # Active >20% of days
            threat_score += 5

        # Determine threat level
        if threat_score >= 75:
            threat_level = "high"
        elif threat_score >= 40:
            threat_level = "medium"
        else:
            threat_level = "low"

        overview["threat_level"] = threat_level
        overview["threat_score"] = threat_score

        return overview

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
@handle_endpoint_errors()
def get_doctrines(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> List[Dict[str, Any]]:
    """Get ship doctrine analysis.

    Returns ship types used most often, indicates fleet composition.
    """
    with db_cursor(cursor_factory=None) as cur:
        sql = """
            SELECT
                it."typeName" AS ship_name,
                ig."groupName" AS ship_group,
                COUNT(DISTINCT km.killmail_id) AS count
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE ka.corporation_id = %(corp_id)s
                AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                AND ig."groupName" NOT IN ('Capsule', 'Rookie ship')
            GROUP BY it."typeName", ig."groupName"
            ORDER BY count DESC
            LIMIT 30
        """

        cur.execute(sql, {"corp_id": corp_id, "days": days})

        rows = cur.fetchall()
        total = sum(int(count) for _, _, count in rows) if rows else 0

        doctrines = []
        for ship_name, ship_group, count in rows:
            doctrines.append({
                "ship_name": ship_name,
                "ship_group": ship_group,
                "count": int(count),
                "percentage": round(100.0 * int(count) / total, 1) if total > 0 else 0.0,
            })

        return doctrines

@router.get("/corporation/{corp_id}/hot-zones")
@handle_endpoint_errors()
def get_hot_zones(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> List[Dict[str, Any]]:
    """Get top systems/regions where this corp operates.

    Returns list of systems with activity count, gatecamp detection, sorted by most active.
    """
    with db_cursor(cursor_factory=None) as cur:
        # Fixed: Separate CTEs to avoid LEFT JOIN cartesian product inflation
        sql = """
            WITH system_kills AS (
                SELECT
                    ms."solarSystemID" AS system_id,
                    ms."solarSystemName" AS system_name,
                    mr."regionID" AS region_id,
                    mr."regionName" AS region_name,
                    COUNT(DISTINCT km.killmail_id) AS kills,
                    SUM(CASE WHEN km.attacker_count <= 3 THEN 1 ELSE 0 END) AS solo_kills
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
                JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
                WHERE ka.corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                GROUP BY ms."solarSystemID", ms."solarSystemName", mr."regionID", mr."regionName"
            ),
            system_deaths AS (
                SELECT
                    ms."solarSystemID" AS system_id,
                    COUNT(*) AS deaths
                FROM killmails km
                JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
                WHERE km.victim_corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                GROUP BY ms."solarSystemID"
            )
            SELECT
                COALESCE(k.system_id, d.system_id) AS system_id,
                k.system_name,
                k.region_id,
                k.region_name,
                COALESCE(k.kills, 0) + COALESCE(d.deaths, 0) AS activity,
                COALESCE(k.kills, 0) AS kills,
                COALESCE(d.deaths, 0) AS deaths,
                ROUND(100.0 * COALESCE(k.kills, 0) / NULLIF(COALESCE(k.kills, 0) + COALESCE(d.deaths, 0), 0), 1) AS efficiency,
                -- Gatecamp detection: >60%% solo kills AND >10 total kills
                CASE
                    WHEN COALESCE(k.solo_kills, 0)::float / NULLIF(COALESCE(k.kills, 0), 0) > 0.6
                         AND COALESCE(k.kills, 0) > 10
                    THEN true
                    ELSE false
                END AS is_gatecamp
            FROM system_kills k
            FULL OUTER JOIN system_deaths d ON k.system_id = d.system_id
            ORDER BY activity DESC
            LIMIT 20
        """
        cur.execute(sql, {"corp_id": corp_id, "days": days})

        hot_zones = []
        for system_id, system_name, region_id, region_name, activity, kills, deaths, efficiency, is_gatecamp in cur.fetchall():
            hot_zones.append({
                "system_id": system_id,
                "system_name": system_name,
                "region_id": region_id,
                "region_name": region_name,
                "activity": activity,
                "kills": kills,
                "deaths": deaths,
                "efficiency": efficiency or 0.0,
                "is_gatecamp": is_gatecamp,
            })
        return hot_zones

        logger.error(f"Error fetching hot zones for {corp_id}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/corporation/{corp_id}/timezone-activity")
@handle_endpoint_errors()
def get_timezone_activity(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> List[Dict[str, Any]]:
    """Get 24-hour activity heatmap (EVE time).

    Returns activity count for each hour of the day (0-23).
    """
    with db_cursor(cursor_factory=None) as cur:
        # Fixed: Use separate CTEs to avoid COUNT(*) inflation from LEFT JOIN
        sql = """
            WITH hourly_kills AS (
                SELECT
                    EXTRACT(HOUR FROM km.killmail_time AT TIME ZONE 'UTC') AS hour,
                    COUNT(DISTINCT km.killmail_id) AS kills
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE ka.corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                GROUP BY hour
            ),
            hourly_deaths AS (
                SELECT
                    EXTRACT(HOUR FROM km.killmail_time AT TIME ZONE 'UTC') AS hour,
                    COUNT(*) AS deaths
                FROM killmails km
                WHERE km.victim_corporation_id = %(corp_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                GROUP BY hour
            )
            SELECT
                COALESCE(k.hour, d.hour) AS hour,
                COALESCE(k.kills, 0) + COALESCE(d.deaths, 0) AS activity,
                COALESCE(k.kills, 0) AS kills,
                COALESCE(d.deaths, 0) AS deaths
            FROM hourly_kills k
            FULL OUTER JOIN hourly_deaths d ON k.hour = d.hour
            ORDER BY COALESCE(k.hour, d.hour)
        """

        cur.execute(sql, {"corp_id": corp_id, "days": days})

        # Initialize all 24 hours with 0 activity
        hourly_data = {hour: {"hour": hour, "activity": 0, "kills": 0, "deaths": 0} for hour in range(24)}

        # Fill in actual data
        for hour_val, activity, kills, deaths in cur.fetchall():
            hour = int(hour_val)
            hourly_data[hour] = {
                "hour": hour,
                "activity": activity,
                "kills": kills,
                "deaths": deaths,
            }

        return [hourly_data[h] for h in range(24)]

@router.get("/corporation/{corp_id}/participation-trends")
@handle_endpoint_errors()
def get_participation_trends(
    corp_id: int,
    days: int = Query(14, ge=7, le=90)
) -> Dict[str, Any]:
    """Get daily participation trends showing if corporation activity is rising or falling.

    Includes active pilot count, kills, deaths per day and trend direction.
    """
    with db_cursor(cursor_factory=None) as cur:
        # Daily activity breakdown
        sql = """
            WITH daily_kills AS (
                SELECT
                    DATE(k.killmail_time) as day,
                    COUNT(DISTINCT k.killmail_id) as kills,
                    COUNT(DISTINCT ka.character_id) as active_attackers,
                    SUM(k.ship_value) as isk_destroyed
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.corporation_id = %(corp_id)s
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                GROUP BY DATE(k.killmail_time)
            ),
            daily_deaths AS (
                SELECT
                    DATE(killmail_time) as day,
                    COUNT(*) as deaths,
                    COUNT(DISTINCT victim_character_id) as pilots_lost,
                    SUM(ship_value) as isk_lost
                FROM killmails
                WHERE victim_corporation_id = %(corp_id)s
                  AND killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                GROUP BY DATE(killmail_time)
            )
            SELECT
                COALESCE(dk.day, dd.day) as day,
                COALESCE(dk.kills, 0) as kills,
                COALESCE(dd.deaths, 0) as deaths,
                COALESCE(dk.active_attackers, 0) as active_pilots,
                COALESCE(dk.isk_destroyed, 0) as isk_destroyed,
                COALESCE(dd.isk_lost, 0) as isk_lost
            FROM daily_kills dk
            FULL OUTER JOIN daily_deaths dd ON dk.day = dd.day
            ORDER BY COALESCE(dk.day, dd.day)
        """

        cur.execute(sql, {"corp_id": corp_id, "days": days})

        daily_data = []
        for row in cur.fetchall():
            daily_data.append({
                "day": row[0].isoformat() if row[0] else None,
                "kills": row[1],
                "deaths": row[2],
                "active_pilots": row[3],
                "isk_destroyed": float(row[4] or 0),
                "isk_lost": float(row[5] or 0)
            })

        # Calculate trend (compare last half vs first half)
        if len(daily_data) >= 4:
            mid = len(daily_data) // 2
            first_half = daily_data[:mid]
            second_half = daily_data[mid:]

            first_avg_kills = sum(d["kills"] for d in first_half) / len(first_half)
            second_avg_kills = sum(d["kills"] for d in second_half) / len(second_half)

            first_avg_pilots = sum(d["active_pilots"] for d in first_half) / len(first_half)
            second_avg_pilots = sum(d["active_pilots"] for d in second_half) / len(second_half)

            kills_trend_pct = 0.0
            if first_avg_kills > 0:
                kills_trend_pct = round((second_avg_kills - first_avg_kills) / first_avg_kills * 100, 1)

            pilots_trend_pct = 0.0
            if first_avg_pilots > 0:
                pilots_trend_pct = round((second_avg_pilots - first_avg_pilots) / first_avg_pilots * 100, 1)

            trend_direction = "rising" if kills_trend_pct > 5 else "falling" if kills_trend_pct < -5 else "stable"
        else:
            kills_trend_pct = 0.0
            pilots_trend_pct = 0.0
            trend_direction = "insufficient_data"

        return {
            "corporation_id": corp_id,
            "period_days": days,
            "daily": daily_data,
            "trend": {
                "direction": trend_direction,
                "kills_change_pct": kills_trend_pct,
                "pilots_change_pct": pilots_trend_pct
            }
        }

@router.get("/corporation/{corp_id}/burnout-index")
@handle_endpoint_errors()
def get_burnout_index(
    corp_id: int,
    days: int = Query(14, ge=7, le=90)
) -> Dict[str, Any]:
    """Burnout Index: kills per active pilot over time.

    If kills/pilot rises while pilot count drops, the remaining core is overworked.
    """
    with db_cursor(cursor_factory=None) as cur:
        sql = """
            WITH daily AS (
                SELECT
                    DATE(k.killmail_time) as day,
                    COUNT(DISTINCT k.killmail_id) as kills,
                    COUNT(DISTINCT ka.character_id) as active_pilots
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.corporation_id = %(corp_id)s
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                  AND ka.character_id IS NOT NULL
                GROUP BY DATE(k.killmail_time)
                ORDER BY day
            )
            SELECT
                day,
                kills,
                active_pilots,
                CASE WHEN active_pilots > 0
                     THEN ROUND(kills::numeric / active_pilots, 2)
                     ELSE 0 END as kills_per_pilot
            FROM daily
        """

        cur.execute(sql, {"corp_id": corp_id, "days": days})

        daily = []
        for row in cur.fetchall():
            daily.append({
                "day": row[0].isoformat() if row[0] else None,
                "kills": row[1],
                "active_pilots": row[2],
                "kills_per_pilot": float(row[3])
            })

        # Burnout detection: compare halves
        burnout_risk = "low"
        kpp_trend = 0.0
        pilot_trend = 0.0
        if len(daily) >= 4:
            mid = len(daily) // 2
            first = daily[:mid]
            second = daily[mid:]

            first_avg_kpp = sum(d["kills_per_pilot"] for d in first) / len(first)
            second_avg_kpp = sum(d["kills_per_pilot"] for d in second) / len(second)
            first_avg_pilots = sum(d["active_pilots"] for d in first) / len(first)
            second_avg_pilots = sum(d["active_pilots"] for d in second) / len(second)

            if first_avg_kpp > 0:
                kpp_trend = round((second_avg_kpp - first_avg_kpp) / first_avg_kpp * 100, 1)
            if first_avg_pilots > 0:
                pilot_trend = round((second_avg_pilots - first_avg_pilots) / first_avg_pilots * 100, 1)

            # Burnout = workload rising + pilots declining
            if kpp_trend > 15 and pilot_trend < -10:
                burnout_risk = "critical"
            elif kpp_trend > 10 and pilot_trend < -5:
                burnout_risk = "high"
            elif kpp_trend > 5 and pilot_trend < 0:
                burnout_risk = "moderate"

        # Current averages
        total_kills = sum(d["kills"] for d in daily)
        total_pilots = sum(d["active_pilots"] for d in daily)
        avg_kpp = round(total_kills / max(total_pilots, 1), 2)

        return {
            "corporation_id": corp_id,
            "period_days": days,
            "daily": daily,
            "summary": {
                "avg_kills_per_pilot": avg_kpp,
                "kpp_trend_pct": kpp_trend,
                "pilot_trend_pct": pilot_trend,
                "burnout_risk": burnout_risk
            }
        }

@router.get("/corporation/{corp_id}/attrition-tracker")
@handle_endpoint_errors()
def get_attrition_tracker(
    corp_id: int,
    days: int = Query(30, ge=14, le=90)
) -> Dict[str, Any]:
    """Attrition Tracker: find pilots who were active for this corporation in the past

    but now appear on killmails for other corporations. Shows where they went.
    """
    half_days = days // 2
    with db_cursor(cursor_factory=None) as cur:
        # Find pilots who were active for this corporation in the first half of the period
        # but are now appearing for different corporations in the recent half
        sql = """
            WITH old_pilots AS (
                -- Pilots active for this corporation in the older period
                SELECT DISTINCT ka.character_id
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.corporation_id = %(corp_id)s
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                  AND k.killmail_time < NOW() - INTERVAL '1 day' * %(half_days)s
                  AND ka.character_id IS NOT NULL
            ),
            current_pilots AS (
                -- Pilots still active for this corporation recently
                SELECT DISTINCT ka.character_id
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.corporation_id = %(corp_id)s
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %(half_days)s
                  AND ka.character_id IS NOT NULL
            ),
            departed AS (
                -- Pilots who left: were active before but NOT recently for this corporation
                SELECT character_id FROM old_pilots
                EXCEPT
                SELECT character_id FROM current_pilots
            ),
            new_homes AS (
                -- Where did they go? Check recent killmails for their new corporation
                SELECT
                    d.character_id,
                    ka.corporation_id as new_corp_id,
                    COUNT(*) as activity_count,
                    ROW_NUMBER() OVER (PARTITION BY d.character_id ORDER BY COUNT(*) DESC) as rn
                FROM departed d
                JOIN killmail_attackers ka ON d.character_id = ka.character_id
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE k.killmail_time >= NOW() - INTERVAL '1 day' * %(half_days)s
                  AND ka.corporation_id IS NOT NULL
                  AND ka.corporation_id != %(corp_id)s
                GROUP BY d.character_id, ka.corporation_id
            )
            SELECT
                nh.new_corp_id,
                cn.corporation_name,
                cn.ticker,
                COUNT(DISTINCT nh.character_id) as pilot_count,
                SUM(nh.activity_count) as total_activity
            FROM new_homes nh
            LEFT JOIN corp_name_cache cn ON nh.new_corp_id = cn.corporation_id
            WHERE nh.rn = 1
            GROUP BY nh.new_corp_id, cn.corporation_name, cn.ticker
            ORDER BY pilot_count DESC
            LIMIT 10
        """

        cur.execute(sql, {"corp_id": corp_id, "days": days, "half_days": half_days})
        destinations = []
        for row in cur.fetchall():
            destinations.append({
                "corporation_id": row[0],
                "corporation_name": row[1] or f"Corp {row[0]}",
                "ticker": row[2] or "???",
                "pilot_count": row[3],
                "total_activity": row[4]
            })

        # Also get total departed count
        summary_sql = """
            WITH old_pilots AS (
                SELECT DISTINCT ka.character_id
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.corporation_id = %(corp_id)s
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                  AND k.killmail_time < NOW() - INTERVAL '1 day' * %(half_days)s
                  AND ka.character_id IS NOT NULL
            ),
            current_pilots AS (
                SELECT DISTINCT ka.character_id
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.corporation_id = %(corp_id)s
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %(half_days)s
                  AND ka.character_id IS NOT NULL
            )
            SELECT
                (SELECT COUNT(*) FROM old_pilots) as old_count,
                (SELECT COUNT(*) FROM current_pilots) as current_count,
                (SELECT COUNT(*) FROM (SELECT character_id FROM old_pilots EXCEPT SELECT character_id FROM current_pilots) x) as departed_count
        """

        cur.execute(summary_sql, {"corp_id": corp_id, "days": days, "half_days": half_days})
        summary_row = cur.fetchone()

    old_count = summary_row[0] if summary_row else 0
    current_count = summary_row[1] if summary_row else 0
    departed_count = summary_row[2] if summary_row else 0
    retention_rate = round((1 - departed_count / max(old_count, 1)) * 100, 1) if old_count > 0 else 100.0

    return {
        "corporation_id": corp_id,
        "period_days": days,
        "summary": {
            "old_active_pilots": old_count,
            "current_active_pilots": current_count,
            "departed_pilots": departed_count,
            "retention_rate": retention_rate,
            "tracked_destinations": sum(d["pilot_count"] for d in destinations)
        },
        "destinations": destinations
    }

# ============================================================================
# OFFENSIVE TAB - Kill Intelligence
# ============================================================================

