"""
Supercapital Construction Timers endpoints for war economy intelligence.
"""

from datetime import date
from typing import Optional, Dict, Any
import logging

from fastapi import APIRouter, Body, Query

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/economy", tags=["War Economy"])


@router.get("/supercap-timers")
@handle_endpoint_errors()
def get_supercap_timers(
    region_id: Optional[int] = Query(None, description="Filter by region")
) -> Dict[str, Any]:
    """
    Get active supercapital construction timers.

    Returns list of construction timers with strike window recommendations.
    Intel is manually entered by Fleet Commanders.
    """
    with db_cursor() as cur:
        query = """
            SELECT
                west.id,
                west.solar_system_id,
                ss."solarSystemName" as system_name,
                reg."regionName" as region_name,
                west.ship_type_id,
                it."typeName" as ship_name,
                west.alliance_id,
                anc.alliance_name,
                west.build_start_date,
                west.estimated_completion_date,
                west.status,
                west.confidence_level,
                west.intel_source,
                west.notes,
                west.reported_by,
                west.created_at,
                west.updated_at
            FROM war_economy_supercap_timers west
            JOIN "mapSolarSystems" ss ON west.solar_system_id = ss."solarSystemID"
            JOIN "mapRegions" reg ON ss."regionID" = reg."regionID"
            JOIN "invTypes" it ON west.ship_type_id = it."typeID"
            LEFT JOIN alliance_name_cache anc ON west.alliance_id = anc.alliance_id
            WHERE west.status = 'active'
        """
        params = []

        if region_id:
            query += " AND ss.\"regionID\" = %s"
            params.append(region_id)

        query += " ORDER BY west.estimated_completion_date ASC"

        cur.execute(query, params)
        rows = cur.fetchall()

    timers = []
    now = date.today()

    for row in rows:
        completion = row['estimated_completion_date']
        days_remaining = (completion - now).days if completion else 0
        hours_remaining = days_remaining * 24

        # Calculate strike window
        if days_remaining <= 3:
            strike_window = "URGENT: ≤3 days remaining"
            alert_level = "critical"
        elif days_remaining <= 7:
            strike_window = "HIGH: 4-7 days remaining"
            alert_level = "high"
        elif days_remaining <= 14:
            strike_window = "MEDIUM: 8-14 days remaining"
            alert_level = "medium"
        else:
            strike_window = f"LOW: {days_remaining} days remaining"
            alert_level = "low"

        timers.append({
            "id": row['id'],
            "ship_type_id": row['ship_type_id'],
            "ship_name": row['ship_name'],
            "solar_system_id": row['solar_system_id'],
            "system_name": row['system_name'],
            "region_name": row['region_name'],
            "alliance_id": row['alliance_id'],
            "alliance_name": row['alliance_name'] or "Unknown",
            "build_start_date": row['build_start_date'].isoformat() if row['build_start_date'] else None,
            "estimated_completion_date": completion.isoformat() if completion else None,
            "days_remaining": max(0, days_remaining),
            "hours_remaining": max(0, hours_remaining),
            "strike_window": strike_window,
            "alert_level": alert_level,
            "confidence_level": row['confidence_level'],
            "intel_source": row['intel_source'],
            "notes": row['notes'],
            "status": row['status']
        })

    return {
        "count": len(timers),
        "timers": timers
    }


@router.post("/supercap-timers")
@handle_endpoint_errors()
def add_supercap_timer(
    solar_system_id: int = Body(..., embed=True),
    ship_type_id: int = Body(..., embed=True),
    build_start_date: str = Body(..., embed=True),
    estimated_completion_date: str = Body(..., embed=True),
    alliance_id: Optional[int] = Body(None, embed=True),
    confidence_level: str = Body("unconfirmed", embed=True),
    intel_source: Optional[str] = Body(None, embed=True),
    notes: Optional[str] = Body(None, embed=True),
    reported_by: Optional[str] = Body(None, embed=True)
) -> Dict[str, Any]:
    """
    Add new supercapital construction timer.

    Requires manual intel input from Fleet Commanders or scouts.
    """
    build_date = date.fromisoformat(build_start_date)
    completion_date = date.fromisoformat(estimated_completion_date)

    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO war_economy_supercap_timers
                (solar_system_id, ship_type_id, alliance_id, build_start_date,
                 estimated_completion_date, confidence_level, intel_source, notes, reported_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (solar_system_id, ship_type_id, alliance_id, build_date,
              completion_date, confidence_level, intel_source, notes, reported_by))

        timer_id = cur.fetchone()['id']

    return {"timer_id": timer_id, "message": "Timer added successfully"}


@router.patch("/supercap-timers/{timer_id}")
@handle_endpoint_errors()
def update_supercap_timer(
    timer_id: int,
    status: Optional[str] = Body(None, embed=True),
    estimated_completion_date: Optional[str] = Body(None, embed=True),
    confidence_level: Optional[str] = Body(None, embed=True),
    notes: Optional[str] = Body(None, embed=True)
) -> Dict[str, Any]:
    """Update supercapital timer details."""
    updates = []
    params = []

    if status:
        updates.append("status = %s")
        params.append(status)
    if estimated_completion_date:
        updates.append("estimated_completion_date = %s")
        params.append(date.fromisoformat(estimated_completion_date))
    if confidence_level:
        updates.append("confidence_level = %s")
        params.append(confidence_level)
    if notes:
        updates.append("notes = %s")
        params.append(notes)

    if not updates:
        return {"message": "No updates provided"}

    updates.append("updated_at = NOW()")
    params.append(timer_id)

    with db_cursor() as cur:
        cur.execute(f"""
            UPDATE war_economy_supercap_timers
            SET {', '.join(updates)}
            WHERE id = %s
        """, params)

    return {"message": "Timer updated successfully"}
