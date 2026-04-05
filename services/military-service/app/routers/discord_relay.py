"""Discord Relay Configuration — Manage webhook notification relays.

CRUD for Discord relay configs that determine which events get forwarded
to which Discord channels via webhooks. Includes a test endpoint to
verify webhook connectivity.
"""

import logging
from typing import Optional
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Body, HTTPException, Path, Query
from pydantic import Field

from app.models.base import CamelModel
from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()

VALID_NOTIFY_TYPES = {
    'timer_created', 'timer_expiring', 'battle_started',
    'structure_attack', 'high_value_kill',
}


# =============================================================================
# Models
# =============================================================================

class RelayCreate(CamelModel):
    name: str = Field(..., max_length=200)
    webhook_url: str = Field(..., description="Discord webhook URL")
    filter_regions: list[int] = Field(default_factory=list)
    filter_alliances: list[int] = Field(default_factory=list)
    notify_types: list[str] = Field(
        default_factory=lambda: ['timer_created', 'battle_started', 'high_value_kill'],
    )
    ping_role_id: Optional[str] = None
    min_isk_threshold: float = 0


class RelayUpdate(CamelModel):
    name: Optional[str] = None
    webhook_url: Optional[str] = None
    filter_regions: Optional[list[int]] = None
    filter_alliances: Optional[list[int]] = None
    notify_types: Optional[list[str]] = None
    ping_role_id: Optional[str] = None
    is_active: Optional[bool] = None
    min_isk_threshold: Optional[float] = None


class RelayResponse(CamelModel):
    id: int
    name: str
    webhook_url: str
    filter_regions: list[int]
    filter_alliances: list[int]
    notify_types: list[str]
    ping_role_id: Optional[str]
    is_active: bool
    min_isk_threshold: float
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/discord/relays")
@handle_endpoint_errors()
def list_relays(active_only: bool = Query(False)):
    """List all Discord relay configurations."""
    with db_cursor() as cur:
        where = "WHERE is_active = TRUE" if active_only else ""
        cur.execute(f"""
            SELECT id, name, webhook_url, filter_regions, filter_alliances,
                   notify_types, ping_role_id, is_active, min_isk_threshold,
                   created_at, updated_at
            FROM discord_relay_configs
            {where}
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
    return [dict(r) for r in rows]


@router.post("/discord/relays", status_code=201)
@handle_endpoint_errors()
def create_relay(req: RelayCreate = Body(...)):
    """Create a new Discord relay configuration."""
    # Validate notify_types
    invalid = set(req.notify_types) - VALID_NOTIFY_TYPES
    if invalid:
        raise ValueError(f"Invalid notify_types: {invalid}. Valid: {VALID_NOTIFY_TYPES}")

    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO discord_relay_configs
                (name, webhook_url, filter_regions, filter_alliances,
                 notify_types, ping_role_id, min_isk_threshold)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, name, webhook_url, filter_regions, filter_alliances,
                      notify_types, ping_role_id, is_active, min_isk_threshold,
                      created_at, updated_at
        """, (
            req.name, req.webhook_url,
            req.filter_regions, req.filter_alliances,
            req.notify_types, req.ping_role_id,
            req.min_isk_threshold,
        ))
        row = cur.fetchone()
    return dict(row)


@router.put("/discord/relays/{relay_id}")
@handle_endpoint_errors()
def update_relay(relay_id: int = Path(...), req: RelayUpdate = Body(...)):
    """Update an existing Discord relay configuration."""
    updates = []
    params = []

    if req.name is not None:
        updates.append("name = %s")
        params.append(req.name)
    if req.webhook_url is not None:
        updates.append("webhook_url = %s")
        params.append(req.webhook_url)
    if req.filter_regions is not None:
        updates.append("filter_regions = %s")
        params.append(req.filter_regions)
    if req.filter_alliances is not None:
        updates.append("filter_alliances = %s")
        params.append(req.filter_alliances)
    if req.notify_types is not None:
        invalid = set(req.notify_types) - VALID_NOTIFY_TYPES
        if invalid:
            raise ValueError(f"Invalid notify_types: {invalid}")
        updates.append("notify_types = %s")
        params.append(req.notify_types)
    if req.ping_role_id is not None:
        updates.append("ping_role_id = %s")
        params.append(req.ping_role_id)
    if req.is_active is not None:
        updates.append("is_active = %s")
        params.append(req.is_active)
    if req.min_isk_threshold is not None:
        updates.append("min_isk_threshold = %s")
        params.append(req.min_isk_threshold)

    if not updates:
        raise ValueError("No fields to update")

    updates.append("updated_at = NOW()")
    params.append(relay_id)

    with db_cursor() as cur:
        cur.execute(f"""
            UPDATE discord_relay_configs
            SET {', '.join(updates)}
            WHERE id = %s
            RETURNING id, name, webhook_url, filter_regions, filter_alliances,
                      notify_types, ping_role_id, is_active, min_isk_threshold,
                      created_at, updated_at
        """, params)
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Relay not found")
    return dict(row)


@router.delete("/discord/relays/{relay_id}")
@handle_endpoint_errors()
def deactivate_relay(relay_id: int = Path(...)):
    """Deactivate a Discord relay (soft delete)."""
    with db_cursor() as cur:
        cur.execute("""
            UPDATE discord_relay_configs
            SET is_active = FALSE, updated_at = NOW()
            WHERE id = %s
            RETURNING id, name, is_active
        """, (relay_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Relay not found")
    return {"message": f"Relay '{row['name']}' deactivated", "id": row['id']}


@router.post("/discord/relays/test/{relay_id}")
@handle_endpoint_errors()
def test_relay(relay_id: int = Path(...)):
    """Send a test message to a Discord relay webhook."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT id, name, webhook_url, notify_types
            FROM discord_relay_configs
            WHERE id = %s
        """, (relay_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Relay not found")

    embed = {
        "embeds": [{
            "title": "EVE Co-Pilot — Relay Test",
            "description": (
                f"Relay **{row['name']}** is connected.\n"
                f"Notify types: {', '.join(row['notify_types'])}"
            ),
            "color": 0x00FF88,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "footer": {"text": "EVE Co-Pilot Military Module"},
        }]
    }

    try:
        resp = httpx.post(row['webhook_url'], json=embed, timeout=10.0)
        if resp.status_code == 204:
            return {"success": True, "message": "Test message sent successfully"}
        return {
            "success": False,
            "message": f"Discord returned status {resp.status_code}",
            "detail": resp.text[:500],
        }
    except httpx.RequestError as e:
        return {"success": False, "message": f"Connection failed: {str(e)}"}
