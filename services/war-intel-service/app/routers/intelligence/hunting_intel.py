"""Hunting Intelligence — multi-source fusion for hunting opportunities."""

import logging
import os
import httpx
from fastapi import APIRouter, Query
from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.utils.cache import get_cached, set_cached
from app.services.hunting.score_calculator import calculate_hunting_score

logger = logging.getLogger(__name__)
router = APIRouter()

DOTLAN_SERVICE_URL = os.getenv("DOTLAN_SERVICE_URL", "http://eve-dotlan-service:8000")
CACHE_TTL = 600  # 10 minutes


def _fetch_dotlan_adm() -> dict:
    """Fetch ADM data from DOTLAN service."""
    try:
        resp = httpx.get(f"{DOTLAN_SERVICE_URL}/api/dotlan/sovereignty/adm", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {item["solar_system_id"]: item for item in data}
    except Exception as e:
        logger.warning(f"Failed to fetch DOTLAN ADM: {e}")
    return {}


def _fetch_dotlan_activity(region_id: int) -> dict:
    """Fetch NPC kills from DOTLAN for a region."""
    try:
        resp = httpx.get(
            f"{DOTLAN_SERVICE_URL}/api/dotlan/activity/regions/{region_id}",
            params={"metric": "npc_kills", "limit": 500},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            return {item["solar_system_id"]: item for item in data}
    except Exception as e:
        logger.warning(f"Failed to fetch DOTLAN activity for region {region_id}: {e}")
    return {}


def _fetch_dotlan_npc_kills(hours: int = 168) -> dict:
    """Fetch NPC kills per system from DOTLAN heatmap (universe-wide)."""
    try:
        resp = httpx.get(
            f"{DOTLAN_SERVICE_URL}/api/dotlan/activity/heatmap",
            params={"metric": "npc_kills", "hours": hours},
            timeout=10,
        )
        if resp.status_code == 200:
            return {item["solar_system_id"]: item["value"] for item in resp.json()}
    except Exception as e:
        logger.warning(f"Failed to fetch DOTLAN NPC kills: {e}")
    return {}


@router.get("/hunting/scores")
@handle_endpoint_errors()
def get_hunting_scores(
    region_id: int = Query(None, description="Filter by region"),
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(50, ge=1, le=200),
):
    """Get ranked hunting opportunities fusing killmail + DOTLAN data."""
    cache_key = f"hunting-scores:{region_id}:{days}:{limit}"
    cached = get_cached(cache_key, CACHE_TTL)
    if cached:
        return cached

    # Get ADM + NPC kill data from DOTLAN
    adm_data = _fetch_dotlan_adm()
    npc_hours = min(days * 24, 168)
    npc_data = _fetch_dotlan_npc_kills(hours=npc_hours)
    npc_days = min(days, 7)

    # Get player deaths from killmails (ratting/mining victims)
    with db_cursor() as cur:
        region_filter = "AND k.region_id = %s" if region_id else ""
        params = [days]
        if region_id:
            params.append(region_id)

        cur.execute(f"""
            SELECT
                k.solar_system_id,
                COALESCE(ss."solarSystemName", k.solar_system_id::text) AS system_name,
                k.region_id,
                COALESCE(r."regionName", '') AS region_name,
                COUNT(*) AS player_deaths,
                AVG(k.ship_value) AS avg_kill_value,
                array_agg(DISTINCT k.victim_alliance_id) FILTER (WHERE k.victim_alliance_id IS NOT NULL) AS victim_alliances
            FROM killmails k
            LEFT JOIN "mapSolarSystems" ss ON ss."solarSystemID" = k.solar_system_id
            LEFT JOIN "mapRegions" r ON r."regionID" = k.region_id
            WHERE k.killmail_time >= NOW() - INTERVAL '1 day' * %s
              AND k.is_npc = false
              AND k.ship_class IN ('mining', 'mining_barge', 'exhumer', 'industrial',
                                   'hauler', 'freighter', 'battlecruiser',
                                   'battleship', 'cruiser')
              {region_filter}
            GROUP BY k.solar_system_id, ss."solarSystemName", k.region_id, r."regionName"
            HAVING COUNT(*) >= 1
            ORDER BY COUNT(*) DESC
            LIMIT 500
        """, params)
        death_systems = cur.fetchall()

        # Capital presence check
        cur.execute(f"""
            SELECT DISTINCT k.solar_system_id
            FROM killmail_attackers ka
            JOIN killmails k ON k.killmail_id = ka.killmail_id
            JOIN "invTypes" it ON it."typeID" = ka.ship_type_id
            JOIN "invGroups" ig ON ig."groupID" = it."groupID"
            WHERE ig."groupID" IN (30, 485, 547, 659, 883, 902, 1538)
              AND k.killmail_time >= NOW() - INTERVAL '1 day' * %s
              {region_filter}
        """, params)
        capital_systems = {row["solar_system_id"] for row in cur.fetchall()}

    # Compute scores
    scored_systems = []
    for system in death_systems:
        sys_id = system["solar_system_id"]
        adm = adm_data.get(sys_id, {})
        adm_mil = adm.get("adm_level", 0) if adm else 0

        npc_total = npc_data.get(sys_id, 0)
        npc_per_day = npc_total / max(1, npc_days)

        score = calculate_hunting_score(
            adm_military=adm_mil,
            npc_kills_per_day=npc_per_day,
            player_deaths_per_week=system["player_deaths"] / (days / 7),
            avg_kill_value=float(system["avg_kill_value"] or 0),
            jumps_to_staging=10,
            capital_presence=sys_id in capital_systems,
        )

        scored_systems.append({
            "solar_system_id": sys_id,
            "system_name": system["system_name"],
            "region_id": system["region_id"],
            "region_name": system["region_name"],
            "score": round(score, 1),
            "adm_military": adm_mil,
            "player_deaths": system["player_deaths"],
            "avg_kill_value": float(system["avg_kill_value"] or 0),
            "has_capital_umbrella": sys_id in capital_systems,
            "victim_alliances": system["victim_alliances"],
        })

    scored_systems.sort(key=lambda x: x["score"], reverse=True)

    result = {
        "systems": scored_systems[:limit],
        "total_systems_analyzed": len(scored_systems),
        "days": days,
        "region_id": region_id,
    }

    set_cached(cache_key, result, CACHE_TTL)
    return result
