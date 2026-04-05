"""Map Intelligence — lightweight global endpoints optimized for ECTMap canvas rendering."""

import logging
import os
import httpx
from fastapi import APIRouter, Query
from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.utils.cache import get_cached, set_cached

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/map")

DOTLAN_SERVICE_URL = os.getenv("DOTLAN_SERVICE_URL", "http://eve-dotlan-service:8000")
CACHE_TTL = 600  # 10 minutes


def _fetch_dotlan_adm() -> dict:
    """Fetch ADM data from DOTLAN service."""
    try:
        resp = httpx.get(f"{DOTLAN_SERVICE_URL}/api/dotlan/sovereignty/adm", timeout=10)
        if resp.status_code == 200:
            return {item["solar_system_id"]: item for item in resp.json()}
    except Exception as e:
        logger.warning(f"Failed to fetch DOTLAN ADM: {e}")
    return {}


def _fetch_dotlan_npc_kills(hours: int = 168) -> dict:
    """Fetch NPC kills per system from DOTLAN heatmap (default: 7 days)."""
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


@router.get("/hunting-heatmap")
@handle_endpoint_errors()
def get_hunting_heatmap(
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(500, ge=1, le=1000),
):
    """Hunting score per system for map heatmap coloring."""
    cache_key = f"map-hunting:{days}:{limit}"
    cached = get_cached(cache_key, CACHE_TTL)
    if cached:
        return cached

    from app.services.hunting.score_calculator import calculate_hunting_score

    adm_data = _fetch_dotlan_adm()
    npc_hours = min(days * 24, 168)  # NPC data max 7 days
    npc_data = _fetch_dotlan_npc_kills(hours=npc_hours)
    npc_days = min(days, 7)

    with db_cursor() as cur:
        cur.execute("""
            SELECT
                k.solar_system_id,
                COUNT(*) AS player_deaths,
                AVG(k.ship_value) AS avg_kill_value
            FROM killmails k
            WHERE k.killmail_time >= NOW() - INTERVAL '1 day' * %s
              AND k.is_npc = false
              AND k.ship_class IN ('mining', 'mining_barge', 'exhumer', 'industrial',
                                   'hauler', 'freighter', 'battlecruiser',
                                   'battleship', 'cruiser')
            GROUP BY k.solar_system_id
            HAVING COUNT(*) >= 1
            ORDER BY COUNT(*) DESC
            LIMIT %s
        """, (days, limit))
        death_systems = cur.fetchall()

        cur.execute("""
            SELECT DISTINCT k.solar_system_id
            FROM killmail_attackers ka
            JOIN killmails k ON k.killmail_id = ka.killmail_id
            JOIN "invTypes" it ON it."typeID" = ka.ship_type_id
            JOIN "invGroups" ig ON ig."groupID" = it."groupID"
            WHERE ig."groupID" IN (30, 485, 547, 659, 883, 902, 1538)
              AND k.killmail_time >= NOW() - INTERVAL '1 day' * %s
        """, (days,))
        capital_systems = {row["solar_system_id"] for row in cur.fetchall()}

    systems = {}
    max_score = 0
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
        score = round(score, 1)
        if score > max_score:
            max_score = score

        systems[sys_id] = {
            "score": score,
            "deaths": system["player_deaths"],
            "avg_isk": round(float(system["avg_kill_value"] or 0)),
            "has_capitals": sys_id in capital_systems,
        }

    result = {"systems": systems, "max_score": max_score}
    set_cached(cache_key, result, CACHE_TTL)
    return result


@router.get("/capital-activity")
@handle_endpoint_errors()
def get_capital_activity(
    days: int = Query(30, ge=1, le=90),
):
    """Global capital ship sightings per system for map overlay."""
    cache_key = f"map-capitals:{days}"
    cached = get_cached(cache_key, CACHE_TTL)
    if cached:
        return cached

    with db_cursor() as cur:
        cur.execute("""
            SELECT
                k.solar_system_id,
                COUNT(DISTINCT k.killmail_id) AS sightings,
                array_agg(DISTINCT ig."groupName") AS capital_classes,
                MAX(k.killmail_time)::text AS last_seen
            FROM killmail_attackers ka
            JOIN killmails k ON k.killmail_id = ka.killmail_id
            JOIN "invTypes" it ON it."typeID" = ka.ship_type_id
            JOIN "invGroups" ig ON ig."groupID" = it."groupID"
            WHERE ig."groupID" IN (30, 485, 547, 659, 883, 902, 1538)
              AND k.killmail_time >= NOW() - INTERVAL '1 day' * %s
            GROUP BY k.solar_system_id
        """, (days,))
        rows = cur.fetchall()

    systems = {}
    max_sightings = 0
    for row in rows:
        sys_id = row["solar_system_id"]
        sightings = row["sightings"]
        if sightings > max_sightings:
            max_sightings = sightings
        systems[sys_id] = {
            "sightings": sightings,
            "capital_classes": row["capital_classes"] or [],
            "last_seen": row["last_seen"],
        }

    result = {"systems": systems, "max_sightings": max_sightings}
    set_cached(cache_key, result, CACHE_TTL)
    return result


@router.get("/logi-presence")
@handle_endpoint_errors()
def get_logi_presence(
    days: int = Query(30, ge=1, le=90),
):
    """Global logistics ship presence per system for map overlay."""
    cache_key = f"map-logi:{days}"
    cached = get_cached(cache_key, CACHE_TTL)
    if cached:
        return cached

    with db_cursor() as cur:
        cur.execute("""
            WITH system_logi AS (
                SELECT
                    k.solar_system_id,
                    COUNT(DISTINCT CASE WHEN ig."groupID" IN (832, 1527)
                          THEN ka.character_id END) AS logi_pilots,
                    COUNT(DISTINCT ka.character_id) AS fleet_size
                FROM killmail_attackers ka
                JOIN killmails k ON k.killmail_id = ka.killmail_id
                JOIN "invTypes" it ON it."typeID" = ka.ship_type_id
                JOIN "invGroups" ig ON ig."groupID" = it."groupID"
                WHERE k.killmail_time >= NOW() - INTERVAL '1 day' * %s
                GROUP BY k.solar_system_id
                HAVING COUNT(DISTINCT CASE WHEN ig."groupID" IN (832, 1527)
                             THEN ka.character_id END) > 0
            )
            SELECT
                solar_system_id,
                logi_pilots,
                fleet_size,
                ROUND(logi_pilots::numeric / NULLIF(fleet_size, 0), 3) AS logi_ratio
            FROM system_logi
        """, (days,))
        rows = cur.fetchall()

    systems = {}
    max_ratio = 0
    for row in rows:
        sys_id = row["solar_system_id"]
        ratio = float(row["logi_ratio"] or 0)
        if ratio > max_ratio:
            max_ratio = ratio
        systems[sys_id] = {
            "logi_pilots": row["logi_pilots"],
            "fleet_size": row["fleet_size"],
            "logi_ratio": ratio,
        }

    result = {"systems": systems, "max_ratio": max_ratio}
    set_cached(cache_key, result, CACHE_TTL)
    return result
