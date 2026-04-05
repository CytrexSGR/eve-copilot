"""Corporation Timeline Endpoints - Optimized for Overview."""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Query
from datetime import datetime, timezone

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/corporation/{corp_id}/timeline")
@handle_endpoint_errors()
def get_corporation_timeline(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """
    Get lightweight kill/death timeline (OPTIMIZED - uses hourly_stats).

    Returns only timeline data without expensive ship/enemy/damage analysis.
    Perfect for CombinedTimelineCard component.

    Uses pre-aggregated corporation_hourly_stats for consistent + fast queries.
    Unified data source with Offensive/Defensive Stats endpoints.
    """
    with db_cursor() as cur:
        # Get daily aggregated kills/deaths from hourly_stats (pre-aggregated)
        cur.execute("""
            SELECT
                DATE(hour_bucket) as day,
                SUM(kills)::INT as kills,
                SUM(deaths)::INT as deaths,
                MAX(active_pilots) as active_pilots
            FROM corporation_hourly_stats
            WHERE corporation_id = %s
              AND hour_bucket >= NOW() - make_interval(days => %s::INT)
            GROUP BY DATE(hour_bucket)
            ORDER BY DATE(hour_bucket)
        """, (corp_id, days))

        timeline = []
        for row in cur.fetchall():
            timeline.append({
                "day": row["day"].isoformat() if row["day"] else None,
                "kills": row["kills"] or 0,
                "deaths": row["deaths"] or 0,
                "active_pilots": row["active_pilots"] or 0
            })

        # Calculate summary stats
        total_kills = sum(t["kills"] for t in timeline)
        total_deaths = sum(t["deaths"] for t in timeline)
        efficiency = round((total_kills / (total_kills + total_deaths)) * 100, 1) if (total_kills + total_deaths) > 0 else 0

        return {
            "corporation_id": corp_id,
            "period_days": days,
            "timeline": timeline,
            "summary": {
                "total_kills": total_kills,
                "total_deaths": total_deaths,
                "efficiency": efficiency,
                "avg_daily_kills": round(total_kills / max(days, 1), 1),
                "avg_daily_deaths": round(total_deaths / max(days, 1), 1)
            }
        }
