"""Fleet Operations & PAP Tracking -- Register fleets, record snapshots, calculate participation.

Supports the snapshot-based PAP model: periodic snapshots capture who is in fleet,
and participation_pct = pilot_snapshots / total_snapshots.

Migrated from war-intel-service to military-service.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Body, Cookie, HTTPException, Path, Query
from pydantic import Field

from app.models.base import CamelModel
from app.database import db_cursor, sde_cursor
from app.services.auth import get_current_user, require_permission
from app.services.discord import (
    notify_event, build_fleet_started_embed, build_fleet_closed_embed
)
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Helpers
# =============================================================================

def _enrich_ship_type_names(rows: list[dict]) -> list[dict]:
    """Look up ship type names from SDE for rows containing ship_type_id."""
    type_ids = {r["ship_type_id"] for r in rows if r.get("ship_type_id")}
    if not type_ids:
        return rows
    try:
        with sde_cursor() as cur:
            cur.execute(
                """SELECT "typeID", "typeName" FROM "invTypes" WHERE "typeID" = ANY(%s)""",
                (list(type_ids),),
            )
            name_map = {r["typeID"]: r["typeName"] for r in cur.fetchall()}
    except Exception:
        logger.warning("Could not look up ship type names from SDE", exc_info=True)
        name_map = {}
    for r in rows:
        r["ship_type_name"] = name_map.get(r.get("ship_type_id"))
    return rows


async def _get_user_or_none(session: Optional[str]) -> Optional[dict]:
    """Try to resolve the session user. Returns None if no session cookie."""
    if not session:
        return None
    try:
        return await get_current_user(session)
    except HTTPException:
        return None


# =============================================================================
# Models
# =============================================================================

class FleetRegisterRequest(CamelModel):
    fleet_name: str = Field(..., max_length=255)
    fc_character_id: Optional[int] = None
    fc_name: Optional[str] = None
    doctrine_id: Optional[int] = None
    notes: Optional[str] = None


class SnapshotMember(CamelModel):
    character_id: int
    character_name: Optional[str] = None
    ship_type_id: Optional[int] = None
    ship_name: Optional[str] = None
    solar_system_id: Optional[int] = None


class SnapshotRequest(CamelModel):
    members: list[SnapshotMember]


class FleetCloseRequest(CamelModel):
    notes: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/fleet/register", status_code=201)
@handle_endpoint_errors()
async def register_fleet(
    req: FleetRegisterRequest = Body(...),
    session: Optional[str] = Cookie(None),
):
    """Register a new fleet operation for PAP tracking."""
    user = await get_current_user(session)
    require_permission(user, "fleet.create")

    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO fleet_operations
                (fleet_name, fc_character_id, fc_name, doctrine_id, notes)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, fleet_name, fc_character_id, fc_name, doctrine_id,
                      start_time, is_active, notes, created_at
        """, (
            req.fleet_name, req.fc_character_id, req.fc_name,
            req.doctrine_id, req.notes,
        ))
        row = cur.fetchone()
    logger.info(f"Fleet operation registered: {row['id']} - {row['fleet_name']}")

    # Send Discord notification for fleet start
    try:
        embed = build_fleet_started_embed(row["fleet_name"], row.get("fc_name"))
        await notify_event("fleet_started", row["id"], user["corporation_id"], embed)
    except Exception:
        logger.warning("Failed to send fleet_started notification", exc_info=True)

    return dict(row)


@router.post("/fleet/{op_id}/snapshot")
@handle_endpoint_errors()
async def record_snapshot(
    op_id: int = Path(..., description="Fleet operation ID"),
    req: SnapshotRequest = Body(...),
    session: Optional[str] = Cookie(None),
):
    """Record a fleet snapshot -- captures current fleet composition."""
    user = await get_current_user(session)
    require_permission(user, "fleet.manage")

    with db_cursor() as cur:
        # Verify fleet exists and is active
        cur.execute(
            "SELECT id, is_active FROM fleet_operations WHERE id = %s",
            (op_id,),
        )
        fleet = cur.fetchone()
        if not fleet:
            raise HTTPException(status_code=404, detail="Fleet operation not found")
        if not fleet['is_active']:
            raise HTTPException(status_code=400, detail="Fleet operation is closed")

        # Store raw snapshot
        raw_data = [m.model_dump() for m in req.members]
        cur.execute("""
            INSERT INTO fleet_snapshots (operation_id, member_count, raw_data)
            VALUES (%s, %s, %s::jsonb)
            RETURNING id, snapshot_time
        """, (op_id, len(req.members), json.dumps(raw_data)))

        # Upsert participation records
        for member in req.members:
            cur.execute("""
                INSERT INTO fleet_participation
                    (operation_id, character_id, character_name,
                     ship_type_id, ship_name, solar_system_id,
                     first_seen, last_seen, snapshot_count)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW(), 1)
                ON CONFLICT (operation_id, character_id) DO UPDATE SET
                    character_name = COALESCE(EXCLUDED.character_name, fleet_participation.character_name),
                    ship_type_id = COALESCE(EXCLUDED.ship_type_id, fleet_participation.ship_type_id),
                    ship_name = COALESCE(EXCLUDED.ship_name, fleet_participation.ship_name),
                    solar_system_id = COALESCE(EXCLUDED.solar_system_id, fleet_participation.solar_system_id),
                    last_seen = NOW(),
                    snapshot_count = fleet_participation.snapshot_count + 1
            """, (
                op_id, member.character_id, member.character_name,
                member.ship_type_id, member.ship_name, member.solar_system_id,
            ))

    return {
        "operation_id": op_id,
        "members_recorded": len(req.members),
        "message": "Snapshot recorded",
    }


@router.get("/fleet/{op_id}/status")
@handle_endpoint_errors()
async def fleet_status(
    op_id: int = Path(...),
    session: Optional[str] = Cookie(None),
):
    """Get current fleet composition and stats."""
    user = await get_current_user(session)
    require_permission(user, "fleet.view")

    with db_cursor() as cur:
        # Fleet info
        cur.execute("""
            SELECT id, fleet_name, fc_name, doctrine_id, start_time,
                   end_time, is_active, notes
            FROM fleet_operations WHERE id = %s
        """, (op_id,))
        fleet = cur.fetchone()
        if not fleet:
            raise HTTPException(status_code=404, detail="Fleet operation not found")

        # Snapshot count
        cur.execute(
            "SELECT COUNT(*) AS total FROM fleet_snapshots WHERE operation_id = %s",
            (op_id,),
        )
        snapshot_count = cur.fetchone()['total']

        # Current members (from participation)
        cur.execute("""
            SELECT character_id, character_name,
                   ship_type_id, ship_name, solar_system_id,
                   first_seen, last_seen, snapshot_count
            FROM fleet_participation
            WHERE operation_id = %s
            ORDER BY last_seen DESC
        """, (op_id,))
        members = [dict(r) for r in cur.fetchall()]

    # Enrich with ship type names from SDE
    members = _enrich_ship_type_names(members)

    return {
        "fleet": dict(fleet),
        "snapshot_count": snapshot_count,
        "member_count": len(members),
        "members": members,
    }


@router.get("/fleet/{op_id}/participation")
@handle_endpoint_errors()
async def fleet_participation(
    op_id: int = Path(...),
    session: Optional[str] = Cookie(None),
):
    """Get PAP report -- per-pilot participation percentages."""
    user = await get_current_user(session)
    require_permission(user, "fleet.view")

    with db_cursor() as cur:
        # Fleet info
        cur.execute("""
            SELECT id, fleet_name, fc_name, start_time, end_time, is_active
            FROM fleet_operations WHERE id = %s
        """, (op_id,))
        fleet = cur.fetchone()
        if not fleet:
            raise HTTPException(status_code=404, detail="Fleet operation not found")

        # Total snapshots for this fleet
        cur.execute(
            "SELECT COUNT(*) AS total FROM fleet_snapshots WHERE operation_id = %s",
            (op_id,),
        )
        total_snapshots = cur.fetchone()['total']

        # Per-pilot participation
        cur.execute("""
            SELECT character_id, character_name,
                   ship_type_id, ship_name,
                   first_seen, last_seen, snapshot_count
            FROM fleet_participation
            WHERE operation_id = %s
            ORDER BY snapshot_count DESC
        """, (op_id,))
        participants = []
        for row in cur.fetchall():
            r = dict(row)
            r['participation_pct'] = round(
                (r['snapshot_count'] / total_snapshots * 100) if total_snapshots > 0 else 0,
                1,
            )
            participants.append(r)

    # Enrich with ship type names from SDE
    participants = _enrich_ship_type_names(participants)

    return {
        "fleet": dict(fleet),
        "total_snapshots": total_snapshots,
        "total_participants": len(participants),
        "participants": participants,
    }


@router.post("/fleet/{op_id}/close")
@handle_endpoint_errors()
async def close_fleet(
    op_id: int = Path(...),
    req: FleetCloseRequest = Body(FleetCloseRequest()),
    session: Optional[str] = Cookie(None),
):
    """Close a fleet operation."""
    user = await get_current_user(session)
    require_permission(user, "fleet.manage")

    with db_cursor() as cur:
        updates = ["is_active = FALSE", "end_time = NOW()"]
        params = []
        if req.notes:
            updates.append("notes = COALESCE(notes || E'\\n', '') || %s")
            params.append(req.notes)
        params.append(op_id)

        cur.execute(f"""
            UPDATE fleet_operations
            SET {", ".join(updates)}
            WHERE id = %s AND is_active = TRUE
            RETURNING id, fleet_name, end_time
        """, params)
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Active fleet operation not found")

    logger.info(f"Fleet operation closed: {row['id']} - {row['fleet_name']}")

    # Send Discord notification for fleet close
    try:
        # Get pilot count and duration for the embed
        with db_cursor() as cur2:
            cur2.execute(
                "SELECT COUNT(DISTINCT character_id) AS total FROM fleet_participation WHERE operation_id = %s",
                (op_id,),
            )
            total_pilots = cur2.fetchone()["total"]

            cur2.execute(
                """SELECT EXTRACT(EPOCH FROM (end_time - start_time)) / 60 AS duration_min
                   FROM fleet_operations WHERE id = %s""",
                (op_id,),
            )
            dur_row = cur2.fetchone()
            duration_min = dur_row["duration_min"] if dur_row and dur_row["duration_min"] else 0

        embed = build_fleet_closed_embed(row["fleet_name"], total_pilots, duration_min)
        await notify_event("fleet_closed", op_id, user["corporation_id"], embed)
    except Exception:
        logger.warning("Failed to send fleet_closed notification", exc_info=True)

    return {"message": f"Fleet '{row['fleet_name']}' closed", **dict(row)}


@router.get("/fleet/active")
@handle_endpoint_errors()
async def list_active_fleets(session: Optional[str] = Cookie(None)):
    """List all active fleet operations."""
    user = await get_current_user(session)
    require_permission(user, "fleet.view")

    with db_cursor() as cur:
        cur.execute("""
            SELECT fo.id, fo.fleet_name, fo.fc_name, fo.doctrine_id,
                   fo.start_time, fo.notes,
                   COUNT(DISTINCT fp.character_id) AS member_count,
                   COUNT(DISTINCT fs.id) AS snapshot_count
            FROM fleet_operations fo
            LEFT JOIN fleet_participation fp ON fo.id = fp.operation_id
            LEFT JOIN fleet_snapshots fs ON fo.id = fs.operation_id
            WHERE fo.is_active = TRUE
            GROUP BY fo.id
            ORDER BY fo.start_time DESC
        """)
        return [dict(r) for r in cur.fetchall()]


@router.get("/fleet/history")
@handle_endpoint_errors()
async def fleet_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Optional[str] = Cookie(None),
):
    """List past fleet operations with summary stats."""
    user = await get_current_user(session)
    require_permission(user, "fleet.view")

    with db_cursor() as cur:
        cur.execute("""
            SELECT fo.id, fo.fleet_name, fo.fc_name, fo.doctrine_id,
                   fo.start_time, fo.end_time, fo.is_active,
                   COUNT(DISTINCT fp.character_id) AS total_participants,
                   COUNT(DISTINCT fs.id) AS total_snapshots,
                   EXTRACT(EPOCH FROM (COALESCE(fo.end_time, NOW()) - fo.start_time)) / 60
                       AS duration_minutes
            FROM fleet_operations fo
            LEFT JOIN fleet_participation fp ON fo.id = fp.operation_id
            LEFT JOIN fleet_snapshots fs ON fo.id = fs.operation_id
            GROUP BY fo.id
            ORDER BY fo.start_time DESC
            LIMIT %s OFFSET %s
        """, (limit, offset))
        return [dict(r) for r in cur.fetchall()]
