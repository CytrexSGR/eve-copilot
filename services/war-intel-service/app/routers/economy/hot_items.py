"""
Hot Items Extended endpoint for war economy intelligence.
"""

from typing import List, Dict, Any
import logging

from fastapi import APIRouter, Query
import asyncio

from eve_shared.utils.error_handling import handle_endpoint_errors
from ._shared import (
    get_base_hot_items,
    get_destruction_zones_batch,
    get_destruction_trends_batch,
    get_regional_prices_batch,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/economy", tags=["War Economy"])


@router.get("/hot-items-extended")
@handle_endpoint_errors()
async def get_hot_items_extended(limit: int = Query(10, ge=1, le=50)) -> Dict[str, Any]:
    """
    Extended hot items with regional prices, destruction zones, and trends.

    Used by the Trading tab for combat-driven market intelligence.
    """
    # Get base hot items from database (async)
    base_items = await asyncio.to_thread(get_base_hot_items, limit)

    if not base_items:
        return {
            "items": [],
            "total_opportunity_value": 0,
            "item_count": 0,
            "period": "24h"
        }

    # Extract all type_ids for batched queries
    type_ids = [item['item_type_id'] for item in base_items]

    # Batch fetch all data in parallel (3 DB queries instead of N+1)
    destruction_zones_map, trends_map, regional_prices_map = await asyncio.gather(
        asyncio.to_thread(get_destruction_zones_batch, type_ids, 1),
        asyncio.to_thread(get_destruction_trends_batch, type_ids),
        asyncio.to_thread(get_regional_prices_batch, type_ids)
    )

    # Enrich each item with extended data
    items: List[Dict[str, Any]] = []
    for item in base_items:
        type_id = item['item_type_id']

        # Get regional prices
        regional_prices = regional_prices_map.get(type_id, {})
        if not regional_prices:
            regional_prices = {"jita": item['jita_price']}

        # Find best buy/sell
        valid_prices = {k: v for k, v in regional_prices.items() if v > 0}
        best_buy = min(valid_prices.items(), key=lambda x: x[1]) if valid_prices else ("jita", item['jita_price'])
        best_sell = max(valid_prices.items(), key=lambda x: x[1]) if valid_prices else ("jita", item['jita_price'])

        # Calculate spread
        spread = 0.0
        if best_buy[1] > 0:
            spread = round(((best_sell[1] - best_buy[1]) / best_buy[1]) * 100, 1)

        # Get destruction zones from batched result
        destruction_zones = destruction_zones_map.get(type_id, [])

        # Get trend from batched result
        trend_7d = trends_map.get(type_id, 0.0)

        # Calculate opportunity value
        opportunity_value = item['quantity_destroyed'] * item['jita_price']

        items.append({
            "type_id": type_id,
            "name": item['item_name'],
            "group": item['group_name'],
            "quantity_destroyed": item['quantity_destroyed'],
            "opportunity_value": opportunity_value,
            "regional_prices": regional_prices,
            "best_buy": {"hub": best_buy[0], "price": best_buy[1]},
            "best_sell": {"hub": best_sell[0], "price": best_sell[1]},
            "spread_percent": spread,
            "destruction_zones": destruction_zones,
            "trend_7d": trend_7d,
            "suggested_margin": spread if destruction_zones else 0
        })

    # Calculate totals
    total_opportunity = sum(i['opportunity_value'] for i in items)

    return {
        "items": items,
        "total_opportunity_value": total_opportunity,
        "item_count": len(items),
        "period": "24h"
    }
