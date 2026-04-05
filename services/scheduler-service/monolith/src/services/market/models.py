"""Market service Pydantic models with cache-aware pricing."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# EVE Online region constants
JITA_REGION_ID = 10000002


class PriceSource(str, Enum):
    """Source of price data."""

    REDIS = "redis"  # L1 Cache - fastest
    CACHE = "cache"  # L2 PostgreSQL cache
    ESI = "esi"  # L3 Fresh from API
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
        """Check if price data is stale.

        Args:
            max_age_seconds: Maximum age in seconds before data is considered stale.
                           Default is 3600 (1 hour).

        Returns:
            True if the price data is older than max_age_seconds.
        """
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
