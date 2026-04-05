"""
Statistics and analytics endpoints for War Intel API.

Provides endpoints for war summaries, top ships, heatmaps, losses, conflicts, and doctrines.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/summary")
@handle_endpoint_errors()
def get_war_summary(
    hours: int = Query(24, ge=1, le=168),
    region_id: Optional[int] = Query(None)
):
    """Get overall war/combat summary."""
    with db_cursor() as cur:
        region_filter = "AND k.region_id = %s" if region_id else ""
        params = [hours]
        if region_id:
            params.append(region_id)

        cur.execute(f"""
            SELECT
                COUNT(*) as total_kills,
                COALESCE(SUM(k.ship_value), 0) as total_isk_destroyed,
                COUNT(DISTINCT k.solar_system_id) as active_systems,
                COUNT(*) FILTER (WHERE k.is_capital = true) as capital_kills
            FROM killmails k
            WHERE k.killmail_time >= NOW() - INTERVAL '%s hours'
            {region_filter}
        """, params)
        row = cur.fetchone()

    return {
        "period_hours": hours,
        "region_id": region_id,
        "total_kills": row["total_kills"],
        "total_isk_destroyed": float(row["total_isk_destroyed"]),
        "active_systems": row["active_systems"],
        "capital_kills": row["capital_kills"],
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/top-ships")
@handle_endpoint_errors()
def get_top_destroyed_ships(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=100),
    region_id: Optional[int] = Query(None)
):
    """Get most destroyed ship types."""
    with db_cursor() as cur:
        region_filter = "AND k.region_id = %s" if region_id else ""
        params = [hours]
        if region_id:
            params.append(region_id)
        params.append(limit)

        cur.execute(f"""
            SELECT
                k.ship_type_id,
                t."typeName" as ship_name,
                g."groupName" as ship_class,
                COUNT(*) as destroyed_count,
                COALESCE(SUM(k.ship_value), 0) as total_value
            FROM killmails k
            LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE k.killmail_time >= NOW() - INTERVAL '%s hours'
            {region_filter}
            GROUP BY k.ship_type_id, t."typeName", g."groupName"
            ORDER BY destroyed_count DESC
            LIMIT %s
        """, params)
        rows = cur.fetchall()

    return [{
        "ship_type_id": row["ship_type_id"],
        "ship_name": row.get("ship_name"),
        "ship_class": row.get("ship_class"),
        "destroyed_count": row["destroyed_count"],
        "total_value": float(row["total_value"])
    } for row in rows]


@router.get("/heatmap")
@handle_endpoint_errors()
def get_heatmap(
    days: int = Query(7, ge=1, le=30),
    min_kills: int = Query(5, ge=1)
):
    """Get heatmap data for galaxy visualization."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                k.solar_system_id,
                s."solarSystemName" as system_name,
                s."regionID" as region_id,
                r."regionName" as region_name,
                s.security,
                s.x, s.z,
                COUNT(*) as kill_count,
                COALESCE(SUM(k.ship_value), 0) as total_value,
                COUNT(*) FILTER (WHERE k.is_capital = true) as capital_kills
            FROM killmails k
            JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
            JOIN "mapRegions" r ON s."regionID" = r."regionID"
            WHERE k.killmail_time >= NOW() - INTERVAL '%s days'
            GROUP BY k.solar_system_id, s."solarSystemName", s."regionID",
                     r."regionName", s.security, s.x, s.z
            HAVING COUNT(*) >= %s
            ORDER BY kill_count DESC
        """, (days, min_kills))
        rows = cur.fetchall()

    return {
        "systems": [{
            "solar_system_id": row["solar_system_id"],
            "system_name": row.get("system_name"),
            "region_id": row.get("region_id"),
            "region_name": row.get("region_name"),
            "security": float(row["security"]) if row.get("security") else 0.0,
            "x": float(row["x"]) if row.get("x") else 0.0,
            "z": float(row["z"]) if row.get("z") else 0.0,
            "kill_count": row["kill_count"],
            "total_value": float(row["total_value"]),
            "capital_kills": row["capital_kills"]
        } for row in rows],
        "period_days": days,
        "min_kills": min_kills,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/hot-systems")
@handle_endpoint_errors()
def get_hot_systems(
    minutes: int = Query(60, ge=10, le=10080),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Get hot systems with sovereignty owner data.
    Combines kill activity with SOV information for battlefield display.
    """
    with db_cursor() as cur:
        cur.execute("""
            WITH hot_systems AS (
                SELECT
                    k.solar_system_id,
                    COUNT(*) as kill_count,
                    COALESCE(SUM(k.ship_value), 0) as total_value,
                    COUNT(*) FILTER (WHERE k.is_capital = true) as capital_kills,
                    MAX(k.killmail_time) as last_kill
                FROM killmails k
                WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
                GROUP BY k.solar_system_id
                HAVING COUNT(*) >= 3
            )
            SELECT
                hs.solar_system_id,
                ss."solarSystemName" as system_name,
                r."regionName" as region_name,
                ss.security as security_status,
                hs.kill_count,
                hs.total_value,
                hs.capital_kills,
                hs.last_kill,
                sov.alliance_id as sov_alliance_id,
                a.alliance_name as sov_alliance_name,
                a.ticker as sov_alliance_ticker
            FROM hot_systems hs
            JOIN "mapSolarSystems" ss ON hs.solar_system_id = ss."solarSystemID"
            JOIN "mapRegions" r ON ss."regionID" = r."regionID"
            LEFT JOIN sovereignty_structures sov ON hs.solar_system_id = sov.solar_system_id
                AND sov.structure_type_id = 32458
            LEFT JOIN alliance_name_cache a ON sov.alliance_id = a.alliance_id
            ORDER BY hs.kill_count DESC
            LIMIT %s
        """, (minutes, limit))
        rows = cur.fetchall()

    systems = []
    for row in rows:
        kills = row["kill_count"]
        caps = row["capital_kills"]
        threat_level = "critical" if kills >= 30 or caps >= 2 else \
                      "hot" if kills >= 15 else \
                      "active" if kills >= 5 else "low"

        last_kill_minutes = None
        if row["last_kill"]:
            last_kill = row["last_kill"]
            if last_kill.tzinfo is None:
                last_kill = last_kill.replace(tzinfo=timezone.utc)
            delta = datetime.now(timezone.utc) - last_kill
            last_kill_minutes = int(delta.total_seconds() / 60)

        systems.append({
            "solar_system_id": row["solar_system_id"],
            "system_name": row.get("system_name"),
            "region_name": row.get("region_name"),
            "security_status": round(float(row["security_status"]), 2) if row.get("security_status") else 0.0,
            "kill_count": row["kill_count"],
            "total_value": float(row["total_value"]),
            "capital_kills": row["capital_kills"],
            "last_kill_minutes_ago": last_kill_minutes,
            "threat_level": threat_level,
            "sov_alliance_id": row.get("sov_alliance_id"),
            "sov_alliance_name": row.get("sov_alliance_name"),
            "sov_alliance_ticker": row.get("sov_alliance_ticker"),
        })

    return {
        "minutes": minutes,
        "systems": systems,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/losses/{region_id}")
@handle_endpoint_errors()
def get_region_losses(
    region_id: int,
    days: int = Query(7, ge=1, le=30),
    loss_type: str = Query("all", pattern="^(all|ships|items)$")
):
    """Get combat losses for a region."""
    with db_cursor() as cur:
        result = {}

        if loss_type in ("all", "ships"):
            cur.execute("""
                SELECT
                    k.ship_type_id,
                    t."typeName" as ship_name,
                    g."groupName" as ship_class,
                    COUNT(*) as quantity,
                    COALESCE(SUM(k.ship_value), 0) as total_value
                FROM killmails k
                JOIN "invTypes" t ON k.ship_type_id = t."typeID"
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE k.region_id = %s
                AND k.killmail_time >= NOW() - INTERVAL '%s days'
                GROUP BY k.ship_type_id, t."typeName", g."groupName"
                ORDER BY quantity DESC
                LIMIT 50
            """, (region_id, days))
            result["ships"] = [{
                "type_id": row["ship_type_id"],
                "name": row.get("ship_name"),
                "class": row.get("ship_class"),
                "quantity": row["quantity"],
                "total_value": float(row["total_value"])
            } for row in cur.fetchall()]

        if loss_type in ("all", "items"):
            cur.execute("""
                SELECT
                    ki.item_type_id,
                    t."typeName" as item_name,
                    SUM(ki.quantity) as quantity_destroyed
                FROM killmail_items ki
                JOIN killmails k ON ki.killmail_id = k.killmail_id
                JOIN "invTypes" t ON ki.item_type_id = t."typeID"
                WHERE k.region_id = %s
                AND k.killmail_time >= NOW() - INTERVAL '%s days'
                AND ki.was_destroyed = true
                GROUP BY ki.item_type_id, t."typeName"
                ORDER BY quantity_destroyed DESC
                LIMIT 50
            """, (region_id, days))
            result["items"] = [{
                "type_id": row["item_type_id"],
                "name": row.get("item_name"),
                "quantity_destroyed": int(row["quantity_destroyed"])
            } for row in cur.fetchall()]

        return result


@router.get("/doctrines/{region_id}")
@handle_endpoint_errors()
def get_region_doctrines(
    region_id: int,
    days: int = Query(7, ge=1, le=30),
    min_fleet_size: int = Query(10, ge=3)
):
    """Detect fleet doctrines from loss patterns in a region."""
    with db_cursor() as cur:
        # Group kills by battle/time window to identify fleets
        cur.execute("""
            WITH fleet_kills AS (
                SELECT
                    k.battle_id,
                    k.victim_alliance_id,
                    k.ship_type_id,
                    t."typeName" as ship_name,
                    g."groupName" as ship_class,
                    COUNT(*) as count
                FROM killmails k
                JOIN "invTypes" t ON k.ship_type_id = t."typeID"
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE k.region_id = %s
                AND k.killmail_time >= NOW() - INTERVAL '%s days'
                AND k.battle_id IS NOT NULL
                GROUP BY k.battle_id, k.victim_alliance_id, k.ship_type_id,
                         t."typeName", g."groupName"
            ),
            fleet_compositions AS (
                SELECT
                    victim_alliance_id,
                    ship_class,
                    ship_name,
                    SUM(count) as total_losses,
                    COUNT(DISTINCT battle_id) as battles_seen
                FROM fleet_kills
                GROUP BY victim_alliance_id, ship_class, ship_name
                HAVING SUM(count) >= %s
            )
            SELECT * FROM fleet_compositions
            ORDER BY total_losses DESC
            LIMIT 30
        """, (region_id, days, min_fleet_size))
        rows = cur.fetchall()

    return {
        "doctrines": [{
            "alliance_id": row["victim_alliance_id"],
            "ship_class": row.get("ship_class"),
            "ship_name": row.get("ship_name"),
            "total_losses": row["total_losses"],
            "battles_seen": row["battles_seen"]
        } for row in rows],
        "region_id": region_id,
        "period_days": days,
        "min_fleet_size": min_fleet_size,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
