"""J-Space activity tracking API."""
from fastapi import APIRouter, Query
from typing import Optional
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.services.activity_tracker import ActivityTracker

router = APIRouter(prefix="/activity", tags=["activity"])
tracker = ActivityTracker()


@router.get("")
@handle_endpoint_errors()
def get_activity_heatmap(
    wh_class: Optional[int] = Query(None, ge=1, le=6),
    limit: int = Query(100, ge=1, le=500)
):
    """
    Get J-Space activity heatmap.

    Returns most active systems with kill counts and ISK destroyed.
    """
    systems = tracker.get_activity_heatmap(wh_class=wh_class, limit=limit)
    return {
        "count": len(systems),
        "filter": {"wh_class": wh_class},
        "systems": systems
    }


@router.get("/system/{system_id}")
@handle_endpoint_errors()
def get_system_activity(system_id: int):
    """Get activity stats for a specific J-Space system."""
    activity = tracker.get_system_activity(system_id)
    return activity or {"system_id": system_id, "kills_30d": 0}


@router.post("/refresh")
@handle_endpoint_errors()
def refresh_activity():
    """Refresh activity statistics (admin endpoint)."""
    count = tracker.refresh_activity_stats()
    return {"status": "refreshed", "systems_updated": count}
