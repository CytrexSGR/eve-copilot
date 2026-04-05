"""Shared helpers for PI router sub-modules."""

from typing import List, Optional
import logging

from fastapi import Request

from eve_shared.constants import JITA_REGION_ID
from app.services.pi.repository import PIRepository
from app.services.pi.models import (
    PISchematic,
    PIChainNode,
    PIProfitability,
)

logger = logging.getLogger(__name__)


# ==================== Dependency Functions ====================

def get_pi_repository(request: Request) -> PIRepository:
    """Get PI repository with database connection from app state."""
    return PIRepository(request.app.state.db)


# ==================== Planet Type → P0 Resource Mapping ====================

PLANET_P0_RESOURCES = {
    "barren": ["Aqueous Liquids", "Base Metals", "Carbon Compounds", "Micro Organisms", "Noble Metals"],
    "gas": ["Aqueous Liquids", "Base Metals", "Ionic Solutions", "Noble Gas", "Reactive Gas"],
    "ice": ["Aqueous Liquids", "Heavy Metals", "Micro Organisms", "Noble Gas", "Planktic Colonies"],
    "lava": ["Base Metals", "Felsic Magma", "Heavy Metals", "Non-CS Crystals", "Suspended Plasma"],
    "oceanic": ["Aqueous Liquids", "Carbon Compounds", "Complex Organisms", "Micro Organisms", "Planktic Colonies"],
    "plasma": ["Base Metals", "Heavy Metals", "Noble Metals", "Non-CS Crystals", "Suspended Plasma"],
    "storm": ["Aqueous Liquids", "Base Metals", "Ionic Solutions", "Noble Gas", "Suspended Plasma"],
    "temperate": ["Aqueous Liquids", "Autotrophs", "Carbon Compounds", "Complex Organisms", "Micro Organisms"],
}

# P0 material → planet types that produce it
P0_PLANET_MAP = {
    "Aqueous Liquids": ["barren", "gas", "ice", "oceanic", "storm", "temperate"],
    "Autotrophs": ["temperate"],
    "Base Metals": ["barren", "gas", "lava", "plasma", "storm"],
    "Carbon Compounds": ["barren", "oceanic", "temperate"],
    "Complex Organisms": ["oceanic", "temperate"],
    "Felsic Magma": ["lava"],
    "Heavy Metals": ["ice", "lava", "plasma"],
    "Ionic Solutions": ["gas", "storm"],
    "Microorganisms": ["barren", "ice", "oceanic", "temperate"],
    "Noble Gas": ["gas", "ice", "storm"],
    "Noble Metals": ["barren", "plasma"],
    "Non-CS Crystals": ["lava", "plasma"],
    "Planktic Colonies": ["ice", "oceanic"],
    "Reactive Gas": ["gas"],
    "Suspended Plasma": ["lava", "plasma", "storm"],
}


# ==================== Helper Classes ====================

class PISchematicService:
    """Schematic service for production chain calculations."""

    def __init__(self, repo: PIRepository):
        self.repo = repo

    def get_production_chain(
        self, type_id: int, quantity: float = 1.0
    ) -> Optional[PIChainNode]:
        """Build production chain tree from P0 to target product."""
        tier = self.repo.get_item_tier(type_id)

        if tier == -1:
            return None

        if tier == 0:
            type_name = self._get_type_name(type_id)
            return PIChainNode(
                type_id=type_id,
                type_name=type_name,
                tier=0,
                quantity_needed=quantity,
                children=[],
            )

        schematic = self.repo.get_schematic_for_output(type_id)
        if not schematic:
            return None

        runs_needed = quantity / schematic.output_quantity

        children = []
        for inp in schematic.inputs:
            input_qty = inp.quantity * runs_needed
            child = self.get_production_chain(inp.type_id, input_qty)
            if child:
                children.append(child)

        return PIChainNode(
            type_id=type_id,
            type_name=schematic.output_name,
            tier=tier,
            quantity_needed=quantity,
            schematic_id=schematic.schematic_id,
            children=children,
        )

    def get_flat_inputs(
        self, type_id: int, quantity: float = 1.0
    ) -> List[dict]:
        """Get all P0 materials needed to produce a PI product."""
        chain = self.get_production_chain(type_id, quantity)
        if not chain:
            return []

        p0_materials = {}
        self._collect_p0_materials(chain, p0_materials)
        return list(p0_materials.values())

    def _collect_p0_materials(
        self, node: PIChainNode, materials: dict
    ) -> None:
        """Recursively collect P0 materials from chain."""
        if node.tier == 0:
            if node.type_id in materials:
                materials[node.type_id]["quantity"] += node.quantity_needed
            else:
                materials[node.type_id] = {
                    "type_id": node.type_id,
                    "type_name": node.type_name,
                    "quantity": node.quantity_needed,
                }
            return

        for child in node.children:
            self._collect_p0_materials(child, materials)

    def _get_type_name(self, type_id: int) -> str:
        """Get item type name."""
        with self.repo.db.cursor() as cur:
            cur.execute(
                'SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s',
                (type_id,),
            )
            result = cur.fetchone()
            if not result:
                return "Unknown"
            # Support both tuple and dict
            if isinstance(result, dict):
                return result.get('typeName', 'Unknown')
            return result[0] if result else "Unknown"


class MarketPriceAdapter:
    """Adapter for market price lookups using database."""

    def __init__(self, db):
        self.db = db

    def get_price(self, type_id: int, region_id: int) -> Optional[float]:
        """Get market price for an item."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT lowest_sell
                FROM market_prices
                WHERE type_id = %s AND region_id = %s
            """, (type_id, region_id))
            result = cur.fetchone()
            if not result:
                return None
            # Support both tuple and dict
            if isinstance(result, dict):
                val = result.get('lowest_sell')
            else:
                val = result[0]
            return float(val) if val else None


class PIProfitabilityService:
    """Service for PI profitability calculations."""

    DEFAULT_REGION_ID = JITA_REGION_ID

    def __init__(self, repo: PIRepository, market: MarketPriceAdapter):
        self.repo = repo
        self.market = market

    def calculate_profitability(
        self, type_id: int, region_id: int = DEFAULT_REGION_ID
    ) -> Optional[PIProfitability]:
        """Calculate profitability for a PI product."""
        schematic = self.repo.get_schematic_for_output(type_id)
        if not schematic:
            return None

        return self._calculate_schematic_profitability(schematic, region_id)

    def get_opportunities(
        self,
        tier: Optional[int] = None,
        limit: int = 50,
        min_roi: float = 0,
        region_id: int = DEFAULT_REGION_ID,
    ) -> List[PIProfitability]:
        """Get profitable PI opportunities."""
        schematics = self.repo.get_all_schematics(tier=tier)

        profitable = []
        for schematic in schematics:
            try:
                profit = self._calculate_schematic_profitability(schematic, region_id)
                if profit is None:
                    continue
                if profit.roi_percent >= min_roi:
                    profitable.append(profit)
            except Exception:
                continue

        profitable.sort(key=lambda p: p.profit_per_hour, reverse=True)
        return profitable[:limit]

    def _calculate_schematic_profitability(
        self, schematic: PISchematic, region_id: int
    ) -> Optional[PIProfitability]:
        """Calculate profitability for a schematic."""
        input_cost = 0.0
        for inp in schematic.inputs:
            price = self.market.get_price(inp.type_id, region_id)
            if price is None or price <= 0:
                return None
            input_cost += price * inp.quantity

        output_price = self.market.get_price(schematic.output_type_id, region_id)
        if output_price is None or output_price <= 0:
            return None

        output_value = output_price * schematic.output_quantity

        profit_per_run = output_value - input_cost
        cycles_per_hour = 3600 / schematic.cycle_time if schematic.cycle_time > 0 else 0
        profit_per_hour = profit_per_run * cycles_per_hour
        roi_percent = (profit_per_run / input_cost * 100) if input_cost > 0 else 0

        return PIProfitability(
            type_id=schematic.output_type_id,
            type_name=schematic.output_name,
            tier=schematic.tier,
            schematic_id=schematic.schematic_id,
            input_cost=round(input_cost, 2),
            output_value=round(output_value, 2),
            profit_per_run=round(profit_per_run, 2),
            profit_per_hour=round(profit_per_hour, 2),
            roi_percent=round(roi_percent, 2),
            cycle_time=schematic.cycle_time,
        )


class PIEmpireService:
    """Service for PI empire-level calculations and planning."""

    # Average P0 extraction rate per planet per month (units)
    P0_RATE_PER_PLANET_MONTH = 40_000_000
    # Average factory planet output per month (P4 units)
    FACTORY_OUTPUT_PER_MONTH = 30_000

    def __init__(self, repo: PIRepository, schematic_service: PISchematicService, market: MarketPriceAdapter):
        self.repo = repo
        self.schematic_service = schematic_service
        self.market = market

    def calculate_empire_profitability(
        self,
        total_planets: int = 18,
        extraction_planets: int = 12,
        factory_planets: int = 6,
        region_id: int = JITA_REGION_ID,
        poco_tax: float = 0.10,
    ):
        """Calculate profitability of all P4 products for an empire configuration."""
        from app.services.pi.models import EmpireConfiguration, EmpireProfitabilityResponse

        config = EmpireConfiguration(
            total_planets=total_planets,
            extraction_planets=extraction_planets,
            factory_planets=factory_planets,
            characters=total_planets // 6,
            poco_tax_rate=poco_tax,
            region_id=region_id,
        )

        # Get all P4 schematics
        p4_schematics = self.repo.get_all_schematics(tier=4)

        results = []
        for schematic in p4_schematics:
            try:
                profitability = self._calculate_p4_profitability(schematic, config)
                if profitability:
                    results.append(profitability)
            except Exception:
                continue

        # Sort by monthly profit descending
        results.sort(key=lambda x: x.monthly_profit, reverse=True)

        # Build comparison summary
        comparison = self._build_comparison(results)

        return EmpireProfitabilityResponse(
            configuration=config,
            products=results,
            comparison=comparison,
        )

    def _calculate_p4_profitability(self, schematic: PISchematic, config):
        """Calculate profitability for a single P4 product."""
        from app.services.pi.models import P4EmpireProfitability

        # Get P0 inputs for this P4
        p0_inputs = self.schematic_service.get_flat_inputs(schematic.output_type_id, quantity=1.0)
        if not p0_inputs:
            return None

        p0_count = len(p0_inputs)

        # Calculate planets needed for extraction
        planets_needed = self._calculate_planets_needed(p0_inputs, config)

        # Monthly output based on factory planets
        monthly_output = config.factory_planets * self.FACTORY_OUTPUT_PER_MONTH

        # Get sell price
        sell_price = self.market.get_price(schematic.output_type_id, config.region_id)
        if not sell_price or sell_price <= 0:
            return None

        monthly_revenue = monthly_output * sell_price

        # Calculate costs (POCO tax on exports)
        poco_cost = monthly_revenue * config.poco_tax_rate
        monthly_costs = {
            "poco_tax": round(poco_cost, 2),
            "import_tax": 0,
            "total": round(poco_cost, 2),
        }

        monthly_profit = monthly_revenue - poco_cost
        profit_per_planet = monthly_profit / config.total_planets if config.total_planets > 0 else 0
        roi_percent = (monthly_profit / poco_cost * 100) if poco_cost > 0 else 0

        complexity = self._rate_complexity(p0_count)
        logistics_score = self._rate_logistics(p0_count, planets_needed)
        recommendation = self._rate_overall(monthly_profit, logistics_score, complexity)

        return P4EmpireProfitability(
            type_id=schematic.output_type_id,
            type_name=schematic.output_name,
            tier=4,
            monthly_output=monthly_output,
            sell_price=round(sell_price, 2),
            monthly_revenue=round(monthly_revenue, 2),
            monthly_costs=monthly_costs,
            monthly_profit=round(monthly_profit, 2),
            profit_per_planet=round(profit_per_planet, 2),
            roi_percent=round(roi_percent, 2),
            complexity=complexity,
            logistics_score=logistics_score,
            p0_count=p0_count,
            planets_needed=planets_needed,
            recommendation=recommendation,
        )

    def _calculate_planets_needed(self, p0_inputs, config) -> dict:
        """Calculate planet types needed for P0 extraction."""
        extraction_needs = {}
        for p0 in p0_inputs:
            p0_name = p0.get("type_name", "")
            for planet_type, resources in PLANET_P0_RESOURCES.items():
                if p0_name in resources:
                    if planet_type not in extraction_needs:
                        extraction_needs[planet_type] = 0
                    extraction_needs[planet_type] += 1
                    break

        factory_needs = {"temperate": config.factory_planets}

        return {
            "extraction": extraction_needs,
            "factory": factory_needs,
        }

    def _rate_complexity(self, p0_count: int) -> str:
        """Rate complexity based on P0 material count."""
        if p0_count <= 3:
            return "low"
        elif p0_count <= 5:
            return "medium"
        return "high"

    def _rate_logistics(self, p0_count: int, planets_needed: dict) -> int:
        """Rate logistics complexity (1-10 scale)."""
        base_score = min(p0_count, 6)
        extraction_types = len(planets_needed.get("extraction", {}))
        diversity_score = min(extraction_types, 4)
        return min(base_score + diversity_score, 10)

    def _rate_overall(self, monthly_profit: float, logistics_score: int, complexity: str) -> str:
        """Rate overall recommendation."""
        if monthly_profit > 2_000_000_000 and logistics_score <= 4:
            return "excellent"
        if monthly_profit > 1_500_000_000 and logistics_score <= 6:
            return "good"
        if monthly_profit > 1_000_000_000:
            return "fair"
        return "poor"

    def _build_comparison(self, results) -> dict:
        """Build comparison summary for results."""
        if not results:
            return {}

        best_profit = results[0] if results else None

        by_logistics = sorted(results, key=lambda x: x.logistics_score)
        best_passive = by_logistics[0] if by_logistics else None

        # Best balanced (profit / logistics ratio)
        by_balance = sorted(
            results,
            key=lambda x: x.monthly_profit / max(x.logistics_score, 1),
            reverse=True
        )
        best_balanced = by_balance[0] if by_balance else None

        return {
            "best_profit": {
                "name": best_profit.type_name,
                "type_id": best_profit.type_id,
                "monthly": best_profit.monthly_profit,
            } if best_profit else None,
            "best_passive": {
                "name": best_passive.type_name,
                "type_id": best_passive.type_id,
                "logistics_score": best_passive.logistics_score,
            } if best_passive else None,
            "best_balanced": {
                "name": best_balanced.type_name,
                "type_id": best_balanced.type_id,
                "score": round(best_balanced.monthly_profit / max(best_balanced.logistics_score, 1) / 1_000_000, 1),
            } if best_balanced else None,
        }
