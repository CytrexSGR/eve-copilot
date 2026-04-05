"""
Warzone Trade Routes endpoint for war economy intelligence.
"""

from typing import List, Dict, Any
import logging

from fastapi import APIRouter, Query
import asyncio

from eve_shared.utils.error_handling import handle_endpoint_errors
from ._shared import (
    get_active_warzones,
    get_warzone_demand_batch,
    estimate_jumps_from_jita,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/economy", tags=["War Economy"])


@router.get("/warzone-routes")
@handle_endpoint_errors()
async def get_warzone_routes(
    min_kills: int = Query(50, ge=10, le=500, description="Minimum kills in 24h to qualify as warzone"),
    budget_isk: float = Query(1000000000.0, ge=10000000.0, description="Budget in ISK for cargo")
) -> Dict[str, Any]:
    """
    Calculate profitable trade routes to active warzones.

    Analyzes combat demand in active warzones and calculates potential
    profit margins based on item destruction rates and transport costs.
    """
    # Get active warzones (async via thread)
    warzones = await asyncio.to_thread(get_active_warzones, min_kills)

    if not warzones:
        return {
            "routes": [],
            "total_potential_profit": 0,
            "warzone_count": 0,
            "period": "24h"
        }

    # Extract all region_ids and batch fetch demand data (eliminates N+1 queries)
    region_ids = [w['region_id'] for w in warzones]
    demand_map = await asyncio.to_thread(get_warzone_demand_batch, region_ids, 10)

    routes: List[Dict[str, Any]] = []

    for warzone in warzones:
        region_id = warzone['region_id']

        # Get demand from pre-fetched batch result
        demand_items = demand_map.get(region_id, [])

        if not demand_items:
            continue

        # Calculate route metrics
        jumps = estimate_jumps_from_jita(region_id)
        travel_time_hours = jumps * 0.05  # ~3 min per jump average

        route_items: List[Dict[str, Any]] = []
        total_buy_cost = 0.0
        total_potential_revenue = 0.0

        for item in demand_items:
            jita_price = float(item['jita_price'] or 0)
            qty_destroyed = int(item['quantity_destroyed'] or 0)

            if jita_price <= 0:
                continue

            # Estimate sell price with markup based on demand signal
            # Higher destruction = higher demand = higher markup potential
            demand_signal = min(qty_destroyed / 100, 2.0)  # Cap at 2x multiplier
            base_markup = 1.15  # 15% base markup
            demand_markup = 1 + (demand_signal * 0.10)  # Up to 20% additional
            estimated_sell_price = jita_price * base_markup * demand_markup

            # Calculate how many we can carry (limited by budget and cargo)
            max_by_budget = int(budget_isk / jita_price) if jita_price > 0 else 0
            suggested_qty = min(max_by_budget, qty_destroyed, 1000)  # Cap at 1000 units

            if suggested_qty <= 0:
                continue

            item_buy_cost = jita_price * suggested_qty
            item_revenue = estimated_sell_price * suggested_qty
            item_profit = item_revenue - item_buy_cost

            total_buy_cost += item_buy_cost
            total_potential_revenue += item_revenue

            route_items.append({
                "type_id": item['type_id'],
                "name": item['name'],
                "jita_price": jita_price,
                "estimated_sell_price": round(estimated_sell_price, 2),
                "quantity_destroyed": qty_destroyed,
                "suggested_quantity": suggested_qty,
                "potential_profit": round(item_profit, 2),
                "markup_percent": round((estimated_sell_price / jita_price - 1) * 100, 1)
            })

        if not route_items:
            continue

        # Calculate route profitability metrics
        total_profit = total_potential_revenue - total_buy_cost
        roi = (total_profit / total_buy_cost * 100) if total_buy_cost > 0 else 0
        isk_per_hour = total_profit / travel_time_hours if travel_time_hours > 0 else 0

        routes.append({
            "region_id": region_id,
            "region_name": warzone['region_name'],
            "kills_24h": warzone['kills_24h'],
            "active_battles": warzone['active_battles'],
            "status_level": warzone.get('max_status_level', 'brawl'),
            "jumps_from_jita": jumps,
            "estimated_travel_hours": round(travel_time_hours, 2),
            "items": route_items,
            "cargo_items": len(route_items),
            "total_buy_cost": round(total_buy_cost, 2),
            "total_potential_revenue": round(total_potential_revenue, 2),
            "estimated_profit": round(total_profit, 2),
            "roi_percent": round(roi, 1),
            "isk_per_hour": round(isk_per_hour, 2)
        })

    # Sort by ISK/hour descending
    routes.sort(key=lambda r: r['isk_per_hour'], reverse=True)

    total_potential = sum(r['estimated_profit'] for r in routes)

    return {
        "routes": routes,
        "total_potential_profit": round(total_potential, 2),
        "warzone_count": len(routes),
        "period": "24h",
        "parameters": {
            "min_kills": min_kills,
            "budget_isk": budget_isk
        }
    }
