"""Production service Pydantic models."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class MaterialItem(BaseModel):
    """Single material item in a bill of materials."""

    type_id: int = Field(..., gt=0, description="EVE type ID of the material")
    name: str = Field(..., description="Name of the material")
    quantity: int = Field(..., gt=0, description="Quantity needed")
    unit_price: float = Field(default=0.0, ge=0.0, description="Price per unit")
    total_cost: float = Field(default=0.0, ge=0.0, description="Total cost for this material")


class BillOfMaterials(BaseModel):
    """Complete bill of materials for production."""

    materials: List[MaterialItem] = Field(
        default_factory=list,
        description="List of materials needed"
    )


class AssetMatch(BaseModel):
    """Result of matching BOM against character assets."""

    materials_available: int = Field(..., ge=0, description="Number of materials fully available")
    materials_missing: int = Field(..., ge=0, description="Number of materials missing or partial")
    fully_covered: bool = Field(..., description="True if all materials are available")


class ProductionTime(BaseModel):
    """Production time information."""

    base_seconds: int = Field(..., ge=0, description="Base production time in seconds")
    actual_seconds: int = Field(..., ge=0, description="Actual time with TE bonus in seconds")
    formatted: str = Field(..., description="Human-readable time format (e.g., '2h 30m')")


class ProductionFinancials(BaseModel):
    """Financial metrics for production."""

    build_cost: float = Field(..., ge=0.0, description="Total cost of all materials at market price")
    cash_to_invest: float = Field(..., ge=0.0, description="Cost of missing materials to buy")
    revenue: float = Field(..., ge=0.0, description="Projected revenue from selling product")
    profit: float = Field(..., description="Profit (revenue - build_cost), can be negative")
    margin: float = Field(..., description="Profit margin percentage, can be negative")
    roi: float = Field(..., description="ROI on investment percentage, can be negative")


class ProductionParameters(BaseModel):
    """Input parameters for production simulation."""

    runs: int = Field(..., gt=0, description="Number of production runs")
    me_level: int = Field(..., ge=0, le=10, description="Material Efficiency level (0-10)")
    te_level: int = Field(..., ge=0, le=20, description="Time Efficiency level (0-20)")
    region_id: int = Field(..., gt=0, description="Region ID for market prices")


class ProductionProduct(BaseModel):
    """Product information."""

    type_id: int = Field(..., gt=0, description="EVE type ID of the product")
    name: str = Field(..., description="Name of the product")
    output_quantity: int = Field(..., gt=0, description="Total output quantity from all runs")
    unit_sell_price: float = Field(..., ge=0.0, description="Sell price per unit")


class ProductionSimulation(BaseModel):
    """Complete production simulation result."""

    product: ProductionProduct
    parameters: ProductionParameters
    production_time: ProductionTime
    bill_of_materials: BillOfMaterials
    asset_match: AssetMatch
    financials: ProductionFinancials
    shopping_list: List[MaterialItem] = Field(
        default_factory=list,
        description="Materials that need to be purchased"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings about profitability or other issues"
    )


class QuickProfitCheck(BaseModel):
    """Fast profit calculation result for bulk scanning."""

    type_id: int = Field(..., gt=0, description="EVE type ID")
    name: str = Field(..., description="Product name")
    runs: int = Field(..., gt=0, description="Number of runs")
    me: int = Field(..., ge=0, le=10, description="Material Efficiency level")
    output_quantity: int = Field(..., gt=0, description="Total output quantity")
    material_cost: float = Field(..., ge=0.0, description="Total material cost")
    product_price: float = Field(..., ge=0.0, description="Product sell price per unit")
    revenue: float = Field(..., ge=0.0, description="Total revenue")
    profit: float = Field(..., description="Profit, can be negative")
    margin_percent: float = Field(..., description="Profit margin percentage, can be negative")


class ProductionChainNode(BaseModel):
    """Node in a production chain tree."""

    type_id: int
    name: str
    quantity: int
    is_manufacturable: bool = False
    children: List["ProductionChainNode"] = Field(default_factory=list)


class ProductionEconomics(BaseModel):
    """Production economics analysis for a single item."""

    type_id: int
    name: str
    region_id: int
    region_name: str
    me: int
    te: int
    material_cost: float
    product_price: float
    profit: float
    margin_percent: float
    roi_percent: float
    production_time_seconds: int
    is_profitable: bool


class RegionEconomics(BaseModel):
    """Multi-region economics comparison."""

    type_id: int
    name: str
    regions: List[ProductionEconomics]
    best_region: Optional[str] = None
    best_profit: Optional[float] = None
