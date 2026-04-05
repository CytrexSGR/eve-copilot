"""Wormhole hunting opportunities API."""
from fastapi import APIRouter, Query
from typing import Optional
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.services.opportunity_scorer import OpportunityScorer

router = APIRouter(prefix="/opportunities", tags=["opportunities"])
scorer = OpportunityScorer()


@router.get("")
@handle_endpoint_errors()
def get_opportunities(
    wh_class: Optional[int] = Query(None, ge=1, le=18, description="Filter by WH class (1-6 standard, 13+ special)"),
    min_activity: int = Query(3, ge=1, le=50, description="Minimum kills in 7d"),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Get hunting opportunity board.

    Returns systems ranked by opportunity score (activity + recency + weakness).
    """
    opportunities = scorer.get_opportunities(
        wh_class=wh_class,
        min_activity=min_activity,
        limit=limit
    )
    return {
        "count": len(opportunities),
        "filter": {"wh_class": wh_class, "min_activity": min_activity},
        "opportunities": opportunities
    }
