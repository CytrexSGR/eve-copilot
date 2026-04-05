"""Corporation data router."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query

from app.models import (
    CorporationInfo, CorporationWallet,
    CorpMarketOrderList, CorpTransactions
)
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.services import CharacterService

logger = logging.getLogger(__name__)
router = APIRouter()


def get_service(request: Request) -> CharacterService:
    """Get character service from app state."""
    return CharacterService(request.app.state.db, request.app.state.redis)


@router.get("/{character_id}/corporation/info")
@handle_endpoint_errors()
def get_corporation_info(
    request: Request,
    character_id: int
) -> CorporationInfo:
    """Get corporation info for character."""
    service = get_service(request)
    corp_id = service.get_corporation_id(character_id)
    if not corp_id:
        raise HTTPException(status_code=404, detail="Corporation not found")

    result = service.get_corporation_info(corp_id)
    if not result:
        raise HTTPException(status_code=404, detail="Corporation not found")
    return result


@router.get("/{character_id}/corporation/wallet")
@handle_endpoint_errors()
def get_corporation_wallets(
    request: Request,
    character_id: int
) -> CorporationWallet:
    """Get corporation wallet balances."""
    service = get_service(request)
    result = service.get_corporation_wallets(character_id)
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result


@router.get("/{character_id}/corporation/orders")
@handle_endpoint_errors()
def get_corporation_orders(
    request: Request,
    character_id: int
) -> CorpMarketOrderList:
    """Get corporation market orders."""
    service = get_service(request)
    result = service.get_corporation_orders(character_id)
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result


@router.get("/{character_id}/corporation/transactions")
@handle_endpoint_errors()
def get_corporation_transactions(
    request: Request,
    character_id: int,
    division: int = Query(1, ge=1, le=7),
    from_id: Optional[int] = Query(None)
) -> CorpTransactions:
    """Get corporation wallet transactions."""
    service = get_service(request)
    result = service.get_corporation_transactions(
        character_id, division, from_id
    )
    if not result:
        raise HTTPException(status_code=401, detail="Authentication required")
    return result


@router.get("/{character_id}/corporation/journal/{division}")
@handle_endpoint_errors()
def get_corporation_journal(
    request: Request,
    character_id: int,
    division: int = 1
) -> dict:
    """Get corporation wallet journal."""
    service = get_service(request)
    token = service._get_token(character_id)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    corp_id = service.get_corporation_id(character_id)
    if not corp_id:
        raise HTTPException(status_code=404, detail="Corporation not found")

    result = service.esi.get_corporation_journal(corp_id, division, token)

    return {
        "corporation_id": corp_id,
        "division": division,
        "entries": len(result),
        "journal": result
    }
