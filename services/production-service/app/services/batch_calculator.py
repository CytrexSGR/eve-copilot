"""Batch calculator for manufacturing opportunities.

Calculates profitability for all T1 blueprints and saves results
to manufacturing_opportunities table. Called periodically by scheduler.
"""
import logging
import math
import time
from collections import defaultdict
from typing import Dict, List, Optional

import httpx
from psycopg2.extras import execute_values

from eve_shared.constants import JITA_REGION_ID

logger = logging.getLogger(__name__)

SELL_FEE_PCT = 0.051  # Broker Relations V (1.5%) + Accounting V (3.6%)
EXCLUDED_TYPE_IDS = {47466, 3756, 42685, 30842, 33513, 33515}

# Material group → difficulty (1=easy, 5=hard)
# Based on material source accessibility
_GROUP_DIFFICULTY: Dict[int, int] = {
    18: 1,     # Minerals — buy on market
    1042: 2,   # PI Tier 1
    1034: 2,   # PI Tier 2
    1040: 2,   # PI Tier 3
    1041: 3,   # PI Tier 4
    423: 2,    # Ice products
    427: 3,    # Moon materials
    428: 3,    # Intermediate moon materials
    429: 3,    # Composites (reactions)
    754: 2,    # Salvage
    966: 4,    # Ancient/Sleeper salvage (wormhole)
    732: 4, 733: 4, 734: 4, 735: 4,  # Decryptors
    1141: 4,   # Datacores
    528: 4,    # Artifacts
    526: 4,    # Commodities (exploration loot)
    334: 2,    # Standard components
    873: 3,    # Capital components
    913: 3,    # Advanced capital components
    964: 3,    # Hybrid tech components
    536: 3,    # Structure components
    974: 3,    # Hybrid polymers (T3)
    712: 3,    # Biochemicals
    1996: 4,   # Abyssal materials
    886: 3,    # Rogue drone components
    1676: 5, 1314: 5,  # Special/event
    1136: 2,   # Fuel blocks
    530: 4,    # Materials (exploration)
    4096: 5,   # Molecular-forged
}


class BatchCalculator:
    """Calculates manufacturing profitability for all T1 items."""

    def __init__(self, db):
        self.db = db

    def run(self, me: int = 10) -> dict:
        """Run full batch calculation.

        Returns:
            Result dict with status, job name, and details.
        """
        start = time.time()

        # Step 1: Fetch adjusted prices from ESI
        adjusted_prices = self._fetch_adjusted_prices()
        if not adjusted_prices:
            return {"status": "error", "job": "batch_calculator",
                    "details": {"error": "Failed to fetch adjusted prices from ESI"}}

        # Step 2: Get all T1 blueprints
        blueprints = self._get_all_t1_blueprints()

        # Step 3: Pre-load all materials, output quantities, and group IDs (batch)
        all_materials = self._get_all_materials()
        all_outputs = self._get_all_output_quantities()
        mat_groups = self._get_material_group_ids()

        # Step 4: Calculate opportunities
        opportunities = []
        for bp in blueprints:
            opp = self._calculate_opportunity(
                bp, adjusted_prices, all_materials, all_outputs, mat_groups, me
            )
            if opp:
                opportunities.append(opp)

        # Step 5: Save to DB + enrich with market data
        saved = self._save_opportunities(opportunities)

        elapsed = round(time.time() - start, 2)
        logger.info(
            f"Batch calculator: {saved} opportunities from "
            f"{len(blueprints)} blueprints in {elapsed}s"
        )

        return {
            "status": "completed",
            "job": "batch_calculator",
            "details": {
                "blueprints_scanned": len(blueprints),
                "opportunities_saved": saved,
                "prices_loaded": len(adjusted_prices),
                "elapsed_seconds": elapsed,
            }
        }

    def _fetch_adjusted_prices(self) -> Dict[int, float]:
        """Fetch adjusted prices from ESI /markets/prices/ (public, no auth)."""
        try:
            resp = httpx.get(
                "https://esi.evetech.net/latest/markets/prices/",
                params={"datasource": "tranquility"},
                timeout=30,
            )
            resp.raise_for_status()
            return {
                item["type_id"]: item.get("adjusted_price", 0)
                for item in resp.json()
                if item.get("adjusted_price", 0) > 0
            }
        except Exception as e:
            logger.error(f"Failed to fetch ESI adjusted prices: {e}")
            return {}

    def _get_all_t1_blueprints(self) -> List[dict]:
        """Get all T1 manufacturing blueprints from SDE."""
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT DISTINCT
                        iap."typeID",
                        iap."productTypeID",
                        it."typeName",
                        ig."groupName",
                        ic."categoryName"
                    FROM "industryActivityProducts" iap
                    JOIN "invTypes" it ON it."typeID" = iap."productTypeID"
                    JOIN "invGroups" ig ON ig."groupID" = it."groupID"
                    JOIN "invCategories" ic ON ic."categoryID" = ig."categoryID"
                    LEFT JOIN "invMetaTypes" imt ON imt."typeID" = iap."productTypeID"
                    WHERE iap."activityID" = 1
                    AND it."published" = 1
                    AND (imt."metaGroupID" IS NULL OR imt."metaGroupID" = 1)
                    AND ic."categoryName" NOT IN (
                        'Blueprint', 'Skill', 'Implant', 'Apparel'
                    )
                ''')
                return [
                    {
                        "blueprint_id": row[0],
                        "product_id": row[1],
                        "product_name": row[2],
                        "group_name": row[3],
                        "category_name": row[4],
                    }
                    for row in cur.fetchall()
                    if row[1] not in EXCLUDED_TYPE_IDS
                ]

    def _get_all_materials(self) -> Dict[int, List[tuple]]:
        """Pre-load all manufacturing materials. Returns {blueprint_id: [(type_id, qty), ...]}."""
        materials = defaultdict(list)
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT "typeID", "materialTypeID", "quantity"
                    FROM "industryActivityMaterials"
                    WHERE "activityID" = 1
                ''')
                for row in cur.fetchall():
                    materials[row[0]].append((row[1], row[2]))
        return dict(materials)

    def _get_all_output_quantities(self) -> Dict[tuple, int]:
        """Pre-load all output quantities. Returns {(blueprint_id, product_id): quantity}."""
        outputs = {}
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT "typeID", "productTypeID", "quantity"
                    FROM "industryActivityProducts"
                    WHERE "activityID" = 1
                ''')
                for row in cur.fetchall():
                    outputs[(row[0], row[1])] = row[2]
        return outputs

    def _get_material_group_ids(self) -> Dict[int, int]:
        """Pre-load all material type_id -> groupID mappings."""
        groups = {}
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    SELECT DISTINCT iam."materialTypeID", it."groupID"
                    FROM "industryActivityMaterials" iam
                    JOIN "invTypes" it ON it."typeID" = iam."materialTypeID"
                    WHERE iam."activityID" = 1
                ''')
                for row in cur.fetchall():
                    groups[row[0]] = row[1]
        return groups

    def _calc_difficulty(
        self,
        materials: List[tuple],
        mat_groups: Dict[int, int],
    ) -> int:
        """Calculate difficulty score (1-5) based on material sources."""
        max_diff = 1
        for mat_type_id, _ in materials:
            group_id = mat_groups.get(mat_type_id, 0)
            diff = _GROUP_DIFFICULTY.get(group_id, 3)
            if diff > max_diff:
                max_diff = diff
        return min(max_diff, 5)

    def _calculate_opportunity(
        self,
        bp: dict,
        prices: Dict[int, float],
        all_materials: Dict[int, List[tuple]],
        all_outputs: Dict[tuple, int],
        mat_groups: Dict[int, int],
        me: int,
    ) -> Optional[dict]:
        """Calculate profitability for a single blueprint."""
        product_price = prices.get(bp["product_id"], 0)
        if product_price <= 0:
            return None

        materials = all_materials.get(bp["blueprint_id"], [])
        if not materials:
            return None

        # Calculate material cost with ME
        material_cost = 0.0
        for mat_type_id, base_qty in materials:
            mat_price = prices.get(mat_type_id, 0)
            if mat_price <= 0:
                return None  # Can't calculate without price
            me_qty = max(1, math.ceil(base_qty * (1 - me / 100)))
            material_cost += me_qty * mat_price

        if material_cost <= 0:
            return None

        output_qty = all_outputs.get(
            (bp["blueprint_id"], bp["product_id"]), 1
        )
        sell_price = product_price * output_qty
        profit = sell_price - material_cost
        roi = (profit / material_cost) * 100

        if roi <= 0:
            return None

        return {
            "product_id": bp["product_id"],
            "blueprint_id": bp["blueprint_id"],
            "product_name": bp["product_name"],
            "category": bp["category_name"],
            "group_name": bp["group_name"],
            "difficulty": self._calc_difficulty(materials, mat_groups),
            "material_cost_jita": material_cost,
            "material_cost_amarr": material_cost,
            "material_cost_rens": material_cost,
            "material_cost_dodixie": material_cost,
            "material_cost_hek": material_cost,
            "cheapest_material_cost": material_cost,
            "cheapest_material_region": "the_forge",
            "sell_price_jita": sell_price,
            "sell_price_amarr": sell_price,
            "sell_price_rens": sell_price,
            "sell_price_dodixie": sell_price,
            "sell_price_hek": sell_price,
            "best_sell_price": sell_price,
            "best_sell_region": "the_forge",
            "profit": round(profit, 2),
            "roi": round(roi, 2),
            "me_level": me,
        }

    def _save_opportunities(self, opportunities: List[dict]) -> int:
        """Save opportunities to DB with market price enrichment."""
        if not opportunities:
            return 0

        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE manufacturing_opportunities")

                rows = [
                    (opp["product_id"], opp["blueprint_id"], opp["product_name"],
                     opp["category"], opp["group_name"], opp["difficulty"],
                     opp["material_cost_jita"], opp["material_cost_amarr"],
                     opp["material_cost_rens"], opp["material_cost_dodixie"],
                     opp["material_cost_hek"],
                     opp["cheapest_material_cost"], opp["cheapest_material_region"],
                     opp["sell_price_jita"], opp["sell_price_amarr"],
                     opp["sell_price_rens"], opp["sell_price_dodixie"],
                     opp["sell_price_hek"],
                     opp["best_sell_price"], opp["best_sell_region"],
                     opp["profit"], opp["roi"], opp["me_level"])
                    for opp in opportunities
                ]
                execute_values(
                    cur,
                    """
                    INSERT INTO manufacturing_opportunities (
                        product_id, blueprint_id, product_name, category,
                        group_name, difficulty,
                        material_cost_jita, material_cost_amarr,
                        material_cost_rens, material_cost_dodixie,
                        material_cost_hek,
                        cheapest_material_cost, cheapest_material_region,
                        sell_price_jita, sell_price_amarr, sell_price_rens,
                        sell_price_dodixie, sell_price_hek,
                        best_sell_price, best_sell_region,
                        profit, roi, me_level, updated_at
                    ) VALUES %s
                    """,
                    rows,
                    template="(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())",
                    page_size=500,
                )

                # Enrich with market_prices (volume, fees, net_profit)
                cur.execute("""
                    UPDATE manufacturing_opportunities mo SET
                        avg_daily_volume = COALESCE(mp.avg_daily_volume, 0),
                        sell_volume = COALESCE(mp.sell_volume, 0),
                        risk_score = COALESCE(mp.risk_score, 50),
                        days_to_sell = mp.days_to_sell_100,
                        net_profit = ROUND(
                            (COALESCE(mp.lowest_sell, mo.best_sell_price)
                             * (1 - %s))
                            - mo.cheapest_material_cost, 2),
                        net_roi = ROUND(
                            ((COALESCE(mp.lowest_sell, mo.best_sell_price)
                              * (1 - %s))
                             - mo.cheapest_material_cost)
                            / NULLIF(mo.cheapest_material_cost, 0) * 100, 2)
                    FROM market_prices mp
                    WHERE mp.type_id = mo.product_id
                    AND mp.region_id = %s
                """, (SELL_FEE_PCT, SELL_FEE_PCT, JITA_REGION_ID))

                # Fallback for items not in market_prices
                cur.execute("""
                    UPDATE manufacturing_opportunities SET
                        net_profit = ROUND(
                            best_sell_price * (1 - %s)
                            - cheapest_material_cost, 2),
                        net_roi = ROUND(
                            (best_sell_price * (1 - %s)
                             - cheapest_material_cost)
                            / NULLIF(cheapest_material_cost, 0) * 100, 2)
                    WHERE net_profit IS NULL
                """, (SELL_FEE_PCT, SELL_FEE_PCT))

                conn.commit()

        return len(opportunities)
