"""System activity router - NPC kills, jumps, ship/pod kills per system."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.database import db_cursor
from app.models.activity import (
    SystemActivity, SystemActivityHistory, SystemActivityResponse,
    HeatmapEntry, TopSystemEntry,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/systems/{system_id}", response_model=SystemActivity)
@handle_endpoint_errors()
def get_system_activity(system_id: int):
    """Get latest activity data for a system."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT a.solar_system_id, a.timestamp, a.npc_kills, a.ship_kills,
                   a.pod_kills, a.jumps,
                   s."solarSystemName" as solar_system_name,
                   s."regionID" as region_id,
                   s."security" as security_status,
                   r."regionName" as region_name
            FROM dotlan_system_activity a
            JOIN "mapSolarSystems" s ON s."solarSystemID" = a.solar_system_id
            JOIN "mapRegions" r ON r."regionID" = s."regionID"
            WHERE a.solar_system_id = %s
            ORDER BY a.timestamp DESC
            LIMIT 1
        """, (system_id,))
        result = cur.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail=f"No activity data for system {system_id}")
    return result


@router.get("/systems/{system_id}/history", response_model=list[SystemActivityHistory])
@handle_endpoint_errors()
def get_system_activity_history(
    system_id: int,
    hours: int = Query(168, ge=1, le=720, description="Hours of history to return"),
):
    """Get hourly activity history for a system."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT timestamp, npc_kills, ship_kills, pod_kills, jumps
            FROM dotlan_system_activity
            WHERE solar_system_id = %s
              AND timestamp > NOW() - INTERVAL '%s hours'
            ORDER BY timestamp ASC
        """, (system_id, hours))
        return cur.fetchall()


@router.get("/regions/{region_id}", response_model=list[SystemActivity])
@handle_endpoint_errors()
def get_region_activity(
    region_id: int,
    metric: str = Query("npc_kills", description="Sort metric"),
    limit: int = Query(100, ge=1, le=500),
):
    """Get latest activity for all systems in a region."""
    valid_metrics = {"npc_kills", "ship_kills", "pod_kills", "jumps"}
    if metric not in valid_metrics:
        raise HTTPException(status_code=400, detail=f"Invalid metric. Use: {valid_metrics}")

    with db_cursor() as cur:
        cur.execute(f"""
            SELECT DISTINCT ON (a.solar_system_id)
                   a.solar_system_id, a.timestamp, a.npc_kills, a.ship_kills,
                   a.pod_kills, a.jumps,
                   s."solarSystemName" as solar_system_name,
                   s."regionID" as region_id,
                   s."security" as security_status,
                   r."regionName" as region_name
            FROM dotlan_system_activity a
            JOIN "mapSolarSystems" s ON s."solarSystemID" = a.solar_system_id
            JOIN "mapRegions" r ON r."regionID" = s."regionID"
            WHERE s."regionID" = %s
              AND a.timestamp > NOW() - INTERVAL '24 hours'
            ORDER BY a.solar_system_id, a.timestamp DESC
        """, (region_id,))
        results = cur.fetchall()

    # Sort by requested metric
    results.sort(key=lambda r: r.get(metric, 0) or 0, reverse=True)
    return results[:limit]


@router.get("/regions/{region_id}/top", response_model=list[TopSystemEntry])
@handle_endpoint_errors()
def get_region_top_systems(
    region_id: int,
    metric: str = Query("npc_kills"),
    limit: int = Query(20, ge=1, le=100),
):
    """Get top systems in a region by a specific metric."""
    valid_metrics = {"npc_kills", "ship_kills", "pod_kills", "jumps"}
    if metric not in valid_metrics:
        raise HTTPException(status_code=400, detail=f"Invalid metric. Use: {valid_metrics}")

    with db_cursor() as cur:
        cur.execute(f"""
            SELECT a.solar_system_id,
                   s."solarSystemName" as solar_system_name,
                   r."regionName" as region_name,
                   s."security" as security_status,
                   SUM(a.npc_kills) as npc_kills,
                   SUM(a.ship_kills) as ship_kills,
                   SUM(a.pod_kills) as pod_kills,
                   SUM(a.jumps) as jumps
            FROM dotlan_system_activity a
            JOIN "mapSolarSystems" s ON s."solarSystemID" = a.solar_system_id
            JOIN "mapRegions" r ON r."regionID" = s."regionID"
            WHERE s."regionID" = %s
              AND a.timestamp > NOW() - INTERVAL '24 hours'
            GROUP BY a.solar_system_id, s."solarSystemName", r."regionName", s."security"
            ORDER BY SUM(a.{metric}) DESC
            LIMIT %s
        """, (region_id, limit))
        return cur.fetchall()


@router.get("/top", response_model=list[TopSystemEntry])
@handle_endpoint_errors()
def get_top_systems(
    metric: str = Query("npc_kills"),
    limit: int = Query(100, ge=1, le=500),
    hours: int = Query(24, ge=1, le=168),
):
    """Get top systems universe-wide by a specific metric."""
    valid_metrics = {"npc_kills", "ship_kills", "pod_kills", "jumps"}
    if metric not in valid_metrics:
        raise HTTPException(status_code=400, detail=f"Invalid metric. Use: {valid_metrics}")

    with db_cursor() as cur:
        cur.execute(f"""
            SELECT a.solar_system_id,
                   s."solarSystemName" as solar_system_name,
                   r."regionName" as region_name,
                   s."security" as security_status,
                   SUM(a.npc_kills) as npc_kills,
                   SUM(a.ship_kills) as ship_kills,
                   SUM(a.pod_kills) as pod_kills,
                   SUM(a.jumps) as jumps
            FROM dotlan_system_activity a
            JOIN "mapSolarSystems" s ON s."solarSystemID" = a.solar_system_id
            JOIN "mapRegions" r ON r."regionID" = s."regionID"
            WHERE a.timestamp > NOW() - INTERVAL '%s hours'
            GROUP BY a.solar_system_id, s."solarSystemName", r."regionName", s."security"
            ORDER BY SUM(a.{metric}) DESC
            LIMIT %s
        """, (hours, limit))
        return cur.fetchall()


@router.get("/heatmap", response_model=list[HeatmapEntry])
@handle_endpoint_errors()
def get_universe_heatmap(
    metric: str = Query("npc_kills"),
    hours: int = Query(24, ge=1, le=168),
):
    """Get universe-wide heatmap data for ectmap visualization.

    Returns normalized values (0-1) for all systems with activity.
    Only systems with value > 0 are returned.
    """
    valid_metrics = {"npc_kills", "ship_kills", "pod_kills", "jumps"}
    if metric not in valid_metrics:
        raise HTTPException(status_code=400, detail=f"Invalid metric. Use: {valid_metrics}")

    with db_cursor() as cur:
        cur.execute(f"""
            SELECT a.solar_system_id,
                   s."solarSystemName" as solar_system_name,
                   SUM(a.{metric}) as value
            FROM dotlan_system_activity a
            JOIN "mapSolarSystems" s ON s."solarSystemID" = a.solar_system_id
            WHERE a.timestamp > NOW() - INTERVAL '%s hours'
            GROUP BY a.solar_system_id, s."solarSystemName"
            HAVING SUM(a.{metric}) > 0
            ORDER BY value DESC
        """, (hours,))
        results = cur.fetchall()

    if not results:
        return []

    max_val = max(r["value"] for r in results) or 1
    return [
        HeatmapEntry(
            solar_system_id=r["solar_system_id"],
            solar_system_name=r["solar_system_name"],
            value=r["value"],
            normalized=round(r["value"] / max_val, 3),
        )
        for r in results
    ]


@router.get("/adm", response_model=list[dict])
@handle_endpoint_errors()
def get_universe_adm():
    """Get latest ADM level for all systems universe-wide.

    Returns only systems with ADM > 0.
    """
    with db_cursor() as cur:
        cur.execute("""
            SELECT DISTINCT ON (solar_system_id)
                   solar_system_id, adm_level
            FROM dotlan_adm_history
            WHERE adm_level > 0
            ORDER BY solar_system_id, timestamp DESC
        """)
        return cur.fetchall()


@router.get("/heatmap/{region_id}", response_model=list[HeatmapEntry])
@handle_endpoint_errors()
def get_heatmap(
    region_id: int,
    metric: str = Query("npc_kills"),
    hours: int = Query(24, ge=1, le=168),
):
    """Get heatmap data for ectmap visualization.

    Returns normalized values (0-1) for each system in the region.
    """
    valid_metrics = {"npc_kills", "ship_kills", "pod_kills", "jumps"}
    if metric not in valid_metrics:
        raise HTTPException(status_code=400, detail=f"Invalid metric. Use: {valid_metrics}")

    with db_cursor() as cur:
        cur.execute(f"""
            SELECT a.solar_system_id,
                   s."solarSystemName" as solar_system_name,
                   SUM(a.{metric}) as value
            FROM dotlan_system_activity a
            JOIN "mapSolarSystems" s ON s."solarSystemID" = a.solar_system_id
            WHERE s."regionID" = %s
              AND a.timestamp > NOW() - INTERVAL '%s hours'
            GROUP BY a.solar_system_id, s."solarSystemName"
            ORDER BY value DESC
        """, (region_id, hours))
        results = cur.fetchall()

    if not results:
        return []

    # Normalize values to 0-1
    max_val = max(r["value"] for r in results) or 1
    return [
        HeatmapEntry(
            solar_system_id=r["solar_system_id"],
            solar_system_name=r["solar_system_name"],
            value=r["value"],
            normalized=round(r["value"] / max_val, 3),
        )
        for r in results
    ]
