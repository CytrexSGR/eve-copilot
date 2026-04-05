"""Wormhole type reference API."""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.services.repository import WormholeRepository

router = APIRouter(prefix="/types", tags=["types"])
repo = WormholeRepository()


@router.get("")
@handle_endpoint_errors()
def list_types(
    target_class: Optional[int] = Query(None, ge=1, le=9, description="Filter by target class"),
    max_ship: Optional[str] = Query(None, description="Filter by max ship class (Frigate, Cruiser, Battleship, Capital)")
):
    """
    List all wormhole types with attributes.

    Returns WH codes (A009, B274, etc.) with:
    - Target class
    - Lifetime
    - Mass limits
    - Max ship class
    """
    types = repo.get_wormhole_types()

    if target_class:
        types = [t for t in types if t.get('target_class') == target_class]

    if max_ship:
        types = [t for t in types if t.get('max_ship_class', '').lower() == max_ship.lower()]

    return {
        "count": len(types),
        "types": types
    }


@router.get("/{type_code}")
@handle_endpoint_errors()
def get_type(type_code: str):
    """
    Get details for a specific wormhole type.

    Example: /types/C140 returns C5→C5 static info
    """
    wh_type = repo.get_wormhole_type(type_code)
    if not wh_type:
        raise HTTPException(404, f"Wormhole type '{type_code}' not found")
    return wh_type


@router.get("/{type_code}/systems")
@handle_endpoint_errors()
def get_systems_with_static(type_code: str):
    """
    Get all J-Space systems that have this wormhole as a static.

    Example: /types/C140/systems returns all C5s with a C5 static
    """
    systems = repo.get_systems_by_static(type_code)
    return {
        "static_type": type_code.upper(),
        "count": len(systems),
        "systems": systems
    }
