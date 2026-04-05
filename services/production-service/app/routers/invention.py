"""Invention cost calculator router."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query

from app.services.invention import InventionService
from eve_shared.constants import JITA_REGION_ID

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/invention/{type_id}")
def get_invention_cost(
    request: Request,
    type_id: int,
    decryptor_type_id: Optional[int] = Query(
        default=None, description="Optional decryptor type_id"
    ),
    region_id: int = Query(
        default=JITA_REGION_ID, description="Region for price lookups (default: The Forge)"
    ),
) -> dict:
    """Calculate invention cost breakdown for a T2 item.

    Returns invention inputs, probability, BPC cost, and T2 manufacturing
    BOM with ME bonus applied.
    """
    try:
        db = request.app.state.db
        service = InventionService(db)
        result = service.get_invention_cost(type_id, decryptor_type_id, region_id)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"No invention path found for type_id {type_id}. "
                "Item may not be a T2 product.",
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Invention cost calculation failed for {type_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/invention/{type_id}/decryptors")
def compare_decryptors(
    request: Request,
    type_id: int,
    region_id: int = Query(
        default=JITA_REGION_ID, description="Region for price lookups (default: The Forge)"
    ),
) -> dict:
    """Compare all decryptor options for a T2 item.

    Returns sorted list (cheapest total cost first) with each decryptor's
    impact on ME, TE, runs, probability, and total cost per run.
    """
    try:
        db = request.app.state.db
        service = InventionService(db)
        results = service.compare_decryptors(type_id, region_id)
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"No invention path found for type_id {type_id}.",
            )
        return {
            "type_id": type_id,
            "comparisons": results,
            "best_option": results[0] if results else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Decryptor comparison failed for {type_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
