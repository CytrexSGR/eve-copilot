"""Auth helper -- validates session cookie and checks fleet/ops permissions.

Calls auth-service /api/auth/public/account to validate the session
and retrieve the user's role. Permission checks are done locally
against the fleet/ops permission matrix.
"""

import logging
import os
from typing import Optional

import httpx
from fastapi import HTTPException, Cookie

logger = logging.getLogger(__name__)

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8000")

# Fleet/ops permission matrix (mirrors auth-service org_store.py)
FLEET_PERMISSIONS = {
    "fleet.create": ["admin", "officer", "fleet_commander"],
    "fleet.manage": ["admin", "officer", "fleet_commander"],
    "fleet.view":   ["admin", "officer", "fleet_commander", "member"],
    "ops.create":   ["admin", "officer", "fleet_commander"],
    "ops.manage":   ["admin", "officer", "fleet_commander"],
}


async def get_current_user(session: Optional[str] = Cookie(None)) -> dict:
    """Validate session cookie via auth-service.

    Returns dict with: account_id, primary_character_id, primary_character_name,
    corporation_id, alliance_id, role, tier.
    Raises 401 if session is missing or invalid.
    """
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"{AUTH_SERVICE_URL}/api/auth/public/account",
                cookies={"session": session},
            )
    except httpx.RequestError as exc:
        logger.error(f"Auth service unreachable: {exc}")
        raise HTTPException(status_code=503, detail="Auth service unavailable")

    if r.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    if r.status_code != 200:
        logger.warning(f"Auth service returned {r.status_code}: {r.text[:200]}")
        raise HTTPException(status_code=502, detail="Auth service error")

    return r.json()


def require_permission(user: dict, permission: str) -> None:
    """Check if user's role grants the required permission. Raises 403 if not."""
    role = user.get("role", "member")
    allowed_roles = FLEET_PERMISSIONS.get(permission, [])
    if role not in allowed_roles:
        raise HTTPException(
            status_code=403,
            detail=f"Missing permission: {permission} (role={role})",
        )
