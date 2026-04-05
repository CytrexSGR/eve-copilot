"""Power Bloc Intelligence MCP Tools."""

import logging
from typing import Literal, Dict, Any, List

from fastapi import APIRouter, Query, HTTPException

from eve_shared.utils.error_handling import handle_endpoint_errors
from ..reports import get_power_blocs_live

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/powerblocs", operation_id="list_power_blocs")
@handle_endpoint_errors(default_status=500)
async def mcp_get_powerblocs(
    min_alliances: int = Query(2, ge=1),
    days: int = Query(7, ge=1, le=90)
) -> Dict[str, Any]:
    """
    MCP Tool: Get all major power blocs in EVE Online.

    Returns coalition-level intelligence showing organized groups of alliances
    that operate together militarily and politically.

    Args:
        min_alliances: Minimum alliances to qualify as power bloc (default: 2)
        days: Historical data period for stats (1-90 days)

    Returns:
        List of power blocs with:
        - Coalition members (alliances)
        - Combined combat statistics
        - ISK efficiency and activity metrics
        - Territory control (regions)
    """
    # Reuse existing power blocs endpoint (uses minutes, not days)
    minutes = days * 24 * 60  # Convert days to minutes
    result = await get_power_blocs_live(minutes=minutes)

    coalitions = result.get('coalitions', [])

    # Filter by min alliance count
    if min_alliances > 1:
        coalitions = [c for c in coalitions if len(c.get('members', [])) >= min_alliances]

    return {
        "power_blocs": coalitions,
        "summary": {
            "total_blocs": len(coalitions),
            "total_alliances": sum(len(c.get('members', [])) for c in coalitions),
            "combined_kills": sum(c.get('total_kills', 0) for c in coalitions),
            "combined_isk_destroyed": sum(c.get('isk_destroyed', 0) for c in coalitions)
        },
        "period_days": days
    }


@router.get("/powerbloc/{leader_alliance_id}", operation_id="analyze_power_bloc")
@handle_endpoint_errors(default_status=500)
async def mcp_analyze_powerbloc(
    leader_alliance_id: int,
    scope: Literal["summary", "complete"] = "summary",
    days: int = Query(7, ge=1, le=90)
) -> Dict[str, Any]:
    """
    MCP Tool: Analyze a specific power bloc/coalition.

    Provides detailed intelligence on a coalition led by a specific alliance.

    Scopes:
    - summary: Basic coalition info (members, total stats)
    - complete: Full analysis with all member alliances, doctrines, threats

    Args:
        leader_alliance_id: Leader alliance ID of the coalition
        scope: Level of detail to return
        days: Historical data period (1-90 days)

    Returns:
        Power bloc intelligence with member alliances and combined stats
    """
    # Get all power blocs (uses minutes, not days)
    minutes = days * 24 * 60
    blocs_result = await get_power_blocs_live(minutes=minutes)
    coalitions = blocs_result.get('coalitions', [])

    # Find the specific coalition
    coalition = None
    for c in coalitions:
        if c.get('leader_alliance_id') == leader_alliance_id:
            coalition = c
            break

    if not coalition:
        raise HTTPException(
            status_code=404,
            detail=f"Power bloc with leader alliance {leader_alliance_id} not found"
        )

    if scope == "summary":
        # Return just basic info
        return {
            "coalition_name": coalition.get('name'),
            "leader_alliance_id": coalition.get('leader_alliance_id'),
            "leader_alliance_name": coalition.get('leader_name'),
            "member_count": len(coalition.get('members', [])),
            "total_kills": coalition.get('total_kills'),
            "total_deaths": coalition.get('total_losses'),
            "total_isk_destroyed": coalition.get('isk_destroyed'),
            "total_isk_lost": coalition.get('isk_lost'),
            "efficiency": coalition.get('efficiency'),
            "period_days": days
        }
    else:
        # Return complete data
        return {
            **coalition,
            "period_days": days
        }
