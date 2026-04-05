"""Market statistics router."""
import logging

from fastapi import APIRouter, HTTPException, Request, Query

from app.models import CacheStats, JITA_REGION_ID
from app.services import MarketRepository, ESIClient
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/stats/{region_id}/{type_id}")
@handle_endpoint_errors()
def get_market_stats(
    request: Request,
    region_id: int,
    type_id: int
) -> dict:
    """
    Get market statistics for an item in a region.

    Returns: lowest_sell, highest_buy, total_orders, volumes, spread
    """
    esi = ESIClient()
    stats = esi.get_market_stats(region_id, type_id)

    if not stats or not stats.get("total_orders"):
        raise HTTPException(
            status_code=404,
            detail=f"No market data found for type_id {type_id} in region {region_id}"
        )

    return stats


@router.get("/cache/stats")
@handle_endpoint_errors()
def get_cache_stats(request: Request) -> CacheStats:
    """
    Get statistics about the market price cache.

    Returns: total_items, oldest_entry, newest_entry, is_stale
    """
    db = request.app.state.db
    repo = MarketRepository(db)
    return repo.get_cache_stats()


@router.post("/cache/clear")
@handle_endpoint_errors()
def clear_cache(request: Request) -> dict:
    """
    Clear the market price cache (Redis L1 only).

    PostgreSQL L2 cache is not cleared to maintain persistence.
    """
    redis = request.app.state.redis

    # Clear all market price keys from Redis
    pattern = "market:price:*"
    cursor = 0
    deleted = 0

    while True:
        cursor, keys = redis.client.scan(cursor, match=pattern, count=1000)
        if keys:
            redis.client.delete(*keys)
            deleted += len(keys)
        if cursor == 0:
            break

    return {
        "status": "cache cleared",
        "keys_deleted": deleted
    }


@router.get("/orders/{type_id}")
@handle_endpoint_errors()
def get_market_orders(
    request: Request,
    type_id: int,
    region_id: int = Query(default=JITA_REGION_ID, description="Region ID"),
    order_type: str = Query(default="all", description="Order type: 'buy', 'sell', or 'all'")
) -> list:
    """
    Get raw market orders for an item in a region.

    Directly queries ESI for fresh order data.
    """
    if order_type not in ("buy", "sell", "all"):
        raise HTTPException(
            status_code=400,
            detail="order_type must be 'buy', 'sell', or 'all'"
        )

    esi = ESIClient()
    orders = esi.get_market_orders(region_id, type_id, order_type)

    if not orders:
        raise HTTPException(
            status_code=404,
            detail=f"No orders found for type_id {type_id} in region {region_id}"
        )

    return orders
