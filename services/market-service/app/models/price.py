"""Market price models."""
from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field

from eve_shared.constants import JITA_REGION_ID


class PriceSource(str, Enum):
    """Source of price data."""
    REDIS = "redis"      # L1 Cache - fastest
    CACHE = "cache"      # L2 PostgreSQL cache
    ESI = "esi"          # L3 Fresh from API
    UNKNOWN = "unknown"


class MarketPrice(BaseModel):
    """Market price with source tracking."""

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    type_id: int = Field(..., description="EVE type ID")
    sell_price: float = Field(default=0.0, ge=0, description="Lowest sell price")
    buy_price: float = Field(default=0.0, ge=0, description="Highest buy price")
    adjusted_price: float = Field(default=0.0, ge=0, description="Adjusted price from ESI")
    average_price: float = Field(default=0.0, ge=0, description="Average price from ESI")
    region_id: int = Field(default=JITA_REGION_ID, description="Region ID (default: Jita)")
    source: PriceSource = Field(default=PriceSource.UNKNOWN, description="Price data source")
    last_updated: datetime = Field(default_factory=datetime.now, description="Timestamp of last update")

    def is_stale(self, max_age_seconds: int = 3600) -> bool:
        """Check if price data is stale."""
        age = datetime.utcnow() - self.last_updated
        return age.total_seconds() > max_age_seconds


class CacheStats(BaseModel):
    """Market price cache statistics."""

    model_config = ConfigDict(from_attributes=True)

    total_items: int = Field(..., ge=0, description="Total number of cached items")
    oldest_entry: Optional[datetime] = Field(None, description="Timestamp of oldest entry")
    newest_entry: Optional[datetime] = Field(None, description="Timestamp of newest entry")
    cache_age_seconds: Optional[float] = Field(None, ge=0, description="Age of cache in seconds")
    is_stale: bool = Field(..., description="Whether cache is stale (>1 hour)")


class PriceUpdate(BaseModel):
    """Price update result model."""

    model_config = ConfigDict(from_attributes=True)

    success: bool = Field(..., description="Whether update was successful")
    items_updated: int = Field(..., ge=0, description="Number of items updated")
    timestamp: datetime = Field(..., description="Timestamp of update")
    message: str = Field(..., description="Human-readable message")


class PriceRequest(BaseModel):
    """Single price request."""
    type_id: int = Field(..., description="EVE type ID")
    region_id: int = Field(default=JITA_REGION_ID, description="Region ID")


class PriceBulkRequest(BaseModel):
    """Bulk price request."""
    type_ids: List[int] = Field(..., max_length=1000, description="List of type IDs (max 1000)")
    region_id: int = Field(default=JITA_REGION_ID, description="Region ID")


class ArbitrageOpportunity(BaseModel):
    """Arbitrage opportunity between regions."""

    model_config = ConfigDict(from_attributes=True)

    type_id: int
    type_name: Optional[str] = None
    buy_region: str
    buy_price: float
    sell_region: str
    sell_price: float
    profit_per_unit: float
    profit_percent: float
    volume: Optional[float] = None


class RegionalComparison(BaseModel):
    """Price comparison across regions."""

    model_config = ConfigDict(from_attributes=True)

    type_id: int
    type_name: Optional[str] = None
    prices_by_region: dict
    best_buy_region: Optional[str] = None
    best_buy_price: Optional[float] = None
    best_sell_region: Optional[str] = None
    best_sell_price: Optional[float] = None
