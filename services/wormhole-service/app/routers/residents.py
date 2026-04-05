"""Wormhole resident tracking API."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.services.resident_detector import ResidentDetector

router = APIRouter(prefix="/residents", tags=["residents"])
detector = ResidentDetector()


@router.get("")
@handle_endpoint_errors()
def list_top_residents(limit: int = Query(50, ge=1, le=200)):
    """
    List most active J-Space residents.

    Returns corps/alliances with highest activity across all J-Space.
    """
    residents = detector.get_top_residents(limit=limit)
    return {
        "count": len(residents),
        "residents": residents
    }


@router.get("/system/{system_id}")
@handle_endpoint_errors()
def get_system_residents(system_id: int):
    """
    Get all detected residents in a specific J-Space system.

    Based on killmail activity (kills + losses in system).
    """
    residents = detector.get_system_residents(system_id)
    return {
        "system_id": system_id,
        "count": len(residents),
        "residents": residents
    }


@router.get("/alliance/{alliance_id}")
@handle_endpoint_errors()
def get_alliance_presence(alliance_id: int):
    """
    Get all J-Space systems where an alliance has presence.

    Shows which wormholes an alliance operates from.
    """
    systems = detector.get_alliance_systems(alliance_id)
    return {
        "alliance_id": alliance_id,
        "systems_count": len(systems),
        "systems": systems
    }


@router.post("/refresh")
@handle_endpoint_errors()
def refresh_residents(days: int = Query(30, ge=7, le=90)):
    """
    Refresh resident data from killmails.

    Admin endpoint to rebuild resident detection.
    """
    count = detector.refresh_residents(days=days)
    return {
        "status": "refreshed",
        "records": count,
        "lookback_days": days
    }
