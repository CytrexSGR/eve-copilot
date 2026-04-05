"""Internal endpoints for scheduler-triggered jobs."""
import asyncio
import logging

from fastapi import APIRouter, Request, Query

from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/internal/batch-calculate")
@handle_endpoint_errors()
async def batch_calculate(
    request: Request,
    me: int = Query(default=10, ge=0, le=10, description="Material Efficiency"),
):
    """
    Recalculate all manufacturing opportunities.

    Fetches adjusted prices from ESI, calculates profitability for all T1
    blueprints, and saves results to manufacturing_opportunities table.
    Called by scheduler-service every 5 minutes.
    """
    from app.services.batch_calculator import BatchCalculator

    db = request.app.state.db
    calculator = BatchCalculator(db)
    result = await asyncio.to_thread(calculator.run, me=me)

    if result["status"] == "error":
        logger.error(f"Batch calculator failed: {result['details']}")
        return result

    return result
