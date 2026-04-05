"""Activity Tracking - Fleet sessions, login tracking, activity summaries."""

from typing import List, Optional

from fastapi import APIRouter, Request, Query
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.models import FleetSession, FleetSessionCreate, ActivitySummary
from app.services.activity_tracker import ActivityTracker

router = APIRouter(prefix="/activity", tags=["Activity Tracking"])


def _get_tracker() -> ActivityTracker:
    return ActivityTracker()


@router.get("/summary/{character_id}", response_model=ActivitySummary)
@handle_endpoint_errors()
def get_activity_summary(request: Request, character_id: int):
    """Get activity summary for a character (30-day window)."""
    tracker = _get_tracker()
    return tracker.get_summary(character_id)


@router.get("/fleet-sessions", response_model=List[FleetSession])
@handle_endpoint_errors()
def get_fleet_sessions(
    request: Request,
    character_id: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
):
    """List fleet sessions with optional character filter."""
    tracker = _get_tracker()
    return tracker.get_fleet_sessions(character_id=character_id, limit=limit)


@router.post("/fleet-sessions", response_model=FleetSession, status_code=201)
@handle_endpoint_errors()
def record_fleet_session(request: Request, session: FleetSessionCreate):
    """Record a fleet participation session."""
    tracker = _get_tracker()
    data = session.model_dump()
    return tracker.record_fleet_session(data)


@router.get("/inactive")
@handle_endpoint_errors()
def get_inactive_members(
    request: Request,
    days: int = Query(30, ge=7, le=90),
):
    """List members inactive for N days."""
    tracker = _get_tracker()
    return tracker.get_inactive_members(days=days)
