"""Strategic Intelligence MCP Tools."""

from typing import Optional, Literal, Dict, Any, List
import logging

from fastapi import APIRouter, Query, HTTPException

from ..reports import get_alliance_wars
from ..war.systems import get_system_danger
from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/threat")
@handle_endpoint_errors(default_status=500)
async def mcp_assess_threat(
    system_id: Optional[int] = None,
    constellation_id: Optional[int] = None,
    region_id: Optional[int] = None,
    hours: int = Query(24, ge=1, le=168),
    include_active_battles: bool = True
) -> Dict[str, Any]:
    """
    MCP Tool: Assess danger level of location.

    Evaluates threat level of system, constellation, or region based on
    recent combat activity.

    Args:
        system_id: System to analyze (mutually exclusive with constellation/region)
        constellation_id: Constellation to analyze
        region_id: Region to analyze
        hours: Historical data period (1-168 hours)
        include_active_battles: Include current battles in assessment

    Returns:
        Threat assessment with danger score, stats, and recommendations
    """
    if not any([system_id, constellation_id, region_id]):
        raise HTTPException(status_code=400, detail="Must provide system_id, constellation_id, or region_id")

    if system_id:
        # Reuse existing system danger endpoint
        danger = await get_system_danger(system_id, minutes=hours * 60)

        danger_dict = danger.model_dump() if hasattr(danger, 'model_dump') else danger.dict()

        result = {
            "location": danger_dict,
            "danger_score": danger_dict.get('danger_score', 0),
            "threat_level": _classify_threat(danger_dict.get('danger_score', 0)),
            f"stats_{hours}h": {
                "kills": danger_dict.get('kills_minutes', 0),
                "isk_destroyed": danger_dict.get('isk_destroyed', 0)
            },
            "recommendation": _generate_recommendation(danger_dict.get('danger_score', 0))
        }

        if include_active_battles:
            result['active_battles'] = danger_dict.get('active_battles', [])

        return result

    else:
        # Constellation or region danger analysis
        return await _get_area_danger(constellation_id, region_id, hours, include_active_battles)


@router.get("/conflicts")
@handle_endpoint_errors(default_status=500)
async def mcp_find_conflicts(
    status: Literal["active", "escalating", "all"] = "active",
    min_isk: Optional[int] = Query(1000000000, ge=0),
    min_battles: int = Query(1, ge=1),
    include_participants: bool = True
) -> Dict[str, Any]:
    """
    MCP Tool: Find ongoing wars/conflicts.

    Discovers conflicts between alliances/coalitions based on combat activity.

    Args:
        status: Conflict status filter
            - "active": Ongoing conflicts (recent activity)
            - "escalating": Conflicts with increasing ISK/day
            - "all": All conflicts in last 7 days
        min_isk: Minimum ISK destroyed (filters small conflicts)
        min_battles: Minimum number of battles
        include_participants: Include detailed participant info

    Returns:
        List of conflicts with statistics and trends
    """
    wars_data = await get_alliance_wars()
    conflicts = wars_data.get('conflicts', [])

    # Apply ISK and battle count filters
    if min_isk:
        conflicts = [c for c in conflicts if c.get('total_isk', 0) >= min_isk]

    if min_battles > 1:
        conflicts = [c for c in conflicts if len(c.get('battles', [])) >= min_battles]

    # Enrich with status and trend data
    if status != "all":
        conflicts = _filter_conflicts_by_status(conflicts, status)

    summary = {
        "total_conflicts": len(conflicts),
        "total_isk_destroyed": sum(c.get('total_isk', 0) for c in conflicts),
        "filter_applied": status
    }

    return {
        "conflicts": conflicts,
        "summary": summary
    }


@router.get("/sovereignty")
@handle_endpoint_errors(default_status=500)
def mcp_get_sovereignty_intel(
    region_id: Optional[int] = None,
    vulnerable_only: bool = False,
    include_cynojammers: bool = False,
    alliance_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    MCP Tool: Sovereignty intel.

    Provides sovereignty map, vulnerable systems, and ADM data.

    Args:
        region_id: Filter by region
        vulnerable_only: Only show vulnerable systems (ADM < 4.0)
        include_cynojammers: Include cynojammer status
        alliance_id: Filter by holding alliance

    Returns:
        Sovereignty data with system ownership and vulnerability
    """
    with db_cursor() as cur:
        # Build dynamic WHERE clauses
        conditions = []
        params = {}

        if alliance_id:
            conditions.append("ss.alliance_id = %(alliance_id)s")
            params["alliance_id"] = alliance_id

        if region_id:
            conditions.append("""ms."regionID" = %(region_id)s""")
            params["region_id"] = region_id

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        # Main sovereignty query with latest ADM
        cur.execute(f"""
            WITH latest_adm AS (
                SELECT DISTINCT ON (solar_system_id)
                    solar_system_id, adm_level
                FROM dotlan_adm_history
                ORDER BY solar_system_id, timestamp DESC
            )
            SELECT
                ss.solar_system_id as system_id,
                ms."solarSystemName" as system_name,
                ms."regionID" as region_id,
                mr."regionName" as region_name,
                ms."constellationID" as constellation_id,
                ss.alliance_id,
                anc.alliance_name,
                COALESCE(la.adm_level, 0) as adm,
                CASE WHEN COALESCE(la.adm_level, 0) < 4.0 THEN true ELSE false END as is_vulnerable,
                ss.vulnerability_occupancy_level
            FROM sovereignty_structures ss
            JOIN "mapSolarSystems" ms ON ss.solar_system_id = ms."solarSystemID"
            JOIN "mapRegions" mr ON ms."regionID" = mr."regionID"
            LEFT JOIN alliance_name_cache anc ON ss.alliance_id = anc.alliance_id
            LEFT JOIN latest_adm la ON ss.solar_system_id = la.solar_system_id
            WHERE ss.structure_type_id = 32458  -- IHUB only
              AND {where_clause}
            {"AND COALESCE(la.adm_level, 0) < 4.0" if vulnerable_only else ""}
            ORDER BY COALESCE(la.adm_level, 0) ASC, ms."solarSystemName"
        """, params)
        systems = [dict(r) for r in cur.fetchall()]

        # Cynojammer status
        cynojammer_count = 0
        if include_cynojammers:
            jammer_conditions = []
            jammer_params = {}
            if alliance_id:
                jammer_conditions.append("ss2.alliance_id = %(alliance_id)s")
                jammer_params["alliance_id"] = alliance_id
            if region_id:
                jammer_conditions.append("""ms2."regionID" = %(region_id)s""")
                jammer_params["region_id"] = region_id
            jammer_where = " AND ".join(jammer_conditions) if jammer_conditions else "1=1"

            cur.execute(f"""
                SELECT COUNT(*) as cnt
                FROM sovereignty_structures ss2
                JOIN "mapSolarSystems" ms2 ON ss2.solar_system_id = ms2."solarSystemID"
                WHERE ss2.structure_type_id = 37534  -- Cyno Jammer
                  AND {jammer_where}
            """, jammer_params)
            cynojammer_count = cur.fetchone()['cnt'] or 0

            # Add jammer flag to each system
            if systems:
                system_ids = [s['system_id'] for s in systems]
                cur.execute("""
                    SELECT solar_system_id
                    FROM sovereignty_structures
                    WHERE structure_type_id = 37534
                      AND solar_system_id = ANY(%s)
                """, (system_ids,))
                jammed_systems = {r['solar_system_id'] for r in cur.fetchall()}
                for s in systems:
                    s['has_cynojammer'] = s['system_id'] in jammed_systems

        # Active campaigns
        cur.execute("""
            SELECT COUNT(*) as active_campaigns
            FROM dotlan_sov_campaigns
            WHERE score IS NOT NULL
        """)
        active_campaigns = cur.fetchone()['active_campaigns'] or 0

    vulnerable_count = sum(1 for s in systems if s.get('is_vulnerable'))

    return {
        "systems": systems,
        "summary": {
            "total_systems": len(systems),
            "vulnerable_systems": vulnerable_count,
            "cynojammers_active": cynojammer_count,
            "active_campaigns": active_campaigns
        }
    }


# ===== Helper Functions =====

async def _get_area_danger(
    constellation_id: Optional[int],
    region_id: Optional[int],
    hours: int,
    include_active_battles: bool
) -> Dict[str, Any]:
    """Assess danger for a constellation or region."""
    with db_cursor() as cur:
        # Get system IDs in the area
        if constellation_id:
            cur.execute("""
                SELECT "solarSystemID" as system_id, "solarSystemName" as system_name
                FROM "mapSolarSystems"
                WHERE "constellationID" = %s
            """, (constellation_id,))
            location_type = "constellation"
            location_id = constellation_id
            # Get constellation name
            cur.execute("""
                SELECT "constellationName" FROM "mapConstellations" WHERE "constellationID" = %s
            """, (constellation_id,))
            name_row = cur.fetchone()
            location_name = name_row['constellationName'] if name_row else str(constellation_id)
            # Re-fetch systems (cursor was consumed)
            cur.execute("""
                SELECT "solarSystemID" as system_id FROM "mapSolarSystems" WHERE "constellationID" = %s
            """, (constellation_id,))
        else:
            cur.execute("""
                SELECT "solarSystemID" as system_id FROM "mapSolarSystems" WHERE "regionID" = %s
            """, (region_id,))
            location_type = "region"
            location_id = region_id
            cur.execute("""
                SELECT "regionName" FROM "mapRegions" WHERE "regionID" = %s
            """, (region_id,))
            name_row = cur.fetchone()
            location_name = name_row['regionName'] if name_row else str(region_id)
            cur.execute("""
                SELECT "solarSystemID" as system_id FROM "mapSolarSystems" WHERE "regionID" = %s
            """, (region_id,))

        system_ids = [r['system_id'] for r in cur.fetchall()]

        if not system_ids:
            raise HTTPException(status_code=404, detail=f"{location_type} not found or has no systems")

        # Kill stats in the area
        cur.execute("""
            SELECT
                COUNT(DISTINCT killmail_id) as kills,
                COALESCE(SUM(ship_value), 0) as isk_destroyed,
                COUNT(DISTINCT solar_system_id) as active_systems
            FROM killmails
            WHERE solar_system_id = ANY(%s)
              AND killmail_time >= NOW() - make_interval(hours => %s)
        """, (system_ids, hours))
        stats = cur.fetchone()
        kills = stats['kills'] or 0
        isk_destroyed = float(stats['isk_destroyed'] or 0)
        active_systems = stats['active_systems'] or 0

        # Active battles
        battles = []
        if include_active_battles:
            cur.execute("""
                SELECT battle_id, solar_system_id, status, started_at,
                       total_kills, total_isk_destroyed
                FROM battles
                WHERE solar_system_id = ANY(%s)
                  AND status = 'active'
                  AND last_kill_at > NOW() - INTERVAL '2 hours'
                ORDER BY total_isk_destroyed DESC
                LIMIT 10
            """, (system_ids,))
            battles = [dict(r) for r in cur.fetchall()]
            for b in battles:
                if b.get('total_isk_destroyed'):
                    b['total_isk_destroyed'] = float(b['total_isk_destroyed'])
                if b.get('started_at'):
                    b['started_at'] = b['started_at'].isoformat()

        # Top dangerous systems in the area
        cur.execute("""
            SELECT
                km.solar_system_id as system_id,
                ss."solarSystemName" as system_name,
                COUNT(DISTINCT km.killmail_id) as kills,
                COALESCE(SUM(km.ship_value), 0) as isk
            FROM killmails km
            JOIN "mapSolarSystems" ss ON km.solar_system_id = ss."solarSystemID"
            WHERE km.solar_system_id = ANY(%s)
              AND km.killmail_time >= NOW() - make_interval(hours => %s)
            GROUP BY km.solar_system_id, ss."solarSystemName"
            ORDER BY kills DESC
            LIMIT 5
        """, (system_ids, hours))
        hotspots = [{**dict(r), "isk": float(r['isk'])} for r in cur.fetchall()]

    # Calculate danger score for area
    kills_per_hour = kills / max(hours, 1)
    danger_score = min(kills_per_hour * 2 + len(battles) * 3, 10.0)

    return {
        "location_type": location_type,
        "location_id": location_id,
        "location_name": location_name,
        "danger_score": round(danger_score, 2),
        "threat_level": _classify_threat(danger_score),
        f"stats_{hours}h": {
            "kills": kills,
            "isk_destroyed": isk_destroyed,
            "active_systems": active_systems,
            "total_systems": len(system_ids)
        },
        "hotspots": hotspots,
        "active_battles": battles if include_active_battles else [],
        "recommendation": _generate_recommendation(danger_score)
    }


def _filter_conflicts_by_status(conflicts: list, status: str) -> list:
    """Filter conflicts by activity status."""
    filtered = []
    for c in conflicts:
        battles = c.get('battles', [])
        if not battles:
            if status == "active":
                continue
            c['status'] = 'inactive'
            c['trend'] = 'stable'
            filtered.append(c)
            continue

        # Check for recent activity (last 24h)
        has_recent = any(
            b.get('last_kill_at') or b.get('status') == 'active'
            for b in battles
        )

        # Estimate trend from ISK data
        total_isk = c.get('total_isk', 0)
        battle_count = len(battles)

        if status == "active" and has_recent:
            c['status'] = 'active'
            c['trend'] = 'stable'
            filtered.append(c)
        elif status == "escalating":
            # Escalating = high ISK + many battles (rough heuristic)
            if total_isk > 5_000_000_000 and battle_count >= 3:
                c['status'] = 'escalating'
                c['trend'] = 'increasing'
                filtered.append(c)

    return filtered


def _classify_threat(score: float) -> str:
    """Classify danger score into threat level."""
    if score >= 8.0:
        return "EXTREME"
    elif score >= 6.0:
        return "HIGH"
    elif score >= 4.0:
        return "MODERATE"
    elif score >= 2.0:
        return "LOW"
    else:
        return "MINIMAL"


def _generate_recommendation(score: float) -> str:
    """Generate travel recommendation based on danger score."""
    if score >= 8.0:
        return "Avoid - Extreme danger, multiple active battles or heavy gate camp activity"
    elif score >= 6.0:
        return "High risk - Scout ahead, use cloaky transport, avoid peak hours"
    elif score >= 4.0:
        return "Moderate risk - Exercise caution, have escape plan ready"
    elif score >= 2.0:
        return "Low risk - Generally safe, but stay alert"
    else:
        return "Safe passage - Minimal recent combat activity"
