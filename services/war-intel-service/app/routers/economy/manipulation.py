"""
Market Manipulation Alerts endpoint for war economy intelligence.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
import logging

from fastapi import APIRouter, Query

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/economy", tags=["War Economy"])


@router.get("/manipulation")
@handle_endpoint_errors()
def get_manipulation_alerts(
    region_id: int = Query(..., description="Region ID"),
    hours: int = Query(24, ge=1, le=168, description="Hours of historical data")
) -> Dict[str, Any]:
    """
    Get recent market manipulation alerts based on Z-score analysis.

    Detects unusual price/volume patterns that may indicate market manipulation.
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    with db_cursor() as cur:
        cur.execute("""
            SELECT
                wem.type_id,
                wem.type_name,
                wem.region_id,
                wem.current_price,
                wem.baseline_price,
                wem.price_change_percent,
                wem.current_volume,
                wem.baseline_volume,
                wem.volume_change_percent,
                wem.z_score,
                wem.severity,
                wem.manipulation_type,
                wem.detected_at
            FROM war_economy_manipulation_alerts wem
            WHERE wem.region_id = %s
              AND wem.detected_at >= %s
              AND wem.status = 'new'
            ORDER BY wem.z_score DESC, wem.detected_at DESC
        """, (region_id, cutoff))

        rows = cur.fetchall()

    alerts = []
    for row in rows:
        alerts.append({
            "type_id": row['type_id'],
            "type_name": row['type_name'],
            "region_id": row['region_id'],
            "current_price": float(row['current_price']) if row['current_price'] else 0,
            "baseline_price": float(row['baseline_price']) if row['baseline_price'] else 0,
            "price_change_percent": float(row['price_change_percent']) if row['price_change_percent'] else 0,
            "current_volume": row['current_volume'] or 0,
            "baseline_volume": row['baseline_volume'] or 0,
            "volume_change_percent": float(row['volume_change_percent']) if row['volume_change_percent'] else 0,
            "z_score": float(row['z_score']) if row['z_score'] else 0,
            "severity": row['severity'],
            "manipulation_type": row['manipulation_type'],
            "detected_at": row['detected_at'].isoformat() if row['detected_at'] else None
        })

    return {
        "region_id": region_id,
        "hours": hours,
        "count": len(alerts),
        "alerts": alerts
    }
