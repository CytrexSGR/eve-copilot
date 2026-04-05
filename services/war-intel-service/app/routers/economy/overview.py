"""
Combined Economic Overview endpoint for war economy intelligence.
"""

from typing import Dict, Any
import logging

from fastapi import APIRouter, Query

from eve_shared.utils.error_handling import handle_endpoint_errors
from .fuel_trends import get_fuel_trends
from .manipulation import get_manipulation_alerts
from .supercap_timers import get_supercap_timers

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/economy", tags=["War Economy"])


@router.get("/overview/{region_id}")
@handle_endpoint_errors()
async def get_economic_overview(
    region_id: int,
    hours: int = Query(24, ge=1, le=168, description="Hours of historical data")
) -> Dict[str, Any]:
    """
    Get comprehensive economic intelligence overview for a region.

    Combines fuel trends, manipulation alerts, and supercap timers.
    """
    # Get fuel trends
    fuel_result = await get_fuel_trends(region_id, hours)

    # Get manipulation alerts
    manipulation_result = await get_manipulation_alerts(region_id, hours)

    # Get supercap timers for this region
    supercap_result = await get_supercap_timers(region_id)

    # Count anomalies
    fuel_anomalies = sum(
        1 for trend in fuel_result.get("trends", [])
        for snap in trend.get("snapshots", [])
        if snap.get("anomaly")
    )

    return {
        "region_id": region_id,
        "hours": hours,
        "summary": {
            "fuel_anomalies": fuel_anomalies,
            "manipulation_alerts": manipulation_result.get("count", 0),
            "active_supercap_timers": supercap_result.get("count", 0)
        },
        "fuel_trends": fuel_result.get("trends", []),
        "manipulation_alerts": manipulation_result.get("alerts", []),
        "supercap_timers": supercap_result.get("timers", [])
    }
