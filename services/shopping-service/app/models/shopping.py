"""Shopping service data models."""
from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class BuildDecision(str, Enum):
    """Build or buy decision for a product."""
    BUY = "buy"
    BUILD = "build"
    UNDECIDED = "undecided"


class ShoppingListCreate(BaseModel):
    """Request model for creating a shopping list."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    character_id: Optional[int] = None


class ShoppingListUpdate(BaseModel):
    """Request model for updating a shopping list."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class ShoppingList(BaseModel):
    """Shopping list model."""
    id: int
    name: str
    description: Optional[str] = None
    character_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    item_count: int = 0
    total_cost: float = 0.0


class ShoppingItemCreate(BaseModel):
    """Request model for creating a shopping item."""
    type_id: int
    quantity: int = Field(default=1, ge=1)
    is_product: bool = False
    blueprint_runs: int = Field(default=1, ge=1)
    me_level: int = Field(default=0, ge=0, le=10)
    region_id: Optional[int] = None
    build_decision: BuildDecision = BuildDecision.UNDECIDED
    parent_item_id: Optional[int] = None


class ShoppingItemUpdate(BaseModel):
    """Request model for updating a shopping item."""
    quantity: Optional[int] = Field(None, ge=1)
    blueprint_runs: Optional[int] = Field(None, ge=1)
    me_level: Optional[int] = Field(None, ge=0, le=10)
    region_id: Optional[int] = None
    build_decision: Optional[BuildDecision] = None
    is_purchased: Optional[bool] = None


class ShoppingItem(BaseModel):
    """Shopping item model."""
    id: int
    list_id: int
    type_id: int
    type_name: str
    quantity: int
    is_product: bool = False
    blueprint_runs: int = 1
    me_level: int = 0
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    build_decision: BuildDecision = BuildDecision.UNDECIDED
    is_purchased: bool = False
    unit_price: float = 0.0
    total_price: float = 0.0
    volume: float = 0.0
    total_volume: float = 0.0
    parent_item_id: Optional[int] = None
    quantity_in_assets: int = 0
    created_at: datetime
    updated_at: datetime


class MaterialRequirement(BaseModel):
    """Material requirement for production."""
    type_id: int
    type_name: str
    quantity_base: int
    quantity_adjusted: int
    unit_price: float = 0.0
    total_price: float = 0.0
    volume: float = 0.0
    is_manufacturable: bool = False


class ShoppingItemWithMaterials(ShoppingItem):
    """Shopping item with material requirements."""
    materials: List[MaterialRequirement] = []
    production_cost: float = 0.0
    market_price: float = 0.0
    profit: float = 0.0
    roi: float = 0.0


class RegionPrice(BaseModel):
    """Price data for a region."""
    region_id: int
    region_name: str
    hub_system: str
    lowest_sell: float
    highest_buy: float
    volume: int = 0
    order_count: int = 0


class RegionalComparison(BaseModel):
    """Regional price comparison for a shopping list."""
    list_id: int
    list_name: str
    regions: List[RegionPrice]
    items: List[dict]
    best_region: Optional[RegionPrice] = None
    total_by_region: dict = {}


class CargoSummary(BaseModel):
    """Cargo summary for transport planning."""
    list_id: int
    total_items: int
    total_volume: float
    total_cost: float
    items_by_volume: List[dict] = []


class TransportOption(BaseModel):
    """Transport ship option."""
    ship_name: str
    ship_type_id: int
    cargo_capacity: float
    trips_needed: int
    fits_in_single_trip: bool


# Wizard models
class WizardMaterialsRequest(BaseModel):
    """Request for calculating materials in wizard."""
    type_id: int
    runs: int = Field(default=1, ge=1)
    me_level: int = Field(default=0, ge=0, le=10)
    include_sub_products: bool = False


class WizardMaterialsResponse(BaseModel):
    """Response for material calculation."""
    type_id: int
    type_name: str
    runs: int
    me_level: int
    materials: List[MaterialRequirement]
    total_cost: float
    sub_products: List[dict] = []


class WizardRegionRequest(BaseModel):
    """Request for comparing regions in wizard."""
    type_ids: List[int]
    quantities: List[int]


class WizardRegionResponse(BaseModel):
    """Response for regional comparison."""
    regions: List[RegionPrice]
    best_region: RegionPrice
    items: List[dict]
    savings_vs_worst: float


# Route models
class RouteStop(BaseModel):
    """A stop in the shopping route."""
    system_name: str
    region_name: str
    jumps_from_previous: int
    items_to_buy: List[dict] = []
    subtotal: float = 0.0


class ShoppingRoute(BaseModel):
    """Calculated shopping route through trade hubs."""
    home_system: str
    total_jumps: int
    stops: List[RouteStop]
    return_home: bool
    total_cost: float


# Market order models
class MarketOrder(BaseModel):
    """A single market order."""
    rank: int
    price: float
    volume: int
    location_id: int
    issued: Optional[str] = None


class RegionOrders(BaseModel):
    """Orders for a specific region."""
    display_name: str
    sells: List[MarketOrder] = []
    buys: List[MarketOrder] = []
    updated_at: Optional[str] = None


class OrderSnapshots(BaseModel):
    """Order snapshots for an item across regions."""
    type_id: int
    regions: dict[str, RegionOrders]


# Items grouped by region
class ItemsByRegion(BaseModel):
    """Shopping list items grouped by their target region."""
    region_id: int
    region_name: str
    hub_system: str
    items: List[ShoppingItem]
    total_cost: float
    total_volume: float


class ItemsByRegionResponse(BaseModel):
    """Response for items grouped by region."""
    list_id: int
    list_name: str
    regions: List[ItemsByRegion]
    unassigned_items: List[ShoppingItem] = []


# Asset models
class AssetMatch(BaseModel):
    """Asset match for a shopping item."""
    type_id: int
    type_name: str
    quantity_needed: int
    quantity_in_assets: int
    quantity_to_buy: int


class ApplyAssetsResponse(BaseModel):
    """Response from applying assets to a shopping list."""
    list_id: int
    character_id: int
    items_updated: int
    total_covered: int
    total_needed: int
    matches: List[AssetMatch]


class ShoppingItemWithAssets(ShoppingItem):
    """Shopping item with asset coverage information."""
    quantity_in_assets: int = 0
    quantity_to_buy: int = 0


class ListWithAssetsResponse(BaseModel):
    """Shopping list with asset deduction information."""
    id: int
    name: str
    description: Optional[str] = None
    character_id: Optional[int] = None
    items: List[ShoppingItemWithAssets]
    total_needed: int
    total_covered: int
    total_to_buy: int


# Production materials response
class ProductionMaterialsResponse(BaseModel):
    """Response for adding production materials."""
    added_items: int
    items: List[ShoppingItem]
