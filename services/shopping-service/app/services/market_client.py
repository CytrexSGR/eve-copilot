"""Market service client for price lookups."""
import logging
from typing import Optional, List, Dict

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class MarketClient:
    """Client for market-service price lookups."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.market_service_url
        self.timeout = 30.0

    async def get_price(self, type_id: int, region_id: int = 10000002) -> Optional[dict]:
        """Get price for a single item."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/prices/{type_id}",
                    params={"region_id": region_id}
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.warning(f"Market service unavailable for {type_id}: {e}")
            return None

    async def get_prices_batch(
        self,
        type_ids: List[int],
        region_id: int = 10000002
    ) -> Dict[int, dict]:
        """Get prices for multiple items."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/prices/batch",
                    json={"type_ids": type_ids, "region_id": region_id}
                )
                if response.status_code == 200:
                    data = response.json()
                    return {p["type_id"]: p for p in data.get("prices", [])}
                return {}
        except Exception as e:
            logger.warning(f"Market service batch unavailable: {e}")
            return {}

    async def compare_regions(self, type_id: int) -> Optional[dict]:
        """Compare prices across all trade hub regions."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/prices/{type_id}/compare"
                )
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.warning(f"Market service compare unavailable: {e}")
            return None


class LocalMarketClient(MarketClient):
    """Market client that falls back to direct database queries."""

    def __init__(self, db):
        super().__init__()
        self.db = db

    async def get_price(self, type_id: int, region_id: int = 10000002) -> Optional[dict]:
        """Get price, falling back to database if service unavailable."""
        # Try service first
        result = await super().get_price(type_id, region_id)
        if result:
            return result

        # Fallback to database
        query = """
            SELECT type_id, region_id, lowest_sell, highest_buy,
                   volume, order_count, updated_at
            FROM market_prices
            WHERE type_id = $1 AND region_id = $2
        """
        row = await self.db.fetchrow(query, type_id, region_id)
        if row:
            return dict(row)
        return None

    async def get_prices_batch(
        self,
        type_ids: List[int],
        region_id: int = 10000002
    ) -> Dict[int, dict]:
        """Get prices batch, falling back to database."""
        # Try service first
        result = await super().get_prices_batch(type_ids, region_id)
        if result:
            return result

        # Fallback to database
        query = """
            SELECT type_id, region_id, lowest_sell, highest_buy,
                   volume, order_count, updated_at
            FROM market_prices
            WHERE type_id = ANY($1) AND region_id = $2
        """
        rows = await self.db.fetch(query, type_ids, region_id)
        return {row["type_id"]: dict(row) for row in rows}
