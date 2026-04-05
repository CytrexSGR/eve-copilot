"""Market prices router - L1/L2/L3 cached price lookups."""
import logging
from typing import Dict, List

from fastapi import APIRouter, HTTPException, Request, Query

from app.models import (
    MarketPrice,
    PriceRequest,
    PriceBulkRequest,
    JITA_REGION_ID,
)
from app.services import UnifiedMarketRepository, ESIClient
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


def get_repository(request: Request) -> UnifiedMarketRepository:
    """Get unified market repository from app state."""
    db = request.app.state.db
    redis = request.app.state.redis
    esi = ESIClient()
    return UnifiedMarketRepository(redis.client, db, esi)


@router.get("/price/{type_id}")
@handle_endpoint_errors()
def get_price(
    request: Request,
    type_id: int,
    region_id: int = Query(default=JITA_REGION_ID, description="Region ID (default: Jita)")
) -> MarketPrice:
    """
    Get price for a single item using L1/L2/L3 cache hierarchy.

    - L1: Redis (5 min TTL)
    - L2: PostgreSQL (1 hour TTL)
    - L3: ESI API (fallback)
    """
    repo = get_repository(request)
    price = repo.get_price(type_id, region_id)

    if not price:
        raise HTTPException(
            status_code=404,
            detail=f"Price not found for type_id {type_id} in region {region_id}"
        )

    return price


@router.post("/prices")
@handle_endpoint_errors()
def get_prices_bulk(
    request: Request,
    price_request: PriceBulkRequest
) -> Dict[int, MarketPrice]:
    """
    Get prices for multiple items in a single request.

    Maximum 1000 items per request.
    """
    if len(price_request.type_ids) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Maximum 1000 type IDs per request"
        )

    repo = get_repository(request)
    prices = repo.get_prices(price_request.type_ids, price_request.region_id)

    return prices


@router.get("/prices/hot-items")
@handle_endpoint_errors()
def get_hot_items_prices(
    request: Request,
    region_id: int = Query(default=JITA_REGION_ID, description="Region ID")
) -> Dict[int, MarketPrice]:
    """
    Get prices for all 'hot' items (minerals, isotopes, fuel, moon materials).

    Hot items are proactively cached for faster access.
    """
    from app.services import get_hot_items

    repo = get_repository(request)
    hot_type_ids = list(get_hot_items())
    prices = repo.get_prices(hot_type_ids, region_id)

    return prices


@router.get("/prices/hot-items/categories")
@handle_endpoint_errors()
def get_hot_items_by_category(
    request: Request,
    region_id: int = Query(default=JITA_REGION_ID, description="Region ID")
) -> Dict[str, Dict[int, MarketPrice]]:
    """
    Get hot items prices organized by category.

    Categories: minerals, isotopes, fuel_blocks, moon_materials, production_materials
    """
    from app.services import get_hot_items_by_category

    repo = get_repository(request)
    categories = get_hot_items_by_category()

    result = {}
    for category, type_ids in categories.items():
        prices = repo.get_prices(list(type_ids), region_id)
        result[category] = prices

    return result


@router.post("/prices/refresh-hot-items")
@handle_endpoint_errors()
def refresh_hot_items(request: Request) -> dict:
    """
    Manually trigger refresh of all hot items.

    This fetches fresh prices from ESI and updates all cache layers.
    """
    repo = get_repository(request)
    result = repo.refresh_hot_items()
    return result
