"""Bulletin Board: Corp announcements with priority and pinning."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Cookie, Query
from pydantic import BaseModel

from app.database import db_cursor
from app.services.jwt_service import JWTService
from app.repository.org_store import OrgRepository
from app.repository.tier_store import TierRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/public/org/bulletins", tags=["Bulletin"])

org_repo = OrgRepository()
tier_repo = TierRepository()


# --- Schemas ---

class BulletinCreate(BaseModel):
    title: str
    body: str
    priority: str = "normal"  # urgent, normal, low
    is_pinned: bool = False
    expires_at: Optional[str] = None


class BulletinUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    priority: Optional[str] = None
    is_pinned: Optional[bool] = None
    expires_at: Optional[str] = None


# --- Helpers ---

def _get_session_payload(session: Optional[str]) -> dict:
    if not session:
        raise HTTPException(status_code=401, detail="Not authenticated")
    jwt_svc = JWTService()
    payload = jwt_svc.validate_token(session)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return payload


def _get_corp_and_role(payload: dict) -> tuple:
    corp_id = payload.get("corp_id")
    character_id = int(payload.get("sub", 0))
    character_name = payload.get("name", "Unknown")
    if not corp_id:
        raise HTTPException(status_code=400, detail="No corporation associated")
    role = tier_repo.get_role(corp_id, character_id)
    if not role:
        role = "member"
    return corp_id, character_id, character_name, role


def _check_permission(corp_id: int, role: str, permission: str):
    if not org_repo.check_permission(corp_id, role, permission):
        raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")


# --- Endpoints ---

@router.get("")
def get_bulletins(
    session: Optional[str] = Cookie(None),
    limit: int = Query(20, le=50),
    offset: int = Query(0, ge=0),
):
    """Get active bulletins for the current corporation."""
    payload = _get_session_payload(session)
    corp_id, character_id, character_name, role = _get_corp_and_role(payload)
    _check_permission(corp_id, role, "members.view")

    with db_cursor() as cur:
        cur.execute("""
            SELECT id, title, body, priority, is_pinned,
                   author_character_id, author_name, expires_at,
                   created_at, updated_at
            FROM bulletin_posts
            WHERE corporation_id = %s
              AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY is_pinned DESC, created_at DESC
            LIMIT %s OFFSET %s
        """, (corp_id, limit, offset))
        rows = cur.fetchall()

        cur.execute("""
            SELECT COUNT(*) as cnt FROM bulletin_posts
            WHERE corporation_id = %s
              AND (expires_at IS NULL OR expires_at > NOW())
        """, (corp_id,))
        total = cur.fetchone()["cnt"]

    bulletins = []
    for r in rows:
        bulletins.append({
            "id": r["id"],
            "title": r["title"],
            "body": r["body"],
            "priority": r["priority"],
            "is_pinned": r["is_pinned"],
            "author_character_id": r["author_character_id"],
            "author_name": r["author_name"],
            "expires_at": r["expires_at"].isoformat() if r["expires_at"] else None,
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        })

    return {"bulletins": bulletins, "total": total}


@router.post("")
def create_bulletin(
    data: BulletinCreate,
    session: Optional[str] = Cookie(None),
):
    """Create a new bulletin (admin/officer only)."""
    payload = _get_session_payload(session)
    corp_id, character_id, character_name, role = _get_corp_and_role(payload)
    _check_permission(corp_id, role, "settings.manage")

    if data.priority not in ("urgent", "normal", "low"):
        raise HTTPException(status_code=400, detail="Invalid priority. Must be: urgent, normal, low")

    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO bulletin_posts (corporation_id, title, body, priority, is_pinned, author_character_id, author_name, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (corp_id, data.title, data.body, data.priority, data.is_pinned, character_id, character_name, data.expires_at))
        result = cur.fetchone()

    return {"success": True, "id": result["id"]}


@router.put("/{bulletin_id}")
def update_bulletin(
    bulletin_id: int,
    data: BulletinUpdate,
    session: Optional[str] = Cookie(None),
):
    """Update a bulletin (admin/officer only)."""
    payload = _get_session_payload(session)
    corp_id, character_id, character_name, role = _get_corp_and_role(payload)
    _check_permission(corp_id, role, "settings.manage")

    updates = []
    params = []
    if data.title is not None:
        updates.append("title = %s")
        params.append(data.title)
    if data.body is not None:
        updates.append("body = %s")
        params.append(data.body)
    if data.priority is not None:
        if data.priority not in ("urgent", "normal", "low"):
            raise HTTPException(status_code=400, detail="Invalid priority")
        updates.append("priority = %s")
        params.append(data.priority)
    if data.is_pinned is not None:
        updates.append("is_pinned = %s")
        params.append(data.is_pinned)
    if data.expires_at is not None:
        updates.append("expires_at = %s")
        params.append(data.expires_at)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = NOW()")
    set_clause = ", ".join(updates)

    with db_cursor() as cur:
        cur.execute(
            f"UPDATE bulletin_posts SET {set_clause} WHERE id = %s AND corporation_id = %s RETURNING id",
            params + [bulletin_id, corp_id]
        )
        result = cur.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Bulletin not found")
    return {"success": True, "id": result["id"]}


@router.delete("/{bulletin_id}")
def delete_bulletin(
    bulletin_id: int,
    session: Optional[str] = Cookie(None),
):
    """Delete a bulletin (admin/officer only)."""
    payload = _get_session_payload(session)
    corp_id, character_id, character_name, role = _get_corp_and_role(payload)
    _check_permission(corp_id, role, "settings.manage")

    with db_cursor() as cur:
        cur.execute(
            "DELETE FROM bulletin_posts WHERE id = %s AND corporation_id = %s RETURNING id",
            (bulletin_id, corp_id)
        )
        result = cur.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Bulletin not found")
    return {"success": True}
