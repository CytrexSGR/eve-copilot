# routers/history.py
"""Trading History Router - Migrated from monolith to market-service."""

import logging

from fastapi import APIRouter, HTTPException, Query, Request

from app.services.trading.history import TradingHistoryService, TradingHistory
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["Trading History"])


def get_history_service(request: Request) -> TradingHistoryService:
    """Dependency injection for history service."""
    db = request.app.state.db
    return TradingHistoryService(db)


@router.get("/{character_id}", response_model=TradingHistory)
@handle_endpoint_errors()
def get_trading_history(
    request: Request,
    character_id: int,
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    include_corp: bool = Query(True, description="Include corporation transactions"),
):
    """
    Get comprehensive trading history with pattern analysis.

    Analyzes:
    - Recent trades journal
    - Daily trading statistics
    - Hourly trading patterns
    - Day of week patterns
    - Per-item performance metrics
    - Actionable insights

    Args:
        character_id: EVE Online character ID
        days: Number of days to analyze (1-90)
        include_corp: Include corporation transactions

    Returns:
        TradingHistory with full analysis
    """
    service = get_history_service(request)
    return service.get_trading_history(character_id, days, include_corp)
