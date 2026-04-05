"""Wormhole stats summary API."""
from fastapi import APIRouter
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.services.activity_tracker import ActivityTracker

router = APIRouter(prefix="/stats", tags=["stats"])
tracker = ActivityTracker()


@router.get("/summary")
@handle_endpoint_errors()
def get_summary_stats():
    """
    Get aggregated J-Space statistics for hero section.

    Returns metrics for: active systems, residents, kills, ISK destroyed, evictions.
    """
    return tracker.get_summary_stats()
