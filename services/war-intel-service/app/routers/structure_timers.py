"""
Structure Timer Router - Track reinforcement and anchoring timers.

Combines ESI sovereignty data with manual intel for comprehensive timer tracking.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import Field

from app.models.base import CamelModel
from app.database import db_cursor

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# Models
# ==============================================================================

class TimerCreate(CamelModel):
    """Create a new structure timer."""
    structure_name: str = Field(..., description="Name of the structure")
    category: str = Field(..., description="Category: tcurfc, ihub, poco, pos, ansiblex, cyno_beacon, cyno_jammer")
    system_id: int = Field(..., description="Solar system ID")
    timer_type: str = Field(..., description="Timer type: armor, hull, anchoring, unanchoring, online")
    timer_end: datetime = Field(..., description="When the timer exits (vulnerability window end)")

    # Optional fields
    structure_id: Optional[int] = None
    structure_type_id: Optional[int] = None
    owner_alliance_id: Optional[int] = None
    owner_alliance_name: Optional[str] = None
    owner_corporation_id: Optional[int] = None
    owner_corporation_name: Optional[str] = None
    reported_by: Optional[str] = None
    notes: Optional[str] = None


class TimerUpdate(CamelModel):
    """Update an existing timer."""
    timer_end: Optional[datetime] = None
    result: Optional[str] = None  # defended, destroyed, repaired, captured
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class TimerResponse(CamelModel):
    """Timer response model."""
    id: int
    structure_id: Optional[int]
    structure_name: str
    category: str
    system_id: int
    system_name: Optional[str]
    region_name: Optional[str]
    owner_alliance_name: Optional[str]
    timer_type: str
    timer_end: datetime
    hours_until: float
    urgency: str
    cyno_jammed: bool
    is_active: bool
    result: Optional[str]
    source: str
    notes: Optional[str]


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get("/upcoming")
def get_upcoming_timers(
    hours: int = Query(72, description="Hours to look ahead"),
    category: Optional[str] = Query(None, description="Filter by category"),
    region_id: Optional[int] = Query(None, description="Filter by region"),
    alliance_id: Optional[int] = Query(None, description="Filter by owner alliance")
):
    """Get all upcoming structure timers."""
    with db_cursor() as cur:
        query = """
            SELECT
                st.id,
                st.structure_id,
                st.structure_name,
                st.category::text,
                st.system_id,
                sr.solar_system_name as system_name,
                sr.region_name,
                st.owner_alliance_id,
                st.owner_alliance_name,
                st.timer_type::text,
                st.timer_end,
                EXTRACT(EPOCH FROM (st.timer_end - NOW())) / 3600 as hours_until,
                CASE
                    WHEN st.timer_end - NOW() < INTERVAL '1 hour' THEN 'critical'
                    WHEN st.timer_end - NOW() < INTERVAL '3 hours' THEN 'urgent'
                    WHEN st.timer_end - NOW() < INTERVAL '24 hours' THEN 'upcoming'
                    ELSE 'planned'
                END as urgency,
                CASE WHEN cj.solar_system_id IS NOT NULL THEN TRUE ELSE FALSE END as cyno_jammed,
                st.is_active,
                st.result,
                st.source,
                st.notes
            FROM structure_timers st
            LEFT JOIN system_region_map sr ON st.system_id = sr.solar_system_id
            LEFT JOIN intel_cyno_jammers cj ON st.system_id = cj.solar_system_id
            WHERE st.is_active = TRUE
              AND st.timer_end > NOW()
              AND st.timer_end < NOW() + INTERVAL '%s hours'
        """
        params = [hours]

        if category:
            query += " AND st.category = %s::structure_category"
            params.append(category)
        if region_id:
            query += " AND sr.region_id = %s"
            params.append(region_id)
        if alliance_id:
            query += " AND st.owner_alliance_id = %s"
            params.append(alliance_id)

        query += " ORDER BY st.timer_end ASC"

        cur.execute(query, params)
        rows = cur.fetchall()

    timers = []
    for row in rows:
        timers.append({
            "id": row['id'],
            "structure_id": row['structure_id'],
            "structure_name": row['structure_name'],
            "category": row['category'],
            "system_id": row['system_id'],
            "system_name": row['system_name'],
            "region_name": row['region_name'],
            "owner_alliance_id": row['owner_alliance_id'],
            "owner_alliance_name": row['owner_alliance_name'],
            "timer_type": row['timer_type'],
            "timer_end": row['timer_end'].isoformat(),
            "hours_until": round(row['hours_until'], 2),
            "urgency": row['urgency'],
            "cyno_jammed": row['cyno_jammed'],
            "is_active": row['is_active'],
            "result": row['result'],
            "source": row['source'],
            "notes": row['notes']
        })

    # Group by urgency for summary
    summary = {
        "critical": len([t for t in timers if t['urgency'] == 'critical']),
        "urgent": len([t for t in timers if t['urgency'] == 'urgent']),
        "upcoming": len([t for t in timers if t['urgency'] == 'upcoming']),
        "planned": len([t for t in timers if t['urgency'] == 'planned']),
        "total": len(timers)
    }

    return {
        "summary": summary,
        "timers": timers
    }


@router.post("/")
def create_timer(timer: TimerCreate):
    """Create a new structure timer."""
    # Get system info
    with db_cursor() as cur:
        cur.execute("""
            SELECT solar_system_name, region_id, region_name
            FROM system_region_map
            WHERE solar_system_id = %s
        """, (timer.system_id,))
        system = cur.fetchone()

        if not system:
            raise HTTPException(status_code=404, detail=f"System {timer.system_id} not found")

        # Calculate timer start (assume 15-minute window for now)
        timer_start = timer.timer_end - timedelta(minutes=15)

        cur.execute("""
            INSERT INTO structure_timers (
                structure_id, structure_name, structure_type_id, category,
                system_id, system_name, region_id, region_name,
                owner_alliance_id, owner_alliance_name,
                owner_corporation_id, owner_corporation_name,
                timer_type, timer_start, timer_end,
                source, reported_by, notes
            ) VALUES (
                %s, %s, %s, %s::structure_category,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s::structure_timer_type, %s, %s,
                'manual', %s, %s
            ) RETURNING id
        """, (
            timer.structure_id, timer.structure_name, timer.structure_type_id, timer.category,
            timer.system_id, system['solar_system_name'], system['region_id'], system['region_name'],
            timer.owner_alliance_id, timer.owner_alliance_name,
            timer.owner_corporation_id, timer.owner_corporation_name,
            timer.timer_type, timer_start, timer.timer_end,
            timer.reported_by, timer.notes
        ))

        timer_id = cur.fetchone()['id']

    return {
        "id": timer_id,
        "message": "Timer created successfully",
        "system_name": system['solar_system_name'],
        "region_name": system['region_name']
    }


@router.get("/{timer_id}")
def get_timer(timer_id: int):
    """Get a specific timer by ID."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                st.*,
                EXTRACT(EPOCH FROM (st.timer_end - NOW())) / 3600 as hours_until,
                CASE
                    WHEN st.timer_end - NOW() < INTERVAL '1 hour' THEN 'critical'
                    WHEN st.timer_end - NOW() < INTERVAL '3 hours' THEN 'urgent'
                    WHEN st.timer_end - NOW() < INTERVAL '24 hours' THEN 'upcoming'
                    ELSE 'planned'
                END as urgency,
                CASE WHEN cj.solar_system_id IS NOT NULL THEN TRUE ELSE FALSE END as cyno_jammed
            FROM structure_timers st
            LEFT JOIN intel_cyno_jammers cj ON st.system_id = cj.solar_system_id
            WHERE st.id = %s
        """, (timer_id,))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Timer not found")

    return {
        "id": row['id'],
        "structure_id": row['structure_id'],
        "structure_name": row['structure_name'],
        "category": row['category'],
        "system_id": row['system_id'],
        "system_name": row['system_name'],
        "region_name": row['region_name'],
        "owner_alliance_id": row['owner_alliance_id'],
        "owner_alliance_name": row['owner_alliance_name'],
        "timer_type": row['timer_type'],
        "timer_start": row['timer_start'].isoformat() if row['timer_start'] else None,
        "timer_end": row['timer_end'].isoformat(),
        "hours_until": round(row['hours_until'], 2),
        "urgency": row['urgency'],
        "cyno_jammed": row['cyno_jammed'],
        "is_active": row['is_active'],
        "result": row['result'],
        "source": row['source'],
        "reported_by": row['reported_by'],
        "notes": row['notes'],
        "created_at": row['created_at'].isoformat(),
        "updated_at": row['updated_at'].isoformat()
    }


@router.patch("/{timer_id}")
def update_timer(timer_id: int, update: TimerUpdate):
    """Update an existing timer."""
    updates = []
    params = []

    if update.timer_end is not None:
        updates.append("timer_end = %s")
        params.append(update.timer_end)
    if update.result is not None:
        updates.append("result = %s")
        params.append(update.result)
        # Auto-deactivate if result is set
        updates.append("is_active = FALSE")
    if update.is_active is not None:
        updates.append("is_active = %s")
        params.append(update.is_active)
    if update.notes is not None:
        updates.append("notes = %s")
        params.append(update.notes)

    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")

    updates.append("updated_at = NOW()")
    params.append(timer_id)

    with db_cursor() as cur:
        cur.execute(f"""
            UPDATE structure_timers
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id
        """, params)

        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Timer not found")

    return {"message": "Timer updated", "id": timer_id}


@router.delete("/{timer_id}")
def delete_timer(timer_id: int):
    """Delete a timer."""
    with db_cursor() as cur:
        cur.execute("DELETE FROM structure_timers WHERE id = %s RETURNING id", (timer_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Timer not found")

    return {"message": "Timer deleted", "id": timer_id}


@router.get("/system/{system_id}")
def get_system_timers(system_id: int):
    """Get all timers for a specific system."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                st.*,
                EXTRACT(EPOCH FROM (st.timer_end - NOW())) / 3600 as hours_until,
                CASE WHEN cj.solar_system_id IS NOT NULL THEN TRUE ELSE FALSE END as cyno_jammed
            FROM structure_timers st
            LEFT JOIN intel_cyno_jammers cj ON st.system_id = cj.solar_system_id
            WHERE st.system_id = %s
              AND st.is_active = TRUE
            ORDER BY st.timer_end ASC
        """, (system_id,))
        rows = cur.fetchall()

    return {
        "system_id": system_id,
        "timers": [{
            "id": row['id'],
            "structure_name": row['structure_name'],
            "category": row['category'],
            "timer_type": row['timer_type'],
            "timer_end": row['timer_end'].isoformat(),
            "hours_until": round(row['hours_until'], 2),
            "cyno_jammed": row['cyno_jammed']
        } for row in rows]
    }


@router.post("/expire-old")
def expire_old_timers():
    """Expire timers that are past due without a result."""
    with db_cursor() as cur:
        cur.execute("""
            UPDATE structure_timers
            SET state = 'expired', is_active = FALSE,
                last_state_change = NOW(), updated_at = NOW()
            WHERE is_active = TRUE
              AND timer_end < NOW() - INTERVAL '2 hours'
              AND result IS NULL
            RETURNING id
        """)
        expired = cur.fetchall()

    return {"expired_count": len(expired), "timer_ids": [r["id"] for r in expired]}


@router.post("/{timer_id}/transition")
def transition_timer_state(
    timer_id: int,
    new_state: str = Query(..., regex="^(reinforced|vulnerable|active|completed|expired)$"),
):
    """Transition a timer to a new state."""
    with db_cursor() as cur:
        cur.execute("""
            UPDATE structure_timers
            SET state = %s, last_state_change = NOW(), updated_at = NOW(),
                is_active = CASE WHEN %s IN ('completed', 'expired') THEN FALSE ELSE TRUE END
            WHERE id = %s
            RETURNING id, state
        """, (new_state, new_state, timer_id))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Timer not found")
    return {"timer_id": row["id"], "state": row["state"]}


@router.get("/stats/summary")
def get_timer_stats():
    """Get overall timer statistics."""
    with db_cursor() as cur:
        # Active timers by category
        cur.execute("""
            SELECT
                category::text,
                COUNT(*) as count
            FROM structure_timers
            WHERE is_active = TRUE AND timer_end > NOW()
            GROUP BY category
        """)
        by_category = {row['category']: row['count'] for row in cur.fetchall()}

        # Active timers by urgency
        cur.execute("""
            SELECT
                CASE
                    WHEN timer_end - NOW() < INTERVAL '1 hour' THEN 'critical'
                    WHEN timer_end - NOW() < INTERVAL '3 hours' THEN 'urgent'
                    WHEN timer_end - NOW() < INTERVAL '24 hours' THEN 'upcoming'
                    ELSE 'planned'
                END as urgency,
                COUNT(*) as count
            FROM structure_timers
            WHERE is_active = TRUE AND timer_end > NOW()
            GROUP BY urgency
        """)
        by_urgency = {row['urgency']: row['count'] for row in cur.fetchall()}

        # Recent results (last 7 days)
        cur.execute("""
            SELECT result, COUNT(*) as count
            FROM structure_timers
            WHERE result IS NOT NULL
              AND updated_at > NOW() - INTERVAL '7 days'
            GROUP BY result
        """)
        recent_results = {row['result']: row['count'] for row in cur.fetchall()}

    return {
        "active_timers": {
            "by_category": by_category,
            "by_urgency": by_urgency,
            "total": sum(by_urgency.values())
        },
        "recent_results": recent_results
    }
