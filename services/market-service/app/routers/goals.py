# routers/goals.py
"""Trading Goals Router - Migrated from monolith to market-service."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request, Body

from app.services.trading.goals import (
    TradingGoalsService,
    TradingGoal,
    GoalsResponse,
)
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/goals", tags=["Trading Goals"])


def get_goals_service(request: Request) -> TradingGoalsService:
    """Dependency injection for goals service."""
    db = request.app.state.db
    return TradingGoalsService(db)


@router.get("/{character_id}", response_model=GoalsResponse)
@handle_endpoint_errors()
def get_goals(
    request: Request,
    character_id: int,
    active_only: bool = Query(True),
    goal_type: Optional[str] = Query(None, description="Filter: daily, weekly, monthly"),
):
    """
    Get trading goals with progress for a character.

    Args:
        character_id: EVE Online character ID
        active_only: Only return active goals
        goal_type: Filter by goal type (daily/weekly/monthly)

    Returns:
        GoalsResponse with goals and achievement statistics
    """
    service = get_goals_service(request)
    return service.get_goals(character_id, active_only, goal_type)


@router.post("/{character_id}", response_model=TradingGoal)
@handle_endpoint_errors()
def create_goal(
    request: Request,
    character_id: int,
    goal_type: str = Body(..., description="daily, weekly, or monthly"),
    target_type: str = Body("profit", description="profit, volume, trades, or roi"),
    target_value: float = Body(..., description="Target value"),
    type_id: Optional[int] = Body(None, description="Specific item type ID"),
    type_name: Optional[str] = Body(None, description="Item name"),
    notify_on_progress: bool = Body(True),
    notify_on_completion: bool = Body(True),
):
    """
    Create a new trading goal.

    Args:
        character_id: EVE Online character ID
        goal_type: Period type (daily/weekly/monthly)
        target_type: What to measure (profit/volume/trades/roi)
        target_value: Target value to achieve
        type_id: Optional item type filter
        type_name: Optional item name
        notify_on_progress: Send alerts at milestones
        notify_on_completion: Send alert when achieved

    Returns:
        Created TradingGoal
    """
    if goal_type not in ("daily", "weekly", "monthly"):
        raise HTTPException(status_code=400, detail="goal_type must be daily, weekly, or monthly")

    if target_type not in ("profit", "volume", "trades", "roi"):
        raise HTTPException(status_code=400, detail="target_type must be profit, volume, trades, or roi")

    if target_value <= 0:
        raise HTTPException(status_code=400, detail="target_value must be positive")

    service = get_goals_service(request)
    return service.create_goal(
        character_id=character_id,
        goal_type=goal_type,
        target_type=target_type,
        target_value=target_value,
        type_id=type_id,
        type_name=type_name,
        notify_on_progress=notify_on_progress,
        notify_on_completion=notify_on_completion
    )


@router.patch("/{character_id}/{goal_id}/progress")
@handle_endpoint_errors()
def update_goal_progress(
    request: Request,
    character_id: int,
    goal_id: int,
    current_value: float = Body(..., embed=True),
):
    """
    Update progress for a specific goal.

    Args:
        character_id: EVE Online character ID (for verification)
        goal_id: Goal ID
        current_value: New current value

    Returns:
        Updated goal or error
    """
    service = get_goals_service(request)
    goal = service.update_goal_progress(goal_id, current_value)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.delete("/{character_id}/{goal_id}")
@handle_endpoint_errors()
def delete_goal(
    request: Request,
    character_id: int,
    goal_id: int,
):
    """
    Delete a trading goal.

    Args:
        character_id: EVE Online character ID
        goal_id: Goal ID

    Returns:
        Success status
    """
    service = get_goals_service(request)
    deleted = service.delete_goal(goal_id, character_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"deleted": True}


@router.post("/{character_id}/{goal_id}/deactivate")
@handle_endpoint_errors()
def deactivate_goal(
    request: Request,
    character_id: int,
    goal_id: int,
):
    """
    Deactivate a trading goal (soft delete).

    Args:
        character_id: EVE Online character ID
        goal_id: Goal ID

    Returns:
        Success status
    """
    service = get_goals_service(request)
    deactivated = service.deactivate_goal(goal_id, character_id)
    if not deactivated:
        raise HTTPException(status_code=404, detail="Goal not found")
    return {"deactivated": True}
