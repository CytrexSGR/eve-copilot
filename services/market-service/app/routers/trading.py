"""
Trading Analytics Router.
Migrated from monolith to market-service.
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, Query, Depends, Request

from app.services.trading import (
    TradingAnalyticsService,
    TradingPnLReport,
    MarginAlert,
    TradingSummary,
    VelocityReport,
    CompetitionReport,
)
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trading", tags=["Trading Analytics"])


def get_trading_service(request: Request) -> TradingAnalyticsService:
    """Dependency injection for trading service."""
    db = request.app.state.db
    return TradingAnalyticsService(db)


@router.get("/{character_id}/pnl", response_model=TradingPnLReport)
@handle_endpoint_errors()
def get_pnl_report(
    request: Request,
    character_id: int,
    include_corp: bool = Query(True, description="Include corp trades"),
    days: int = Query(30, ge=1, le=365, description="Lookback period"),
):
    """
    Get aggregated P&L report per item.

    Calculates realized and unrealized P&L using average cost basis.
    Includes top winners and losers.

    Args:
        character_id: EVE Online character ID
        include_corp: Include corporation transactions
        days: Lookback period in days

    Returns:
        TradingPnLReport with item-level P&L
    """
    service = get_trading_service(request)
    return service.calculate_pnl(character_id, include_corp, days)


@router.get("/{character_id}/margin-alerts", response_model=List[MarginAlert])
@handle_endpoint_errors()
def get_margin_alerts(
    request: Request,
    character_id: int,
    threshold: float = Query(10.0, ge=0, le=100, description="Alert threshold %"),
):
    """
    Get items with low or negative margins.

    Returns alerts for items where margin is below threshold.

    Args:
        character_id: EVE Online character ID
        threshold: Margin threshold percentage

    Returns:
        List of MarginAlert for items needing attention
    """
    service = get_trading_service(request)
    return service.get_margin_alerts(character_id, threshold)


@router.get("/{character_id}/summary", response_model=TradingSummary)
@handle_endpoint_errors()
def get_trading_summary(
    request: Request,
    character_id: int,
    include_corp: bool = Query(True),
):
    """
    Get quick trading summary for dashboard.

    Returns key metrics: total P&L, order count, alerts.

    Args:
        character_id: EVE Online character ID
        include_corp: Include corporation data

    Returns:
        TradingSummary with key trading metrics
    """
    service = get_trading_service(request)
    return service.get_trading_summary(character_id, include_corp)


@router.get("/{character_id}/velocity", response_model=VelocityReport)
@handle_endpoint_errors()
def get_velocity_report(
    request: Request,
    character_id: int,
    include_corp: bool = Query(True, description="Include corp trades"),
):
    """
    Get velocity analysis for traded items.

    Classifies items by sell velocity:
    - Fast movers: High daily volume (>=10/day)
    - Medium: Moderate volume (1-10/day)
    - Slow: Low volume (<1/day but sold in 30d)
    - Dead stock: Inventory with no recent sales

    Args:
        character_id: EVE Online character ID
        include_corp: Include corporation transactions

    Returns:
        VelocityReport with items classified by velocity
    """
    service = get_trading_service(request)
    return service.get_velocity_report(character_id, include_corp)


@router.get("/{character_id}/competition", response_model=CompetitionReport)
@handle_endpoint_errors()
def get_competition_report(
    request: Request,
    character_id: int,
    include_corp: bool = Query(True, description="Include corp orders"),
):
    """
    Analyze competitive position for all active orders.

    Compares your orders with market prices to determine:
    - Position (1 = best price, 2+ = beaten)
    - Price gap to best offer
    - Status (ok, undercut, outbid)

    Args:
        character_id: EVE Online character ID
        include_corp: Include corporation orders

    Returns:
        CompetitionReport with order positions and gaps
    """
    service = get_trading_service(request)
    return service.get_competition_report(character_id, include_corp)
