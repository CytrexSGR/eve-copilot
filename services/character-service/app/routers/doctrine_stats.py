"""Doctrine Engine REST API.

Endpoints for Dogma-powered doctrine stats, pilot readiness,
killmail compliance, fleet BOM generation, fleet readiness aggregation,
and skill plan export.
"""

import logging
from typing import List, Optional
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.services.doctrine_engine import DoctrineEngine
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Helpers ---

def _to_roman(num: int) -> str:
    """Convert integer 1-5 to Roman numeral."""
    return {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V"}.get(num, str(num))


# --- Request / Response models ---

class ComplianceRequest(BaseModel):
    doctrine_id: int
    killmail_items: list  # [{type_id: int, flag: int}]


class BomItem(BaseModel):
    type_id: int
    type_name: str
    quantity: int


# --- Existing endpoints ---

@router.get(
    "/{doctrine_id}/stats",
    summary="Get Dogma-powered doctrine stats",
)
def get_doctrine_stats(
    request: Request,
    doctrine_id: int,
    character_id: Optional[int] = Query(None),
):
    engine = DoctrineEngine(request.app.state.db, request.app.state.redis)
    try:
        return engine.calculate_doctrine_stats(doctrine_id, character_id=character_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{doctrine_id}/readiness/{character_id}",
    summary="Check pilot readiness for a doctrine",
)
def get_doctrine_readiness(
    request: Request,
    doctrine_id: int,
    character_id: int,
):
    engine = DoctrineEngine(request.app.state.db, request.app.state.redis)
    try:
        return engine.check_readiness(doctrine_id, character_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/compliance",
    summary="Check killmail compliance against a doctrine",
)
def check_compliance(
    request: Request,
    req: ComplianceRequest,
):
    engine = DoctrineEngine(request.app.state.db, request.app.state.redis)
    try:
        return engine.check_compliance(req.doctrine_id, req.killmail_items)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{doctrine_id}/bom",
    summary="Generate Bill of Materials for a doctrine",
    response_model=List[BomItem],
)
def get_doctrine_bom(
    request: Request,
    doctrine_id: int,
    quantity: int = Query(1, ge=1, le=1000),
):
    engine = DoctrineEngine(request.app.state.db, request.app.state.redis)
    try:
        return engine.generate_bom(doctrine_id, quantity=quantity)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- New endpoints: Fleet Readiness & Skill Plan Export ---

@router.get(
    "/{doctrine_id}/fleet-readiness/{corp_id}",
    summary="Aggregate fleet readiness across all corp members",
)
def get_fleet_readiness(
    request: Request,
    doctrine_id: int,
    corp_id: int,
):
    """Aggregate readiness for all primary characters in a corporation.

    Returns per-pilot readiness status and overall corp readiness percentage.
    A pilot is 'partial' if dps_ratio > 0.5 but can_fly is false.
    """
    engine = DoctrineEngine(request.app.state.db, request.app.state.redis)
    db = request.app.state.db

    # 1. Get all primary characters in the corp
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT pa.primary_character_id AS character_id,
                   pa.primary_character_name AS character_name
            FROM platform_accounts pa
            WHERE pa.corporation_id = %s
              AND pa.primary_character_id IS NOT NULL
            ORDER BY pa.primary_character_name
            """,
            (corp_id,),
        )
        corp_pilots = cur.fetchall()

    if not corp_pilots:
        raise HTTPException(
            status_code=404,
            detail=f"No pilots found for corporation {corp_id}",
        )

    # 2. Check readiness for each pilot (graceful per-pilot error handling)
    pilots = []
    for pilot in corp_pilots:
        try:
            readiness = engine.check_readiness(doctrine_id, pilot["character_id"])

            dps_ratio = readiness["dps_ratio"]
            can_fly = readiness["can_fly"]
            missing_count = len(readiness["missing_skills"])

            if can_fly:
                status = "can_fly"
            elif dps_ratio > 0.5:
                status = "partial"
            else:
                status = "cannot_fly"

            pilots.append({
                "character_id": pilot["character_id"],
                "character_name": pilot["character_name"],
                "status": status,
                "dps_ratio": dps_ratio,
                "ehp_ratio": readiness["ehp_ratio"],
                "missing_skills_count": missing_count,
            })
        except Exception as exc:
            logger.warning(
                "Readiness check failed for character %s: %s",
                pilot["character_id"], exc,
            )
            pilots.append({
                "character_id": pilot["character_id"],
                "character_name": pilot["character_name"],
                "status": "cannot_fly",
                "dps_ratio": 0.0,
                "ehp_ratio": 0.0,
                "missing_skills_count": -1,
            })

    # 3. Sort by dps_ratio descending
    pilots.sort(key=lambda p: p["dps_ratio"], reverse=True)

    # 4. Aggregate counts
    total = len(pilots)
    can_fly_count = sum(1 for p in pilots if p["status"] == "can_fly")
    partial_count = sum(1 for p in pilots if p["status"] == "partial")
    cannot_fly_count = sum(1 for p in pilots if p["status"] == "cannot_fly")
    readiness_pct = round((can_fly_count / total) * 100, 1) if total > 0 else 0.0

    return {
        "doctrine_id": doctrine_id,
        "corporation_id": corp_id,
        "total_pilots": total,
        "can_fly": can_fly_count,
        "partial": partial_count,
        "cannot_fly": cannot_fly_count,
        "readiness_pct": readiness_pct,
        "pilots": pilots,
    }


@router.get(
    "/{doctrine_id}/skill-plan/{character_id}",
    summary="Generate exportable skill plan from missing skills",
)
def get_skill_plan(
    request: Request,
    doctrine_id: int,
    character_id: int,
    format: str = Query("text", pattern="^(text|evemon)$"),
):
    """Generate an exportable skill plan for a character's missing doctrine skills.

    Supports two formats:
    - text: plain text list with Roman numeral levels
    - evemon: XML plan compatible with EVEMon
    """
    engine = DoctrineEngine(request.app.state.db, request.app.state.redis)

    try:
        readiness = engine.check_readiness(doctrine_id, character_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    missing_skills = readiness["missing_skills"]

    if format == "text":
        lines = []
        for s in missing_skills:
            lines.append(f"{s.skill_name} {_to_roman(s.required_level)}")
        content = "\n".join(lines)
    else:
        # EVEMon XML format
        plan = Element("plan", attrib={
            "name": f"Doctrine {doctrine_id} - Character {character_id}",
            "revision": "1",
        })
        for s in missing_skills:
            SubElement(plan, "entry", attrib={
                "skillID": str(s.skill_id),
                "skill": s.skill_name,
                "level": str(s.required_level),
                "priority": "3",
                "type": "Prerequisite",
            })
        content = tostring(plan, encoding="unicode")

    return {
        "doctrine_id": doctrine_id,
        "character_id": character_id,
        "format": format,
        "content": content,
        "skill_count": len(missing_skills),
    }
