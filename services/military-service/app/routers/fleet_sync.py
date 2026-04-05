"""Fleet Sync Router -- ESI live fleet sync endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Cookie
from pydantic import BaseModel

from app.services.auth import get_current_user, require_permission
from app.services import fleet_sync as sync_service

router = APIRouter(prefix="/fleet", tags=["Fleet Sync"])


class SyncStartRequest(BaseModel):
    """Request body for starting fleet ESI sync."""
    esi_fleet_id: int
    fc_character_id: int


@router.post("/{op_id}/sync/start")
async def start_sync(
    op_id: int,
    req: SyncStartRequest,
    session: Optional[str] = Cookie(None),
):
    """Start ESI auto-sync for a fleet operation.

    Begins background polling of ESI /fleets/{fleet_id}/members/ every 60s.
    Creates snapshots and updates participation records automatically.
    Requires fleet.manage permission.
    """
    user = await get_current_user(session)
    require_permission(user, "fleet.manage")

    try:
        started = await sync_service.start_sync(op_id, req.esi_fleet_id, req.fc_character_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not started:
        raise HTTPException(status_code=400, detail="Sync already active for this operation")

    return {"syncing": True, "operation_id": op_id}


@router.post("/{op_id}/sync/stop")
async def stop_sync(
    op_id: int,
    session: Optional[str] = Cookie(None),
):
    """Stop ESI auto-sync for a fleet operation.

    Cancels the background polling task and marks sync as inactive.
    Requires fleet.manage permission.
    """
    user = await get_current_user(session)
    require_permission(user, "fleet.manage")

    await sync_service.stop_sync(op_id)
    return {"syncing": False, "operation_id": op_id}


@router.get("/{op_id}/sync/status")
async def sync_status(
    op_id: int,
    session: Optional[str] = Cookie(None),
):
    """Get current ESI sync status for a fleet operation.

    Returns sync state including last sync time, error count, and snapshot count.
    Requires fleet.view permission.
    """
    user = await get_current_user(session)
    require_permission(user, "fleet.view")

    return sync_service.get_sync_status(op_id)
