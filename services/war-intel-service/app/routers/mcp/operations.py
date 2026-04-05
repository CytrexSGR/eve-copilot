"""Operations MCP Tools."""

from typing import Optional, Literal, Dict, Any, List
import logging

from fastapi import APIRouter, Query, HTTPException

from eve_shared.utils.error_handling import handle_endpoint_errors
from ..jump_planner import calculate_jump_route as _calc_route, get_jump_ships as _get_ships
from ..structure_timers import get_upcoming_timers as _get_timers

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/jump-route")
@handle_endpoint_errors()
async def mcp_calculate_jump_route(
    origin_id: int = Query(..., description="Origin system ID"),
    destination_id: int = Query(..., description="Destination system ID"),
    ship_name: str = Query("Rhea", description="Jump-capable ship name"),
    jdc_level: int = Query(5, ge=0, le=5, description="Jump Drive Calibration skill level"),
    jf_level: int = Query(5, ge=0, le=5, description="Jump Freighters skill level"),
    avoid_jammed: bool = Query(True, description="Avoid cyno-jammed systems")
) -> Dict[str, Any]:
    """
    MCP Tool: Capital jump route planning.

    Calculates optimal jump route for capital ships with fatigue estimation.
    Wraps the existing jump planner with MCP-friendly interface.

    Args:
        origin_id: Origin solar system ID
        destination_id: Destination solar system ID
        ship_name: Jump-capable ship (Rhea, Anshar, Ark, Nomad, etc.)
        jdc_level: Jump Drive Calibration skill level (0-5)
        jf_level: Jump Freighters skill level (0-5)
        avoid_jammed: Skip cyno-jammed systems in route

    Returns:
        Jump route with waypoints, distances, fatigue, and cyno requirements
    """
    result = await _calc_route(
        origin_id=origin_id,
        destination_id=destination_id,
        ship_name=ship_name,
        jdc_level=jdc_level,
        jf_level=jf_level,
        avoid_jammed=avoid_jammed,
    )
    # Convert Pydantic model to dict if needed
    if hasattr(result, 'model_dump'):
        return result.model_dump()
    elif hasattr(result, 'dict'):
        return result.dict()
    return result


@router.get("/jump-ships")
@handle_endpoint_errors()
async def mcp_get_jump_ships() -> Dict[str, Any]:
    """
    MCP Tool: List all jump-capable ships.

    Returns all capital ships capable of jumping with their base range
    and skill requirements.

    Returns:
        List of jump-capable ships with stats
    """
    return await _get_ships()


@router.get("/timers")
@handle_endpoint_errors()
async def mcp_get_structure_timers(
    region_id: Optional[int] = Query(None, description="Filter by region"),
    alliance_id: Optional[int] = Query(None, description="Filter by structure owner"),
    hours_ahead: int = Query(48, ge=1, le=168, description="Time window (hours)"),
    category: Optional[str] = Query(None, description="Filter: tcurfc, ihub, poco, pos, ansiblex, cyno_beacon, cyno_jammer")
) -> Dict[str, Any]:
    """
    MCP Tool: Structure vulnerability timers.

    Lists upcoming structure reinforcement timers with countdown and urgency.
    Wraps the existing structure timer system.

    Args:
        region_id: Filter by region
        alliance_id: Filter by structure owner alliance
        hours_ahead: Time window to look ahead (1-168 hours)
        category: Structure category filter

    Returns:
        List of upcoming timers with urgency classification
    """
    return await _get_timers(
        hours=hours_ahead,
        category=category,
        region_id=region_id,
        alliance_id=alliance_id,
    )
