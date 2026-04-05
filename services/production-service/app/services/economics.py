"""Production economics service - profitability analysis."""
import logging
import math
from typing import Dict, List, Any, Optional

from app.models import ProductionEconomics, RegionEconomics
from app.services.repository import ProductionRepository
from app.services.market_client import LocalMarketClient
from eve_shared.constants import JITA_REGION_ID, TRADE_HUB_REGIONS

logger = logging.getLogger(__name__)


class ProductionEconomicsService:
    """Service for production economics and profitability analysis."""

    def __init__(self, db):
        """Initialize with database pool."""
        self.repository = ProductionRepository(db)
        self.market_client = LocalMarketClient(db)

    def get_economics(
        self,
        type_id: int,
        region_id: int = JITA_REGION_ID,
        me: int = 0,
        te: int = 0
    ) -> Dict[str, Any]:
        """
        Get complete production economics analysis for an item.

        Args:
            type_id: Item type ID
            region_id: Region ID for pricing
            me: Material Efficiency level
            te: Time Efficiency level

        Returns:
            Economics data with costs, prices, profit, and ROI
        """
        name = self.repository.get_item_name(type_id)
        if not name:
            return {"error": f"Item not found: {type_id}"}

        blueprint_id = self.repository.get_blueprint_for_product(type_id)
        if not blueprint_id:
            return {"error": f"No blueprint found for: {name}"}

        # Get materials with ME
        materials = self.repository.get_blueprint_materials(blueprint_id)
        me_factor = 1 - (me / 100)

        material_type_ids = [m[0] for m in materials]
        all_type_ids = material_type_ids + [type_id]

        # Get prices
        prices = self.market_client.get_prices_bulk(all_type_ids, region_id)

        # Calculate material cost
        material_cost = 0.0
        material_details = []
        for material_id, base_qty in materials:
            adjusted_qty = max(1, math.ceil(base_qty * me_factor))
            mat_name = self.repository.get_item_name(material_id) or "Unknown"
            unit_price = prices.get(material_id, 0.0)
            total = unit_price * adjusted_qty

            material_details.append({
                "type_id": material_id,
                "name": mat_name,
                "base_quantity": base_qty,
                "adjusted_quantity": adjusted_qty,
                "unit_price": unit_price,
                "total_cost": total
            })
            material_cost += total

        # Get output quantity
        output_per_run = self.repository.get_output_quantity(blueprint_id, type_id)

        # Calculate revenue and profit
        product_price = prices.get(type_id, 0.0)
        revenue = product_price * output_per_run
        profit = revenue - material_cost
        margin = (profit / material_cost * 100) if material_cost > 0 else 0.0
        roi = margin  # For single run, ROI equals margin

        # Get production time
        base_time = self.repository.get_base_production_time(blueprint_id)
        te_factor = 1 - (te / 100)
        actual_time = int(base_time * te_factor)

        # Calculate profit per hour
        profit_per_hour = (profit / actual_time * 3600) if actual_time > 0 else 0.0

        # Get region name
        region_name = next(
            (name for name, rid in TRADE_HUB_REGIONS.items() if rid == region_id),
            "Unknown"
        )

        # Get daily volume from market data
        daily_volume = self._get_daily_volume(type_id, region_id)

        return {
            "type_id": type_id,
            "name": name,
            "region_id": region_id,
            "region_name": region_name,
            "me": me,
            "te": te,
            "output_per_run": output_per_run,
            "materials": material_details,
            "material_cost": round(material_cost, 2),
            "product_price": round(product_price, 2),
            "revenue": round(revenue, 2),
            "profit": round(profit, 2),
            "margin_percent": round(margin, 2),
            "roi_percent": round(roi, 2),
            "production_time_seconds": actual_time,
            "profit_per_hour": round(profit_per_hour, 2),
            "daily_volume": daily_volume,
            "is_profitable": profit > 0
        }

    def _get_daily_volume(self, type_id: int, region_id: int) -> int:
        """Get average daily volume from market_prices table."""
        try:
            with self.repository.db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT COALESCE(avg_daily_volume, 0)
                        FROM market_prices
                        WHERE type_id = %s AND region_id = %s
                    """, (type_id, region_id))
                    row = cur.fetchone()
                    return int(row[0]) if row else 0
        except Exception as e:
            logger.warning(f"Failed to get daily volume for {type_id}: {e}")
            return 0

    def compare_regions(self, type_id: int) -> Dict[str, Any]:
        """Compare production profitability across multiple regions."""
        name = self.repository.get_item_name(type_id)
        if not name:
            return {"error": f"Item not found: {type_id}"}

        regions = []
        best_region = None
        best_profit = None

        for region_name, region_id in TRADE_HUB_REGIONS.items():
            economics = self.get_economics(type_id, region_id)
            if "error" not in economics:
                regions.append(economics)
                profit = economics.get("profit", 0)
                if best_profit is None or profit > best_profit:
                    best_profit = profit
                    best_region = region_name

        return {
            "type_id": type_id,
            "name": name,
            "regions": regions,
            "best_region": best_region,
            "best_profit": best_profit
        }

    def find_opportunities(
        self,
        region_id: int = JITA_REGION_ID,
        min_roi: float = 0,
        min_profit: float = 0,
        min_volume: int = 0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Find profitable manufacturing opportunities from pre-calculated table.

        Uses manufacturing_opportunities table (populated by batch_calculator every 5 min)
        instead of N+1 individual economics calculations.
        """
        from psycopg2.extras import RealDictCursor

        where_clauses = [
            "mo.roi >= %s",
            "COALESCE(mo.net_profit, mo.profit) >= %s",
            "COALESCE(mo.sell_volume, 0) > 0",
        ]
        params: list = [min_roi, min_profit]

        if min_volume > 0:
            where_clauses.append("COALESCE(mo.avg_daily_volume, 0) >= %s")
            params.append(min_volume)

        where_sql = " AND ".join(where_clauses)

        try:
            with self.repository.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(f"""
                        SELECT
                            mo.product_id as type_id,
                            mo.product_name as type_name,
                            mo.category,
                            mo.group_name,
                            mo.cheapest_material_cost as production_cost,
                            COALESCE(mp.lowest_sell, mo.best_sell_price) as sell_price,
                            COALESCE(mo.net_profit, mo.profit) as profit_per_unit,
                            COALESCE(mo.net_roi, mo.roi) as roi_percent,
                            COALESCE(mo.avg_daily_volume, 0) as daily_volume
                        FROM manufacturing_opportunities mo
                        LEFT JOIN market_prices mp ON mp.type_id = mo.product_id AND mp.region_id = %s
                        WHERE {where_sql}
                        ORDER BY
                            CASE WHEN COALESCE(mo.avg_daily_volume, 0) > 0 THEN 0 ELSE 1 END,
                            COALESCE(mo.net_roi, mo.roi) DESC
                        LIMIT %s
                    """, (JITA_REGION_ID, *params, limit))
                    rows = cur.fetchall()
        except Exception as e:
            logger.error(f"Failed to query manufacturing_opportunities: {e}")
            rows = []

        opportunities = []
        for row in rows:
            opportunities.append({
                "type_id": row["type_id"],
                "type_name": row["type_name"],
                "group": row.get("group_name", "Unknown"),
                "production_cost": float(row["production_cost"] or 0),
                "sell_price": float(row["sell_price"] or 0),
                "profit_per_unit": float(row["profit_per_unit"] or 0),
                "roi_percent": min(float(row["roi_percent"] or 0), 9999),
                "daily_volume": int(row["daily_volume"] or 0),
            })

        region_name = next(
            (name for name, rid in TRADE_HUB_REGIONS.items() if rid == region_id),
            "Unknown"
        )

        return {
            "region_id": region_id,
            "region_name": region_name,
            "min_roi": min_roi,
            "min_profit": min_profit,
            "opportunities": opportunities,
            "total_found": len(opportunities)
        }
