"""Character sync router."""
import logging
from typing import List

from fastapi import APIRouter, HTTPException, Request

from app.services import CharacterService

logger = logging.getLogger(__name__)
router = APIRouter()


def get_service(request: Request) -> CharacterService:
    """Get character service from app state."""
    return CharacterService(request.app.state.db, request.app.state.redis)


@router.post("/{character_id}/sync")
def sync_character(
    request: Request,
    character_id: int
) -> dict:
    """Trigger full data sync for a character."""
    try:
        service = get_service(request)
        result = service.sync_character(character_id)
        return {
            "character_id": character_id,
            "synced": result
        }
    except Exception as e:
        logger.error(f"Sync failed for {character_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/characters")
def get_characters(
    request: Request
) -> List[dict]:
    """Get all authenticated characters."""
    try:
        service = get_service(request)
        return service.get_all_characters()
    except Exception as e:
        logger.error(f"Failed to get characters: {e}")
        raise HTTPException(status_code=500, detail=str(e))
