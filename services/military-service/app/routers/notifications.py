"""Notifications Config — Manage Discord webhook notification configs.

CRUD for per-corporation notification configs that control which
fleet/ops events get sent to which Discord channels.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, Body, Cookie, HTTPException, Path
from pydantic import BaseModel, Field

from app.database import db_cursor
from app.services.auth import get_current_user, require_permission

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_EVENT_TYPES = ["op_created", "op_reminder", "fleet_started", "fleet_closed"]


# =============================================================================
# Models
# =============================================================================

class NotificationConfigCreate(BaseModel):
    webhook_url: str = Field(..., description="Discord webhook URL")
    event_types: List[str] = Field(
        ..., description="List of event types to subscribe to"
    )
    ping_role: Optional[str] = Field(
        None, description="Discord role ID to ping (optional)"
    )


class NotificationConfigResponse(BaseModel):
    id: int
    corporation_id: int
    channel_type: str
    webhook_url: str
    event_types: List[str]
    ping_role: Optional[str]
    is_active: bool
    created_at: str


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/notifications")
async def list_notification_configs(
    session: Optional[str] = Cookie(None),
):
    """List all notification configs for the user's corporation."""
    user = await get_current_user(session)
    require_permission(user, "fleet.manage")
    corp_id = user["corporation_id"]

    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, corporation_id, channel_type, webhook_url,
                   event_types, ping_role, is_active, created_at
            FROM notification_configs
            WHERE corporation_id = %s
            ORDER BY created_at DESC
            """,
            (corp_id,),
        )
        rows = cur.fetchall()

    return {"configs": [dict(r) for r in rows], "total": len(rows)}


@router.post("/notifications", status_code=201)
async def create_notification_config(
    req: NotificationConfigCreate = Body(...),
    session: Optional[str] = Cookie(None),
):
    """Create a new notification config for the user's corporation."""
    user = await get_current_user(session)
    require_permission(user, "fleet.manage")
    corp_id = user["corporation_id"]

    # Validate event types
    invalid = set(req.event_types) - set(VALID_EVENT_TYPES)
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event types: {invalid}. Valid: {VALID_EVENT_TYPES}",
        )
    if not req.event_types:
        raise HTTPException(
            status_code=400,
            detail="At least one event type is required",
        )

    # Validate webhook URL format
    if not req.webhook_url.startswith("https://discord.com/api/webhooks/"):
        raise HTTPException(
            status_code=400,
            detail="Invalid Discord webhook URL format",
        )

    with db_cursor() as cur:
        cur.execute(
            """
            INSERT INTO notification_configs
                (corporation_id, webhook_url, event_types, ping_role)
            VALUES (%s, %s, %s, %s)
            RETURNING id, corporation_id, channel_type, webhook_url,
                      event_types, ping_role, is_active, created_at
            """,
            (corp_id, req.webhook_url, req.event_types, req.ping_role),
        )
        row = cur.fetchone()

    logger.info("Created notification config %s for corp %s", row["id"], corp_id)
    return dict(row)


@router.delete("/notifications/{config_id}")
async def deactivate_notification_config(
    config_id: int = Path(...),
    session: Optional[str] = Cookie(None),
):
    """Deactivate a notification config (soft-delete)."""
    user = await get_current_user(session)
    require_permission(user, "fleet.manage")
    corp_id = user["corporation_id"]

    with db_cursor() as cur:
        cur.execute(
            """
            UPDATE notification_configs
            SET is_active = FALSE
            WHERE id = %s AND corporation_id = %s
            RETURNING id
            """,
            (config_id, corp_id),
        )
        row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Notification config not found",
        )

    logger.info("Deactivated notification config %s for corp %s", config_id, corp_id)
    return {"deactivated": True, "config_id": config_id}
