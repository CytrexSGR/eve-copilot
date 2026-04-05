"""Invention Cost Calculator.

Calculates T2 production costs including invention step:
1. Find T2 blueprint via industryActivityProducts (activityID=8)
2. Get invention inputs (datacores) from industryActivityMaterials (activityID=8)
3. Get invention probability from industryActivityProbabilities
4. Invention cost = input_cost / (output_runs × probability)
5. T2 manufacturing BOM with ME bonus + invention cost as virtual input
"""

import math
import logging
from decimal import Decimal
from typing import Optional, Dict, List, Any

from eve_shared.constants import JITA_REGION_ID

logger = logging.getLogger(__name__)

# Activity IDs
ACTIVITY_MANUFACTURING = 1
ACTIVITY_INVENTION = 8

# Decryptor effect attribute IDs (from SDE dgmTypeAttributes)
ATTR_INVENTION_ME_MODIFIER = 1113
ATTR_INVENTION_TE_MODIFIER = 1114
ATTR_INVENTION_RUN_MODIFIER = 1124
ATTR_INVENTION_PROB_MODIFIER = 1112


class InventionService:
    """Calculates invention costs and T2 production economics."""

    def __init__(self, db):
        self.db = db

    def get_invention_cost(
        self,
        t2_type_id: int,
        decryptor_type_id: Optional[int] = None,
        region_id: int = JITA_REGION_ID,
    ) -> Optional[dict]:
        """Calculate the full invention cost breakdown for a T2 item.

        Args:
            t2_type_id: The type_id of the T2 item to produce
            decryptor_type_id: Optional decryptor to use
            region_id: Region for price lookups (default: The Forge/Jita)

        Returns:
            Dict with invention cost details or None if not a T2 item.
        """
        # Step 1: Find T2 blueprint from the product
        t2_bp_id = self._get_blueprint_for_product(t2_type_id, ACTIVITY_MANUFACTURING)
        if not t2_bp_id:
            return None

        # Step 2: Find invention blueprint (T1 BP that invents this T2 BP)
        t1_bp_id = self._find_invention_source(t2_bp_id)
        if not t1_bp_id:
            return None  # Not a T2 item (no invention path)

        # Step 3: Get invention inputs (datacores)
        invention_inputs = self._get_activity_materials(t1_bp_id, ACTIVITY_INVENTION)
        if not invention_inputs:
            return None

        # Step 4: Get invention probability
        probability = self._get_invention_probability(t1_bp_id, t2_bp_id)
        if not probability or probability <= 0:
            return None

        # Step 5: Get base invention output runs
        base_runs = self._get_invention_output_runs(t2_bp_id)

        # Step 6: Apply decryptor if specified
        decryptor_info = None
        me_modifier = 0
        te_modifier = 0
        run_modifier = 0
        prob_modifier = 1.0
        decryptor_cost = Decimal("0")

        if decryptor_type_id:
            decryptor_info = self._get_decryptor_effects(decryptor_type_id)
            if decryptor_info:
                me_modifier = decryptor_info.get("me_modifier", 0)
                te_modifier = decryptor_info.get("te_modifier", 0)
                run_modifier = decryptor_info.get("run_modifier", 0)
                prob_modifier = decryptor_info.get("prob_modifier", 1.0)
                decryptor_cost = self._get_price(decryptor_type_id, region_id)

        adjusted_probability = probability * prob_modifier
        adjusted_runs = max(1, base_runs + run_modifier)
        result_me = 2 + me_modifier  # T2 base ME = 2
        result_te = 4 + te_modifier  # T2 base TE = 4

        # Step 7: Calculate invention input costs
        total_input_cost = decryptor_cost
        input_details = []

        for mat_id, qty in invention_inputs:
            name = self._get_type_name(mat_id) or f"Type {mat_id}"
            price = self._get_price(mat_id, region_id)
            cost = price * qty
            total_input_cost += cost
            input_details.append({
                "type_id": mat_id,
                "type_name": name,
                "quantity": qty,
                "unit_price": float(price),
                "total_cost": float(cost),
            })

        if decryptor_type_id and decryptor_cost > 0:
            dec_name = self._get_type_name(decryptor_type_id) or "Decryptor"
            input_details.append({
                "type_id": decryptor_type_id,
                "type_name": dec_name,
                "quantity": 1,
                "unit_price": float(decryptor_cost),
                "total_cost": float(decryptor_cost),
            })

        # Step 8: Cost per T2 BPC = total_input_cost / (runs × probability)
        cost_per_bpc = float(total_input_cost / Decimal(str(
            adjusted_runs * adjusted_probability
        )))

        # Step 9: Get T2 manufacturing materials
        t2_materials = self._get_activity_materials(t2_bp_id, ACTIVITY_MANUFACTURING)
        t2_bom = []
        t2_material_cost = Decimal("0")
        me_factor = 1 - (result_me / 100)

        for mat_id, base_qty in t2_materials:
            qty_per_run = max(1, math.ceil(base_qty * me_factor))
            name = self._get_type_name(mat_id) or f"Type {mat_id}"
            price = self._get_price(mat_id, region_id)
            cost = price * qty_per_run
            t2_material_cost += cost
            t2_bom.append({
                "type_id": mat_id,
                "type_name": name,
                "base_quantity": base_qty,
                "quantity_per_run": qty_per_run,
                "unit_price": float(price),
                "total_cost": float(cost),
            })

        t1_bp_name = self._get_type_name(t1_bp_id) or "Unknown"
        t2_item_name = self._get_type_name(t2_type_id) or "Unknown"
        t2_bp_name = self._get_type_name(t2_bp_id) or "Unknown"

        return {
            "t2_type_id": t2_type_id,
            "t2_name": t2_item_name,
            "t2_blueprint_id": t2_bp_id,
            "t1_blueprint_id": t1_bp_id,
            "t1_blueprint_name": t1_bp_name,
            "invention": {
                "inputs": input_details,
                "total_input_cost": float(total_input_cost),
                "base_probability": probability,
                "adjusted_probability": adjusted_probability,
                "base_output_runs": base_runs,
                "adjusted_output_runs": adjusted_runs,
                "cost_per_bpc": cost_per_bpc,
                "result_me": result_me,
                "result_te": result_te,
            },
            "decryptor": decryptor_info,
            "manufacturing": {
                "materials": t2_bom,
                "material_cost_per_run": float(t2_material_cost),
                "invention_cost_per_run": cost_per_bpc,
                "total_cost_per_run": float(t2_material_cost) + cost_per_bpc,
            },
        }

    def compare_decryptors(
        self,
        t2_type_id: int,
        region_id: int = JITA_REGION_ID,
    ) -> list[dict]:
        """Compare all decryptors for a T2 item to find optimal choice.

        Returns list of results sorted by total cost per run (cheapest first).
        """
        # Get all decryptors (groupID = 1304)
        decryptor_ids = self._get_all_decryptors()

        results = []

        # No decryptor baseline
        baseline = self.get_invention_cost(t2_type_id, None, region_id)
        if baseline:
            results.append({
                "decryptor": None,
                "decryptor_name": "No Decryptor",
                "total_cost_per_run": baseline["manufacturing"]["total_cost_per_run"],
                "invention_cost": baseline["invention"]["cost_per_bpc"],
                "probability": baseline["invention"]["adjusted_probability"],
                "output_runs": baseline["invention"]["adjusted_output_runs"],
                "result_me": baseline["invention"]["result_me"],
                "result_te": baseline["invention"]["result_te"],
            })

        for dec_id in decryptor_ids:
            result = self.get_invention_cost(t2_type_id, dec_id, region_id)
            if result:
                dec_name = self._get_type_name(dec_id) or f"Type {dec_id}"
                results.append({
                    "decryptor": dec_id,
                    "decryptor_name": dec_name,
                    "total_cost_per_run": result["manufacturing"]["total_cost_per_run"],
                    "invention_cost": result["invention"]["cost_per_bpc"],
                    "probability": result["invention"]["adjusted_probability"],
                    "output_runs": result["invention"]["adjusted_output_runs"],
                    "result_me": result["invention"]["result_me"],
                    "result_te": result["invention"]["result_te"],
                })

        results.sort(key=lambda x: x["total_cost_per_run"])
        return results

    # ─────────────────────────── SDE Queries ──────────────────────────────

    def _get_blueprint_for_product(
        self, product_type_id: int, activity_id: int
    ) -> Optional[int]:
        """Find blueprint that produces a given item for an activity."""
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT "typeID" FROM "industryActivityProducts"
                    WHERE "productTypeID" = %s AND "activityID" = %s
                    LIMIT 1
                    """,
                    (product_type_id, activity_id),
                )
                row = cur.fetchone()
        return row[0] if row else None

    def _find_invention_source(self, t2_bp_id: int) -> Optional[int]:
        """Find the T1 blueprint that invents a T2 blueprint.

        The T2 BP type_id appears as productTypeID in invention activity.
        """
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT "typeID" FROM "industryActivityProducts"
                    WHERE "productTypeID" = %s AND "activityID" = %s
                    LIMIT 1
                    """,
                    (t2_bp_id, ACTIVITY_INVENTION),
                )
                row = cur.fetchone()
        return row[0] if row else None

    def _get_activity_materials(
        self, blueprint_id: int, activity_id: int
    ) -> list[tuple]:
        """Get materials for a blueprint activity."""
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT "materialTypeID", "quantity"
                    FROM "industryActivityMaterials"
                    WHERE "typeID" = %s AND "activityID" = %s
                    """,
                    (blueprint_id, activity_id),
                )
                return cur.fetchall()

    def _get_invention_probability(
        self, t1_bp_id: int, t2_bp_id: int
    ) -> Optional[float]:
        """Get invention probability for T1→T2."""
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT "probability"
                    FROM "industryActivityProbabilities"
                    WHERE "typeID" = %s AND "activityID" = %s
                      AND "productTypeID" = %s
                    """,
                    (t1_bp_id, ACTIVITY_INVENTION, t2_bp_id),
                )
                row = cur.fetchone()
        return float(row[0]) if row else None

    def _get_invention_output_runs(self, t2_bp_id: int) -> int:
        """Get base output runs for an invented T2 BPC.

        Default is usually 10 for most T2 items, 1 for T2 ships.
        """
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT "maxProductionLimit"
                    FROM "industryBlueprints"
                    WHERE "typeID" = %s
                    """,
                    (t2_bp_id,),
                )
                row = cur.fetchone()
        if row:
            # Invention typically gives maxProductionLimit / 10 runs
            # but for ships it's usually 1
            limit = row[0]
            return max(1, limit // 10) if limit > 10 else 1
        return 1

    def _get_decryptor_effects(self, decryptor_type_id: int) -> Optional[dict]:
        """Get decryptor ME/TE/run/probability modifiers from SDE."""
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT "attributeID",
                           COALESCE("valueFloat", "valueInt") as value
                    FROM "dgmTypeAttributes"
                    WHERE "typeID" = %s
                      AND "attributeID" IN (%s, %s, %s, %s)
                    """,
                    (
                        decryptor_type_id,
                        ATTR_INVENTION_ME_MODIFIER,
                        ATTR_INVENTION_TE_MODIFIER,
                        ATTR_INVENTION_RUN_MODIFIER,
                        ATTR_INVENTION_PROB_MODIFIER,
                    ),
                )
                rows = cur.fetchall()

        if not rows:
            return None

        effects = {}
        for row in rows:
            attr_id = row[0]
            value = float(row[1])
            if attr_id == ATTR_INVENTION_ME_MODIFIER:
                effects["me_modifier"] = int(value)
            elif attr_id == ATTR_INVENTION_TE_MODIFIER:
                effects["te_modifier"] = int(value)
            elif attr_id == ATTR_INVENTION_RUN_MODIFIER:
                effects["run_modifier"] = int(value)
            elif attr_id == ATTR_INVENTION_PROB_MODIFIER:
                effects["prob_modifier"] = value

        effects["type_id"] = decryptor_type_id
        effects["name"] = self._get_type_name(decryptor_type_id)
        return effects

    def _get_all_decryptors(self) -> list[int]:
        """Get all decryptor type_ids from SDE (groupID = 1304)."""
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT t."typeID"
                    FROM "invTypes" t
                    JOIN "invGroups" g ON g."groupID" = t."groupID"
                    WHERE g."groupID" = 1304
                      AND t.published = 1
                    ORDER BY t."typeName"
                    """,
                )
                return [row[0] for row in cur.fetchall()]

    def _get_type_name(self, type_id: int) -> Optional[str]:
        """Get type name from SDE."""
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                    (type_id,),
                )
                row = cur.fetchone()
        return row[0] if row else None

    def _get_price(self, type_id: int, region_id: int) -> Decimal:
        """Get item price from market_prices_cache or market_prices."""
        with self.db.connection() as conn:
            with conn.cursor() as cur:
                # Try adjusted price first
                cur.execute(
                    """
                    SELECT adjusted_price FROM market_prices_cache
                    WHERE type_id = %s
                    """,
                    (type_id,),
                )
                row = cur.fetchone()
                if row and row[0]:
                    return Decimal(str(row[0]))

                # Fallback to regional sell price
                cur.execute(
                    """
                    SELECT sell_price FROM market_prices
                    WHERE type_id = %s AND region_id = %s
                    """,
                    (type_id, region_id),
                )
                row = cur.fetchone()
                if row and row[0]:
                    return Decimal(str(row[0]))

        return Decimal("0")
