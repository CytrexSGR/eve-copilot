"""
Capital Intelligence endpoints for war economy intelligence.

Includes capital alliance analysis, capital intel dashboard, and per-alliance capital intel.
"""

from datetime import datetime
from typing import Dict, List, Any
import logging

from fastapi import APIRouter, Query

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/economy", tags=["War Economy"])


# ============================================================
# CAPITAL ALLIANCES (Isotope-to-Alliance Correlation)
# ============================================================

# Isotope -> Capital Race mapping
ISOTOPE_RACE_MAP = {
    16274: "Minmatar",   # Helium Isotopes -> Naglfar, Hel, Ragnarok
    17887: "Gallente",   # Oxygen Isotopes -> Moros, Nyx, Erebus
    17888: "Caldari",    # Nitrogen Isotopes -> Phoenix, Wyvern, Leviathan
    17889: "Amarr",      # Hydrogen Isotopes -> Revelation, Aeon, Avatar
}

# Capital ship group IDs by race
CAPITAL_RACE_GROUPS = {
    "Minmatar": [
        ("Naglfar", 19722),      # Dreadnought
        ("Hel", 23913),          # Supercarrier
        ("Ragnarok", 3764),      # Titan
    ],
    "Gallente": [
        ("Moros", 19724),        # Dreadnought
        ("Nyx", 23917),          # Supercarrier
        ("Erebus", 671),         # Titan
    ],
    "Caldari": [
        ("Phoenix", 19726),      # Dreadnought
        ("Wyvern", 23919),       # Supercarrier
        ("Leviathan", 3764),     # Titan
    ],
    "Amarr": [
        ("Revelation", 19720),   # Dreadnought
        ("Aeon", 23911),         # Supercarrier
        ("Avatar", 11567),       # Titan
    ],
}


@router.get("/capital-alliances")
@handle_endpoint_errors()
def get_capital_alliances(
    days: int = Query(30, ge=7, le=90, description="Days of killmail history to analyze")
) -> Dict[str, Any]:
    """
    Get top alliances by capital race preference with corp-level breakdown.
    """
    with db_cursor() as cur:
        # Main alliance query (existing logic)
        cur.execute("""
            WITH capital_kills AS (
                SELECT
                    ka.alliance_id,
                    anc.alliance_name,
                    anc.ticker as alliance_ticker,
                    ka.corporation_id,
                    cnc.corporation_name,
                    ka.ship_type_id,
                    it."typeName" as ship_name,
                    ka.character_id,
                    k.killmail_time,
                    k.solar_system_id,
                    CASE
                        WHEN it."typeName" IN ('Naglfar', 'Hel', 'Ragnarok') THEN 'Minmatar'
                        WHEN it."typeName" IN ('Moros', 'Nyx', 'Erebus') THEN 'Gallente'
                        WHEN it."typeName" IN ('Phoenix', 'Wyvern', 'Leviathan') THEN 'Caldari'
                        WHEN it."typeName" IN ('Revelation', 'Aeon', 'Avatar') THEN 'Amarr'
                        ELSE NULL
                    END as capital_race
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                LEFT JOIN alliance_name_cache anc ON ka.alliance_id = anc.alliance_id
                LEFT JOIN corp_name_cache cnc ON ka.corporation_id = cnc.corporation_id
                WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND ka.alliance_id IS NOT NULL
                  AND ig."categoryID" = 6
                  AND it."typeName" IN (
                      'Naglfar', 'Hel', 'Ragnarok',
                      'Moros', 'Nyx', 'Erebus',
                      'Phoenix', 'Wyvern', 'Leviathan',
                      'Revelation', 'Aeon', 'Avatar'
                  )
            ),
            alliance_totals AS (
                SELECT
                    alliance_id,
                    alliance_name,
                    alliance_ticker,
                    capital_race,
                    COUNT(*) as race_total,
                    MAX(killmail_time) as last_activity
                FROM capital_kills
                WHERE capital_race IS NOT NULL
                GROUP BY alliance_id, alliance_name, alliance_ticker, capital_race
            ),
            alliance_race_rank AS (
                SELECT
                    alliance_id,
                    alliance_name,
                    alliance_ticker,
                    capital_race,
                    race_total,
                    last_activity,
                    SUM(race_total) OVER (PARTITION BY alliance_id) as alliance_total,
                    ROUND(100.0 * race_total / SUM(race_total) OVER (PARTITION BY alliance_id), 1) as race_pct,
                    ROW_NUMBER() OVER (PARTITION BY alliance_id ORDER BY race_total DESC) as rank
                FROM alliance_totals
            )
            SELECT
                capital_race,
                alliance_id,
                alliance_name,
                alliance_ticker,
                race_total as capital_count,
                alliance_total as total_capitals,
                race_pct,
                last_activity
            FROM alliance_race_rank
            WHERE rank = 1
              AND alliance_total >= 5
            ORDER BY capital_race, race_total DESC
        """, (days,))

        alliance_rows = cur.fetchall()

        # Get corp breakdown for top alliances
        alliance_ids = [r['alliance_id'] for r in alliance_rows]
        corp_data = {}
        regional_data = {}

        if alliance_ids:
            # Corp breakdown query
            cur.execute("""
                SELECT
                    ka.alliance_id,
                    ka.corporation_id,
                    cnc.corporation_name,
                    COUNT(*) as engagements,
                    COUNT(DISTINCT ka.character_id) as pilots,
                    array_agg(DISTINCT it."typeName") as ships
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
                LEFT JOIN corp_name_cache cnc ON ka.corporation_id = cnc.corporation_id
                WHERE it."typeName" IN (
                    'Naglfar', 'Hel', 'Ragnarok',
                    'Moros', 'Nyx', 'Erebus',
                    'Phoenix', 'Wyvern', 'Leviathan',
                    'Revelation', 'Aeon', 'Avatar'
                )
                AND k.killmail_time >= NOW() - INTERVAL '%s days'
                AND ka.alliance_id = ANY(%s)
                GROUP BY ka.alliance_id, ka.corporation_id, cnc.corporation_name
                ORDER BY ka.alliance_id, engagements DESC
            """, (days, alliance_ids))

            for row in cur.fetchall():
                aid = row['alliance_id']
                if aid not in corp_data:
                    corp_data[aid] = []
                if len(corp_data[aid]) < 3:  # Top 3 corps per alliance
                    corp_data[aid].append({
                        "corporation_id": row['corporation_id'],
                        "corporation_name": row['corporation_name'] or f"Corp {row['corporation_id']}",
                        "engagements": row['engagements'],
                        "pilots": row['pilots'],
                        "ships": row['ships'] or []
                    })

            # Regional activity query (last 7 days)
            cur.execute("""
                SELECT
                    ka.alliance_id,
                    r."regionName" as region,
                    COUNT(*) as ops,
                    MAX(k.killmail_time) as last_seen
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
                JOIN "mapRegions" r ON s."regionID" = r."regionID"
                JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
                WHERE it."typeName" IN (
                    'Naglfar', 'Hel', 'Ragnarok',
                    'Moros', 'Nyx', 'Erebus',
                    'Phoenix', 'Wyvern', 'Leviathan',
                    'Revelation', 'Aeon', 'Avatar'
                )
                AND k.killmail_time >= NOW() - INTERVAL '7 days'
                AND ka.alliance_id = ANY(%s)
                GROUP BY ka.alliance_id, r."regionName"
                ORDER BY ka.alliance_id, ops DESC
            """, (alliance_ids,))

            for row in cur.fetchall():
                aid = row['alliance_id']
                if aid not in regional_data:
                    regional_data[aid] = []
                if len(regional_data[aid]) < 2:  # Top 2 regions per alliance
                    hours_ago = int((datetime.utcnow() - row['last_seen']).total_seconds() / 3600) if row['last_seen'] else 999
                    regional_data[aid].append({
                        "region": row['region'],
                        "ops": row['ops'],
                        "hours_ago": hours_ago
                    })

    # Calculate confidence scores and build response
    def calculate_confidence(alliance_row, race_match_pct):
        hours_since = (datetime.utcnow() - alliance_row['last_activity']).total_seconds() / 3600 if alliance_row['last_activity'] else 999
        recency_score = max(0, 100 - (hours_since * 2))
        volume_score = min(100, (alliance_row['capital_count'] / 100) * 100)
        race_score = race_match_pct
        return int(recency_score * 0.4 + volume_score * 0.3 + race_score * 0.3)

    alliances_by_race: Dict[str, List[Dict]] = {
        "Minmatar": [], "Gallente": [], "Caldari": [], "Amarr": []
    }

    for row in alliance_rows:
        race = row['capital_race']
        if race in alliances_by_race and len(alliances_by_race[race]) < 5:
            aid = row['alliance_id']
            alliances_by_race[race].append({
                "alliance_id": aid,
                "alliance_name": row['alliance_name'] or f"Alliance {aid}",
                "ticker": row['alliance_ticker'] or "???",
                "capital_count": int(row['capital_count']),
                "total_capitals": int(row['total_capitals']),
                "race_preference_pct": float(row['race_pct']),
                "confidence_score": calculate_confidence(row, float(row['race_pct'])),
                "last_activity": row['last_activity'].isoformat() if row['last_activity'] else None,
                "top_corps": corp_data.get(aid, []),
                "active_regions": regional_data.get(aid, [])
            })

    isotope_alliances = {}
    for isotope_id, race in ISOTOPE_RACE_MAP.items():
        isotope_alliances[isotope_id] = {
            "race": race,
            "alliances": alliances_by_race.get(race, [])
        }

    return {
        "days_analyzed": days,
        "by_race": alliances_by_race,
        "by_isotope": isotope_alliances
    }


# ============================================================
# CAPITAL INTELLIGENCE DASHBOARD
# ============================================================

@router.get("/capital-intel")
@handle_endpoint_errors()
def get_capital_intel(
    days: int = Query(30, ge=1, le=90, description="Days of history")
) -> Dict[str, Any]:
    """
    Comprehensive capital intelligence dashboard.

    Returns top operators, regional deployments, and activity data.
    """
    with db_cursor() as cur:
        # Top Capital Alliances with breakdown
        cur.execute("""
            WITH capital_usage AS (
                SELECT
                    ka.alliance_id,
                    anc.alliance_name,
                    anc.ticker,
                    it."typeName" as ship_name,
                    CASE
                        WHEN it."typeName" IN ('Naglfar', 'Hel', 'Ragnarok') THEN 'Minmatar'
                        WHEN it."typeName" IN ('Moros', 'Nyx', 'Erebus') THEN 'Gallente'
                        WHEN it."typeName" IN ('Phoenix', 'Wyvern', 'Leviathan') THEN 'Caldari'
                        WHEN it."typeName" IN ('Revelation', 'Aeon', 'Avatar') THEN 'Amarr'
                    END as race,
                    CASE
                        WHEN it."typeName" IN ('Hel', 'Nyx', 'Wyvern', 'Aeon') THEN 'Supercarrier'
                        WHEN it."typeName" IN ('Ragnarok', 'Erebus', 'Leviathan', 'Avatar') THEN 'Titan'
                        ELSE 'Dreadnought'
                    END as ship_class,
                    COUNT(*) as count
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
                LEFT JOIN alliance_name_cache anc ON ka.alliance_id = anc.alliance_id
                WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
                  AND ka.alliance_id IS NOT NULL
                  AND it."typeName" IN (
                      'Naglfar', 'Hel', 'Ragnarok', 'Moros', 'Nyx', 'Erebus',
                      'Phoenix', 'Wyvern', 'Leviathan', 'Revelation', 'Aeon', 'Avatar'
                  )
                GROUP BY ka.alliance_id, anc.alliance_name, anc.ticker, it."typeName"
            )
            SELECT
                alliance_id, alliance_name, ticker,
                SUM(count) as total_caps,
                SUM(CASE WHEN ship_class = 'Titan' THEN count ELSE 0 END) as titans,
                SUM(CASE WHEN ship_class = 'Supercarrier' THEN count ELSE 0 END) as supers,
                SUM(CASE WHEN ship_class = 'Dreadnought' THEN count ELSE 0 END) as dreads,
                json_agg(json_build_object('race', race, 'count', count)) as race_breakdown
            FROM capital_usage
            GROUP BY alliance_id, alliance_name, ticker
            ORDER BY total_caps DESC
            LIMIT 20
        """, (days,))
        top_alliances = cur.fetchall()

        # Regional Capital Activity
        cur.execute("""
            SELECT
                r."regionName" as region,
                r."regionID" as region_id,
                COUNT(*) as capital_ops,
                COUNT(DISTINCT ka.alliance_id) as alliances_active,
                MAX(k.killmail_time) as last_activity
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            JOIN "mapSolarSystems" ss ON k.solar_system_id = ss."solarSystemID"
            JOIN "mapRegions" r ON ss."regionID" = r."regionID"
            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
              AND it."typeName" IN (
                  'Naglfar', 'Hel', 'Ragnarok', 'Moros', 'Nyx', 'Erebus',
                  'Phoenix', 'Wyvern', 'Leviathan', 'Revelation', 'Aeon', 'Avatar'
              )
            GROUP BY r."regionID", r."regionName"
            HAVING COUNT(*) >= 10
            ORDER BY capital_ops DESC
            LIMIT 15
        """, (days,))
        regional_activity = cur.fetchall()

        # Recent Deployments (last 48h with location)
        cur.execute("""
            SELECT
                anc.alliance_name,
                anc.ticker,
                ka.alliance_id,
                r."regionName" as region,
                COUNT(*) as ops,
                MAX(k.killmail_time) as last_seen
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            JOIN "mapSolarSystems" ss ON k.solar_system_id = ss."solarSystemID"
            JOIN "mapRegions" r ON ss."regionID" = r."regionID"
            LEFT JOIN alliance_name_cache anc ON ka.alliance_id = anc.alliance_id
            WHERE k.killmail_time >= NOW() - INTERVAL '48 hours'
              AND ka.alliance_id IS NOT NULL
              AND it."typeName" IN (
                  'Naglfar', 'Hel', 'Ragnarok', 'Moros', 'Nyx', 'Erebus',
                  'Phoenix', 'Wyvern', 'Leviathan', 'Revelation', 'Aeon', 'Avatar'
              )
            GROUP BY ka.alliance_id, anc.alliance_name, anc.ticker, r."regionName"
            HAVING COUNT(*) >= 3
            ORDER BY ops DESC
            LIMIT 20
        """)
        recent_deployments = cur.fetchall()

        # Summary stats
        cur.execute("""
            SELECT
                COUNT(*) as total_engagements,
                COUNT(DISTINCT ka.alliance_id) as unique_alliances,
                COUNT(DISTINCT k.solar_system_id) as systems_active
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
              AND it."typeName" IN (
                  'Naglfar', 'Hel', 'Ragnarok', 'Moros', 'Nyx', 'Erebus',
                  'Phoenix', 'Wyvern', 'Leviathan', 'Revelation', 'Aeon', 'Avatar'
              )
        """, (days,))
        summary = cur.fetchone()

    return {
        "days": days,
        "summary": {
            "total_engagements": summary['total_engagements'],
            "unique_alliances": summary['unique_alliances'],
            "systems_active": summary['systems_active']
        },
        "top_alliances": [{
            "alliance_id": r['alliance_id'],
            "alliance_name": r['alliance_name'] or f"Alliance {r['alliance_id']}",
            "ticker": r['ticker'] or "???",
            "total_caps": int(r['total_caps']),
            "titans": int(r['titans']),
            "supers": int(r['supers']),
            "dreads": int(r['dreads']),
            "race_breakdown": r['race_breakdown']
        } for r in top_alliances],
        "regional_activity": [{
            "region": r['region'],
            "region_id": r['region_id'],
            "capital_ops": r['capital_ops'],
            "alliances_active": r['alliances_active'],
            "last_activity": r['last_activity'].isoformat() if r['last_activity'] else None
        } for r in regional_activity],
        "recent_deployments": [{
            "alliance_id": r['alliance_id'],
            "alliance_name": r['alliance_name'] or f"Alliance {r['alliance_id']}",
            "ticker": r['ticker'] or "???",
            "region": r['region'],
            "ops": r['ops'],
            "last_seen": r['last_seen'].isoformat() if r['last_seen'] else None
        } for r in recent_deployments]
    }


@router.get("/capital-intel/alliance/{alliance_id}")
@handle_endpoint_errors()
def get_alliance_capital_intel(
    alliance_id: int,
    days: int = Query(30, ge=7, le=90, description="Days of history")
) -> Dict[str, Any]:
    """
    Capital intelligence for a specific alliance.

    Shows fleet composition, top corps, regional activity.
    """
    with db_cursor() as cur:
        # Fleet composition by ship
        cur.execute("""
            SELECT
                it."typeName" as ship_name,
                CASE
                    WHEN it."typeName" IN ('Naglfar', 'Hel', 'Ragnarok') THEN 'Minmatar'
                    WHEN it."typeName" IN ('Moros', 'Nyx', 'Erebus') THEN 'Gallente'
                    WHEN it."typeName" IN ('Phoenix', 'Wyvern', 'Leviathan') THEN 'Caldari'
                    WHEN it."typeName" IN ('Revelation', 'Aeon', 'Avatar') THEN 'Amarr'
                END as race,
                CASE
                    WHEN it."typeName" IN ('Hel', 'Nyx', 'Wyvern', 'Aeon') THEN 'Supercarrier'
                    WHEN it."typeName" IN ('Ragnarok', 'Erebus', 'Leviathan', 'Avatar') THEN 'Titan'
                    ELSE 'Dreadnought'
                END as ship_class,
                COUNT(*) as engagements,
                COUNT(DISTINCT ka.corporation_id) as corps_using
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
              AND ka.alliance_id = %s
              AND it."typeName" IN (
                  'Naglfar', 'Hel', 'Ragnarok', 'Moros', 'Nyx', 'Erebus',
                  'Phoenix', 'Wyvern', 'Leviathan', 'Revelation', 'Aeon', 'Avatar'
              )
            GROUP BY it."typeName"
            ORDER BY engagements DESC
        """, (days, alliance_id))
        ships = cur.fetchall()

        # Top corps with capitals
        cur.execute("""
            SELECT
                ka.corporation_id,
                cnc.corporation_name,
                COUNT(*) as engagements,
                COUNT(DISTINCT it."typeName") as ship_types,
                array_agg(DISTINCT it."typeName") as ships_used
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            LEFT JOIN corp_name_cache cnc ON ka.corporation_id = cnc.corporation_id
            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
              AND ka.alliance_id = %s
              AND it."typeName" IN (
                  'Naglfar', 'Hel', 'Ragnarok', 'Moros', 'Nyx', 'Erebus',
                  'Phoenix', 'Wyvern', 'Leviathan', 'Revelation', 'Aeon', 'Avatar'
              )
            GROUP BY ka.corporation_id, cnc.corporation_name
            ORDER BY engagements DESC
            LIMIT 10
        """, (days, alliance_id))
        corps = cur.fetchall()

        # Regional activity
        cur.execute("""
            SELECT
                r."regionName" as region,
                COUNT(*) as ops,
                MAX(k.killmail_time) as last_seen
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            JOIN "mapSolarSystems" ss ON k.solar_system_id = ss."solarSystemID"
            JOIN "mapRegions" r ON ss."regionID" = r."regionID"
            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
              AND ka.alliance_id = %s
              AND it."typeName" IN (
                  'Naglfar', 'Hel', 'Ragnarok', 'Moros', 'Nyx', 'Erebus',
                  'Phoenix', 'Wyvern', 'Leviathan', 'Revelation', 'Aeon', 'Avatar'
              )
            GROUP BY r."regionName"
            HAVING COUNT(*) >= 3
            ORDER BY ops DESC
            LIMIT 10
        """, (days, alliance_id))
        regions = cur.fetchall()

        # Daily activity trend
        cur.execute("""
            SELECT
                DATE(k.killmail_time) as day,
                COUNT(*) as engagements
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
              AND ka.alliance_id = %s
              AND it."typeName" IN (
                  'Naglfar', 'Hel', 'Ragnarok', 'Moros', 'Nyx', 'Erebus',
                  'Phoenix', 'Wyvern', 'Leviathan', 'Revelation', 'Aeon', 'Avatar'
              )
            GROUP BY DATE(k.killmail_time)
            ORDER BY day
        """, (days, alliance_id))
        daily = cur.fetchall()

        # Hourly activity pattern (for timezone chart)
        cur.execute("""
            SELECT EXTRACT(HOUR FROM k.killmail_time)::int as hour,
                   COUNT(*) as engagements
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            WHERE ka.alliance_id = %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
              AND it."typeName" IN (
                  'Naglfar', 'Hel', 'Ragnarok', 'Moros', 'Nyx', 'Erebus',
                  'Phoenix', 'Wyvern', 'Leviathan', 'Revelation', 'Aeon', 'Avatar'
              )
            GROUP BY hour
            ORDER BY hour
        """, (alliance_id, days))
        hourly = cur.fetchall()

        # Recent capital kills (for activity feed)
        cur.execute("""
            SELECT DISTINCT ON (k.killmail_id)
                k.killmail_id,
                k.killmail_time as timestamp,
                it."typeName" as attacker_ship,
                vit."typeName" as victim_ship,
                COUNT(*) OVER (PARTITION BY k.killmail_id) as pilots_involved,
                ss."solarSystemName" as solar_system,
                r."regionName" as region,
                vanc.alliance_name as victim_alliance
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            JOIN "invTypes" vit ON k.ship_type_id = vit."typeID"
            JOIN "mapSolarSystems" ss ON k.solar_system_id = ss."solarSystemID"
            JOIN "mapRegions" r ON ss."regionID" = r."regionID"
            LEFT JOIN alliance_name_cache vanc ON k.victim_alliance_id = vanc.alliance_id
            WHERE ka.alliance_id = %s
              AND it."typeName" IN (
                  'Naglfar', 'Hel', 'Ragnarok', 'Moros', 'Nyx', 'Erebus',
                  'Phoenix', 'Wyvern', 'Leviathan', 'Revelation', 'Aeon', 'Avatar'
              )
              AND k.killmail_time >= NOW() - INTERVAL '7 days'
            ORDER BY k.killmail_id, k.killmail_time DESC
            LIMIT 10
        """, (alliance_id,))
        recent_kills = cur.fetchall()

        # Race totals for pie chart
        race_totals = {"Minmatar": 0, "Gallente": 0, "Caldari": 0, "Amarr": 0}
        for s in ships:
            if s['race'] in race_totals:
                race_totals[s['race']] += s['engagements']

    total_engagements = sum(s['engagements'] for s in ships)

    return {
        "alliance_id": alliance_id,
        "days": days,
        "summary": {
            "total_engagements": total_engagements,
            "unique_corps": len(corps),
            "regions_active": len(regions),
            "ship_types": len(ships)
        },
        "race_distribution": race_totals,
        "ships": [{
            "ship_name": s['ship_name'],
            "race": s['race'],
            "ship_class": s['ship_class'],
            "engagements": s['engagements'],
            "corps_using": s['corps_using']
        } for s in ships],
        "top_corps": [{
            "corporation_id": c['corporation_id'],
            "corporation_name": c['corporation_name'] or f"Corp {c['corporation_id']}",
            "engagements": c['engagements'],
            "ship_types": c['ship_types'],
            "ships_used": c['ships_used'][:5] if c['ships_used'] else []
        } for c in corps],
        "regions": [{
            "region": r['region'],
            "ops": r['ops'],
            "last_seen": r['last_seen'].isoformat() if r['last_seen'] else None
        } for r in regions],
        "daily_activity": [{
            "day": d['day'].isoformat(),
            "engagements": d['engagements']
        } for d in daily],
        "hourly_activity": [{
            "hour": h['hour'],
            "engagements": h['engagements']
        } for h in hourly],
        "recent_kills": [{
            "killmail_id": rk['killmail_id'],
            "timestamp": rk['timestamp'].isoformat() if rk['timestamp'] else None,
            "attacker_ship": rk['attacker_ship'],
            "victim_ship": rk['victim_ship'],
            "pilots_involved": rk['pilots_involved'],
            "solar_system": rk['solar_system'],
            "region": rk['region'],
            "victim_alliance": rk['victim_alliance']
        } for rk in recent_kills]
    }
