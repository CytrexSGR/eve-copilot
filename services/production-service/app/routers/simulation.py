"""Production simulation router."""
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from app.models import ProductionSimulation, QuickProfitCheck
from app.services import ProductionService
from app.config import settings
from eve_shared.constants import JITA_REGION_ID

logger = logging.getLogger(__name__)
router = APIRouter()


class SimulationRequest(BaseModel):
    """Request model for production simulation."""
    type_id: int
    runs: int = 1
    me: int = 0
    te: int = 0
    region_id: Optional[int] = None
    character_assets: Optional[List[dict]] = None


class CostRequest(BaseModel):
    """Request model for production cost calculation."""
    type_id: int
    me_level: int = 0
    te_level: int = 0
    region_id: int = JITA_REGION_ID
    runs: int = 1


@router.post("/simulate")
def simulate_build(
    request: Request,
    sim_request: SimulationRequest
) -> ProductionSimulation:
    """
    Simulate a production run with all metrics and warnings.

    Returns complete simulation including:
    - Bill of materials with prices
    - Asset matching (if assets provided)
    - Financial analysis (cost, profit, ROI)
    - Production time with TE
    - Shopping list for missing materials
    - Warnings about profitability
    """
    try:
        db = request.app.state.db
        service = ProductionService(db, settings.default_region_id)

        result = service.simulate_build(
            type_id=sim_request.type_id,
            runs=sim_request.runs,
            me=sim_request.me,
            te=sim_request.te,
            character_assets=sim_request.character_assets,
            region_id=sim_request.region_id
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulate/{type_id}")
def simulate_build_get(
    request: Request,
    type_id: int,
    runs: int = Query(default=1, ge=1, le=1000),
    me: int = Query(default=0, ge=0, le=10),
    te: int = Query(default=0, ge=0, le=20),
    region_id: int = Query(default=JITA_REGION_ID)
) -> ProductionSimulation:
    """GET endpoint for production simulation."""
    try:
        db = request.app.state.db
        service = ProductionService(db, settings.default_region_id)

        result = service.simulate_build(
            type_id=type_id,
            runs=runs,
            me=me,
            te=te,
            character_assets=None,
            region_id=region_id
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cost")
def calculate_cost(
    request: Request,
    cost_request: CostRequest
) -> dict:
    """Calculate production cost for an item."""
    try:
        db = request.app.state.db
        service = ProductionService(db, settings.default_region_id)

        bom = service.get_bom(
            cost_request.type_id,
            cost_request.runs,
            cost_request.me_level
        )

        if not bom:
            raise HTTPException(
                status_code=404,
                detail=f"No blueprint found for type_id {cost_request.type_id}"
            )

        bom_items = service.get_bom_with_prices(
            cost_request.type_id,
            cost_request.runs,
            cost_request.me_level,
            cost_request.region_id
        )

        total_cost = sum(item.total_cost for item in bom_items)

        return {
            "type_id": cost_request.type_id,
            "runs": cost_request.runs,
            "me": cost_request.me_level,
            "region_id": cost_request.region_id,
            "materials": [item.model_dump() for item in bom_items],
            "total_cost": round(total_cost, 2)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cost calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost/{type_id}")
def calculate_cost_get(
    request: Request,
    type_id: int,
    me: int = Query(default=0, ge=0, le=10),
    runs: int = Query(default=1, ge=1),
    region_id: int = Query(default=JITA_REGION_ID)
) -> dict:
    """GET endpoint for production cost calculation."""
    try:
        db = request.app.state.db
        service = ProductionService(db, settings.default_region_id)

        bom = service.get_bom(type_id, runs, me)

        if not bom:
            raise HTTPException(
                status_code=404,
                detail=f"No blueprint found for type_id {type_id}"
            )

        bom_items = service.get_bom_with_prices(type_id, runs, me, region_id)
        total_cost = sum(item.total_cost for item in bom_items)

        return {
            "type_id": type_id,
            "runs": runs,
            "me": me,
            "region_id": region_id,
            "materials": [item.model_dump() for item in bom_items],
            "total_cost": round(total_cost, 2)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Cost calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profit-check/{type_id}")
def quick_profit_check(
    request: Request,
    type_id: int,
    runs: int = Query(default=1, ge=1),
    me: int = Query(default=0, ge=0, le=10),
    region_id: int = Query(default=JITA_REGION_ID)
) -> QuickProfitCheck:
    """
    Fast profit calculation for an item.

    Ideal for scanning many items to find opportunities.
    """
    try:
        db = request.app.state.db
        service = ProductionService(db, settings.default_region_id)

        result = service.quick_profit_check(type_id, runs, me, region_id)

        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"No blueprint found for type_id {type_id}"
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profit check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
