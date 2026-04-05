"""
Fuel Market Trends endpoint for war economy intelligence.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

from fastapi import APIRouter, Query

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/economy", tags=["War Economy"])


@router.get("/fuel/trends")
@handle_endpoint_errors()
def get_fuel_trends(
    region_id: int = Query(..., description="Region ID (e.g., 10000002 for The Forge)"),
    hours: int = Query(24, ge=1, le=168, description="Hours of historical data (1-168)")
) -> Dict[str, Any]:
    """
    Get isotope market trends for capital movement prediction.

    Large isotope volume changes may indicate capital ship movements or deployments.
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    with db_cursor() as cur:
        cur.execute("""
            SELECT
                wef.isotope_type_id,
                it."typeName" as isotope_name,
                wef.snapshot_time,
                wef.total_volume,
                wef.baseline_7d_volume as baseline_volume,
                wef.volume_delta_percent as delta_percent,
                wef.average_price,
                wef.anomaly_detected,
                wef.anomaly_severity
            FROM war_economy_fuel_snapshots wef
            JOIN "invTypes" it ON wef.isotope_type_id = it."typeID"
            WHERE wef.region_id = %s
              AND wef.snapshot_time >= %s
            ORDER BY wef.isotope_type_id, wef.snapshot_time DESC
        """, (region_id, cutoff))

        rows = cur.fetchall()

    # Group by isotope
    trends_by_isotope: Dict[int, List[Dict]] = {}
    for row in rows:
        iso_id = row['isotope_type_id']
        if iso_id not in trends_by_isotope:
            trends_by_isotope[iso_id] = {
                "isotope_id": iso_id,
                "isotope_name": row['isotope_name'],
                "snapshots": []
            }
        trends_by_isotope[iso_id]["snapshots"].append({
            "timestamp": row['snapshot_time'].isoformat() if row['snapshot_time'] else None,
            "volume": row['total_volume'],
            "baseline": row['baseline_volume'],
            "delta_percent": float(row['delta_percent']) if row['delta_percent'] else 0,
            "price": float(row['average_price']) if row['average_price'] else 0,
            "anomaly": row['anomaly_detected'],
            "severity": row['anomaly_severity'] or 'normal'
        })

    return {
        "region_id": region_id,
        "hours": hours,
        "trends": list(trends_by_isotope.values())
    }
