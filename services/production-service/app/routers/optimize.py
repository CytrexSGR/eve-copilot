"""Production optimization router - Regional production analysis."""
import logging
from typing import Dict, List, Optional, Any

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from eve_shared.constants import TRADE_HUB_REGIONS

logger = logging.getLogger(__name__)
router = APIRouter()

# Region ID to name mapping (derived from shared constants)
REGION_ID_TO_NAME = {v: k for k, v in TRADE_HUB_REGIONS.items()}

# Region name to ID mapping (alias for shared constant)
REGIONS = TRADE_HUB_REGIONS


class MaterialDetail(BaseModel):
    """Material details with regional prices."""
    type_id: int
    name: str
    base_quantity: int
    adjusted_quantity: int
    prices_by_region: Dict[str, Optional[float]]
    volumes_by_region: Dict[str, int]


class OptimizeResponse(BaseModel):
    """Response model for production optimization."""
    type_id: int
    item_name: str
    me_level: int
    materials: List[MaterialDetail]
    production_cost_by_region: Dict[str, Optional[float]]
    cheapest_production_region: Optional[str]
    cheapest_production_cost: Optional[float]
    product_prices: Dict[str, Dict[str, Optional[float]]]
    best_sell_region: str
    best_sell_price: float


@router.get("/optimize/{type_id}")
def api_optimize_production(
    request: Request,
    type_id: int,
    me: int = Query(default=10, ge=0, le=10, description="Material Efficiency level")
) -> OptimizeResponse:
    """
    Find optimal regions for production using cached regional prices.

    Analyzes all major trade hub regions to determine:
    - Cheapest region to source materials
    - Best region to sell the product
    - Complete material breakdown with regional prices

    Args:
        type_id: The type ID of the item to manufacture
        me: Material Efficiency level (0-10, default 10)

    Returns:
        Regional production analysis with optimal buying/selling regions
    """
    try:
        db = request.app.state.db

        with db.cursor() as cur:
            # Get materials for the blueprint
            cur.execute("""
                SELECT m."materialTypeID", t."typeName", m.quantity
                FROM "invTypeMaterials" m
                JOIN "invTypes" t ON m."materialTypeID" = t."typeID"
                WHERE m."typeID" = %s
            """, (type_id,))
            materials = cur.fetchall()

            if not materials:
                raise HTTPException(
                    status_code=404,
                    detail="No blueprint found for this item"
                )

            # Get the item name
            cur.execute(
                'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                (type_id,)
            )
            item_row = cur.fetchone()
            item_name = item_row[0] if item_row else f"Type {type_id}"

            # Get all material type IDs plus the product type ID
            material_type_ids = [m[0] for m in materials]
            all_type_ids = material_type_ids + [type_id]

            # Fetch all regional prices in one query
            cur.execute("""
                SELECT type_id, region_id, lowest_sell, highest_buy, sell_volume, buy_volume
                FROM market_prices
                WHERE type_id = ANY(%s)
            """, (all_type_ids,))

            # Build price dictionary by type_id and region
            all_prices: Dict[int, Dict[str, Dict[str, Any]]] = {}
            for row in cur.fetchall():
                tid, region_id, lowest_sell, highest_buy, sell_vol, buy_vol = row
                region_name = REGION_ID_TO_NAME.get(region_id)
                if not region_name:
                    continue
                if tid not in all_prices:
                    all_prices[tid] = {}
                all_prices[tid][region_name] = {
                    'lowest_sell': float(lowest_sell) if lowest_sell else None,
                    'highest_buy': float(highest_buy) if highest_buy else None,
                    'sell_volume': sell_vol or 0,
                    'buy_volume': buy_vol or 0,
                }

        # Apply ME factor to material quantities
        me_factor = 1 - (me / 100)
        material_details: List[MaterialDetail] = []

        for mat_id, mat_name, base_qty in materials:
            adjusted_qty = max(1, int(base_qty * me_factor))
            mat_prices = all_prices.get(mat_id, {})
            material_details.append(MaterialDetail(
                type_id=mat_id,
                name=mat_name,
                base_quantity=base_qty,
                adjusted_quantity=adjusted_qty,
                prices_by_region={
                    r: d.get("lowest_sell") for r, d in mat_prices.items()
                },
                volumes_by_region={
                    r: d.get("sell_volume", 0) for r, d in mat_prices.items()
                }
            ))

        # Calculate total production cost per region
        region_totals: Dict[str, Optional[float]] = {}
        for region in REGIONS.keys():
            total = sum(
                (mat.prices_by_region.get(region) or 0) * mat.adjusted_quantity
                for mat in material_details
            )
            region_totals[region] = total if total > 0 else None

        # Find cheapest production region
        valid_regions = [(r, c) for r, c in region_totals.items() if c]
        best_region = (
            min(valid_regions, key=lambda x: x[1])
            if valid_regions else (None, None)
        )

        # Get product prices for selling analysis
        product_prices_raw = all_prices.get(type_id, {})
        product_prices = {
            r: {
                "lowest_sell": d.get("lowest_sell"),
                "highest_buy": d.get("highest_buy")
            }
            for r, d in product_prices_raw.items()
        }

        # Find best sell region (highest sell price)
        best_sell = max(
            [(r, p.get("lowest_sell", 0) or 0) for r, p in product_prices.items()],
            key=lambda x: x[1],
            default=("the_forge", 0)
        )

        return OptimizeResponse(
            type_id=type_id,
            item_name=item_name,
            me_level=me,
            materials=material_details,
            production_cost_by_region=region_totals,
            cheapest_production_region=best_region[0],
            cheapest_production_cost=best_region[1],
            product_prices=product_prices,
            best_sell_region=best_sell[0],
            best_sell_price=best_sell[1]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Optimization failed for type_id {type_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
