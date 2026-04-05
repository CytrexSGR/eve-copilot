"""
Skill Prerequisites API Router
Provides endpoints for calculating complete skill trees.
"""

from fastapi import APIRouter, Request, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
from typing import List, Dict, Any

router = APIRouter()


class SkillNode(BaseModel):
    skill_id: int
    skill_name: str
    level: int
    rank: float
    sp_required: int
    primary_attribute: str
    secondary_attribute: str
    requires: List["SkillNode"] = []


class FlatSkill(BaseModel):
    skill_id: int
    skill_name: str
    level: int
    rank: float
    sp_required: int
    primary_attribute: str
    secondary_attribute: str


class ItemPrerequisitesResponse(BaseModel):
    type_id: int
    type_name: str
    skill_trees: List[Dict[str, Any]]
    flat_skills: List[FlatSkill]
    total_sp: int


class SkillTreeResponse(BaseModel):
    skill_id: int
    skill_name: str
    level: int
    skill_tree: Dict[str, Any]
    flat_skills: List[FlatSkill]
    total_sp: int


class CachePopulateResponse(BaseModel):
    processed: int
    errors: int
    total_skills: int


def _get_service(request: Request):
    """Get or create SkillPrerequisitesService instance."""
    from app.services.skill_prerequisites_service import SkillPrerequisitesService

    # Cache service on app state
    if not hasattr(request.app.state, 'skill_prereq_service'):
        request.app.state.skill_prereq_service = SkillPrerequisitesService(
            request.app.state.db
        )
    return request.app.state.skill_prereq_service


@router.get("/item/{type_id}", response_model=ItemPrerequisitesResponse)
def get_item_prerequisites(
    request: Request,
    type_id: int,
):
    """
    Get complete skill tree for using an item (ship, module, etc).

    Returns both tree structure and flattened unique skill list.
    """
    service = _get_service(request)
    result = service.get_prerequisites_for_item(type_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/skill/{skill_id}", response_model=SkillTreeResponse)
def get_skill_prerequisites(
    request: Request,
    skill_id: int,
    level: int = Query(5, ge=1, le=5, description="Target skill level"),
):
    """
    Get complete prerequisite tree for a skill at specified level.
    """
    service = _get_service(request)

    tree = service.get_full_skill_tree(skill_id, level)
    if not tree:
        raise HTTPException(status_code=404, detail=f"Skill {skill_id} not found")

    flat = service.get_flat_prerequisites(skill_id, level)
    total_sp = sum(req.sp_required for req in flat.values())

    return {
        "skill_id": skill_id,
        "skill_name": tree["skill_name"],
        "level": level,
        "skill_tree": tree,
        "flat_skills": [
            {
                "skill_id": req.skill_id,
                "skill_name": req.skill_name,
                "level": req.level,
                "rank": req.rank,
                "sp_required": req.sp_required,
                "primary_attribute": req.primary_attribute,
                "secondary_attribute": req.secondary_attribute,
            }
            for req in sorted(flat.values(), key=lambda x: -x.sp_required)
        ],
        "total_sp": total_sp
    }


@router.get("/skill/{skill_id}/cached")
def get_cached_prerequisites(
    request: Request,
    skill_id: int,
):
    """
    Get cached prerequisites from database (faster, but needs cache populated).
    """
    service = _get_service(request)
    result = service.get_cached_prerequisites(skill_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No cached data for skill {skill_id}. Run /populate-cache first."
        )

    return result


@router.post("/populate-cache", response_model=CachePopulateResponse)
def populate_prerequisites_cache(request: Request):
    """
    Populate skill_prerequisites_cache table for all skills.

    Run once after SDE update. Takes ~30 seconds.
    """
    service = _get_service(request)
    result = service.populate_prerequisites_cache()
    return result


@router.get("/pilot/{character_id}/estimated-skills")
def get_pilot_estimated_skills(
    request: Request,
    character_id: int,
    days: int = Query(90, ge=1, le=365, description="Days to analyze"),
):
    """
    Get estimated minimum skills for a pilot based on killmail activity.

    Analyzes:
    - Ships flown (from kills as attacker)
    - Weapons used (from kills as attacker)
    - Ships lost (from kills as victim)
    - Fitted modules from losses (killmail_items)

    Returns complete skill trees with all prerequisites.
    """
    from psycopg2.extras import RealDictCursor

    service = _get_service(request)
    db = request.app.state.db

    with db.cursor(cursor_factory=RealDictCursor) as cur:
        # Get ships flown by pilot (as attacker)
        cur.execute("""
            SELECT DISTINCT ka.ship_type_id, t."typeName" as ship_name
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            JOIN "invTypes" t ON t."typeID" = ka.ship_type_id
            WHERE ka.character_id = %s
              AND k.killmail_time > NOW() - INTERVAL '%s days'
              AND ka.ship_type_id IS NOT NULL
              AND ka.ship_type_id > 0
        """, (character_id, days))
        ships_flown = cur.fetchall()

        # Get ships lost by pilot (as victim)
        cur.execute("""
            SELECT DISTINCT k.ship_type_id, t."typeName" as ship_name
            FROM killmails k
            JOIN "invTypes" t ON t."typeID" = k.ship_type_id
            WHERE k.victim_character_id = %s
              AND k.killmail_time > NOW() - INTERVAL '%s days'
              AND k.ship_type_id IS NOT NULL
              AND k.ship_type_id > 0
        """, (character_id, days))
        ships_lost = cur.fetchall()

        # Get weapons/modules used (from kills as attacker)
        cur.execute("""
            SELECT DISTINCT ka.weapon_type_id, t."typeName" as weapon_name
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            JOIN "invTypes" t ON t."typeID" = ka.weapon_type_id
            JOIN "invGroups" g ON g."groupID" = t."groupID"
            WHERE ka.character_id = %s
              AND k.killmail_time > NOW() - INTERVAL '%s days'
              AND ka.weapon_type_id IS NOT NULL
              AND ka.weapon_type_id > 0
              AND g."categoryID" <> 6  -- Exclude ships
        """, (character_id, days))
        weapons = cur.fetchall()

        # Get fitted modules from losses (killmail_items)
        # Flags: 11-18 Low, 19-26 Mid, 27-34 High, 87-93 Drone, 125-132 Rig
        cur.execute("""
            SELECT DISTINCT ki.item_type_id, t."typeName" as module_name,
                   c."categoryName" as category
            FROM killmail_items ki
            JOIN killmails k ON ki.killmail_id = k.killmail_id
            JOIN "invTypes" t ON t."typeID" = ki.item_type_id
            JOIN "invGroups" g ON g."groupID" = t."groupID"
            JOIN "invCategories" c ON c."categoryID" = g."categoryID"
            WHERE k.victim_character_id = %s
              AND k.killmail_time > NOW() - INTERVAL '%s days'
              AND ki.flag BETWEEN 11 AND 132
              AND ki.flag <> 5  -- Exclude cargo
              AND c."categoryName" IN ('Module', 'Drone')  -- Only modules and drones
        """, (character_id, days))
        fitted_modules = cur.fetchall()

        # Get character name
        cur.execute("""
            SELECT character_name FROM character_name_cache
            WHERE character_id = %s
        """, (character_id,))
        char_row = cur.fetchone()
        character_name = char_row['character_name'] if char_row else f"Pilot {character_id}"

    # Calculate skill trees for all items
    all_flat = {}
    ship_skills = {}
    weapon_skills = {}
    module_skills = {}

    # Combine ships flown and ships lost
    all_ships = {s['ship_type_id']: s for s in ships_flown}
    for s in ships_lost:
        if s['ship_type_id'] not in all_ships:
            all_ships[s['ship_type_id']] = s

    for ship in all_ships.values():
        result = service.get_prerequisites_for_item(ship['ship_type_id'])
        if 'flat_skills' in result:
            ship_skills[ship['ship_name']] = result['flat_skills']
            for skill in result['flat_skills']:
                sid = skill['skill_id']
                if sid not in all_flat or skill['level'] > all_flat[sid]['level']:
                    all_flat[sid] = skill

    for weapon in weapons:
        result = service.get_prerequisites_for_item(weapon['weapon_type_id'])
        if 'flat_skills' in result:
            weapon_skills[weapon['weapon_name']] = result['flat_skills']
            for skill in result['flat_skills']:
                sid = skill['skill_id']
                if sid not in all_flat or skill['level'] > all_flat[sid]['level']:
                    all_flat[sid] = skill

    # Process fitted modules from losses
    for module in fitted_modules:
        result = service.get_prerequisites_for_item(module['item_type_id'])
        if 'flat_skills' in result:
            module_skills[module['module_name']] = result['flat_skills']
            for skill in result['flat_skills']:
                sid = skill['skill_id']
                if sid not in all_flat or skill['level'] > all_flat[sid]['level']:
                    all_flat[sid] = skill

    total_sp = sum(s['sp_required'] for s in all_flat.values())

    return {
        "character_id": character_id,
        "character_name": character_name,
        "period_days": days,
        "data_sources": {
            "ships_flown": len(ships_flown),
            "ships_lost": len(ships_lost),
            "weapons_used": len(weapons),
            "fitted_modules_from_losses": len(fitted_modules),
        },
        "total_unique_skills": len(all_flat),
        "total_sp_required": total_sp,
        "skills": sorted(all_flat.values(), key=lambda x: -x['sp_required']),
        "by_ship": ship_skills,
        "by_weapon": weapon_skills,
        "by_module": module_skills,
    }
