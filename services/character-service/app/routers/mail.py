"""EVE Mail reader: ESI passthrough with label support."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Cookie, Query
import httpx

from app.config import settings
from app.services.auth_client import AuthClient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Mail"])

ESI_BASE = settings.esi_base_url
auth_client = AuthClient()


def _validate_session(session: Optional[str]) -> dict:
    """Validate session by calling auth-service."""
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                f"{settings.auth_service_url}/api/auth/public/account",
                cookies={"session": session},
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid session")
            return resp.json()
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Auth service unavailable")


def _get_esi_token(character_id: int) -> str:
    """Get ESI access token for a character."""
    token = auth_client.get_valid_token(character_id)
    if not token:
        raise HTTPException(status_code=401, detail=f"No valid token for character {character_id}")
    return token


def _check_character_access(account: dict, character_id: int):
    """Ensure the character belongs to the authenticated account."""
    char_ids = [c["character_id"] for c in account.get("characters", [])]
    if character_id not in char_ids:
        raise HTTPException(status_code=403, detail="Character not in your account")


async def _resolve_names(ids: list[int]) -> dict[int, str]:
    """Resolve EVE entity IDs to names via ESI."""
    if not ids:
        return {}
    unique_ids = list(set(ids))
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{ESI_BASE}/universe/names/",
                json=unique_ids,
            )
            if resp.status_code == 200:
                return {e["id"]: e["name"] for e in resp.json()}
    except Exception:
        pass
    return {}


@router.get("/mail/{character_id}")
async def get_mail_headers(
    character_id: int,
    session: Optional[str] = Cookie(None),
    last_mail_id: Optional[int] = Query(None),
    labels: Optional[int] = Query(None),
):
    """Get mail headers for a character (50 per page, ESI passthrough)."""
    account = _validate_session(session)
    _check_character_access(account, character_id)
    token = _get_esi_token(character_id)

    params: dict = {}
    if last_mail_id:
        params["last_mail_id"] = last_mail_id
    if labels is not None:
        params["labels"] = labels

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{ESI_BASE}/characters/{character_id}/mail/",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="ESI mail request failed")
        mails = resp.json()

    # Resolve sender names
    sender_ids = [m.get("from") for m in mails if m.get("from")]
    names = await _resolve_names(sender_ids)

    results = []
    for m in mails:
        results.append({
            "mail_id": m.get("mail_id"),
            "subject": m.get("subject", "(no subject)"),
            "from_id": m.get("from"),
            "from_name": names.get(m.get("from"), f"ID {m.get('from')}"),
            "timestamp": m.get("timestamp"),
            "labels": m.get("labels", []),
            "is_read": m.get("is_read", True),
            "recipients": m.get("recipients", []),
        })

    return {"mails": results, "count": len(results)}


@router.get("/mail/{character_id}/{mail_id}")
async def get_mail_body(
    character_id: int,
    mail_id: int,
    session: Optional[str] = Cookie(None),
):
    """Get a single mail with body."""
    account = _validate_session(session)
    _check_character_access(account, character_id)
    token = _get_esi_token(character_id)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{ESI_BASE}/characters/{character_id}/mail/{mail_id}/",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="ESI mail request failed")
        mail = resp.json()

    # Resolve names
    ids_to_resolve = []
    if mail.get("from"):
        ids_to_resolve.append(mail["from"])
    for r in mail.get("recipients", []):
        if r.get("recipient_id"):
            ids_to_resolve.append(r["recipient_id"])
    names = await _resolve_names(ids_to_resolve)

    return {
        "mail_id": mail_id,
        "subject": mail.get("subject", "(no subject)"),
        "from_id": mail.get("from"),
        "from_name": names.get(mail.get("from"), f"ID {mail.get('from')}"),
        "body": mail.get("body", ""),
        "timestamp": mail.get("timestamp"),
        "labels": mail.get("labels", []),
        "is_read": mail.get("read", True),
        "recipients": [
            {
                "recipient_id": r.get("recipient_id"),
                "recipient_name": names.get(r.get("recipient_id"), f"ID {r.get('recipient_id')}"),
                "recipient_type": r.get("recipient_type"),
            }
            for r in mail.get("recipients", [])
        ],
    }


@router.get("/mail/{character_id}/labels")
async def get_mail_labels(
    character_id: int,
    session: Optional[str] = Cookie(None),
):
    """Get mail labels with unread counts."""
    account = _validate_session(session)
    _check_character_access(account, character_id)
    token = _get_esi_token(character_id)

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{ESI_BASE}/characters/{character_id}/mail/labels/",
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail="ESI labels request failed")
        data = resp.json()

    total_unread = data.get("total_unread_count", 0)
    labels = []
    for label in data.get("labels", []):
        labels.append({
            "label_id": label.get("label_id"),
            "name": label.get("name", "Unknown"),
            "color": label.get("color"),
            "unread_count": label.get("unread_count", 0),
        })

    return {"labels": labels, "total_unread": total_unread}
