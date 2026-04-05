"""Production economics router."""
import logging

from fastapi import APIRouter, HTTPException, Request, Query

from app.services import ProductionEconomicsService
from eve_shared.constants import JITA_REGION_ID

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/economics/opportunities")
def find_opportunities(
    request: Request,
    region_id: int = Query(default=JITA_REGION_ID, description="Region ID"),
    min_roi: float = Query(default=0, description="Minimum ROI percentage"),
    min_profit: float = Query(default=0, description="Minimum profit in ISK"),
    min_volume: int = Query(default=0, ge=0, description="Minimum average daily volume"),
    limit: int = Query(default=50, ge=1, le=500, description="Max results")
) -> dict:
    """
    Find profitable manufacturing opportunities.

    Scans manufacturable items and returns those meeting profit criteria.
    """
    try:
        db = request.app.state.db
        service = ProductionEconomicsService(db)

        result = service.find_opportunities(
            region_id=region_id,
            min_roi=min_roi,
            min_profit=min_profit,
            min_volume=min_volume,
            limit=limit
        )

        return result
    except Exception as e:
        logger.error(f"Failed to find opportunities: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/economics/{type_id}")
def get_economics(
    request: Request,
    type_id: int,
    region_id: int = Query(default=JITA_REGION_ID, description="Region ID"),
    me: int = Query(default=0, ge=0, le=10, description="Material Efficiency"),
    te: int = Query(default=0, ge=0, le=20, description="Time Efficiency")
) -> dict:
    """
    Get complete production economics analysis for an item.

    Returns:
        Economics data with costs, market prices, profit, ROI, and production time
    """
    try:
        db = request.app.state.db
        service = ProductionEconomicsService(db)

        result = service.get_economics(type_id, region_id, me=me, te=te)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get economics for {type_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/economics/{type_id}/regions")
def compare_regions(
    request: Request,
    type_id: int
) -> dict:
    """
    Compare production profitability across all trade hub regions.

    Returns:
        Multi-region comparison with best region recommendation
    """
    try:
        db = request.app.state.db
        service = ProductionEconomicsService(db)

        result = service.compare_regions(type_id)

        if not result.get("regions"):
            raise HTTPException(
                status_code=404,
                detail="No economics data found for this item in any region"
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compare regions for {type_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
