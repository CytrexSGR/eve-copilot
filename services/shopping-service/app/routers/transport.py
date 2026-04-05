"""Transport planning router."""
import logging
from typing import List

from fastapi import APIRouter, HTTPException, Request
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.models import CargoSummary, TransportOption
from app.services import ShoppingService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/lists/{list_id}/cargo-summary")
@handle_endpoint_errors()
def get_cargo_summary(
    request: Request,
    list_id: int
) -> CargoSummary:
    """Get cargo volume summary for a shopping list."""
    try:
        db = request.app.state.db
        service = ShoppingService(db)
        result = service.get_cargo_summary(list_id)
        if not result:
            raise HTTPException(status_code=404, detail="List not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cargo summary for {list_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lists/{list_id}/transport-options")
@handle_endpoint_errors()
def get_transport_options(
    request: Request,
    list_id: int
) -> List[TransportOption]:
    """Get transport ship recommendations for a shopping list."""
    try:
        db = request.app.state.db
        service = ShoppingService(db)
        result = service.get_transport_options(list_id)
        if not result:
            raise HTTPException(status_code=404, detail="List not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get transport options for {list_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
