"""Wormhole eviction tracking API."""
from fastapi import APIRouter, Query
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.services.activity_tracker import ActivityTracker

router = APIRouter(prefix="/evictions", tags=["evictions"])
tracker = ActivityTracker()


@router.get("")
@handle_endpoint_errors()
def get_recent_evictions(
    days: int = Query(30, ge=1, le=90)
):
    """
    Get recent large-scale fights in J-Space.

    Potential evictions are identified by:
    - 20+ kills in a single battle
    - Located in J-Space (system ID 31000000-31999999)
    """
    evictions = tracker.get_recent_evictions(days=days)
    return {
        "count": len(evictions),
        "lookback_days": days,
        "evictions": evictions
    }
