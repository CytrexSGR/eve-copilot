"""Production service - business logic for manufacturing simulation."""
import math
import logging
from typing import Dict, List, Tuple, Optional

from app.models import (
    MaterialItem,
    BillOfMaterials,
    AssetMatch,
    ProductionTime,
    ProductionFinancials,
    ProductionParameters,
    ProductionProduct,
    ProductionSimulation,
    QuickProfitCheck,
)
from app.services.repository import ProductionRepository
from app.services.market_client import LocalMarketClient
from eve_shared.constants import JITA_REGION_ID

logger = logging.getLogger(__name__)


class ProductionService:
    """
    Production Service provides business logic for manufacturing calculations.

    Responsibilities:
    - Calculate Bill of Materials (BOM) with Material Efficiency (ME) bonuses
    - Match BOM against character assets
    - Calculate production financials (cost, profit, ROI)
    - Simulate complete production runs with time and warnings
    """

    def __init__(self, db, region_id: int = JITA_REGION_ID):
        """
        Initialize Production Service.

        Args:
            db: Database pool
            region_id: Default region for market prices (The Forge/Jita)
        """
        self.repository = ProductionRepository(db)
        self.market_client = LocalMarketClient(db)
        self.region_id = region_id

    def get_bom(
        self, type_id: int, runs: int, me: int,
        facility_id: Optional[int] = None,
    ) -> Dict[int, int]:
        """
        Calculate Bill of Materials for manufacturing with ME bonus
        and optional structure/rig bonuses.

        The Material Efficiency (ME) bonus reduces material requirements:
        - ME 10 = 10% reduction (factor 0.9)
        - Formula: max(1, ceil(base_quantity * (1 - me/100) * structure_mult))

        If facility_id is provided, applies Engineering Complex and rig bonuses
        with security scaling (highsec 1.0x, lowsec 1.9x, null 2.1x).
        """
        blueprint_id = self.repository.get_blueprint_for_product(type_id)
        if not blueprint_id:
            return {}

        materials = self.repository.get_blueprint_materials(blueprint_id)
        bom = {}
        me_factor = 1 - (me / 100)

        # Get structure modifier if facility specified
        structure_modifier = 1.0
        if facility_id:
            from app.services.structure_bonus import StructureBonusCalculator
            calc = StructureBonusCalculator(self.repository.db)
            structure_modifier = calc.get_material_modifier(facility_id)

        for material_id, base_quantity in materials:
            quantity_per_run = max(1, math.ceil(
                base_quantity * me_factor * structure_modifier
            ))
            total_quantity = quantity_per_run * runs
            bom[material_id] = total_quantity

        return bom

    def get_bom_with_prices(
        self,
        type_id: int,
        runs: int,
        me: int,
        region_id: int
    ) -> List[MaterialItem]:
        """Get Bill of Materials with names and prices."""
        bom = self.get_bom(type_id, runs, me)
        if not bom:
            return []

        # Get names and prices
        names = self.repository.get_item_names_bulk(list(bom.keys()))
        prices = self.market_client.get_prices_bulk(list(bom.keys()), region_id)

        result = []
        for material_id, quantity in bom.items():
            name = names.get(material_id, "Unknown")
            price = prices.get(material_id, 0.0)

            result.append(MaterialItem(
                type_id=material_id,
                name=name,
                quantity=quantity,
                unit_price=price,
                total_cost=price * quantity
            ))

        result.sort(key=lambda x: x.name)
        return result

    def match_assets(
        self,
        bom: Dict[int, int],
        character_assets: List[Dict]
    ) -> Tuple[Dict[int, int], Dict[int, int]]:
        """
        Match Bill of Materials against character assets.

        Returns:
            Tuple of (available_materials, missing_materials)
        """
        asset_totals: Dict[int, int] = {}
        for asset in character_assets:
            type_id = asset.get("type_id")
            quantity = asset.get("quantity", 0)
            if type_id:
                asset_totals[type_id] = asset_totals.get(type_id, 0) + quantity

        available = {}
        missing = {}

        for material_id, needed in bom.items():
            have = asset_totals.get(material_id, 0)

            if have >= needed:
                available[material_id] = needed
            elif have > 0:
                available[material_id] = have
                missing[material_id] = needed - have
            else:
                missing[material_id] = needed

        return available, missing

    def calculate_financials(
        self,
        type_id: int,
        runs: int,
        bom: Dict[int, int],
        missing: Dict[int, int],
        region_id: int
    ) -> ProductionFinancials:
        """Calculate financial metrics for production."""
        blueprint_id = self.repository.get_blueprint_for_product(type_id)
        output_per_run = 1
        if blueprint_id:
            output_per_run = self.repository.get_output_quantity(blueprint_id, type_id)
        output_quantity = output_per_run * runs

        all_type_ids = list(bom.keys()) + [type_id]
        prices = self.market_client.get_prices_bulk(all_type_ids, region_id)

        build_cost = sum(
            prices.get(material_id, 0.0) * quantity
            for material_id, quantity in bom.items()
        )

        cash_to_invest = sum(
            prices.get(material_id, 0.0) * quantity
            for material_id, quantity in missing.items()
        )

        product_price = prices.get(type_id, 0.0)
        revenue = product_price * output_quantity
        profit = revenue - build_cost
        margin = (profit / build_cost * 100) if build_cost > 0 else 0.0

        if cash_to_invest > 0:
            roi = (profit / cash_to_invest * 100)
        elif profit > 0:
            roi = float('inf')
        else:
            roi = 0.0

        return ProductionFinancials(
            build_cost=round(build_cost, 2),
            cash_to_invest=round(cash_to_invest, 2),
            revenue=round(revenue, 2),
            profit=round(profit, 2),
            margin=round(margin, 2),
            roi=round(roi, 2) if not math.isinf(roi) else roi
        )

    def _format_time(self, seconds: int) -> str:
        """Format production time in human-readable format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"

    def simulate_build(
        self,
        type_id: int,
        runs: int,
        me: int,
        te: int,
        character_assets: Optional[List[Dict]],
        region_id: Optional[int]
    ) -> ProductionSimulation:
        """Full production simulation with all metrics and warnings."""
        actual_region = region_id or self.region_id

        product_name = self.repository.get_item_name(type_id)
        if not product_name:
            raise ValueError(f"Product not found: {type_id}")

        bom = self.get_bom(type_id, runs, me)
        if not bom:
            raise ValueError(f"No blueprint found for product: {type_id}")

        bom_items = self.get_bom_with_prices(type_id, runs, me, actual_region)

        if character_assets:
            available, missing = self.match_assets(bom, character_assets)
        else:
            available = {}
            missing = bom.copy()

        financials = self.calculate_financials(type_id, runs, bom, missing, actual_region)

        blueprint_id = self.repository.get_blueprint_for_product(type_id)
        base_time_per_run = 0
        if blueprint_id:
            base_time_per_run = self.repository.get_base_production_time(blueprint_id)

        base_time_total = base_time_per_run * runs
        te_factor = 1 - (te / 100)
        actual_time = int(base_time_total * te_factor)

        production_time = ProductionTime(
            base_seconds=base_time_total,
            actual_seconds=actual_time,
            formatted=self._format_time(actual_time)
        )

        output_per_run = 1
        if blueprint_id:
            output_per_run = self.repository.get_output_quantity(blueprint_id, type_id)
        output_quantity = output_per_run * runs

        prices = self.market_client.get_prices_bulk([type_id], actual_region)
        product_price = prices.get(type_id, 0.0)

        product = ProductionProduct(
            type_id=type_id,
            name=product_name,
            output_quantity=output_quantity,
            unit_sell_price=product_price
        )

        parameters = ProductionParameters(
            runs=runs,
            me_level=me,
            te_level=te,
            region_id=actual_region
        )

        asset_match = AssetMatch(
            materials_available=len(available),
            materials_missing=len(missing),
            fully_covered=(len(missing) == 0)
        )

        shopping_list = []
        if missing:
            names = self.repository.get_item_names_bulk(list(missing.keys()))
            missing_prices = self.market_client.get_prices_bulk(list(missing.keys()), actual_region)
            for material_id, quantity in missing.items():
                name = names.get(material_id, "Unknown")
                price = missing_prices.get(material_id, 0.0)
                shopping_list.append(MaterialItem(
                    type_id=material_id,
                    name=name,
                    quantity=quantity,
                    unit_price=price,
                    total_cost=price * quantity
                ))
            shopping_list.sort(key=lambda x: x.total_cost, reverse=True)

        warnings = []
        if financials.profit < 0:
            warnings.append(
                f"LOSS WARNING: Building costs {abs(financials.profit):,.2f} ISK "
                f"more than selling. Consider selling materials instead."
            )
        if 0 <= financials.margin < 5:
            warnings.append(
                f"LOW MARGIN: Only {financials.margin:.1f}% profit margin. "
                f"Market fees may eat into profits."
            )

        bom_result = BillOfMaterials(materials=bom_items)

        return ProductionSimulation(
            product=product,
            parameters=parameters,
            production_time=production_time,
            bill_of_materials=bom_result,
            asset_match=asset_match,
            financials=financials,
            shopping_list=shopping_list,
            warnings=warnings
        )

    def quick_profit_check(
        self,
        type_id: int,
        runs: int,
        me: int,
        region_id: int
    ) -> Optional[QuickProfitCheck]:
        """Fast profit calculation for bulk scanning."""
        blueprint_id = self.repository.get_blueprint_for_product(type_id)
        if not blueprint_id:
            return None

        bom = self.get_bom(type_id, runs, me)
        if not bom:
            return None

        output_per_run = self.repository.get_output_quantity(blueprint_id, type_id)
        output_quantity = output_per_run * runs

        all_type_ids = list(bom.keys()) + [type_id]
        prices = self.market_client.get_prices_bulk(all_type_ids, region_id)

        material_cost = sum(
            prices.get(material_id, 0.0) * quantity
            for material_id, quantity in bom.items()
        )
        product_price = prices.get(type_id, 0.0)
        revenue = product_price * output_quantity
        profit = revenue - material_cost
        margin = (profit / material_cost * 100) if material_cost > 0 else 0.0

        name = self.repository.get_item_name(type_id) or "Unknown"

        return QuickProfitCheck(
            type_id=type_id,
            name=name,
            runs=runs,
            me=me,
            output_quantity=output_quantity,
            material_cost=round(material_cost, 2),
            product_price=round(product_price, 2),
            revenue=round(revenue, 2),
            profit=round(profit, 2),
            margin_percent=round(margin, 2)
        )
