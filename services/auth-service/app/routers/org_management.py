"""Organisation management endpoints: members, roles, permissions, audit."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Cookie, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.jwt_service import JWTService
from app.repository.org_store import OrgRepository, VALID_ROLES, ALL_PERMISSIONS
from app.repository.tier_store import TierRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/public/org", tags=["Org Management"])

org_repo = OrgRepository()
tier_repo = TierRepository()


# --- Pydantic models ---

class RoleUpdate(BaseModel):
    role: str


class PermissionUpdate(BaseModel):
    updates: list


# --- Helper functions ---

def _get_session_payload(session: Optional[str]) -> dict:
    """Validate session cookie and return JWT payload."""
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    jwt_svc = JWTService()
    payload = jwt_svc.validate_token(session)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return payload


def _get_corp_and_role(payload: dict) -> tuple:
    """Extract corp_id, character_id, role from JWT payload."""
    corp_id = payload.get("corp_id")
    character_id = int(payload.get("sub", 0))
    if not corp_id:
        raise HTTPException(status_code=400, detail="No corporation associated")
    role = tier_repo.get_role(corp_id, character_id)
    if not role:
        role = "member"
    return corp_id, character_id, role


def _check_permission(corp_id: int, role: str, permission: str):
    """Check permission, raise 403 if denied."""
    if not org_repo.check_permission(corp_id, role, permission):
        raise HTTPException(
            status_code=403,
            detail=f"Missing permission: {permission}",
        )


# --- Endpoints ---

@router.get("/overview")
def get_overview(session: Optional[str] = Cookie(None)):
    """Corp overview stats."""
    payload = _get_session_payload(session)
    corp_id, character_id, role = _get_corp_and_role(payload)
    _check_permission(corp_id, role, "members.view")
    return org_repo.get_overview(corp_id)


@router.get("/members")
def get_members(session: Optional[str] = Cookie(None)):
    """List all corp members."""
    payload = _get_session_payload(session)
    corp_id, character_id, role = _get_corp_and_role(payload)
    _check_permission(corp_id, role, "members.view")
    return org_repo.get_members(corp_id)


@router.put("/members/{target_character_id}/role")
def change_role(
    target_character_id: int,
    body: RoleUpdate,
    session: Optional[str] = Cookie(None),
):
    """Change a member's role."""
    payload = _get_session_payload(session)
    corp_id, character_id, role = _get_corp_and_role(payload)
    _check_permission(corp_id, role, "roles.manage")

    # Cannot change own role
    if target_character_id == character_id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    # Validate target role
    if body.role not in VALID_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}",
        )

    result = tier_repo.set_role(corp_id, target_character_id, body.role, character_id)

    # Audit log
    actor_name = payload.get("name", "Unknown")
    org_repo.log_action(
        corporation_id=corp_id,
        actor_character_id=character_id,
        actor_name=actor_name,
        action="role.change",
        target_type="character",
        target_id=target_character_id,
        details={"new_role": body.role},
    )

    logger.info(f"Corp {corp_id}: {actor_name} changed role of {target_character_id} to {body.role}")
    return {"message": "Role updated", "result": result}


@router.delete("/members/{target_character_id}")
def remove_member(
    target_character_id: int,
    session: Optional[str] = Cookie(None),
):
    """Remove a member from the corp platform."""
    payload = _get_session_payload(session)
    corp_id, character_id, role = _get_corp_and_role(payload)
    _check_permission(corp_id, role, "members.manage")

    # Cannot remove self
    if target_character_id == character_id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")

    tier_repo.remove_role(corp_id, target_character_id)

    # Audit log
    actor_name = payload.get("name", "Unknown")
    org_repo.log_action(
        corporation_id=corp_id,
        actor_character_id=character_id,
        actor_name=actor_name,
        action="member.remove",
        target_type="character",
        target_id=target_character_id,
    )

    logger.info(f"Corp {corp_id}: {actor_name} removed member {target_character_id}")
    return {"message": "Member removed"}


@router.get("/permissions")
def get_permissions(session: Optional[str] = Cookie(None)):
    """Get permission matrix. Auto-initializes defaults if empty."""
    payload = _get_session_payload(session)
    corp_id, character_id, role = _get_corp_and_role(payload)
    _check_permission(corp_id, role, "settings.manage")

    perms = org_repo.get_permissions(corp_id)
    if not perms:
        org_repo.init_default_permissions(corp_id)
        perms = org_repo.get_permissions(corp_id)

    return {"permissions": perms, "valid_roles": VALID_ROLES, "all_permissions": ALL_PERMISSIONS}


@router.put("/permissions")
def update_permissions(
    body: PermissionUpdate,
    session: Optional[str] = Cookie(None),
):
    """Update permission matrix."""
    payload = _get_session_payload(session)
    corp_id, character_id, role = _get_corp_and_role(payload)
    _check_permission(corp_id, role, "settings.manage")

    count = org_repo.update_permissions(corp_id, body.updates)

    # Audit log
    actor_name = payload.get("name", "Unknown")
    org_repo.log_action(
        corporation_id=corp_id,
        actor_character_id=character_id,
        actor_name=actor_name,
        action="permissions.update",
        target_type="permissions",
        details={"changes": len(body.updates)},
    )

    logger.info(f"Corp {corp_id}: {actor_name} updated {count} permissions")
    return {"message": f"{count} permissions updated"}


@router.get("/audit")
def get_audit_log(
    session: Optional[str] = Cookie(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None),
    actor_id: Optional[int] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """Get audit log with pagination and filters."""
    payload = _get_session_payload(session)
    corp_id, character_id, role = _get_corp_and_role(payload)
    _check_permission(corp_id, role, "audit.view")

    return org_repo.get_audit_log(
        corporation_id=corp_id,
        limit=limit,
        offset=offset,
        action_filter=action,
        actor_filter=actor_id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/audit/export")
def export_audit_csv(session: Optional[str] = Cookie(None)):
    """CSV export of audit log."""
    payload = _get_session_payload(session)
    corp_id, character_id, role = _get_corp_and_role(payload)
    _check_permission(corp_id, role, "audit.view")

    csv_content = org_repo.export_audit_csv(corp_id)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
    )
