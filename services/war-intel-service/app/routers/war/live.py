"""
Live combat intelligence endpoints for War Intel API.

Provides real-time endpoints for live kills, hotspots, demand tracking, and statistics.
"""

from datetime import datetime, timezone
from typing import Optional, List
import logging

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
import httpx

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
logger = logging.getLogger(__name__)

router = APIRouter()


async def _fetch_and_cache_corp_names(corp_ids: List[int]):
    """Fetch corporation names from ESI and cache them."""
    if not corp_ids:
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        for corp_id in corp_ids[:10]:  # Limit to 10 per request
            try:
                resp = await client.get(f"https://esi.evetech.net/latest/corporations/{corp_id}/")
                if resp.status_code == 200:
                    data = resp.json()
                    corp_name = data.get("name")
                    ticker = data.get("ticker")
                    if corp_name:
                        with db_cursor() as cur:
                            cur.execute("""
                                INSERT INTO corp_name_cache (corporation_id, corporation_name, ticker)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (corporation_id) DO UPDATE SET
                                    corporation_name = EXCLUDED.corporation_name,
                                    ticker = EXCLUDED.ticker,
                                    updated_at = NOW()
                            """, (corp_id, corp_name, ticker))
                        logger.debug(f"Cached corp {corp_id}: {corp_name}")
            except Exception as e:
                logger.debug(f"Failed to fetch corp {corp_id}: {e}")


@router.get("/live/kills/recent")
@handle_endpoint_errors()
def get_recent_kills_global(
    background_tasks: BackgroundTasks,
    minutes: int = Query(60, ge=1, le=1440, description="Time window in minutes (max 24h)")
):
    """Get recent killmails globally (for live map layer)."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                k.killmail_id, k.killmail_time, k.solar_system_id,
                k.ship_type_id, k.ship_value,
                k.victim_corporation_id, k.battle_id,
                t."typeName" as ship_name,
                c.corporation_name as victim_corp_name
            FROM killmails k
            LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            LEFT JOIN corp_name_cache c ON k.victim_corporation_id = c.corporation_id
            WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
            ORDER BY k.killmail_time DESC
        """, (minutes,))
        rows = cur.fetchall()

    # Collect missing corp IDs for background fetching
    missing_corp_ids = [
        row["victim_corporation_id"]
        for row in rows
        if row.get("victim_corporation_id") and not row.get("victim_corp_name")
    ]
    if missing_corp_ids:
        # Remove duplicates
        unique_missing = list(set(missing_corp_ids))
        background_tasks.add_task(_fetch_and_cache_corp_names, unique_missing)

    kills = [{
        "killmail_id": row["killmail_id"],
        "killmail_time": row["killmail_time"].isoformat() + "Z",
        "solar_system_id": row["solar_system_id"],
        "ship_type_id": row["ship_type_id"],
        "ship_name": row.get("ship_name"),
        "ship_value": float(row["ship_value"] or 0),
        "victim_corporation_id": row.get("victim_corporation_id"),
        "victim_corp_name": row.get("victim_corp_name"),
        "battle_id": row.get("battle_id")
    } for row in rows]

    return {
        "kills": kills,
        "count": len(kills),
        "minutes": minutes
    }


@router.get("/live/kills")
@handle_endpoint_errors()
def get_live_kills(
    system_id: Optional[int] = Query(None, description="Filter by solar system ID"),
    region_id: Optional[int] = Query(None, description="Filter by region ID"),
    limit: int = Query(50, ge=1, le=200, description="Max results")
):
    """Get recent killmails from database (last 24h)."""
    if not system_id and not region_id:
        return {
            "error": "Must specify either system_id or region_id",
            "example": "/api/war/live/kills?region_id=10000002&limit=50"
        }

    with db_cursor() as cur:
        if system_id:
            cur.execute("""
                SELECT
                    k.killmail_id, k.killmail_time, k.solar_system_id,
                    k.ship_type_id, k.ship_value, k.attacker_count,
                    k.victim_character_id, k.victim_alliance_id,
                    t."typeName" as ship_name
                FROM killmails k
                LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
                WHERE k.solar_system_id = %s
                AND k.killmail_time >= NOW() - INTERVAL '24 hours'
                ORDER BY k.killmail_time DESC
                LIMIT %s
            """, (system_id, limit))
        else:
            cur.execute("""
                SELECT
                    k.killmail_id, k.killmail_time, k.solar_system_id,
                    k.ship_type_id, k.ship_value, k.attacker_count,
                    k.victim_character_id, k.victim_alliance_id,
                    t."typeName" as ship_name
                FROM killmails k
                LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
                WHERE k.region_id = %s
                AND k.killmail_time >= NOW() - INTERVAL '24 hours'
                ORDER BY k.killmail_time DESC
                LIMIT %s
            """, (region_id, limit))

        rows = cur.fetchall()

    kills = [{
        "killmail_id": row["killmail_id"],
        "killmail_time": row["killmail_time"].isoformat() + "Z",
        "solar_system_id": row["solar_system_id"],
        "ship_type_id": row["ship_type_id"],
        "ship_name": row.get("ship_name"),
        "ship_value": float(row["ship_value"] or 0),
        "victim_character_id": row["victim_character_id"],
        "victim_alliance_id": row["victim_alliance_id"],
        "attacker_count": row["attacker_count"]
    } for row in rows]

    return {
        "kills": kills,
        "count": len(kills),
        "filter": {
            "system_id": system_id,
            "region_id": region_id
        }
    }


@router.get("/live/hotspots")
@handle_endpoint_errors()
def get_live_hotspots():
    """Get active combat hotspots (last hour)."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                k.solar_system_id,
                s."solarSystemName" as system_name,
                s."regionID" as region_id,
                r."regionName" as region_name,
                s.security,
                COUNT(*) as kill_count,
                COALESCE(SUM(k.ship_value), 0) as total_value,
                MAX(k.killmail_time) as last_kill
            FROM killmails k
            JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
            JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE k.killmail_time >= NOW() - INTERVAL '1 hour'
            GROUP BY k.solar_system_id, s."solarSystemName", s."regionID",
                     r."regionName", s.security
            HAVING COUNT(*) >= 5
            ORDER BY kill_count DESC
            LIMIT 20
        """)
        rows = cur.fetchall()

    hotspots = [{
        "system_id": row["solar_system_id"],
        "system_name": row["system_name"],
        "region_id": row["region_id"],
        "region_name": row["region_name"],
        "security": float(row["security"]) if row.get("security") else 0.0,
        "kill_count": row["kill_count"],
        "total_value": float(row["total_value"]),
        "last_kill": row["last_kill"].isoformat() + "Z"
    } for row in rows]

    return {
        "hotspots": hotspots,
        "count": len(hotspots),
        "threshold": "5 kills in 1 hour"
    }


@router.get("/live/demand/top")
@handle_endpoint_errors()
def get_top_destroyed_items(limit: int = Query(20, ge=1, le=100)):
    """Get most destroyed items in last 24h."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                ki.item_type_id,
                t."typeName" as item_name,
                SUM(ki.quantity) as quantity_destroyed
            FROM killmail_items ki
            JOIN killmails k ON ki.killmail_id = k.killmail_id
            JOIN "invTypes" t ON ki.item_type_id = t."typeID"
            WHERE k.killmail_time >= NOW() - INTERVAL '24 hours'
            AND ki.was_destroyed = true
            GROUP BY ki.item_type_id, t."typeName"
            ORDER BY quantity_destroyed DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()

    return {
        "items": [{
            "type_id": row["item_type_id"],
            "name": row.get("item_name"),
            "quantity_destroyed": int(row["quantity_destroyed"])
        } for row in rows],
        "count": len(rows),
        "window": "24 hours"
    }


@router.get("/live/demand/{item_type_id}")
@handle_endpoint_errors()
def get_item_demand(item_type_id: int):
    """Get destroyed quantity for an item (last 24h)."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT COALESCE(SUM(ki.quantity), 0) as quantity_destroyed
            FROM killmail_items ki
            JOIN killmails k ON ki.killmail_id = k.killmail_id
            WHERE ki.item_type_id = %s
            AND k.killmail_time >= NOW() - INTERVAL '24 hours'
            AND ki.was_destroyed = true
        """, (item_type_id,))
        row = cur.fetchone()

    return {
        "item_type_id": item_type_id,
        "quantity_destroyed_24h": int(row["quantity_destroyed"]),
        "note": "Only destroyed items counted (not dropped)"
    }


@router.get("/live/stats")
@handle_endpoint_errors()
def get_live_stats():
    """Get overall live combat statistics."""
    with db_cursor() as cur:
        # Get 24h stats
        cur.execute("""
            SELECT
                COUNT(*) as kills_24h,
                COALESCE(SUM(ship_value), 0) as isk_24h,
                COUNT(DISTINCT solar_system_id) as active_systems,
                COUNT(DISTINCT region_id) as active_regions
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '24 hours'
        """)
        stats_24h = cur.fetchone()

        # Get 1h stats
        cur.execute("""
            SELECT COUNT(*) as kills_1h, COALESCE(SUM(ship_value), 0) as isk_1h
            FROM killmails
            WHERE killmail_time >= NOW() - INTERVAL '1 hour'
        """)
        stats_1h = cur.fetchone()

        # Get active battles
        cur.execute("SELECT COUNT(*) as cnt FROM battles WHERE status = 'active'")
        active_battles = cur.fetchone()["cnt"]

    return {
        "last_24h": {
            "kills": stats_24h["kills_24h"],
            "isk_destroyed": float(stats_24h["isk_24h"]),
            "active_systems": stats_24h["active_systems"],
            "active_regions": stats_24h["active_regions"]
        },
        "last_hour": {
            "kills": stats_1h["kills_1h"],
            "isk_destroyed": float(stats_1h["isk_1h"])
        },
        "active_battles": active_battles,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
