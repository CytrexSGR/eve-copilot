"""Sovereignty router - campaigns, changes, ADM history."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.database import db_cursor
from app.models.sovereignty import SovCampaign, SovChange, ADMHistoryEntry

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/campaigns", response_model=list[SovCampaign])
@handle_endpoint_errors()
def get_campaigns(
    status: str = Query("active", description="Filter by status: active, upcoming, finished, all"),
):
    """Get sovereignty campaigns."""
    with db_cursor() as cur:
        if status == "all":
            cur.execute("""
                SELECT c.*, s."solarSystemName" as solar_system_name,
                       s."regionID" as region_id,
                       r."regionName" as region_name
                FROM dotlan_sov_campaigns c
                LEFT JOIN "mapSolarSystems" s ON s."solarSystemID" = c.solar_system_id
                LEFT JOIN "mapRegions" r ON r."regionID" = s."regionID"
                ORDER BY c.last_updated DESC
                LIMIT 200
            """)
        else:
            cur.execute("""
                SELECT c.*, s."solarSystemName" as solar_system_name,
                       s."regionID" as region_id,
                       r."regionName" as region_name
                FROM dotlan_sov_campaigns c
                LEFT JOIN "mapSolarSystems" s ON s."solarSystemID" = c.solar_system_id
                LEFT JOIN "mapRegions" r ON r."regionID" = s."regionID"
                WHERE c.status = %s
                ORDER BY c.last_updated DESC
            """, (status,))
        return cur.fetchall()


@router.get("/campaigns/map")
@handle_endpoint_errors()
def get_campaigns_map():
    """Get active campaigns optimized for map overlay.

    Returns minimal data needed for ectmap rendering.
    """
    with db_cursor() as cur:
        cur.execute("""
            SELECT c.campaign_id, c.solar_system_id, c.structure_type,
                   c.defender_name, c.defender_id, c.score, c.status,
                   s."solarSystemName" as solar_system_name,
                   s."regionID" as region_id,
                   r."regionName" as region_name
            FROM dotlan_sov_campaigns c
            LEFT JOIN "mapSolarSystems" s ON s."solarSystemID" = c.solar_system_id
            LEFT JOIN "mapRegions" r ON r."regionID" = s."regionID"
            WHERE c.status = 'active'
            ORDER BY c.score DESC NULLS LAST
        """)
        return cur.fetchall()


@router.get("/changes", response_model=list[SovChange])
@handle_endpoint_errors()
def get_sov_changes(
    days: int = Query(7, ge=1, le=365),
    alliance_id: Optional[int] = None,
):
    """Get sovereignty changes for the last N days."""
    with db_cursor() as cur:
        if alliance_id:
            cur.execute("""
                SELECT c.*, s."solarSystemName" as solar_system_name,
                       r."regionName" as region_name
                FROM dotlan_sov_changes c
                LEFT JOIN "mapSolarSystems" s ON s."solarSystemID" = c.solar_system_id
                LEFT JOIN "mapRegions" r ON r."regionID" = c.region_id
                WHERE c.changed_at > NOW() - INTERVAL '%s days'
                  AND (c.old_alliance_id = %s OR c.new_alliance_id = %s)
                ORDER BY c.changed_at DESC
            """, (days, alliance_id, alliance_id))
        else:
            cur.execute("""
                SELECT c.*, s."solarSystemName" as solar_system_name,
                       r."regionName" as region_name
                FROM dotlan_sov_changes c
                LEFT JOIN "mapSolarSystems" s ON s."solarSystemID" = c.solar_system_id
                LEFT JOIN "mapRegions" r ON r."regionID" = c.region_id
                WHERE c.changed_at > NOW() - INTERVAL '%s days'
                ORDER BY c.changed_at DESC
                LIMIT 200
            """, (days,))
        return cur.fetchall()


@router.get("/adm-history/{system_id}", response_model=list[ADMHistoryEntry])
@handle_endpoint_errors()
def get_adm_history(
    system_id: int,
    days: int = Query(30, ge=1, le=180),
):
    """Get ADM history for a system."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT timestamp, adm_level
            FROM dotlan_adm_history
            WHERE solar_system_id = %s
              AND timestamp > NOW() - INTERVAL '%s days'
            ORDER BY timestamp ASC
        """, (system_id, days))
        results = cur.fetchall()

    if not results:
        raise HTTPException(status_code=404, detail=f"No ADM history for system {system_id}")
    return results
