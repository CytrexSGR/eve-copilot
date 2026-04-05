"""Shopping service business logic."""
import logging
import os
from typing import Optional, List

import httpx

from app.models import (
    ShoppingList, ShoppingListCreate, ShoppingListUpdate,
    ShoppingItem, ShoppingItemCreate, ShoppingItemUpdate,
    ShoppingItemWithMaterials, MaterialRequirement,
    RegionalComparison, RegionPrice, CargoSummary, TransportOption,
    BuildDecision,
    WizardMaterialsRequest, WizardMaterialsResponse,
    WizardRegionRequest, WizardRegionResponse,
    # New models
    RouteStop, ShoppingRoute,
    MarketOrder, RegionOrders, OrderSnapshots,
    ItemsByRegion, ItemsByRegionResponse,
    AssetMatch, ApplyAssetsResponse, ShoppingItemWithAssets,
    ListWithAssetsResponse, ProductionMaterialsResponse
)
from app.services.repository import ShoppingRepository
from app.services.market_client import LocalMarketClient
from app.services.production_client import LocalProductionClient

logger = logging.getLogger(__name__)

CHARACTER_SERVICE_URL = os.environ.get(
    "CHARACTER_SERVICE_URL", "http://character-service:8000"
)


def fetch_doctrine_bom(
    doctrine_id: int, quantity: int = 1
) -> Optional[List[dict]]:
    """Fetch doctrine BOM from character-service.

    Returns list of dicts with type_id, type_name, quantity — or None on failure.
    """
    try:
        url = f"{CHARACTER_SERVICE_URL}/api/doctrines/{doctrine_id}/bom"
        response = httpx.get(url, params={"quantity": quantity}, timeout=10.0)
        if response.status_code != 200:
            logger.warning(
                "Doctrine BOM fetch failed: %s %s", response.status_code, url
            )
            return None
        return response.json()
    except Exception as e:
        logger.error("Failed to fetch doctrine BOM: %s", e)
        return None


# Transport ships with cargo capacities
TRANSPORT_SHIPS = [
    {"ship_name": "Tayra", "ship_type_id": 648, "cargo_capacity": 42000.0},
    {"ship_name": "Mammoth", "ship_type_id": 652, "cargo_capacity": 41400.0},
    {"ship_name": "Bestower", "ship_type_id": 1944, "cargo_capacity": 38500.0},
    {"ship_name": "Iteron Mark V", "ship_type_id": 657, "cargo_capacity": 38400.0},
    {"ship_name": "Nereus", "ship_type_id": 655, "cargo_capacity": 20000.0},
    {"ship_name": "Badger", "ship_type_id": 648, "cargo_capacity": 17500.0},
    {"ship_name": "Miasmos", "ship_type_id": 654, "cargo_capacity": 63000.0},  # Ore only
    {"ship_name": "Kryos", "ship_type_id": 653, "cargo_capacity": 43000.0},  # Minerals only
]


class ShoppingService:
    """Business logic for shopping list management."""

    def __init__(self, db):
        self.db = db
        self.repo = ShoppingRepository(db)
        self.market = LocalMarketClient(db)
        self.production = LocalProductionClient(db)

    # List operations

    def get_lists(self, character_id: Optional[int] = None) -> List[ShoppingList]:
        """Get all shopping lists."""
        return self.repo.get_lists(character_id)

    def get_list(self, list_id: int) -> Optional[ShoppingList]:
        """Get a shopping list by ID."""
        return self.repo.get_list(list_id)

    def create_list(self, data: ShoppingListCreate) -> ShoppingList:
        """Create a new shopping list."""
        return self.repo.create_list(data)

    def update_list(self, list_id: int, data: ShoppingListUpdate) -> Optional[ShoppingList]:
        """Update a shopping list."""
        return self.repo.update_list(list_id, data)

    def delete_list(self, list_id: int) -> bool:
        """Delete a shopping list."""
        return self.repo.delete_list(list_id)

    # Item operations

    def get_items(self, list_id: int) -> List[ShoppingItem]:
        """Get all items in a list."""
        return self.repo.get_items(list_id)

    def get_item(self, item_id: int) -> Optional[ShoppingItem]:
        """Get a shopping item."""
        return self.repo.get_item(item_id)

    def create_item(self, list_id: int, data: ShoppingItemCreate) -> ShoppingItem:
        """Create a new shopping item."""
        return self.repo.create_item(list_id, data)

    def update_item(self, item_id: int, data: ShoppingItemUpdate) -> Optional[ShoppingItem]:
        """Update a shopping item."""
        return self.repo.update_item(item_id, data)

    def delete_item(self, item_id: int) -> bool:
        """Delete a shopping item."""
        return self.repo.delete_item(item_id)

    def mark_purchased(self, item_id: int, purchased: bool = True) -> Optional[ShoppingItem]:
        """Mark an item as purchased."""
        return self.repo.mark_purchased(item_id, purchased)

    # Material calculations

    def get_item_with_materials(self, item_id: int) -> Optional[ShoppingItemWithMaterials]:
        """Get a product item with its material requirements."""
        item = self.repo.get_item(item_id)
        if not item or not item.is_product:
            return None

        # Get materials from production service
        materials_data = self.production.get_materials(
            item.type_id,
            runs=item.blueprint_runs,
            me_level=item.me_level
        )

        materials = []
        if materials_data and "materials" in materials_data:
            # Get prices for all materials
            type_ids = [m["type_id"] for m in materials_data["materials"]]
            region_id = item.region_id or 10000002
            prices = self.market.get_prices_batch(type_ids, region_id)

            for mat in materials_data["materials"]:
                type_id = mat["type_id"]
                price_data = prices.get(type_id, {})
                unit_price = price_data.get("lowest_sell", 0) or 0

                is_manufacturable = self.repo.is_manufacturable(type_id)
                type_info = self.repo.get_type_info(type_id)
                volume = type_info.get("volume", 0) if type_info else 0

                materials.append(MaterialRequirement(
                    type_id=type_id,
                    type_name=mat["type_name"],
                    quantity_base=mat.get("quantity_base", mat["quantity_adjusted"]),
                    quantity_adjusted=mat["quantity_adjusted"],
                    unit_price=unit_price,
                    total_price=unit_price * mat["quantity_adjusted"],
                    volume=volume,
                    is_manufacturable=is_manufacturable
                ))

        # Calculate economics
        production_cost = sum(m.total_price for m in materials)
        market_price = item.unit_price * item.quantity
        profit = market_price - production_cost
        roi = (profit / production_cost * 100) if production_cost > 0 else 0

        return ShoppingItemWithMaterials(
            **item.model_dump(),
            materials=materials,
            production_cost=production_cost,
            market_price=market_price,
            profit=profit,
            roi=roi
        )

    def calculate_materials(
        self,
        item_id: int,
        include_sub_products: bool = False
    ) -> Optional[dict]:
        """Calculate materials for a product."""
        item = self.repo.get_item(item_id)
        if not item:
            return None

        materials_data = self.production.get_materials(
            item.type_id,
            runs=item.blueprint_runs,
            me_level=item.me_level
        )

        if not materials_data:
            return {"error": "No blueprint found for this item"}

        return materials_data

    def apply_materials_to_list(self, item_id: int) -> List[ShoppingItem]:
        """Add calculated materials to the shopping list."""
        item = self.repo.get_item(item_id)
        if not item:
            return []

        # Remove existing child materials
        self.repo.delete_child_items(item_id)

        # Get materials
        materials_data = self.production.get_materials(
            item.type_id,
            runs=item.blueprint_runs,
            me_level=item.me_level
        )

        if not materials_data or "materials" not in materials_data:
            return []

        created_items = []
        for mat in materials_data["materials"]:
            is_manufacturable = self.repo.is_manufacturable(mat["type_id"])

            item_data = ShoppingItemCreate(
                type_id=mat["type_id"],
                quantity=mat["quantity_adjusted"],
                is_product=False,
                region_id=item.region_id,
                build_decision=BuildDecision.UNDECIDED if is_manufacturable else BuildDecision.BUY,
                parent_item_id=item_id
            )
            created_item = self.repo.create_item(item.list_id, item_data)
            created_items.append(created_item)

        return created_items

    # Regional comparison

    def get_regional_comparison(self, list_id: int) -> Optional[RegionalComparison]:
        """Compare shopping list prices across regions."""
        shopping_list = self.repo.get_list(list_id)
        if not shopping_list:
            return None

        items = self.repo.get_items(list_id)
        if not items:
            return RegionalComparison(
                list_id=list_id,
                list_name=shopping_list.name,
                regions=[],
                items=[],
                best_region=None,
                total_by_region={}
            )

        # Get all type IDs
        type_ids = list(set(item.type_id for item in items))

        # Get regional prices
        prices = self.repo.get_regional_prices(type_ids)

        # Build price lookup: {type_id: {region_id: price_data}}
        price_lookup = {}
        for p in prices:
            if p["type_id"] not in price_lookup:
                price_lookup[p["type_id"]] = {}
            price_lookup[p["type_id"]][p["region_id"]] = p

        # Get regions
        regions_data = self.repo.get_regions()
        regions = []
        total_by_region = {}

        for reg in regions_data:
            region_id = reg["region_id"]
            total = 0.0

            for item in items:
                price_data = price_lookup.get(item.type_id, {}).get(region_id, {})
                unit_price = price_data.get("lowest_sell", 0) or 0
                total += unit_price * item.quantity

            total_by_region[region_id] = total
            regions.append(RegionPrice(
                region_id=region_id,
                region_name=reg["region_name"],
                hub_system=reg["hub_system"],
                lowest_sell=total,
                highest_buy=0,
                volume=0,
                order_count=0
            ))

        # Find best region (lowest total)
        best_region = min(regions, key=lambda r: r.lowest_sell) if regions else None

        # Build items with regional prices
        items_data = []
        for item in items:
            item_prices = {}
            for reg in regions_data:
                region_id = reg["region_id"]
                price_data = price_lookup.get(item.type_id, {}).get(region_id, {})
                item_prices[region_id] = price_data.get("lowest_sell", 0) or 0

            items_data.append({
                "type_id": item.type_id,
                "type_name": item.type_name,
                "quantity": item.quantity,
                "prices": item_prices
            })

        return RegionalComparison(
            list_id=list_id,
            list_name=shopping_list.name,
            regions=regions,
            items=items_data,
            best_region=best_region,
            total_by_region=total_by_region
        )

    # Cargo and transport

    def get_cargo_summary(self, list_id: int) -> Optional[CargoSummary]:
        """Get cargo volume summary for a shopping list."""
        shopping_list = self.repo.get_list(list_id)
        if not shopping_list:
            return None

        items = self.repo.get_items(list_id)

        total_volume = sum(item.total_volume for item in items)
        total_cost = sum(item.total_price for item in items)

        items_by_volume = sorted(
            [{"type_name": i.type_name, "volume": i.total_volume, "quantity": i.quantity}
             for i in items],
            key=lambda x: x["volume"],
            reverse=True
        )

        return CargoSummary(
            list_id=list_id,
            total_items=len(items),
            total_volume=total_volume,
            total_cost=total_cost,
            items_by_volume=items_by_volume[:10]  # Top 10
        )

    def get_transport_options(self, list_id: int) -> List[TransportOption]:
        """Get transport ship options for a shopping list."""
        cargo = self.get_cargo_summary(list_id)
        if not cargo:
            return []

        options = []
        for ship in TRANSPORT_SHIPS:
            trips = max(1, int(cargo.total_volume / ship["cargo_capacity"]) + 1)
            fits = cargo.total_volume <= ship["cargo_capacity"]

            options.append(TransportOption(
                ship_name=ship["ship_name"],
                ship_type_id=ship["ship_type_id"],
                cargo_capacity=ship["cargo_capacity"],
                trips_needed=trips if not fits else 1,
                fits_in_single_trip=fits
            ))

        return sorted(options, key=lambda x: x.trips_needed)

    # Wizard operations

    def wizard_calculate_materials(
        self,
        request: WizardMaterialsRequest
    ) -> WizardMaterialsResponse:
        """Wizard: Calculate materials for production."""
        type_info = self.repo.get_type_info(request.type_id)
        if not type_info:
            raise ValueError(f"Type {request.type_id} not found")

        materials_data = self.production.get_materials(
            request.type_id,
            runs=request.runs,
            me_level=request.me_level
        )

        if not materials_data:
            raise ValueError(f"No blueprint found for type {request.type_id}")

        # Get prices
        type_ids = [m["type_id"] for m in materials_data.get("materials", [])]
        prices = self.market.get_prices_batch(type_ids, 10000002)

        materials = []
        total_cost = 0.0

        for mat in materials_data.get("materials", []):
            type_id = mat["type_id"]
            price_data = prices.get(type_id, {})
            unit_price = price_data.get("lowest_sell", 0) or 0
            total = unit_price * mat["quantity_adjusted"]
            total_cost += total

            is_manufacturable = self.repo.is_manufacturable(type_id)
            mat_type_info = self.repo.get_type_info(type_id)
            volume = mat_type_info.get("volume", 0) if mat_type_info else 0

            materials.append(MaterialRequirement(
                type_id=type_id,
                type_name=mat["type_name"],
                quantity_base=mat.get("quantity_base", mat["quantity_adjusted"]),
                quantity_adjusted=mat["quantity_adjusted"],
                unit_price=unit_price,
                total_price=total,
                volume=volume,
                is_manufacturable=is_manufacturable
            ))

        return WizardMaterialsResponse(
            type_id=request.type_id,
            type_name=type_info["type_name"],
            runs=request.runs,
            me_level=request.me_level,
            materials=materials,
            total_cost=total_cost,
            sub_products=[]
        )

    def wizard_compare_regions(
        self,
        request: WizardRegionRequest
    ) -> WizardRegionResponse:
        """Wizard: Compare prices across regions."""
        prices = self.repo.get_regional_prices(request.type_ids)
        regions_data = self.repo.get_regions()

        # Build price lookup
        price_lookup = {}
        for p in prices:
            if p["type_id"] not in price_lookup:
                price_lookup[p["type_id"]] = {}
            price_lookup[p["type_id"]][p["region_id"]] = p

        # Calculate totals per region
        regions = []
        for reg in regions_data:
            region_id = reg["region_id"]
            total = 0.0

            for type_id, qty in zip(request.type_ids, request.quantities):
                price_data = price_lookup.get(type_id, {}).get(region_id, {})
                unit_price = price_data.get("lowest_sell", 0) or 0
                total += unit_price * qty

            regions.append(RegionPrice(
                region_id=region_id,
                region_name=reg["region_name"],
                hub_system=reg["hub_system"],
                lowest_sell=total,
                highest_buy=0
            ))

        # Find best and worst
        best_region = min(regions, key=lambda r: r.lowest_sell) if regions else None
        worst_region = max(regions, key=lambda r: r.lowest_sell) if regions else None
        savings = worst_region.lowest_sell - best_region.lowest_sell if best_region and worst_region else 0

        # Build items list
        items = []
        for type_id, qty in zip(request.type_ids, request.quantities):
            type_info = self.repo.get_type_info(type_id)
            item_prices = {}
            for reg in regions_data:
                price_data = price_lookup.get(type_id, {}).get(reg["region_id"], {})
                item_prices[reg["region_id"]] = price_data.get("lowest_sell", 0) or 0

            items.append({
                "type_id": type_id,
                "type_name": type_info["type_name"] if type_info else f"Type {type_id}",
                "quantity": qty,
                "prices": item_prices
            })

        return WizardRegionResponse(
            regions=regions,
            best_region=best_region,
            items=items,
            savings_vs_worst=savings
        )

    # Export

    def export_list(self, list_id: int, format: str = "eve") -> Optional[str]:
        """Export shopping list to EVE-compatible format."""
        items = self.repo.get_items(list_id)
        if not items:
            return None

        if format == "eve":
            # EVE multibuy format
            lines = [f"{item.type_name}\t{item.quantity}" for item in items if not item.is_purchased]
            return "\n".join(lines)
        elif format == "csv":
            lines = ["Type Name,Quantity,Unit Price,Total Price"]
            for item in items:
                lines.append(f"{item.type_name},{item.quantity},{item.unit_price},{item.total_price}")
            return "\n".join(lines)

        return None

    # Route calculation

    REGION_KEY_TO_HUB = {
        'the_forge': ('Jita', 30000142),
        'domain': ('Amarr', 30002187),
        'heimatar': ('Rens', 30002510),
        'sinq_laison': ('Dodixie', 30002659),
        'metropolis': ('Hek', 30002053),
    }

    def calculate_shopping_route(
        self,
        regions: List[str],
        home_system: str = 'isikemi',
        include_systems: bool = True,
        return_home: bool = True
    ) -> ShoppingRoute:
        """Calculate optimal route through trade hubs."""
        if not regions:
            return ShoppingRoute(
                home_system=home_system,
                total_jumps=0,
                stops=[],
                return_home=return_home,
                total_cost=0.0
            )

        # Get home system info
        home_info = self.repo.get_system_info(home_system)
        if not home_info:
            raise ValueError(f"Unknown system: {home_system}")

        home_system_id = home_info['solar_system_id']

        # Build list of hub systems to visit
        hubs_to_visit = []
        for region_key in regions:
            if region_key in self.REGION_KEY_TO_HUB:
                hub_name, hub_id = self.REGION_KEY_TO_HUB[region_key]
                hubs_to_visit.append({
                    'region_key': region_key,
                    'hub_name': hub_name,
                    'hub_id': hub_id
                })

        if not hubs_to_visit:
            return ShoppingRoute(
                home_system=home_system,
                total_jumps=0,
                stops=[],
                return_home=return_home,
                total_cost=0.0
            )

        # Calculate distances from home to each hub
        distances = {}
        for hub in hubs_to_visit:
            route = self.repo.get_route(home_system_id, hub['hub_id'])
            distances[hub['hub_id']] = len(route) - 1 if route else 999

        # Simple greedy algorithm: visit nearest hub first
        # (Optimal TSP would require more complex algorithm)
        visited = []
        current_id = home_system_id
        total_jumps = 0

        remaining = list(hubs_to_visit)
        while remaining:
            # Find nearest unvisited hub
            nearest = None
            nearest_dist = float('inf')

            for hub in remaining:
                route = self.repo.get_route(current_id, hub['hub_id'])
                dist = len(route) - 1 if route else 999
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest = hub

            if nearest:
                remaining.remove(nearest)
                visited.append({
                    **nearest,
                    'jumps': nearest_dist
                })
                total_jumps += nearest_dist
                current_id = nearest['hub_id']

        # Build stops
        stops = []
        for hub in visited:
            region_name = hub['region_key'].replace('_', ' ').title()
            stops.append(RouteStop(
                system_name=hub['hub_name'],
                region_name=region_name,
                jumps_from_previous=hub['jumps'],
                items_to_buy=[],
                subtotal=0.0
            ))

        # Add return trip if requested
        if return_home and visited:
            last_hub = visited[-1]
            route = self.repo.get_route(last_hub['hub_id'], home_system_id)
            return_jumps = len(route) - 1 if route else 0
            total_jumps += return_jumps

        return ShoppingRoute(
            home_system=home_system,
            total_jumps=total_jumps,
            stops=stops,
            return_home=return_home,
            total_cost=0.0
        )

    # Market orders

    REGION_NAME_TO_ID = {
        'the_forge': 10000002,
        'domain': 10000043,
        'heimatar': 10000030,
        'sinq_laison': 10000032,
        'metropolis': 10000042,
    }

    REGION_DISPLAY_NAMES = {
        'the_forge': 'Jita',
        'domain': 'Amarr',
        'heimatar': 'Rens',
        'sinq_laison': 'Dodixie',
        'metropolis': 'Hek',
    }

    def get_order_snapshots(
        self,
        type_id: int,
        region: Optional[str] = None
    ) -> OrderSnapshots:
        """Get market order snapshots for an item."""
        region_id = None
        if region:
            region_id = self.REGION_NAME_TO_ID.get(region)
            if not region_id:
                raise ValueError(f"Unknown region: {region}")

        rows = self.repo.get_order_snapshots(type_id, region_id)

        # Group by region
        result = {}
        for row in rows:
            rid = row['region_id']
            region_key = next(
                (k for k, v in self.REGION_NAME_TO_ID.items() if v == rid),
                str(rid)
            )

            if region_key not in result:
                result[region_key] = RegionOrders(
                    display_name=self.REGION_DISPLAY_NAMES.get(region_key, region_key),
                    sells=[],
                    buys=[],
                    updated_at=None
                )

            order = MarketOrder(
                rank=row['rank'],
                price=float(row['price']),
                volume=row['volume_remain'],
                location_id=row['location_id'],
                issued=row['issued'].isoformat() if row.get('issued') else None
            )

            if row['is_buy_order']:
                result[region_key].buys.append(order)
            else:
                result[region_key].sells.append(order)

            if row.get('updated_at'):
                result[region_key].updated_at = row['updated_at'].isoformat()

        return OrderSnapshots(type_id=type_id, regions=result)

    # Items by region

    def get_items_by_region(self, list_id: int) -> Optional[ItemsByRegionResponse]:
        """Get shopping list items grouped by target region."""
        shopping_list = self.repo.get_list(list_id)
        if not shopping_list:
            return None

        items = self.repo.get_items(list_id)

        # Group items by region
        region_groups = {}
        unassigned = []

        for item in items:
            if item.region_id:
                if item.region_id not in region_groups:
                    region_groups[item.region_id] = {
                        'items': [],
                        'total_cost': 0.0,
                        'total_volume': 0.0
                    }
                region_groups[item.region_id]['items'].append(item)
                region_groups[item.region_id]['total_cost'] += item.total_price
                region_groups[item.region_id]['total_volume'] += item.total_volume
            else:
                unassigned.append(item)

        # Get region info
        regions_data = self.repo.get_regions()
        region_info = {r['region_id']: r for r in regions_data}

        regions = []
        for region_id, data in region_groups.items():
            info = region_info.get(region_id, {})
            regions.append(ItemsByRegion(
                region_id=region_id,
                region_name=info.get('region_name', f'Region {region_id}'),
                hub_system=info.get('hub_system', 'Unknown'),
                items=data['items'],
                total_cost=data['total_cost'],
                total_volume=data['total_volume']
            ))

        return ItemsByRegionResponse(
            list_id=list_id,
            list_name=shopping_list.name,
            regions=regions,
            unassigned_items=unassigned
        )

    # Asset operations

    def apply_assets_to_list(
        self,
        list_id: int,
        character_id: int
    ) -> Optional[ApplyAssetsResponse]:
        """Apply character assets to shopping list items."""
        shopping_list = self.repo.get_list(list_id)
        if not shopping_list:
            return None

        items = self.repo.get_items(list_id)
        assets = self.repo.get_character_assets(character_id)

        # Build asset lookup by type_id
        asset_quantities = {}
        for asset in assets:
            type_id = asset['type_id']
            asset_quantities[type_id] = asset_quantities.get(type_id, 0) + asset['quantity']

        matches = []
        items_updated = 0
        total_covered = 0
        total_needed = 0

        for item in items:
            quantity_in_assets = min(
                asset_quantities.get(item.type_id, 0),
                item.quantity
            )
            quantity_to_buy = max(0, item.quantity - quantity_in_assets)

            # Update item in database
            if quantity_in_assets > 0:
                self.repo.update_item_quantity_in_assets(item.id, quantity_in_assets)
                items_updated += 1

            total_covered += quantity_in_assets
            total_needed += item.quantity

            matches.append(AssetMatch(
                type_id=item.type_id,
                type_name=item.type_name,
                quantity_needed=item.quantity,
                quantity_in_assets=quantity_in_assets,
                quantity_to_buy=quantity_to_buy
            ))

            # Reduce available assets for next items of same type
            if item.type_id in asset_quantities:
                asset_quantities[item.type_id] -= quantity_in_assets

        return ApplyAssetsResponse(
            list_id=list_id,
            character_id=character_id,
            items_updated=items_updated,
            total_covered=total_covered,
            total_needed=total_needed,
            matches=matches
        )

    def get_list_with_assets(self, list_id: int) -> Optional[ListWithAssetsResponse]:
        """Get shopping list with asset coverage information."""
        shopping_list = self.repo.get_list(list_id)
        if not shopping_list:
            return None

        items = self.repo.get_items(list_id)

        items_with_assets = []
        total_needed = 0
        total_covered = 0
        total_to_buy = 0

        for item in items:
            # Get quantity_in_assets from item if available, otherwise 0
            quantity_in_assets = getattr(item, 'quantity_in_assets', 0) or 0
            quantity_to_buy = max(0, item.quantity - quantity_in_assets)

            items_with_assets.append(ShoppingItemWithAssets(
                **item.model_dump(),
                quantity_in_assets=quantity_in_assets,
                quantity_to_buy=quantity_to_buy
            ))

            total_needed += item.quantity
            total_covered += quantity_in_assets
            total_to_buy += quantity_to_buy

        return ListWithAssetsResponse(
            id=shopping_list.id,
            name=shopping_list.name,
            description=shopping_list.description,
            character_id=shopping_list.character_id,
            items=items_with_assets,
            total_needed=total_needed,
            total_covered=total_covered,
            total_to_buy=total_to_buy
        )

    # Production materials

    def add_production_materials(
        self,
        list_id: int,
        type_id: int,
        me_level: int = 10,
        runs: int = 1
    ) -> Optional[ProductionMaterialsResponse]:
        """Add production materials for an item to the shopping list."""
        shopping_list = self.repo.get_list(list_id)
        if not shopping_list:
            return None

        # Check if blueprint exists
        blueprint = self.repo.get_blueprint_for_product(type_id)
        if not blueprint:
            return None

        # Get materials
        materials = self.repo.get_blueprint_materials(type_id, me_level, runs)
        if not materials:
            return None

        # Add materials to shopping list
        created_items = []
        for mat in materials:
            item_data = ShoppingItemCreate(
                type_id=mat['type_id'],
                quantity=int(mat['adjusted_quantity']),
                is_product=False,
                blueprint_runs=runs,
                me_level=me_level,
                build_decision=BuildDecision.BUY
            )
            created_item = self.repo.create_item(list_id, item_data)
            created_items.append(created_item)

        return ProductionMaterialsResponse(
            added_items=len(created_items),
            items=created_items
        )

    # Doctrine BOM

    def add_bom_items(
        self,
        list_id: int,
        bom_items: List[dict],
    ) -> List[ShoppingItem]:
        """Add doctrine BOM items to a shopping list.

        Each bom_item dict must have type_id, type_name, quantity.
        Returns list of created ShoppingItem instances.
        """
        if not bom_items:
            return []

        created_items = []
        for item in bom_items:
            item_data = ShoppingItemCreate(
                type_id=item["type_id"],
                quantity=item["quantity"],
                is_product=False,
                build_decision=BuildDecision.BUY,
            )
            created_item = self.repo.create_item(list_id, item_data)
            created_items.append(created_item)

        return created_items
