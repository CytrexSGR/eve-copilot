"""Corp Diplomacy: Standings, Contacts, Alumni management."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Cookie, Query
from pydantic import BaseModel

from app.database import db_cursor
from app.services.jwt_service import JWTService
from app.repository.org_store import OrgRepository
from app.repository.tier_store import TierRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/public/org/diplomacy", tags=["Diplomacy"])

org_repo = OrgRepository()
tier_repo = TierRepository()


# --- Schemas ---

class StandingEntry(BaseModel):
    contact_id: int
    contact_name: Optional[str] = None
    contact_type: str  # character, corporation, alliance, faction
    standing: float = 0.0
    is_blocked: bool = False
    is_watched: bool = False
    labels: Optional[list] = None


class AlumniMember(BaseModel):
    character_id: int
    character_name: str
    left_at: Optional[str] = None
    destination_corp_id: Optional[int] = None
    destination_corp_name: Optional[str] = None
    note: str = ""
    noted_by_name: Optional[str] = None
    created_at: Optional[str] = None


class AlumniNote(BaseModel):
    character_id: int
    character_name: str
    note: str = ""


class ContactsSummary(BaseModel):
    total: int = 0
    positive: int = 0
    negative: int = 0
    neutral: int = 0
    watched: int = 0
    blocked: int = 0
    contacts: list[StandingEntry] = []


class StandingsSummary(BaseModel):
    total: int = 0
    entries: list[StandingEntry] = []


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
    """Extract corp_id, character_id, character_name, role from JWT payload."""
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
    """Check permission, raise 403 if denied."""
    if not org_repo.check_permission(corp_id, role, permission):
        raise HTTPException(
            status_code=403,
            detail=f"Missing permission: {permission}",
        )


# --- Endpoints ---

@router.get("/standings")
def get_corp_standings(
    session: Optional[str] = Cookie(None),
    limit: int = Query(200, le=500),
    offset: int = Query(0, ge=0),
    contact_type: Optional[str] = Query(None),
):
    """Aggregierte Standings aller Corp-Member (aus character_contacts mit standing != 0)."""
    payload = _get_session_payload(session)
    corp_id, character_id, character_name, role = _get_corp_and_role(payload)
    _check_permission(corp_id, role, "members.view")

    with db_cursor() as cur:
        filters = ["pa.corporation_id = %s", "cc.standing != 0"]
        params: list = [corp_id]
        if contact_type:
            filters.append("cc.contact_type = %s")
            params.append(contact_type)

        where = " AND ".join(filters)
        cur.execute(f"""
            SELECT cc.contact_id, cc.contact_type,
                   AVG(cc.standing) as avg_standing,
                   COUNT(*) as member_count,
                   bool_or(cc.is_watched) as anyone_watching,
                   bool_or(cc.is_blocked) as anyone_blocked
            FROM character_contacts cc
            JOIN platform_accounts pa ON pa.primary_character_id = cc.character_id
            WHERE {where}
            GROUP BY cc.contact_id, cc.contact_type
            ORDER BY AVG(cc.standing) DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])
        rows = cur.fetchall()

    entries = []
    for r in rows:
        entries.append(StandingEntry(
            contact_id=r["contact_id"],
            contact_type=r["contact_type"],
            standing=round(float(r["avg_standing"]), 2),
            is_watched=r["anyone_watching"] or False,
            is_blocked=r["anyone_blocked"] or False,
        ))

    return StandingsSummary(total=len(entries), entries=entries)


@router.get("/contacts")
def get_corp_contacts(
    session: Optional[str] = Cookie(None),
    limit: int = Query(200, le=500),
    offset: int = Query(0, ge=0),
    contact_type: Optional[str] = Query(None),
    min_standing: Optional[float] = Query(None),
    max_standing: Optional[float] = Query(None),
    watched_only: bool = Query(False),
):
    """Detaillierte Contact-Liste der Corp (aggregiert ueber alle Member)."""
    payload = _get_session_payload(session)
    corp_id, character_id, character_name, role = _get_corp_and_role(payload)
    _check_permission(corp_id, role, "members.view")

    with db_cursor() as cur:
        filters = ["pa.corporation_id = %s"]
        params: list = [corp_id]
        if contact_type:
            filters.append("cc.contact_type = %s")
            params.append(contact_type)
        if min_standing is not None:
            filters.append("cc.standing >= %s")
            params.append(min_standing)
        if max_standing is not None:
            filters.append("cc.standing <= %s")
            params.append(max_standing)
        if watched_only:
            filters.append("cc.is_watched = true")

        where = " AND ".join(filters)
        cur.execute(f"""
            SELECT cc.contact_id, cc.contact_type,
                   AVG(cc.standing) as avg_standing,
                   COUNT(*) as member_count,
                   bool_or(cc.is_watched) as anyone_watching,
                   bool_or(cc.is_blocked) as anyone_blocked
            FROM character_contacts cc
            JOIN platform_accounts pa ON pa.primary_character_id = cc.character_id
            WHERE {where}
            GROUP BY cc.contact_id, cc.contact_type
            ORDER BY AVG(cc.standing) DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])
        rows = cur.fetchall()

        # Get total count
        cur.execute(f"""
            SELECT COUNT(DISTINCT (cc.contact_id, cc.contact_type))
            FROM character_contacts cc
            JOIN platform_accounts pa ON pa.primary_character_id = cc.character_id
            WHERE {where}
        """, params)
        total = cur.fetchone()["count"]

    contacts = []
    for r in rows:
        contacts.append(StandingEntry(
            contact_id=r["contact_id"],
            contact_type=r["contact_type"],
            standing=round(float(r["avg_standing"]), 2),
            is_watched=r["anyone_watching"] or False,
            is_blocked=r["anyone_blocked"] or False,
        ))

    positive = sum(1 for c in contacts if c.standing > 0)
    negative = sum(1 for c in contacts if c.standing < 0)
    neutral = sum(1 for c in contacts if c.standing == 0)
    watched = sum(1 for c in contacts if c.is_watched)
    blocked = sum(1 for c in contacts if c.is_blocked)

    return ContactsSummary(
        total=total,
        positive=positive,
        negative=negative,
        neutral=neutral,
        watched=watched,
        blocked=blocked,
        contacts=contacts,
    )


@router.get("/alumni")
def get_alumni(
    session: Optional[str] = Cookie(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
):
    """Ex-Member die die Corp verlassen haben (aus character_corporation_history)."""
    payload = _get_session_payload(session)
    corp_id, character_id, character_name, role = _get_corp_and_role(payload)
    _check_permission(corp_id, role, "hr.view")

    with db_cursor() as cur:
        cur.execute("""
            SELECT DISTINCT ON (cch.character_id)
                cch.character_id,
                c.name as character_name,
                cch.valid_to as left_at,
                cch_current.corporation_id as current_corp_id,
                corp_current.name as current_corp_name,
                an.note,
                an.noted_by_name,
                an.created_at as note_created_at
            FROM character_corporation_history cch
            JOIN characters c ON c.character_id = cch.character_id
            LEFT JOIN character_corporation_history cch_current
                ON cch_current.character_id = cch.character_id AND cch_current.is_current = true
            LEFT JOIN corporations corp_current
                ON corp_current.corporation_id = cch_current.corporation_id
            LEFT JOIN alumni_notes an
                ON an.corporation_id = %s AND an.character_id = cch.character_id
            WHERE cch.corporation_id = %s
              AND cch.is_current = false
              AND cch.valid_to IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM character_corporation_history h2
                  WHERE h2.character_id = cch.character_id
                    AND h2.corporation_id = %s
                    AND h2.is_current = true
              )
            ORDER BY cch.character_id, cch.valid_to DESC
            LIMIT %s OFFSET %s
        """, (corp_id, corp_id, corp_id, limit, offset))
        rows = cur.fetchall()

    alumni = []
    for r in rows:
        alumni.append(AlumniMember(
            character_id=r["character_id"],
            character_name=r["character_name"] or f"Character {r['character_id']}",
            left_at=r["left_at"].isoformat() if r["left_at"] else None,
            destination_corp_id=r["current_corp_id"],
            destination_corp_name=r["current_corp_name"],
            note=r["note"] or "",
            noted_by_name=r["noted_by_name"],
            created_at=r["note_created_at"].isoformat() if r["note_created_at"] else None,
        ))

    return {"alumni": alumni, "total": len(alumni)}


@router.post("/alumni/note")
def upsert_alumni_note(
    data: AlumniNote,
    session: Optional[str] = Cookie(None),
):
    """Notiz zu einem Ex-Member hinzufuegen oder aktualisieren."""
    payload = _get_session_payload(session)
    corp_id, character_id, character_name, role = _get_corp_and_role(payload)
    _check_permission(corp_id, role, "hr.manage")

    with db_cursor() as cur:
        cur.execute("""
            INSERT INTO alumni_notes (corporation_id, character_id, character_name, note, noted_by_character_id, noted_by_name)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (corporation_id, character_id)
            DO UPDATE SET note = EXCLUDED.note, noted_by_character_id = EXCLUDED.noted_by_character_id,
                          noted_by_name = EXCLUDED.noted_by_name, updated_at = NOW()
            RETURNING id
        """, (corp_id, data.character_id, data.character_name, data.note, character_id, character_name))
        result = cur.fetchone()

    return {"success": True, "id": result["id"]}
