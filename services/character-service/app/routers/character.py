"""Character data router."""
import logging
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Request, Query

from app.models import (
    WalletBalance, AssetList, SkillData, SkillQueue,
    MarketOrderList, IndustryJobList, BlueprintList,
    CharacterInfo, CharacterLocation, CharacterShip,
    CharacterAttributes, CharacterImplants,
    WalletJournal, WalletTransactions,
    ValuedAssetList,
)
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.services import CharacterService

logger = logging.getLogger(__name__)
router = APIRouter()


def get_service(request: Request) -> CharacterService:
    """Get character service from app state."""
    return CharacterService(request.app.state.db, request.app.state.redis)


@router.get("/summary/all")
@handle_endpoint_errors()
def get_all_summaries(
    request: Request,
    ids: Optional[str] = Query(None, description="Comma-separated character IDs to filter"),
):
    """Get summary data for authenticated characters from DB (fast).

    Reads pre-synced data from database tables instead of calling ESI.
    Pass ?ids=123,456 to fetch only specific characters.
    Use /summary/all/live for on-demand ESI refresh.
    """
    service = get_service(request)

    character_ids = None
    if ids:
        character_ids = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]

    results = service.repo.get_all_summaries_from_db(character_ids)
    # If no character has wallet data, DB hasn't been populated by sync yet
    sync_needed = not any(r.get("wallet") for r in results)
    return {
        "characters": results,
        "count": len(results),
        "sync_needed": sync_needed,
    }


@router.get("/summary/all/live")
@handle_endpoint_errors()
def get_all_summaries_live(
    request: Request,
    ids: Optional[str] = Query(None, description="Comma-separated character IDs to filter"),
):
    """Get summary data for authenticated characters via live ESI calls (slow fallback).

    Makes ~7 ESI calls per character. Use /summary/all for fast DB reads.
    """
    service = get_service(request)
    characters = service.get_all_characters()

    # Filter to requested character IDs if specified
    if ids:
        requested_ids = {int(x.strip()) for x in ids.split(",") if x.strip().isdigit()}
        characters = [c for c in characters if c.get("character_id") in requested_ids]

    results = []
    for char in characters:
        char_id = char.get("character_id")
        char_name = char.get("character_name", "Unknown")

        char_data: Dict[str, Any] = {
            "character_id": char_id,
            "character_name": char_name,
            "info": None,
            "wallet": None,
            "skills": None,
            "skillqueue": None,
            "location": None,
            "ship": None,
            "industry": None,
        }

        # Info (public, no token needed)
        try:
            info = service.get_character_info(char_id)
            if info:
                char_data["info"] = info.model_dump()
        except Exception as e:
            logger.warning(f"Failed to get info for {char_id}: {e}")

        # Wallet
        try:
            wallet = service.get_wallet(char_id)
            if wallet:
                char_data["wallet"] = {"balance": wallet.balance}
        except Exception as e:
            logger.warning(f"Failed to get wallet for {char_id}: {e}")

        # Skills
        try:
            skills = service.get_skills(char_id)
            if skills:
                char_data["skills"] = {
                    "total_sp": skills.total_sp,
                    "unallocated_sp": skills.unallocated_sp,
                    "skills": [s.model_dump() for s in skills.skills],
                }
        except Exception as e:
            logger.warning(f"Failed to get skills for {char_id}: {e}")

        # Skill queue
        try:
            queue = service.get_skillqueue(char_id)
            if queue:
                char_data["skillqueue"] = {
                    "queue": [q.model_dump() for q in queue.queue],
                }
        except Exception as e:
            logger.warning(f"Failed to get skillqueue for {char_id}: {e}")

        # Location
        try:
            location = service.get_location(char_id)
            if location:
                char_data["location"] = {
                    "solar_system_id": location.solar_system_id,
                    "solar_system_name": location.solar_system_name,
                    "station_id": location.station_id,
                    "station_name": location.station_name,
                    "structure_id": location.structure_id,
                }
        except Exception as e:
            logger.warning(f"Failed to get location for {char_id}: {e}")

        # Ship
        try:
            ship = service.get_ship(char_id)
            if ship:
                char_data["ship"] = {
                    "ship_type_id": ship.ship_type_id,
                    "ship_type_name": ship.ship_type_name,
                    "ship_item_id": ship.ship_item_id,
                }
        except Exception as e:
            logger.warning(f"Failed to get ship for {char_id}: {e}")

        # Industry
        try:
            industry = service.get_industry_jobs(char_id)
            if industry:
                char_data["industry"] = {
                    "jobs": [j.model_dump() for j in industry.jobs],
                    "active_jobs": industry.active_jobs,
                }
        except Exception as e:
            logger.warning(f"Failed to get industry for {char_id}: {e}")

        results.append(char_data)

    return {"characters": results, "count": len(results)}


@router.get("/{character_id}/wallet")
@handle_endpoint_errors()
def get_wallet(
    request: Request,
    character_id: int
) -> WalletBalance:
    """Get character wallet balance."""
    service = get_service(request)
    result = service.get_wallet(character_id)
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result


@router.get("/{character_id}/assets/valued")
@handle_endpoint_errors()
def get_valued_assets(
    request: Request,
    character_id: int,
    location_id: Optional[int] = Query(None)
) -> ValuedAssetList:
    """Get character assets with market valuations."""
    service = get_service(request)
    result = service.get_valued_assets(character_id, location_id)
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result


@router.get("/{character_id}/assets")
@handle_endpoint_errors()
def get_assets(
    request: Request,
    character_id: int,
    location_id: Optional[int] = Query(None)
) -> AssetList:
    """Get character assets."""
    service = get_service(request)
    result = service.get_assets(character_id, location_id)
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result


@router.get("/{character_id}/skills")
@handle_endpoint_errors()
def get_skills(
    request: Request,
    character_id: int
) -> SkillData:
    """Get character skills."""
    service = get_service(request)
    result = service.get_skills(character_id)
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result


@router.get("/{character_id}/skillqueue")
@handle_endpoint_errors()
def get_skillqueue(
    request: Request,
    character_id: int
) -> SkillQueue:
    """Get character skill queue."""
    service = get_service(request)
    result = service.get_skillqueue(character_id)
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result


@router.get("/{character_id}/orders")
@handle_endpoint_errors()
def get_orders(
    request: Request,
    character_id: int
) -> MarketOrderList:
    """Get character market orders."""
    service = get_service(request)
    result = service.get_orders(character_id)
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result


@router.get("/{character_id}/orders/undercuts")
@handle_endpoint_errors()
def get_order_undercuts(
    request: Request,
    character_id: int
):
    """
    Check character's orders for undercuts/outbids.

    Currently returns stub data - no orders = no undercuts.
    Full implementation pending market service integration.
    """
    service = get_service(request)
    orders = service.get_orders(character_id)
    if not orders:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Stub response - if no orders, no undercuts
    return {
        "character_id": character_id,
        "total_orders": orders.total_orders,
        "undercut_count": 0,
        "outbid_count": 0,
        "orders": []
    }


@router.get("/{character_id}/industry")
@handle_endpoint_errors()
def get_industry_jobs(
    request: Request,
    character_id: int,
    include_completed: bool = Query(False)
) -> IndustryJobList:
    """Get character industry jobs."""
    service = get_service(request)
    result = service.get_industry_jobs(character_id, include_completed)
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result


@router.get("/{character_id}/blueprints")
@handle_endpoint_errors()
def get_blueprints(
    request: Request,
    character_id: int
) -> BlueprintList:
    """Get character blueprints."""
    service = get_service(request)
    result = service.get_blueprints(character_id)
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result


@router.get("/{character_id}/info")
@handle_endpoint_errors()
def get_character_info(
    request: Request,
    character_id: int
) -> CharacterInfo:
    """Get public character information."""
    service = get_service(request)
    result = service.get_character_info(character_id)
    if not result:
        raise HTTPException(status_code=404, detail="Character not found")
    return result


@router.get("/{character_id}/location")
@handle_endpoint_errors()
def get_location(
    request: Request,
    character_id: int
) -> CharacterLocation:
    """Get character current location."""
    service = get_service(request)
    result = service.get_location(character_id)
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result


@router.get("/{character_id}/ship")
@handle_endpoint_errors()
def get_ship(
    request: Request,
    character_id: int
) -> CharacterShip:
    """Get character current ship."""
    service = get_service(request)
    result = service.get_ship(character_id)
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result


@router.get("/{character_id}/attributes")
@handle_endpoint_errors()
def get_attributes(
    request: Request,
    character_id: int
) -> CharacterAttributes:
    """Get character attributes."""
    service = get_service(request)
    result = service.get_attributes(character_id)
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result


@router.get("/{character_id}/implants")
@handle_endpoint_errors()
def get_implants(
    request: Request,
    character_id: int
) -> CharacterImplants:
    """Get character implants."""
    service = get_service(request)
    result = service.get_implants(character_id)
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result


@router.get("/{character_id}/wallet/journal")
@handle_endpoint_errors()
def get_wallet_journal(
    request: Request,
    character_id: int,
    page: int = Query(1, ge=1)
) -> WalletJournal:
    """Get character wallet journal."""
    service = get_service(request)
    result = service.get_wallet_journal(character_id, page)
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result


@router.get("/{character_id}/wallet/transactions")
@handle_endpoint_errors()
def get_wallet_transactions(
    request: Request,
    character_id: int,
    from_id: Optional[int] = Query(None)
) -> WalletTransactions:
    """Get character wallet transactions."""
    service = get_service(request)
    result = service.get_wallet_transactions(character_id, from_id)
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result
