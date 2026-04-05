"""Battle Intelligence MCP Tools."""

from typing import Optional, Literal, Dict, Any, List

from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
import asyncio

from ..war.battles.active import get_active_battles, get_battle
from ..war.battles.kills import get_battle_kills, get_battle_ship_classes
from ..war.battles.participants import get_battle_participants
from eve_shared.utils.error_handling import handle_endpoint_errors
router = APIRouter()

# Create a dummy BackgroundTasks for get_battle calls
_bg_tasks = BackgroundTasks()


@router.get("/battles")
@handle_endpoint_errors(default_status=500)
async def mcp_get_battles(
    status: Literal["active", "recent", "all"] = "active",
    min_isk: Optional[int] = None,
    min_kills: int = Query(5, ge=1),
    region_id: Optional[int] = None,
    alliance_id: Optional[int] = None,
    limit: int = Query(20, ge=1, le=100)
) -> Dict[str, Any]:
    """
    MCP Tool: Find battles with flexible filtering.

    Args:
        status: Battle status filter
            - "active": Currently ongoing battles
            - "recent": Battles in last 4 hours
            - "all": All battles in last 24 hours
        min_isk: Minimum ISK destroyed (filters out small skirmishes)
        min_kills: Minimum kill count (default: 5)
        region_id: Filter by region
        alliance_id: Find battles involving this alliance
        limit: Maximum battles to return (1-100)

    Returns:
        List of battles matching filters with summary statistics
    """
    # Fetch battles based on status
    # Note: pass minutes=None explicitly for active battles to avoid Query object
    if status == "active":
        battles_result = await get_active_battles(_bg_tasks, limit=limit * 2, min_kills=min_kills, minutes=None)
    elif status == "recent":
        battles_result = await get_active_battles(_bg_tasks, limit=limit * 2, min_kills=min_kills, minutes=240)
    else:  # all
        battles_result = await get_active_battles(_bg_tasks, limit=limit * 2, min_kills=min_kills, minutes=1440)

    # Convert Pydantic model to dict
    battles_dict = battles_result.model_dump() if hasattr(battles_result, 'model_dump') else battles_result.dict()
    battles = battles_dict.get('battles', [])

    # Apply filters
    if min_isk:
        battles = [b for b in battles if b.get('total_isk_destroyed', 0) >= min_isk]

    if region_id:
        battles = [b for b in battles if b.get('region_id') == region_id]

    if alliance_id:
        # Filter battles where alliance participated
        battles = await _filter_battles_by_alliance(battles, alliance_id)

    # Limit results
    battles = battles[:limit]

    # Generate summary
    summary = {
        "total_battles": len(battles),
        "total_isk": sum(b.get('total_isk_destroyed', 0) for b in battles),
        "most_intense": _get_most_intense_battle(battles)
    }

    return {
        "battles": battles,
        "summary": summary
    }


@router.get("/battle/{battle_id}")
@handle_endpoint_errors(default_status=500)
async def mcp_analyze_battle(
    battle_id: int,
    include_kills: bool = False,
    include_doctrines: bool = True,
    include_reshipments: bool = False,
    include_timeline: bool = False
) -> Dict[str, Any]:
    """
    MCP Tool: Deep battle analysis.

    Provides comprehensive battle intelligence including participants,
    doctrines, timeline, and individual kills if requested.

    Args:
        battle_id: Battle ID from get_battles
        include_kills: Include individual kill data (can be large)
        include_doctrines: Include doctrine analysis (default: true)
        include_reshipments: Include pilot reshipment analysis
        include_timeline: Include battle timeline/events

    Returns:
        Complete battle analysis with requested details
    """
    # Fetch core battle data
    battle_data = await get_battle(battle_id, _bg_tasks)

    if not battle_data:
        raise HTTPException(status_code=404, detail=f"Battle {battle_id} not found")

    # Build result with core data
    result = {
        "battle_id": battle_id,
        "system_id": battle_data.get('system_id'),
        "system_name": battle_data.get('system_name'),
        "region_name": battle_data.get('region_name'),
        "status": battle_data.get('status'),
        "stats": {
            "total_kills": battle_data.get('total_kills'),
            "total_isk": battle_data.get('total_isk_destroyed'),
            "duration_minutes": battle_data.get('duration_minutes'),
            "started_at": battle_data.get('started_at'),
            "last_kill_at": battle_data.get('last_kill_at')
        }
    }

    # Fetch optional data in parallel
    tasks = []
    task_names = []

    # Always fetch participants
    tasks.append(get_battle_participants(battle_id))
    task_names.append('participants')

    if include_doctrines:
        tasks.append(get_battle_ship_classes(battle_id))
        task_names.append('doctrines')

    if include_kills:
        tasks.append(get_battle_kills(battle_id, limit=100))
        task_names.append('kills')

    # Execute parallel queries
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for name, data in zip(task_names, results):
            if not isinstance(data, Exception):
                result[name] = data

    return result


# ===== Helper Functions =====

async def _filter_battles_by_alliance(battles: List[Dict], alliance_id: int) -> List[Dict]:
    """Filter battles where alliance participated."""
    filtered = []

    for battle in battles:
        battle_id = battle.get('battle_id')
        if not battle_id:
            continue

        # Check if alliance participated
        participants = await get_battle_participants(battle_id)
        sides = participants.get('sides', [])

        for side in sides:
            alliances = side.get('alliances', [])
            if any(a.get('alliance_id') == alliance_id for a in alliances):
                filtered.append(battle)
                break

    return filtered


def _get_most_intense_battle(battles: List[Dict]) -> Optional[str]:
    """Get name of most intense battle (highest ISK)."""
    if not battles:
        return None

    most_intense = max(battles, key=lambda b: b.get('total_isk_destroyed', 0))
    isk_b = most_intense.get('total_isk_destroyed', 0) / 1_000_000_000
    system = most_intense.get('system_name', 'Unknown')

    return f"{system} ({isk_b:.1f}B ISK)"
