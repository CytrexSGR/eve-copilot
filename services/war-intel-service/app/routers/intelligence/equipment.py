"""Equipment Intel Endpoints."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Query

from app.services.intelligence.equipment_service import equipment_intel_service
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/fast/{alliance_id}/weapons-lost")
@handle_endpoint_errors()
def get_weapons_lost(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(20, ge=1, le=50)
) -> Dict[str, Any]:
    """Analyze weapon systems lost by an alliance."""
    return equipment_intel_service.get_weapons_lost(alliance_id, days, limit)

@router.get("/fast/{alliance_id}/tank-profile")
@handle_endpoint_errors()
def get_tank_profile(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(20, ge=1, le=50)
) -> Dict[str, Any]:
    """Analyze tank modules lost by an alliance."""
    return equipment_intel_service.get_tank_profile(alliance_id, days, limit)

@router.get("/fast/{alliance_id}/cargo-intel")
@handle_endpoint_errors()
def get_cargo_intel(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(50, ge=1, le=100)
) -> Dict[str, Any]:
    """Analyze cargo hold contents lost by an alliance."""
    return equipment_intel_service.get_cargo_intel(alliance_id, days, limit)

@router.get("/fast/{alliance_id}/equipment-intel")
@handle_endpoint_errors()
def get_equipment_intel(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30)
) -> Dict[str, Any]:
    """Comprehensive equipment intelligence combining weapons, tank, and cargo analysis."""
    return equipment_intel_service.get_equipment_intel(alliance_id, days)
