"""Corporation Intelligence MCP Tools."""

from typing import Literal, Dict, Any, List
import logging

from fastapi import APIRouter, Query, HTTPException

from eve_shared.utils.error_handling import handle_endpoint_errors

from app.database import db_cursor
logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/search/corporation", operation_id="search_corporation")
@handle_endpoint_errors()
def mcp_search_corporation(
    name: str = Query(..., description="Corporation name to search for"),
    limit: int = Query(10, ge=1, le=50)
) -> Dict[str, Any]:
    """
    MCP Tool: Search for corporations by name.

    Returns matching corporations with IDs for use with mcp_analyze_corporation.

    Args:
        name: Corporation name (partial match supported)
        limit: Maximum results to return

    Returns:
        List of matching corporations with IDs and alliance info
    """
    with db_cursor() as cur:
        # Search in corp_name_cache and get alliance from latest killmail
        cur.execute("""
            WITH corp_alliances AS (
                SELECT DISTINCT ON (victim_corporation_id)
                    victim_corporation_id,
                    victim_alliance_id
                FROM killmails
                WHERE victim_alliance_id IS NOT NULL
                ORDER BY victim_corporation_id, killmail_time DESC
            )
            SELECT
                c.corporation_id,
                c.corporation_name,
                ca.victim_alliance_id as alliance_id,
                a.alliance_name
            FROM corp_name_cache c
            LEFT JOIN corp_alliances ca ON c.corporation_id = ca.victim_corporation_id
            LEFT JOIN alliance_name_cache a ON ca.victim_alliance_id = a.alliance_id
            WHERE LOWER(c.corporation_name) LIKE LOWER(%s)
            LIMIT %s
        """, (f'%{name}%', limit))

        results = []
        for row in cur.fetchall():
            results.append({
                "corporation_id": row['corporation_id'],
                "corporation_name": row['corporation_name'],
                "alliance_id": row['alliance_id'],
                "alliance_name": row['alliance_name']
            })

        return {
            "query": name,
            "results": results,
            "count": len(results)
        }


@router.get("/corporation/{corporation_id}", operation_id="analyze_corporation")
@handle_endpoint_errors()
async def mcp_analyze_corporation(
    corporation_id: int,
    scope: Literal["summary", "complete"] = "summary",
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """
    MCP Tool: Analyze corporation combat capabilities and activity.

    Provides intelligence on individual corporations:
    - Combat stats (kills, deaths, efficiency, ISK)
    - Ship class distribution
    - Geographic operations (top regions/systems)
    - Pilot statistics
    - Alliance membership

    Scopes:
    - summary: Basic stats (kills, deaths, efficiency, ISK)
    - complete: Full analysis with ships, regions, pilots

    Args:
        corporation_id: EVE corporation ID
        scope: Level of detail to return
        days: Historical data period (1-90 days)

    Returns:
        Corporation intelligence data based on scope parameter
    """
    if scope == "summary":
        return await _get_corporation_summary(corporation_id, days)
    else:  # complete
        return await _get_corporation_complete(corporation_id, days)


# ===== Helper Functions =====

async def _get_corporation_summary(corporation_id: int, days: int) -> Dict[str, Any]:
    """Get fast summary stats for corporation."""
    with db_cursor() as cur:
        # Get corporation name
        cur.execute("""
            SELECT corporation_name
            FROM corp_name_cache
            WHERE corporation_id = %s
        """, (corporation_id,))
        name_row = cur.fetchone()
        corporation_name = name_row['corporation_name'] if name_row else f"Corporation {corporation_id}"

        # Get alliance if any
        cur.execute("""
            SELECT DISTINCT victim_alliance_id
            FROM killmails
            WHERE victim_corporation_id = %s
            AND victim_alliance_id IS NOT NULL
            LIMIT 1
        """, (corporation_id,))
        alliance_row = cur.fetchone()
        alliance_id = alliance_row['victim_alliance_id'] if alliance_row else None

        # Get alliance name if exists
        alliance_name = None
        if alliance_id:
            cur.execute("""
                SELECT alliance_name
                FROM alliance_name_cache
                WHERE alliance_id = %s
            """, (alliance_id,))
            alliance_name_row = cur.fetchone()
            alliance_name = alliance_name_row['alliance_name'] if alliance_name_row else None

        # Get combat stats (kills where corporation was attacker)
        cur.execute("""
            SELECT
                COUNT(DISTINCT km.killmail_id) as kills,
                COALESCE(SUM(km.ship_value), 0) as isk_destroyed
            FROM killmails km
            INNER JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            WHERE km.killmail_time >= NOW() - make_interval(days => %s)
            AND ka.corporation_id = %s
        """, (days, corporation_id))
        kills_row = cur.fetchone()

        # Get deaths (kills where corporation was victim)
        cur.execute("""
            SELECT
                COUNT(DISTINCT killmail_id) as deaths,
                COALESCE(SUM(ship_value), 0) as isk_lost
            FROM killmails
            WHERE killmail_time >= NOW() - make_interval(days => %s)
            AND victim_corporation_id = %s
        """, (days, corporation_id))
        deaths_row = cur.fetchone()

        kills = kills_row['kills'] if kills_row else 0
        deaths = deaths_row['deaths'] if deaths_row else 0
        isk_destroyed = float(kills_row['isk_destroyed']) if kills_row else 0.0
        isk_lost = float(deaths_row['isk_lost']) if deaths_row else 0.0

        efficiency = isk_destroyed / (isk_destroyed + isk_lost) if (isk_destroyed + isk_lost) > 0 else 0

        return {
            "corporation_id": corporation_id,
            "corporation_name": corporation_name,
            "alliance_id": alliance_id,
            "alliance_name": alliance_name,
            "period_days": days,
            "kills": kills,
            "deaths": deaths,
            "isk_destroyed": isk_destroyed,
            "isk_lost": isk_lost,
            "efficiency": round(efficiency, 4)
        }


async def _get_corporation_complete(corporation_id: int, days: int) -> Dict[str, Any]:
    """Get complete corporation analysis."""
    # Get summary first
    summary = await _get_corporation_summary(corporation_id, days)

    with db_cursor() as cur:
        # Top ship classes used
        cur.execute("""
            SELECT
                km.ship_class,
                COUNT(DISTINCT km.killmail_id) as kills
            FROM killmails km
            INNER JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            WHERE km.killmail_time >= NOW() - make_interval(days => %s)
            AND ka.corporation_id = %s
            AND km.ship_class IS NOT NULL
            GROUP BY km.ship_class
            ORDER BY kills DESC
            LIMIT 10
        """, (days, corporation_id))
        ship_classes = [
            {"ship_class": row['ship_class'], "kills": row['kills']}
            for row in cur.fetchall()
        ]

        # Top regions
        cur.execute("""
            SELECT
                r."regionName" as region_name,
                COUNT(DISTINCT km.killmail_id) as kills
            FROM killmails km
            INNER JOIN killmail_attackers ka ON km.killmail_id = ka.killmail_id
            INNER JOIN "mapSolarSystems" s ON km.solar_system_id = s."solarSystemID"
            INNER JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE km.killmail_time >= NOW() - make_interval(days => %s)
            AND ka.corporation_id = %s
            GROUP BY r."regionName"
            ORDER BY kills DESC
            LIMIT 10
        """, (days, corporation_id))
        top_regions = [
            {"region_name": row['region_name'], "kills": row['kills']}
            for row in cur.fetchall()
        ]

        # Pilot count (unique characters)
        cur.execute("""
            SELECT COUNT(DISTINCT ka.character_id) as pilot_count
            FROM killmail_attackers ka
            INNER JOIN killmails km ON ka.killmail_id = km.killmail_id
            WHERE km.killmail_time >= NOW() - make_interval(days => %s)
            AND ka.corporation_id = %s
        """, (days, corporation_id))
        pilot_row = cur.fetchone()
        pilot_count = pilot_row['pilot_count'] if pilot_row else 0

    # Combine summary with detailed data
    return {
        **summary,
        "ship_classes": ship_classes,
        "top_regions": top_regions,
        "active_pilots": pilot_count
    }
