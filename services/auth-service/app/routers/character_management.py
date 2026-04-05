"""Character management endpoints: token health, primary switch, remove alt."""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Cookie

from app.database import db_cursor
from app.services.jwt_service import JWTService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/public", tags=["Character Management"])

# ESI scope groups for display
SCOPE_GROUPS = {
    "Skills": ["esi-skills.read_skills.v1", "esi-skills.read_skillqueue.v1"],
    "Wallet": ["esi-wallet.read_character_wallet.v1"],
    "Assets": ["esi-assets.read_assets.v1"],
    "Industry": ["esi-industry.read_character_jobs.v1", "esi-industry.read_character_mining.v1"],
    "Fittings": ["esi-fittings.read_fittings.v1", "esi-fittings.write_fittings.v1"],
    "Location": ["esi-location.read_location.v1", "esi-location.read_ship_type.v1", "esi-location.read_online.v1"],
    "Contacts": ["esi-characters.read_contacts.v1"],
    "Contracts": ["esi-contracts.read_character_contracts.v1"],
    "Mail": ["esi-mail.read_mail.v1"],
    "Clones": ["esi-clones.read_clones.v1", "esi-clones.read_implants.v1"],
    "Blueprints": ["esi-characters.read_blueprints.v1"],
    "Killmails": ["esi-killmails.read_killmails.v1"],
    "Corp Roles": ["esi-characters.read_corporation_roles.v1"],
}


def _get_session_payload(session: Optional[str]) -> dict:
    """Validate session cookie and return JWT payload."""
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    jwt_svc = JWTService()
    payload = jwt_svc.validate_token(session)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return payload


def _verify_character_ownership(account_id: int, character_id: int) -> dict:
    """Verify a character belongs to the given account. Returns the row."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT account_id FROM account_characters WHERE character_id = %s",
            (character_id,),
        )
        row = cur.fetchone()
    if not row or row["account_id"] != account_id:
        raise HTTPException(status_code=403, detail="Character does not belong to your account")
    return row


@router.get("/characters/{character_id}/token-health")
def get_token_health(character_id: int, session: Optional[str] = Cookie(None)):
    """Get ESI token health status for a character."""
    payload = _get_session_payload(session)
    account_id = payload.get("account_id")
    if not account_id:
        raise HTTPException(status_code=400, detail="Account not found in token")

    _verify_character_ownership(account_id, character_id)

    # Get token info
    with db_cursor() as cur:
        cur.execute(
            """SELECT character_id, character_name, expires_at, scopes, updated_at
               FROM character_tokens WHERE character_id = %s""",
            (character_id,),
        )
        token = cur.fetchone()

    if not token:
        return {
            "character_id": character_id,
            "is_valid": False,
            "status": "missing",
            "character_name": "",
            "scopes": [],
            "missing_scopes": [],
            "scope_groups": {},
            "expires_in_hours": 0,
            "last_refresh": None,
        }

    now = datetime.now(timezone.utc)
    expires_at = token["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    is_expired = expires_at < now
    hours_remaining = max(0, (expires_at - now).total_seconds() / 3600)
    granted = set(token["scopes"] or [])

    # Check scope consents
    with db_cursor() as cur:
        cur.execute(
            "SELECT granted_scopes, requested_scopes FROM character_scope_consents WHERE character_id = %s",
            (character_id,),
        )
        consents = cur.fetchone()

    requested = set(consents["requested_scopes"]) if consents else set()
    missing = list(requested - granted) if requested else []

    # Build scope group status
    scope_groups = {}
    for group_name, group_scopes in SCOPE_GROUPS.items():
        has_all = all(s in granted for s in group_scopes)
        has_any = any(s in granted for s in group_scopes)
        scope_groups[group_name] = "full" if has_all else ("partial" if has_any else "none")

    # Determine status
    if is_expired:
        status = "expired"
    elif missing:
        status = "incomplete"
    elif hours_remaining < 1:
        status = "expiring"
    else:
        status = "valid"

    return {
        "character_id": character_id,
        "character_name": token["character_name"],
        "is_valid": not is_expired,
        "status": status,
        "scopes": list(granted),
        "missing_scopes": missing,
        "scope_groups": scope_groups,
        "expires_in_hours": round(hours_remaining, 1),
        "last_refresh": token["updated_at"].isoformat() if token["updated_at"] else None,
    }


@router.put("/account/primary/{character_id}")
def set_primary_character(character_id: int, session: Optional[str] = Cookie(None)):
    """Set a linked character as the primary character for this account."""
    payload = _get_session_payload(session)
    account_id = payload.get("account_id")
    if not account_id:
        raise HTTPException(status_code=400, detail="Account not found in token")

    _verify_character_ownership(account_id, character_id)

    # Get character name
    with db_cursor() as cur:
        cur.execute(
            "SELECT character_name FROM account_characters WHERE character_id = %s AND account_id = %s",
            (character_id, account_id),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Character not found")

    character_name = row["character_name"]

    # Update primary
    with db_cursor() as cur:
        cur.execute(
            "UPDATE account_characters SET is_primary = false WHERE account_id = %s",
            (account_id,),
        )
        cur.execute(
            "UPDATE account_characters SET is_primary = true WHERE account_id = %s AND character_id = %s",
            (account_id, character_id),
        )
        cur.execute(
            "UPDATE platform_accounts SET primary_character_id = %s, primary_character_name = %s WHERE id = %s",
            (character_id, character_name, account_id),
        )

    logger.info(f"Account {account_id}: primary changed to {character_id} ({character_name})")
    return {"message": "Primary character updated", "character_id": character_id, "character_name": character_name}


@router.delete("/account/characters/{character_id}")
def remove_character(character_id: int, session: Optional[str] = Cookie(None)):
    """Remove an alt character from this account. Cannot remove primary."""
    payload = _get_session_payload(session)
    account_id = payload.get("account_id")
    if not account_id:
        raise HTTPException(status_code=400, detail="Account not found in token")

    _verify_character_ownership(account_id, character_id)

    # Check not primary
    with db_cursor() as cur:
        cur.execute(
            "SELECT is_primary FROM account_characters WHERE character_id = %s AND account_id = %s",
            (character_id, account_id),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Character not found")
    if row["is_primary"]:
        raise HTTPException(status_code=400, detail="Cannot remove the primary character. Set another character as primary first.")

    # Delete character link + tokens + scope consents
    with db_cursor() as cur:
        cur.execute("DELETE FROM account_characters WHERE account_id = %s AND character_id = %s", (account_id, character_id))
        cur.execute("DELETE FROM character_tokens WHERE character_id = %s", (character_id,))
        cur.execute("DELETE FROM character_scope_consents WHERE character_id = %s", (character_id,))

    logger.info(f"Account {account_id}: removed character {character_id}")
    return {"message": "Character removed"}
