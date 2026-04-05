"""Shopping service models."""
from app.models.shopping import (
    ShoppingList,
    ShoppingListCreate,
    ShoppingListUpdate,
    ShoppingItem,
    ShoppingItemCreate,
    ShoppingItemUpdate,
    ShoppingItemWithMaterials,
    MaterialRequirement,
    RegionalComparison,
    RegionPrice,
    CargoSummary,
    TransportOption,
    BuildDecision,
    WizardMaterialsRequest,
    WizardMaterialsResponse,
    WizardRegionRequest,
    WizardRegionResponse,
    # Route models
    RouteStop,
    ShoppingRoute,
    # Market order models
    MarketOrder,
    RegionOrders,
    OrderSnapshots,
    # Items by region
    ItemsByRegion,
    ItemsByRegionResponse,
    # Asset models
    AssetMatch,
    ApplyAssetsResponse,
    ShoppingItemWithAssets,
    ListWithAssetsResponse,
    # Production materials
    ProductionMaterialsResponse
)

__all__ = [
    "ShoppingList",
    "ShoppingListCreate",
    "ShoppingListUpdate",
    "ShoppingItem",
    "ShoppingItemCreate",
    "ShoppingItemUpdate",
    "ShoppingItemWithMaterials",
    "MaterialRequirement",
    "RegionalComparison",
    "RegionPrice",
    "CargoSummary",
    "TransportOption",
    "BuildDecision",
    "WizardMaterialsRequest",
    "WizardMaterialsResponse",
    "WizardRegionRequest",
    "WizardRegionResponse",
    # Route models
    "RouteStop",
    "ShoppingRoute",
    # Market order models
    "MarketOrder",
    "RegionOrders",
    "OrderSnapshots",
    # Items by region
    "ItemsByRegion",
    "ItemsByRegionResponse",
    # Asset models
    "AssetMatch",
    "ApplyAssetsResponse",
    "ShoppingItemWithAssets",
    "ListWithAssetsResponse",
    # Production materials
    "ProductionMaterialsResponse"
]
