"""J-Space system lookup API."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.services.repository import WormholeRepository

router = APIRouter(prefix="/systems", tags=["systems"])
repo = WormholeRepository()


@router.get("")
@handle_endpoint_errors()
def list_systems(
    wh_class: Optional[int] = Query(None, ge=1, le=6, description="Filter by WH class (1-6)"),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    List J-Space systems.

    Returns system name, class, region, and static count.
    """
    systems = repo.get_wormhole_systems(wh_class=wh_class, limit=limit)
    return {
        "count": len(systems),
        "filter": {"wh_class": wh_class},
        "systems": systems
    }


@router.get("/search")
@handle_endpoint_errors()
def search_systems(
    q: str = Query(..., min_length=1, description="Search query (system name)"),
    limit: int = Query(20, ge=1, le=100)
):
    """
    Search J-Space systems by name.

    Example: /systems/search?q=J123 finds all systems starting with J123
    """
    systems = repo.search_system(q, limit=limit)
    return {
        "query": q,
        "count": len(systems),
        "systems": systems
    }


@router.get("/class/{wh_class}")
@handle_endpoint_errors()
def get_class_info(wh_class: int):
    """
    Get information about a wormhole class.
    """
    class_info = {
        1: {"name": "C1", "difficulty": "Entry", "effects": "None", "statics": "HS/LS or C1-C3"},
        2: {"name": "C2", "difficulty": "Easy", "effects": "Varies", "statics": "Two statics (unique)"},
        3: {"name": "C3", "difficulty": "Medium", "effects": "Varies", "statics": "LS or C1-C3"},
        4: {"name": "C4", "difficulty": "Hard", "effects": "Varies", "statics": "Two statics (C1-C5)"},
        5: {"name": "C5", "difficulty": "Very Hard", "effects": "Varies", "statics": "C5 or C6"},
        6: {"name": "C6", "difficulty": "Extreme", "effects": "Varies", "statics": "C5 or C6"},
    }

    info = class_info.get(wh_class)
    if not info:
        raise HTTPException(404, f"Unknown wormhole class: {wh_class}")

    # Get system count
    systems = repo.get_wormhole_systems(wh_class=wh_class, limit=10000)

    return {
        "class": wh_class,
        **info,
        "system_count": len(systems)
    }


@router.get("/{system_id}")
@handle_endpoint_errors()
def get_system(system_id: int):
    """
    Get details for a specific J-Space system.

    Returns system info and its static connections.
    """
    # Get system from view
    systems = repo.get_wormhole_systems(limit=10000)
    system = next((s for s in systems if s['system_id'] == system_id), None)

    if not system:
        raise HTTPException(404, f"System {system_id} not found or not a J-Space system")

    # Get statics
    statics = repo.get_system_statics(system_id)

    return {
        **system,
        "statics": statics
    }


@router.get("/{system_id}/statics")
@handle_endpoint_errors()
def get_system_statics(system_id: int):
    """
    Get static wormhole connections for a J-Space system.
    """
    statics = repo.get_system_statics(system_id)
    if not statics:
        raise HTTPException(404, f"No statics found for system {system_id}")

    return {
        "system_id": system_id,
        "system_name": statics[0]['system_name'],
        "system_class": statics[0]['system_class'],
        "statics": statics
    }
