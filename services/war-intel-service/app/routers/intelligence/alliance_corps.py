"""Alliance Corporations Intelligence Endpoints.

Provides actionable leadership intelligence for alliance commanders:
- Problem corps identification (red flags)
- Carry vs dead weight ranking
- Performance trends
- Ship specialization
- Geographic spread
- Pilot engagement
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/fast/{alliance_id}/corps-ranking")
@handle_endpoint_errors()
def get_corps_ranking(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90)
) -> List[Dict[str, Any]]:
    """Get corporation ranking with activity share and efficiency.

    Returns:
        - corp_id: Corporation ID
        - corporation_name: Corporation name
        - kills: Total kills
        - deaths: Total deaths
        - isk_killed: Total ISK destroyed
        - isk_lost: Total ISK lost
        - activity_share_pct: % of alliance total activity (kills + deaths)
        - efficiency: Kill efficiency % (kills / (kills + deaths) * 100)
        - active_pilots: Count of unique pilots who participated
        - deaths_per_pilot: Average deaths per pilot
    """
    with db_cursor() as cur:
        # Main corp stats with activity share (OPTIMIZED: uses hourly_stats)
        cur.execute("""
            WITH corp_stats AS (
                SELECT
                    chs.corporation_id AS corp_id,
                    cn.corporation_name,
                    SUM(chs.kills) AS kills,
                    SUM(chs.deaths) AS deaths,
                    SUM(chs.isk_destroyed) AS isk_killed,
                    SUM(chs.isk_lost) AS isk_lost,
                    MAX(chs.active_pilots) AS active_pilots
                FROM corporation_hourly_stats chs
                LEFT JOIN corp_name_cache cn ON chs.corporation_id = cn.corporation_id
                LEFT JOIN corporations c ON chs.corporation_id = c.corporation_id
                WHERE c.alliance_id = %(alliance_id)s
                    AND chs.hour_bucket >= NOW() - make_interval(days => %(days)s)
                GROUP BY chs.corporation_id, cn.corporation_name
            ),
            alliance_total AS (
                SELECT SUM(kills + deaths) AS total_activity FROM corp_stats
            )
            SELECT
                cs.corp_id,
                cs.corporation_name,
                cs.kills::INT,
                cs.deaths::INT,
                cs.isk_killed,
                cs.isk_lost,
                ROUND(100.0 * (cs.kills + cs.deaths) / NULLIF(at.total_activity, 0), 1) AS activity_share_pct,
                ROUND(100.0 * cs.kills / NULLIF(cs.kills + cs.deaths, 0), 1) AS efficiency,
                cs.active_pilots,
                ROUND(cs.deaths::numeric / NULLIF(cs.active_pilots, 0), 1) AS deaths_per_pilot
            FROM corp_stats cs
            CROSS JOIN alliance_total at
            WHERE cs.kills + cs.deaths > 0
            ORDER BY activity_share_pct DESC;
        """, {"alliance_id": alliance_id, "days": days})

        rows = cur.fetchall()

    return [
        {
            "corp_id": row["corp_id"],
            "corporation_name": row["corporation_name"] or f"Corporation {row['corp_id']}",
            "kills": row["kills"] or 0,
            "deaths": row["deaths"] or 0,
            "isk_killed": float(row["isk_killed"] or 0),
            "isk_lost": float(row["isk_lost"] or 0),
            "activity_share_pct": float(row["activity_share_pct"] or 0),
            "efficiency": float(row["efficiency"] or 0),
            "active_pilots": row["active_pilots"] or 0,
            "deaths_per_pilot": float(row["deaths_per_pilot"] or 0)
        }
        for row in rows
    ]

@router.get("/fast/{alliance_id}/corps-trends")
@handle_endpoint_errors()
def get_corps_trends(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90)
) -> List[Dict[str, Any]]:
    """Get 7-day performance trends for each corporation.

    Returns daily efficiency for the last 7 days to calculate sparklines and trend indicators.

    Returns:
        - corp_id: Corporation ID
        - corporation_name: Corporation name
        - day: Date
        - efficiency: Kill efficiency % for that day
        - activity: Total kills + deaths for that day
    """
    with db_cursor() as cur:
        # Get last 7 days of data per corp
        cur.execute("""
            WITH daily_corp_stats AS (
                SELECT
                    COALESCE(ka.corporation_id, km.victim_corporation_id) AS corp_id,
                    DATE(km.killmail_time) AS day,
                    COUNT(CASE WHEN ka.corporation_id IS NOT NULL THEN 1 END) AS kills,
                    COUNT(CASE WHEN km.victim_corporation_id = COALESCE(ka.corporation_id, km.victim_corporation_id)
                                AND km.victim_alliance_id = %(alliance_id)s THEN 1 END) AS deaths
                FROM killmails km
                LEFT JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                    AND ka.alliance_id = %(alliance_id)s
                WHERE (ka.alliance_id = %(alliance_id)s OR km.victim_alliance_id = %(alliance_id)s)
                    AND km.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                GROUP BY corp_id, day
            ),
            corp_trends AS (
                SELECT
                    corp_id,
                    day,
                    ROUND(100.0 * kills / NULLIF(kills + deaths, 0), 1) AS efficiency,
                    kills + deaths AS activity
                FROM daily_corp_stats
            )
            SELECT
                ct.corp_id,
                cn.corporation_name,
                ct.day,
                ct.efficiency,
                ct.activity
            FROM corp_trends ct
            LEFT JOIN corp_name_cache cn ON ct.corp_id = cn.corporation_id
            WHERE ct.activity > 0
            ORDER BY ct.corp_id, ct.day;
        """, {"alliance_id": alliance_id, "days": days})

        rows = cur.fetchall()

    return [
        {
            "corp_id": row["corp_id"],
            "corporation_name": row["corporation_name"] or f"Corporation {row['corp_id']}",
            "day": row["day"].isoformat() if row["day"] else None,
            "efficiency": float(row["efficiency"] or 0),
            "activity": row["activity"] or 0
        }
        for row in rows
    ]

@router.get("/fast/{alliance_id}/corps-ships")
@handle_endpoint_errors()
def get_corps_ships(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90)
) -> List[Dict[str, Any]]:
    """Get ship class specialization for each corporation.

    Shows which ship classes each corp prefers (Frigate, Cruiser, Capital, etc.)
    to help identify corp roles (tacklers, DPS, capital fleet).

    Returns:
        - corp_id: Corporation ID
        - corporation_name: Corporation name
        - ship_class: Ship class name (Frigate, Destroyer, Cruiser, Battlecruiser, Battleship, Capital, Other)
        - count: Number of kills with this ship class
        - percentage: % of corp's total kills with this class
    """
    with db_cursor() as cur:
        cur.execute("""
            WITH corp_ship_raw AS (
                SELECT
                    ka.corporation_id AS corp_id,
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
                WHERE ka.alliance_id = %(alliance_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '%(days)s days'
            ),
            corp_ships AS (
                SELECT
                    corp_id,
                    ship_class,
                    COUNT(*) AS count
                FROM corp_ship_raw
                GROUP BY corp_id, ship_class
            ),
            corp_totals AS (
                SELECT
                    corp_id,
                    SUM(count) AS total_count
                FROM corp_ships
                GROUP BY corp_id
            )
            SELECT
                cs.corp_id,
                cn.corporation_name,
                cs.ship_class,
                cs.count,
                ROUND(100.0 * cs.count / NULLIF(ct.total_count, 0), 1) AS percentage
            FROM corp_ships cs
            JOIN corp_totals ct ON cs.corp_id = ct.corp_id
            LEFT JOIN corp_name_cache cn ON cs.corp_id = cn.corporation_id
            ORDER BY cs.corp_id, cs.count DESC;
        """, {"alliance_id": alliance_id, "days": days})

        rows = cur.fetchall()

    return [
        {
            "corp_id": row["corp_id"],
            "corporation_name": row["corporation_name"] or f"Corporation {row['corp_id']}",
            "ship_class": row["ship_class"],
            "count": row["count"] or 0,
            "percentage": float(row["percentage"] or 0)
        }
        for row in rows
    ]

@router.get("/fast/{alliance_id}/corps-regions")
@handle_endpoint_errors()
def get_corps_regions(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90)
) -> List[Dict[str, Any]]:
    """Get geographic spread for each corporation.

    Shows how many regions each corp operates in and their top regions.
    Helps identify isolated corps (1-2 regions) vs wide-roaming corps (5+ regions).

    Returns:
        - corp_id: Corporation ID
        - corporation_name: Corporation name
        - region_count: Number of unique regions active in
        - top_regions: Array of top 3 region names by activity
    """
    with db_cursor() as cur:
        cur.execute("""
            WITH corp_regions AS (
                SELECT
                    ka.corporation_id AS corp_id,
                    ms."regionID" AS region_id,
                    mr."regionName" AS region_name,
                    COUNT(*) AS kills_in_region
                FROM killmails km
                JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                JOIN "mapSolarSystems" ms ON km.solar_system_id = ms."solarSystemID"
                JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
                WHERE ka.alliance_id = %(alliance_id)s
                    AND km.killmail_time >= NOW() - INTERVAL '%(days)s days'
                GROUP BY ka.corporation_id, ms."regionID", mr."regionName"
            ),
            ranked_regions AS (
                SELECT
                    corp_id,
                    region_name,
                    kills_in_region,
                    ROW_NUMBER() OVER (PARTITION BY corp_id ORDER BY kills_in_region DESC) AS rank
                FROM corp_regions
            ),
            corp_region_summary AS (
                SELECT
                    corp_id,
                    COUNT(DISTINCT region_name) AS region_count,
                    ARRAY_AGG(region_name ORDER BY kills_in_region DESC) FILTER (WHERE rank <= 3) AS top_regions
                FROM ranked_regions
                GROUP BY corp_id
            )
            SELECT
                crs.corp_id,
                cn.corporation_name,
                crs.region_count,
                crs.top_regions
            FROM corp_region_summary crs
            LEFT JOIN corp_name_cache cn ON crs.corp_id = cn.corporation_id
            ORDER BY crs.region_count DESC;
        """, {"alliance_id": alliance_id, "days": days})

        rows = cur.fetchall()

    return [
        {
            "corp_id": row["corp_id"],
            "corporation_name": row["corporation_name"] or f"Corporation {row['corp_id']}",
            "region_count": row["region_count"] or 0,
            "top_regions": row["top_regions"] or []
        }
        for row in rows
    ]
