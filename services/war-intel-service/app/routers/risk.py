# app/routers/risk.py
"""Risk Management Router.

Migrated from monolith to war-intel-service.
Uses eve_shared pattern for database access.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.trading.risk import (
    RiskManagementService,
    RiskSummary,
    ConcentrationRisk,
    LiquidityRisk,
)
from eve_shared.utils.error_handling import handle_endpoint_errors

router = APIRouter()


def get_risk_service() -> RiskManagementService:
    """Get risk service instance."""
    return RiskManagementService()


@router.get("/{character_id}/summary", response_model=RiskSummary)
@handle_endpoint_errors()
def get_risk_summary(
    character_id: int,
    include_corp: bool = Query(True, description="Include corporation data"),
    concentration_threshold: float = Query(10.0, description="Concentration warning threshold (%)"),
    liquidity_threshold: float = Query(7.0, description="Liquidity warning threshold (days to sell)"),
):
    """
    Get comprehensive risk summary for trading portfolio.

    Analyzes:
    - Concentration risk: Items that represent too large a portion of portfolio
    - Liquidity risk: Items that may take too long to sell
    - Overall portfolio health score

    Args:
        character_id: EVE Online character ID
        include_corp: Whether to include corporation orders
        concentration_threshold: Percentage threshold for concentration warnings (default 10%)
        liquidity_threshold: Days-to-sell threshold for liquidity warnings (default 7 days)

    Returns:
        RiskSummary with overall scores and top risks
    """
    service = get_risk_service()
    return service.get_risk_summary(
        character_id,
        include_corp,
        concentration_threshold,
        liquidity_threshold
    )


@router.get("/{character_id}/concentration", response_model=list[ConcentrationRisk])
@handle_endpoint_errors()
def get_concentration_details(
    character_id: int,
    include_corp: bool = Query(True),
):
    """
    Get detailed concentration analysis for all items.

    Returns all items with their portfolio percentage and concentration risk levels.
    """
    service = get_risk_service()
    return service.get_concentration_details(character_id, include_corp)


@router.get("/{character_id}/liquidity", response_model=list[LiquidityRisk])
@handle_endpoint_errors()
def get_liquidity_details(
    character_id: int,
    include_corp: bool = Query(True),
):
    """
    Get detailed liquidity analysis for all items.

    Returns all items with days-to-sell estimates and liquidity scores.
    """
    service = get_risk_service()
    return service.get_liquidity_details(character_id, include_corp)
