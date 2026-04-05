# app/routers/dps.py
"""DPS Calculator REST API.

Migrated from monolith to war-intel-service.
Uses eve_shared pattern for database access.
"""

import logging
import os
from typing import Optional, List, Dict, Any

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.services.dps.models import DPSResult
from app.services.dps.repository import DPSRepository
from app.services.dps.service import DPSCalculatorService

logger = logging.getLogger(__name__)
router = APIRouter()

CHARACTER_SERVICE_URL = os.environ.get("CHARACTER_SERVICE_URL", "http://character-service:8000")


async def _fetch_character_skills(character_id: int) -> Optional[Dict[int, int]]:
    """Fetch character skills from character-service.

    Returns dict of {skill_id: trained_level} or None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{CHARACTER_SERVICE_URL}/api/character/{character_id}/skills")
            if resp.status_code != 200:
                logger.warning(f"Failed to fetch skills for {character_id}: HTTP {resp.status_code}")
                return None
            data = resp.json()
            skills = data.get("skills", [])
            return {s["skill_id"]: s.get("trained_level", s.get("level", 0)) for s in skills}
    except Exception as e:
        logger.warning(f"Error fetching skills for {character_id}: {e}")
        return None


@router.get(
    "/calculate",
    response_model=DPSResult,
    summary="Calculate weapon DPS",
    description="Calculate DPS for a weapon/ammo combination with optional skill and ship bonuses."
)
async def calculate_dps(
    weapon_id: int = Query(..., description="Weapon type ID"),
    ammo_id: int = Query(..., description="Ammunition type ID"),
    character_id: Optional[int] = Query(None, description="Character ID for skill bonuses"),
    ship_id: Optional[int] = Query(None, description="Ship type ID for ship bonuses")
) -> DPSResult:
    """Calculate DPS for weapon/ammo combination."""
    service = DPSCalculatorService()

    # Get character skills if provided
    character_skills = None
    ship_skill_levels = None

    if character_id:
        skills = await _fetch_character_skills(character_id)
        if skills:
            character_skills = skills
            ship_skill_levels = skills

    result = service.calculate_dps(
        weapon_type_id=weapon_id,
        ammo_type_id=ammo_id,
        character_skills=character_skills,
        ship_type_id=ship_id,
        ship_skill_levels=ship_skill_levels
    )

    if not result:
        raise HTTPException(status_code=404, detail="Weapon or ammo not found")

    return result


@router.get(
    "/compare-ammo",
    response_model=List[DPSResult],
    summary="Compare ammo DPS",
    description="Compare DPS across different ammo types for a weapon."
)
async def compare_ammo(
    weapon_id: int = Query(..., description="Weapon type ID"),
    ammo_ids: str = Query(..., description="Comma-separated ammo type IDs"),
    character_id: Optional[int] = Query(None, description="Character ID for skill bonuses"),
    ship_id: Optional[int] = Query(None, description="Ship type ID for ship bonuses")
) -> List[DPSResult]:
    """Compare DPS for different ammo types."""
    service = DPSCalculatorService()

    ammo_type_ids = [int(x.strip()) for x in ammo_ids.split(',')]

    character_skills = None
    ship_skill_levels = None

    if character_id:
        skills = await _fetch_character_skills(character_id)
        if skills:
            character_skills = skills
            ship_skill_levels = skills

    return service.compare_ammo(
        weapon_type_id=weapon_id,
        ammo_type_ids=ammo_type_ids,
        character_skills=character_skills,
        ship_type_id=ship_id,
        ship_skill_levels=ship_skill_levels
    )


@router.get(
    "/weapons/search",
    summary="Search weapons",
    description="Search for weapons by name."
)
def search_weapons(
    name: str = Query(..., description="Weapon name to search"),
    limit: int = Query(20, le=50, description="Max results")
) -> Dict[str, Any]:
    """Search weapons by name."""
    repo = DPSRepository()
    results = repo.search_weapons(name, limit)
    return {"search_term": name, "results": results}


@router.get(
    "/ammo/search",
    summary="Search ammunition",
    description="Search for ammunition by name."
)
def search_ammo(
    name: str = Query(..., description="Ammo name to search"),
    limit: int = Query(20, le=50, description="Max results")
) -> Dict[str, Any]:
    """Search ammo by name."""
    repo = DPSRepository()
    results = repo.search_ammo(name, limit)
    return {"search_term": name, "results": results}


@router.get(
    "/weapon/{weapon_id}",
    summary="Get weapon attributes",
    description="Get detailed weapon attributes."
)
def get_weapon(weapon_id: int):
    """Get weapon attributes."""
    repo = DPSRepository()
    weapon = repo.get_weapon_attributes(weapon_id)
    if not weapon:
        raise HTTPException(status_code=404, detail="Weapon not found")
    return weapon


@router.get(
    "/ammo/{ammo_id}",
    summary="Get ammo attributes",
    description="Get ammunition damage attributes."
)
def get_ammo(ammo_id: int):
    """Get ammo attributes."""
    repo = DPSRepository()
    ammo = repo.get_ammo_attributes(ammo_id)
    if not ammo:
        raise HTTPException(status_code=404, detail="Ammo not found")
    return ammo


@router.get(
    "/ship/{ship_id}/bonuses",
    summary="Get ship damage bonuses",
    description="Get ship damage-related bonuses from traits."
)
def get_ship_bonuses(ship_id: int):
    """Get ship damage bonuses."""
    repo = DPSRepository()
    bonuses = repo.get_ship_damage_bonuses(ship_id)
    return {"ship_type_id": ship_id, "bonuses": bonuses}
