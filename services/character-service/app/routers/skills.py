"""
Skills Browser API Router
Provides all skills from SDE for the skill browser UI.
Migrated from monolith to character-service.
"""

from fastapi import APIRouter, Query, HTTPException, Request
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from psycopg2.extras import RealDictCursor

router = APIRouter()

# Attribute ID to name mapping
ATTRIBUTE_MAP = {
    164: "charisma",
    165: "intelligence",
    166: "memory",
    167: "perception",
    168: "willpower",
}


class SkillInfo(BaseModel):
    type_id: int
    type_name: str
    description: str
    rank: int
    primary_attribute: str
    secondary_attribute: str
    trained_level: Optional[int] = None
    skillpoints: Optional[int] = None


class SkillGroup(BaseModel):
    group_id: int
    group_name: str
    skill_count: int
    skills: List[SkillInfo]


class SkillBrowserResponse(BaseModel):
    groups: List[SkillGroup]
    total_skills: int


def _get_character_skills(request: Request, character_id: int) -> Dict[int, Dict[str, int]]:
    """Get character skills as dict {skill_id: {level, skillpoints}}."""
    try:
        from app.services import CharacterService
        service = CharacterService(request.app.state.db, request.app.state.redis)
        result = service.get_skills(character_id)
        if not result:
            return {}
        return {
            s.skill_id: {
                "level": s.trained_level or s.level,
                "skillpoints": s.skillpoints
            }
            for s in result.skills
        }
    except Exception:
        return {}


@router.get("/browser", response_model=SkillBrowserResponse)
def get_skill_browser(
    request: Request,
    character_id: Optional[int] = Query(None, description="Character ID to include trained levels")
) -> SkillBrowserResponse:
    """
    Get all skills from SDE grouped by category.

    If character_id is provided, includes trained_level and skillpoints for each skill.
    """
    # Get character skills if provided
    char_skills = {}
    if character_id:
        char_skills = _get_character_skills(request, character_id)

    db = request.app.state.db
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # Get all skills with attributes
        # Note: published is smallint (1/0), not boolean
        cur.execute("""
            SELECT
                t."typeID" as type_id,
                t."typeName" as type_name,
                COALESCE(t."description", '') as description,
                g."groupID" as group_id,
                g."groupName" as group_name,
                COALESCE(rank.value, 1) as rank,
                COALESCE(primary_attr.value, 165) as primary_attribute,
                COALESCE(secondary_attr.value, 166) as secondary_attribute
            FROM "invTypes" t
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            LEFT JOIN (
                SELECT "typeID", COALESCE("valueInt", "valueFloat")::int as value
                FROM "dgmTypeAttributes" WHERE "attributeID" = 275
            ) rank ON rank."typeID" = t."typeID"
            LEFT JOIN (
                SELECT "typeID", COALESCE("valueInt", "valueFloat")::int as value
                FROM "dgmTypeAttributes" WHERE "attributeID" = 180
            ) primary_attr ON primary_attr."typeID" = t."typeID"
            LEFT JOIN (
                SELECT "typeID", COALESCE("valueInt", "valueFloat")::int as value
                FROM "dgmTypeAttributes" WHERE "attributeID" = 181
            ) secondary_attr ON secondary_attr."typeID" = t."typeID"
            WHERE g."categoryID" = 16
              AND t."published" = 1
              AND g."groupName" != 'Fake Skills'
            ORDER BY g."groupName", t."typeName"
        """)

        rows = cur.fetchall()

    # Group skills by category
    groups_dict: Dict[int, SkillGroup] = {}
    total_skills = 0

    for row in rows:
        group_id = row["group_id"]

        if group_id not in groups_dict:
            groups_dict[group_id] = SkillGroup(
                group_id=group_id,
                group_name=row["group_name"],
                skill_count=0,
                skills=[]
            )

        # Get trained info if character provided
        trained_level = None
        skillpoints = None
        if char_skills and row["type_id"] in char_skills:
            trained_level = char_skills[row["type_id"]]["level"]
            skillpoints = char_skills[row["type_id"]]["skillpoints"]

        skill = SkillInfo(
            type_id=row["type_id"],
            type_name=row["type_name"],
            description=row["description"][:500] if row["description"] else "",
            rank=row["rank"],
            primary_attribute=ATTRIBUTE_MAP.get(row["primary_attribute"], "perception"),
            secondary_attribute=ATTRIBUTE_MAP.get(row["secondary_attribute"], "willpower"),
            trained_level=trained_level,
            skillpoints=skillpoints,
        )

        groups_dict[group_id].skills.append(skill)
        groups_dict[group_id].skill_count += 1
        total_skills += 1

    # Sort groups by name
    groups = sorted(groups_dict.values(), key=lambda g: g.group_name)

    return SkillBrowserResponse(groups=groups, total_skills=total_skills)


@router.get("/requirements/ship/{type_id}")
def get_ship_requirements(
    request: Request,
    type_id: int,
    mastery_level: int = Query(1, ge=1, le=5)
):
    """Get required skills for a ship at specified mastery level."""
    db = request.app.state.db
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # Get ship name
        cur.execute('SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s', (type_id,))
        ship = cur.fetchone()
        if not ship:
            raise HTTPException(status_code=404, detail="Ship not found")

        # Get mastery requirements from certMasteries
        cur.execute("""
            SELECT DISTINCT
                s."typeID" as skill_type_id,
                s."typeName" as skill_name,
                cs."skillLevel" as level
            FROM "certMasteries" cm
            JOIN "certSkills" cs ON cs."certID" = cm."certID"
            JOIN "invTypes" s ON s."typeID" = cs."skillID"
            WHERE cm."typeID" = %s AND cm."masteryLevel" <= %s
            ORDER BY cs."skillLevel" DESC, s."typeName"
        """, (type_id, mastery_level))
        skills = cur.fetchall()

    return {
        "ship_type_id": type_id,
        "ship_name": ship['typeName'],
        "mastery_level": mastery_level,
        "required_skills": skills
    }


@router.get("/requirements/item/{type_id}")
def get_item_requirements(request: Request, type_id: int):
    """Get required skills for an item."""
    db = request.app.state.db
    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # Get item name
        cur.execute('SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s', (type_id,))
        item = cur.fetchone()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Get skill requirements (attributeIDs 182-184 = requiredSkill1-3, 277-279 = requiredSkill1Level-3Level)
        # Optimized: Use JOINs instead of nested subqueries for better performance
        cur.execute("""
            SELECT DISTINCT
                CASE a."attributeID"
                    WHEN 182 THEN COALESCE(lvl1."valueInt", lvl1."valueFloat")::int
                    WHEN 183 THEN COALESCE(lvl2."valueInt", lvl2."valueFloat")::int
                    WHEN 184 THEN COALESCE(lvl3."valueInt", lvl3."valueFloat")::int
                END as level,
                COALESCE(a."valueInt", a."valueFloat")::int as skill_type_id,
                s."typeName" as skill_name
            FROM "dgmTypeAttributes" a
            JOIN "invTypes" s ON s."typeID" = COALESCE(a."valueInt", a."valueFloat")::int
            LEFT JOIN "dgmTypeAttributes" lvl1 ON lvl1."typeID" = a."typeID" AND lvl1."attributeID" = 277
            LEFT JOIN "dgmTypeAttributes" lvl2 ON lvl2."typeID" = a."typeID" AND lvl2."attributeID" = 278
            LEFT JOIN "dgmTypeAttributes" lvl3 ON lvl3."typeID" = a."typeID" AND lvl3."attributeID" = 279
            WHERE a."typeID" = %s
              AND a."attributeID" IN (182, 183, 184)
              AND COALESCE(a."valueInt", a."valueFloat") IS NOT NULL
        """, (type_id,))
        skills = cur.fetchall()

    return {
        "item_type_id": type_id,
        "item_name": item['typeName'],
        "required_skills": [s for s in skills if s['skill_type_id']]
    }
