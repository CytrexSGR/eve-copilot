"""Ops Calendar — Scheduled operations management."""
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Cookie
from pydantic import BaseModel

from app.database import db_cursor
from app.services.auth import get_current_user, require_permission
from app.services.discord import notify_event, build_op_created_embed

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ops", tags=["Ops Calendar"])


class OpCreate(BaseModel):
    title: str
    description: Optional[str] = None
    fc_character_id: int
    fc_name: str
    doctrine_id: Optional[int] = None
    doctrine_name: Optional[str] = None
    formup_system: Optional[str] = None
    formup_time: datetime
    op_type: str = "fleet"
    importance: str = "normal"
    max_pilots: Optional[int] = None


class OpUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    fc_character_id: Optional[int] = None
    fc_name: Optional[str] = None
    doctrine_id: Optional[int] = None
    doctrine_name: Optional[str] = None
    formup_system: Optional[str] = None
    formup_time: Optional[datetime] = None
    op_type: Optional[str] = None
    importance: Optional[str] = None
    max_pilots: Optional[int] = None


@router.get("")
async def list_ops(
    session: Optional[str] = Cookie(None),
    days_ahead: int = Query(7, ge=1, le=90),
    op_type: Optional[str] = None,
    include_cancelled: bool = False,
):
    """List scheduled operations."""
    user = await get_current_user(session)
    require_permission(user, "fleet.view")
    corp_id = user["corporation_id"]

    with db_cursor() as cur:
        sql = """
            SELECT * FROM scheduled_operations
            WHERE corporation_id = %s
              AND formup_time >= NOW()
              AND formup_time <= NOW() + INTERVAL '1 day' * %s
        """
        params = [corp_id, days_ahead]

        if not include_cancelled:
            sql += " AND is_cancelled = FALSE"
        if op_type:
            sql += " AND op_type = %s"
            params.append(op_type)

        sql += " ORDER BY formup_time ASC"
        cur.execute(sql, params)
        rows = cur.fetchall()

    return {"operations": [dict(r) for r in rows], "total": len(rows)}


@router.get("/{op_id}")
async def get_op(op_id: int, session: Optional[str] = Cookie(None)):
    """Get operation details."""
    user = await get_current_user(session)
    require_permission(user, "fleet.view")

    with db_cursor() as cur:
        cur.execute("SELECT * FROM scheduled_operations WHERE id = %s", (op_id,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, "Operation not found")
    return dict(row)


@router.post("", status_code=201)
async def create_op(req: OpCreate, session: Optional[str] = Cookie(None)):
    """Create a scheduled operation."""
    user = await get_current_user(session)
    require_permission(user, "ops.create")

    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO scheduled_operations
            (title, description, fc_character_id, fc_name, doctrine_id, doctrine_name,
             formup_system, formup_time, op_type, importance, max_pilots,
             created_by, corporation_id)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            RETURNING *
        """, (
            req.title, req.description, req.fc_character_id, req.fc_name,
            req.doctrine_id, req.doctrine_name, req.formup_system, req.formup_time,
            req.op_type, req.importance, req.max_pilots,
            user["character_id"], user["corporation_id"]
        ))
        row = cur.fetchone()

    # Send Discord notification for new op
    try:
        embed = build_op_created_embed(dict(row))
        await notify_event("op_created", row["id"], user["corporation_id"], embed)
    except Exception:
        logger.warning("Failed to send op_created notification", exc_info=True)

    return dict(row)


@router.put("/{op_id}")
async def update_op(op_id: int, req: OpUpdate, session: Optional[str] = Cookie(None)):
    """Update a scheduled operation."""
    user = await get_current_user(session)
    require_permission(user, "ops.manage")

    updates = {}
    for field in ["title", "description", "fc_character_id", "fc_name",
                  "doctrine_id", "doctrine_name", "formup_system", "formup_time",
                  "op_type", "importance", "max_pilots"]:
        val = getattr(req, field)
        if val is not None:
            updates[field] = val

    if not updates:
        raise HTTPException(400, "No fields to update")

    set_clause = ", ".join(f"{k} = %s" for k in updates.keys())
    values = list(updates.values()) + [op_id, user["corporation_id"]]

    with db_cursor() as cur:
        cur.execute(f"""
            UPDATE scheduled_operations SET {set_clause}
            WHERE id = %s AND corporation_id = %s
            RETURNING *
        """, values)
        row = cur.fetchone()

    if not row:
        raise HTTPException(404, "Operation not found")
    return dict(row)


@router.delete("/{op_id}")
async def cancel_op(op_id: int, session: Optional[str] = Cookie(None)):
    """Cancel a scheduled operation (soft-delete)."""
    user = await get_current_user(session)
    require_permission(user, "ops.manage")

    with db_cursor() as cur:
        cur.execute("""
            UPDATE scheduled_operations SET is_cancelled = TRUE
            WHERE id = %s AND corporation_id = %s
            RETURNING id
        """, (op_id, user["corporation_id"]))
        row = cur.fetchone()

    if not row:
        raise HTTPException(404, "Operation not found")
    return {"cancelled": True, "op_id": op_id}


@router.post("/{op_id}/start")
async def start_op(op_id: int, session: Optional[str] = Cookie(None)):
    """Start a scheduled operation — creates a fleet_operation and links it."""
    user = await get_current_user(session)
    require_permission(user, "fleet.create")

    with db_cursor() as cur:
        cur.execute("SELECT * FROM scheduled_operations WHERE id = %s", (op_id,))
        op = cur.fetchone()
        if not op:
            raise HTTPException(404, "Operation not found")
        if op["fleet_operation_id"]:
            raise HTTPException(400, "Operation already started")

        cur.execute("""
            INSERT INTO fleet_operations (fleet_name, fc_character_id, fc_name, doctrine_id, notes)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (op["title"], op["fc_character_id"], op["fc_name"],
              op["doctrine_id"], op["description"]))
        fleet_op = cur.fetchone()

        cur.execute("""
            UPDATE scheduled_operations SET fleet_operation_id = %s WHERE id = %s
        """, (fleet_op["id"], op_id))

    return {"fleet_operation_id": fleet_op["id"], "op_id": op_id}
