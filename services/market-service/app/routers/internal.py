"""Internal endpoints for scheduler-triggered market jobs.

These endpoints are called by the scheduler-service via HTTP POST
and are not exposed through the API gateway.
"""

import asyncio
import logging

from fastapi import APIRouter, Request

from app.services.internal.manipulation_scanner import scan_manipulation
from app.services.internal.regional_prices import refresh_regional_prices
from app.services.internal.arbitrage_calculator import calculate_arbitrage
from app.services.internal.undercut_checker import check_undercuts
from app.services.internal.fuel_scanner import scan_fuel_markets
from app.services.internal.price_snapshotter import snapshot_prices

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/internal", tags=["Internal Jobs"])


@router.post("/scan-manipulation")
async def api_scan_manipulation(request: Request):
    """Run market manipulation scanner across trade hub regions."""
    db = request.app.state.db
    return await asyncio.to_thread(scan_manipulation, db)


@router.post("/refresh-regional-prices")
async def api_refresh_regional_prices(request: Request):
    """Fetch and save regional prices from ESI for all trade hubs."""
    db = request.app.state.db
    return await asyncio.to_thread(refresh_regional_prices, db)


@router.post("/calculate-arbitrage")
async def api_calculate_arbitrage(request: Request):
    """Calculate profitable arbitrage routes between trade hubs."""
    db = request.app.state.db
    return await asyncio.to_thread(calculate_arbitrage, db)


@router.post("/check-undercuts")
async def api_check_undercuts(request: Request):
    """Check character orders for undercuts."""
    db = request.app.state.db
    return await asyncio.to_thread(check_undercuts, db)


@router.post("/scan-fuel-markets")
async def api_scan_fuel_markets(request: Request):
    """Scan fuel isotope markets for anomalies."""
    db = request.app.state.db
    return await asyncio.to_thread(scan_fuel_markets, db)


@router.post("/snapshot-prices")
async def api_snapshot_prices(request: Request):
    """Snapshot critical item prices for manipulation detection."""
    db = request.app.state.db
    return await asyncio.to_thread(snapshot_prices, db)
