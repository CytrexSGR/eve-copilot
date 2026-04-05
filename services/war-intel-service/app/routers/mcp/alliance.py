"""Alliance Intelligence MCP Tools."""

from typing import Optional, Literal, Dict, Any, List
import logging

from fastapi import APIRouter, Query, HTTPException

from eve_shared.utils.error_handling import handle_endpoint_errors

from ..intelligence.danger_activity import get_top_enemies
from ..intelligence.dashboard import get_dashboard
from app.database import db_cursor
logger = logging.getLogger(__name__)

router = APIRouter()

from eve_shared.constants import CAPITAL_GROUP_IDS as _CAPITAL_GROUP_IDS

# Tank type mapping for counter recommendations
_TANK_COUNTERS = {
    "shield": {"primary": "EM", "secondary": "Thermal", "advice": "Focus EM/Thermal damage — shield ships are weakest to EM"},
    "armor": {"primary": "Explosive", "secondary": "Kinetic", "advice": "Focus Explosive/Kinetic damage — armor ships are weakest to Explosive"},
    "hull": {"primary": "Explosive", "secondary": "Kinetic", "advice": "Focus Explosive damage — hull tanks have uniform low resists"},
}

# Ship class to likely tank type
_CLASS_TANK_MAP = {
    "Frigate": "shield", "Destroyer": "shield", "Cruiser": "armor",
    "Battlecruiser": "armor", "Battleship": "armor", "Carrier": "armor",
    "Dreadnought": "armor", "Force Auxiliary": "armor", "Supercarrier": "armor",
    "Titan": "armor", "Logistics": "armor", "HAC": "armor",
    "Assault Frigate": "armor", "Command Ship": "armor",
    "Strategic Cruiser": "armor", "Interdictor": "shield",
    "Heavy Interdictor": "shield", "Interceptor": "shield",
    "Electronic Attack Ship": "shield", "Stealth Bomber": "shield",
}


@router.get("/alliance/{alliance_id}")
@handle_endpoint_errors()
async def mcp_analyze_alliance(
    alliance_id: int,
    scope: Literal["summary", "detailed", "complete"] = "summary",
    days: int = Query(7, ge=1, le=90),
    include_threats: bool = False,
    include_doctrines: bool = False
) -> Dict[str, Any]:
    """
    MCP Tool: Analyze alliance combat capabilities and strategic position.

    Scopes:
    - summary: Basic stats (50ms) - K/D, ISK, efficiency, member count
    - detailed: Stats + ships + systems + activity (300ms)
    - complete: Full dashboard with recommendations (2-3s)

    Args:
        alliance_id: EVE alliance ID
        scope: Level of detail to return
        days: Historical data period (1-90 days)
        include_threats: Add threat analysis (only for complete scope)
        include_doctrines: Add doctrine analysis (only for complete scope)

    Returns:
        Alliance intelligence data based on scope parameter
    """
    if scope == "summary":
        return await _get_alliance_summary(alliance_id, days)

    elif scope == "detailed":
        return await _get_alliance_detailed(alliance_id, days)

    else:  # complete
        return await _get_alliance_complete(
            alliance_id, days, include_threats, include_doctrines
        )


@router.get("/alliance/{alliance_id}/threats")
@handle_endpoint_errors()
async def mcp_assess_threats(
    alliance_id: int,
    days: int = Query(7, ge=1, le=90),
    min_kills: int = Query(5, ge=1),
    include_doctrine_counters: bool = False
) -> Dict[str, Any]:
    """
    MCP Tool: Identify threats to an alliance.

    Analyzes who is attacking this alliance and how dangerous they are.

    Args:
        alliance_id: EVE alliance ID
        days: Historical data period (1-90 days)
        min_kills: Minimum kills to qualify as threat
        include_doctrine_counters: Add counter-doctrine suggestions

    Returns:
        Threat analysis with danger scores and recommendations
    """
    threats_data = await get_top_enemies(alliance_id, days, limit=20)

    threats = [t for t in threats_data if t.get('kills', 0) >= min_kills]

    for threat in threats:
        threat['danger_score'] = _calculate_danger_score(threat)

    threats.sort(key=lambda x: x['danger_score'], reverse=True)

    result = {
        "alliance_id": alliance_id,
        "threats": threats[:10],
        "summary": {
            "total_attackers": len(threats),
            "total_kills_taken": sum(t.get('kills', 0) for t in threats),
            "most_dangerous": threats[0]['alliance_name'] if threats else None
        }
    }

    if include_doctrine_counters and threats:
        result['counter_recommendations'] = _get_counter_recommendations(
            [t.get('alliance_id') for t in threats[:5]], days
        )

    return result


@router.get("/alliance/{alliance_id}/readiness")
@handle_endpoint_errors()
def mcp_get_fleet_readiness(
    alliance_id: int,
    doctrine_name: Optional[str] = None,
    include_pilots: bool = False
) -> Dict[str, Any]:
    """
    MCP Tool: Assess fleet combat readiness.

    Analyzes alliance's fleet composition, doctrines, and pilot availability.

    Args:
        alliance_id: EVE alliance ID
        doctrine_name: Filter for specific doctrine
        include_pilots: Include detailed pilot statistics

    Returns:
        Fleet readiness assessment with ships, doctrines, and pilot counts
    """
    with db_cursor() as cur:
        cur.execute("""
            SELECT alliance_name
            FROM alliance_name_cache
            WHERE alliance_id = %s
        """, (alliance_id,))
        row = cur.fetchone()
        alliance_name = row['alliance_name'] if row else f"Alliance {alliance_id}"

        # Observed doctrines from auto-detection
        doctrines = _get_alliance_doctrines(cur, alliance_id)
        if doctrine_name:
            doctrines = [d for d in doctrines if doctrine_name.lower() in d['name'].lower()]

        # Capital fleet composition (unique pilots per class in last 30d)
        cur.execute("""
            SELECT ig."groupName" as ship_class,
                   COUNT(DISTINCT ka.character_id) as unique_pilots,
                   COUNT(DISTINCT ka.killmail_id) as appearances
            FROM killmail_attackers ka
            JOIN killmails km ON ka.killmail_id = km.killmail_id
            JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE ka.alliance_id = %s
              AND km.killmail_time >= NOW() - INTERVAL '30 days'
              AND ig."groupName" IN ('Carrier', 'Dreadnought', 'Force Auxiliary',
                                     'Supercarrier', 'Titan')
            GROUP BY ig."groupName"
            ORDER BY unique_pilots DESC
        """, (alliance_id,))
        capital_rows = cur.fetchall()
        capital_fleet = {
            r['ship_class']: {"unique_pilots": r['unique_pilots'], "appearances": r['appearances']}
            for r in capital_rows
        }

        # Active pilots = attackers + victims (all PvP participants)
        cur.execute("""
            SELECT COUNT(DISTINCT character_id) as active_pilots
            FROM (
                SELECT ka.character_id
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = %(aid)s
                  AND k.killmail_time >= NOW() - INTERVAL '7 days'
                  AND ka.character_id IS NOT NULL
                UNION
                SELECT k.victim_character_id
                FROM killmails k
                WHERE k.victim_alliance_id = %(aid)s
                  AND k.killmail_time >= NOW() - INTERVAL '7 days'
                  AND k.victim_character_id IS NOT NULL
            ) all_pilots
        """, {"aid": alliance_id})
        active_pilots = cur.fetchone()['active_pilots'] or 0

        # Member count for readiness score
        cur.execute("""
            SELECT COALESCE(SUM(member_count), 0) as total_members
            FROM corporations WHERE alliance_id = %s
        """, (alliance_id,))
        member_row = cur.fetchone()
        total_members = member_row['total_members'] if member_row else 0

        # Efficiency (7d)
        cur.execute("""
            SELECT
                COALESCE(SUM(kills), 0) as kills,
                COALESCE(SUM(deaths), 0) as deaths,
                COALESCE(SUM(isk_destroyed), 0) as isk_d,
                COALESCE(SUM(isk_lost), 0) as isk_l
            FROM intelligence_hourly_stats
            WHERE alliance_id = %s
              AND hour_bucket >= NOW() - INTERVAL '7 days'
        """, (alliance_id,))
        eff_row = cur.fetchone()
        isk_d = float(eff_row['isk_d'] or 0)
        isk_l = float(eff_row['isk_l'] or 0)
        efficiency = isk_d / (isk_d + isk_l) if (isk_d + isk_l) > 0 else 0

    # Calculate readiness score (0-100)
    doctrine_score = min(len(doctrines) / 3, 1.0) * 25  # 25pts for 3+ doctrines
    capital_score = min(sum(v['unique_pilots'] for v in capital_fleet.values()) / 50, 1.0) * 25
    activity_score = min(active_pilots / max(total_members * 0.1, 1), 1.0) * 25  # 25pts for 10%+ active
    eff_score = efficiency * 25  # 25pts for 100% efficiency

    readiness_score = round(doctrine_score + capital_score + activity_score + eff_score, 1)

    result = {
        "alliance": {"id": alliance_id, "name": alliance_name},
        "doctrines": doctrines,
        "capital_fleet": capital_fleet,
        "active_pilots_7d": active_pilots,
        "total_members": total_members,
        "efficiency_7d": round(efficiency, 4),
        "readiness_score": readiness_score,
        "readiness_breakdown": {
            "doctrine_coverage": round(doctrine_score, 1),
            "capital_strength": round(capital_score, 1),
            "pilot_activity": round(activity_score, 1),
            "combat_efficiency": round(eff_score, 1)
        }
    }

    return result


# ===== Helper Functions =====

def _get_alliance_doctrines(cur, alliance_id: int) -> List[Dict[str, Any]]:
    """Get observed doctrines for an alliance from auto-detection."""
    cur.execute("""
        SELECT doctrine_name, primary_doctrine_type, composition,
               confidence_score, observation_count, last_seen,
               total_pilots_avg
        FROM doctrine_templates
        WHERE alliance_id = %s
        ORDER BY observation_count DESC
        LIMIT 20
    """, (alliance_id,))
    rows = cur.fetchall()
    return [
        {
            "name": r['doctrine_name'],
            "type": r['primary_doctrine_type'],
            "composition": r['composition'],
            "confidence": float(r['confidence_score']) if r['confidence_score'] else 0,
            "observations": r['observation_count'],
            "last_seen": r['last_seen'].isoformat() if r['last_seen'] else None,
            "avg_fleet_size": r['total_pilots_avg']
        }
        for r in rows
    ]


def _get_counter_recommendations(threat_alliance_ids: List[int], days: int) -> List[Dict[str, Any]]:
    """Generate counter-doctrine recommendations based on threat ship usage."""
    recommendations = []

    with db_cursor() as cur:
        for aid in threat_alliance_ids:
            if not aid:
                continue
            # Get top ship classes used by threat
            cur.execute("""
                SELECT ig."groupName" as ship_class,
                       COUNT(DISTINCT ka.killmail_id) as usage_count
                FROM killmail_attackers ka
                JOIN killmails km ON ka.killmail_id = km.killmail_id
                JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE ka.alliance_id = %s
                  AND km.killmail_time >= NOW() - make_interval(days => %s)
                  AND ig."categoryID" = 6
                GROUP BY ig."groupName"
                ORDER BY usage_count DESC
                LIMIT 5
            """, (aid, days))
            ship_rows = cur.fetchall()

            if not ship_rows:
                continue

            # Get alliance name
            cur.execute("SELECT alliance_name FROM alliance_name_cache WHERE alliance_id = %s", (aid,))
            name_row = cur.fetchone()
            ally_name = name_row['alliance_name'] if name_row else str(aid)

            # Determine dominant tank type
            tank_counts = {"shield": 0, "armor": 0, "hull": 0}
            for sr in ship_rows:
                tank = _CLASS_TANK_MAP.get(sr['ship_class'], "armor")
                tank_counts[tank] += sr['usage_count']

            dominant_tank = max(tank_counts, key=tank_counts.get)
            counter = _TANK_COUNTERS.get(dominant_tank, _TANK_COUNTERS["armor"])

            top_classes = [r['ship_class'] for r in ship_rows[:3]]
            recommendations.append({
                "threat_alliance": ally_name,
                "threat_alliance_id": aid,
                "dominant_ship_classes": top_classes,
                "dominant_tank_type": dominant_tank,
                "counter_damage_primary": counter["primary"],
                "counter_damage_secondary": counter["secondary"],
                "advice": counter["advice"]
            })

    return recommendations


async def _get_alliance_summary(alliance_id: int, days: int) -> Dict[str, Any]:
    """Get fast summary stats from pre-aggregated data."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT alliance_name
            FROM alliance_name_cache
            WHERE alliance_id = %s
        """, (alliance_id,))
        name_row = cur.fetchone()
        alliance_name = name_row['alliance_name'] if name_row else f"Alliance {alliance_id}"

        cur.execute("""
            SELECT
                COUNT(*) as kills,
                COALESCE(SUM(ship_value), 0) as isk_destroyed
            FROM (
                SELECT DISTINCT km.killmail_id, km.ship_value
                FROM killmails km
                INNER JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
                WHERE km.killmail_time >= NOW() - make_interval(days => %s)
                AND ka.alliance_id = %s
            ) distinct_kills
        """, (days, alliance_id))
        kills_row = cur.fetchone()

        cur.execute("""
            SELECT
                COUNT(DISTINCT killmail_id) as deaths,
                COALESCE(SUM(ship_value), 0) as isk_lost
            FROM killmails
            WHERE killmail_time >= NOW() - make_interval(days => %s)
            AND victim_alliance_id = %s
        """, (days, alliance_id))
        deaths_row = cur.fetchone()

        kills = kills_row['kills'] if kills_row else 0
        deaths = deaths_row['deaths'] if deaths_row else 0
        isk_destroyed = float(kills_row['isk_destroyed']) if kills_row else 0.0
        isk_lost = float(deaths_row['isk_lost']) if deaths_row else 0.0

        efficiency = isk_destroyed / (isk_destroyed + isk_lost) if (isk_destroyed + isk_lost) > 0 else 0

        return {
            "alliance_id": alliance_id,
            "alliance_name": alliance_name,
            "period_days": days,
            "kills": kills,
            "deaths": deaths,
            "isk_destroyed": isk_destroyed,
            "isk_lost": isk_lost,
            "efficiency": round(efficiency, 4)
        }


async def _get_alliance_detailed(alliance_id: int, days: int) -> Dict[str, Any]:
    """Get detailed stats with top ships, systems, and activity patterns."""
    summary = await _get_alliance_summary(alliance_id, days)

    with db_cursor() as cur:
        # Top ships used by this alliance
        cur.execute("""
            SELECT it."typeName" as ship_name, it."typeID" as ship_type_id,
                   ig."groupName" as ship_class,
                   COUNT(DISTINCT ka.killmail_id) as kill_count
            FROM killmail_attackers ka
            JOIN killmails km ON ka.killmail_id = km.killmail_id
            JOIN "invTypes" it ON ka.ship_type_id = it."typeID"
            JOIN "invGroups" ig ON it."groupID" = ig."groupID"
            WHERE ka.alliance_id = %s
              AND km.killmail_time >= NOW() - make_interval(days => %s)
              AND ig."categoryID" = 6
            GROUP BY it."typeID", it."typeName", ig."groupName"
            ORDER BY kill_count DESC
            LIMIT 10
        """, (alliance_id, days))
        top_ships = [dict(r) for r in cur.fetchall()]

        # Top systems
        cur.execute("""
            SELECT ss."solarSystemName" as system_name,
                   km.solar_system_id as system_id,
                   COUNT(DISTINCT km.killmail_id) as kill_count,
                   COALESCE(SUM(km.ship_value), 0) as total_isk
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            JOIN "mapSolarSystems" ss ON km.solar_system_id = ss."solarSystemID"
            WHERE ka.alliance_id = %s
              AND km.killmail_time >= NOW() - make_interval(days => %s)
            GROUP BY km.solar_system_id, ss."solarSystemName"
            ORDER BY kill_count DESC
            LIMIT 10
        """, (alliance_id, days))
        top_systems = [
            {**dict(r), "total_isk": float(r['total_isk'])}
            for r in cur.fetchall()
        ]

        # Activity by hour of day (UTC)
        cur.execute("""
            SELECT EXTRACT(hour FROM km.killmail_time)::int as hour,
                   COUNT(DISTINCT km.killmail_id) as kill_count
            FROM killmails km
            JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            WHERE ka.alliance_id = %s
              AND km.killmail_time >= NOW() - make_interval(days => %s)
            GROUP BY hour
            ORDER BY hour
        """, (alliance_id, days))
        activity_hours = {r['hour']: r['kill_count'] for r in cur.fetchall()}
        # Fill missing hours with 0
        activity_pattern = [{"hour": h, "kills": activity_hours.get(h, 0)} for h in range(24)]

        # Peak hour
        peak = max(activity_pattern, key=lambda x: x['kills']) if activity_pattern else {"hour": 0, "kills": 0}

    summary["top_ships"] = top_ships
    summary["top_systems"] = top_systems
    summary["activity_pattern"] = activity_pattern
    summary["peak_hour_utc"] = peak["hour"]

    return summary


async def _get_alliance_complete(
    alliance_id: int,
    days: int,
    include_threats: bool,
    include_doctrines: bool
) -> Dict[str, Any]:
    """Get complete dashboard data."""
    result = await get_dashboard(alliance_id, days)

    if include_threats:
        threats = await get_top_enemies(alliance_id, days, limit=5)
        result['threats'] = threats

    if include_doctrines:
        with db_cursor() as cur:
            result['doctrines'] = _get_alliance_doctrines(cur, alliance_id)

    return result


def _calculate_danger_score(threat: Dict[str, Any]) -> float:
    """Calculate threat danger score (0-10)."""
    kills = threat.get('kills', 0)
    isk = threat.get('isk_destroyed', 0)
    efficiency = threat.get('efficiency', 0)

    score = (
        min(kills / 50, 1.0) * 4.0 +
        min(isk / 10_000_000_000, 1.0) * 4.0 +
        efficiency * 2.0
    )

    return round(score, 2)
