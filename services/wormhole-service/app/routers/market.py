"""Wormhole market signals API."""
from fastapi import APIRouter, Query
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.services.market_analyzer import MarketAnalyzer
from app.services.commodity_tracker import CommodityTracker

router = APIRouter(prefix="/market", tags=["market"])
analyzer = MarketAnalyzer()
tracker = CommodityTracker()


@router.get("/signals")
@handle_endpoint_errors()
def get_market_signals(
    days: int = Query(7, ge=1, le=30, description="Lookback period in days")
):
    """
    Get market demand signals from J-Space activity.

    Returns eviction impact, capital losses, and demand indicators.
    """
    return analyzer.get_market_signals(days=days)


@router.get("/commodities")
@handle_endpoint_errors()
def get_commodity_prices():
    """
    Get current prices for all WH commodities.

    Returns:
    - Gas prices (Fullerites) with tiers and trends
    - Blue loot prices with NPC buy values
    - Polymer prices with trends
    """
    return tracker.get_commodity_prices()


@router.get("/eviction-intel")
@handle_endpoint_errors()
def get_eviction_intel(
    days: int = Query(7, ge=1, le=30, description="Lookback period in days")
):
    """
    Get detailed eviction intelligence.

    Returns:
    - Recent evictions with victim details
    - Structures lost
    - Estimated loot values and timing
    """
    return tracker.get_eviction_intel(days=days)


@router.get("/disruptions")
@handle_endpoint_errors()
def get_supply_disruptions(
    days: int = Query(7, ge=1, le=30, description="Lookback period in days")
):
    """
    Get supply chain disruption alerts.

    Identifies major producers that were evicted and
    predicts market impact.
    """
    return tracker.get_supply_disruptions(days=days)


@router.get("/index")
@handle_endpoint_errors()
def get_market_index():
    """
    Get J-Space Market Index.

    Aggregate health indicator showing overall market direction
    with buy/sell/hold recommendation.
    """
    return tracker.get_market_index()


@router.get("/price-history")
@handle_endpoint_errors()
def get_price_history(
    days: int = Query(7, ge=1, le=30, description="History period in days")
):
    """
    Get price history for sparklines.

    Returns historical prices keyed by type_id with:
    - prices: daily price series
    - min/max/avg prices
    - percentage vs average
    """
    return tracker.get_price_history(days=days)


@router.get("/price-context")
@handle_endpoint_errors()
def get_price_context():
    """
    Get 30-day price context for historical comparison.

    Returns context keyed by type_id with:
    - 30-day average price
    - current price vs 30-day average
    """
    return tracker.get_price_context()
