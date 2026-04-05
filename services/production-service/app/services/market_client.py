"""Market service client for price lookups."""
import logging
from typing import Dict, List, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class MarketClient:
    """Client for the Market Service API."""

    def __init__(self, base_url: Optional[str] = None):
        """Initialize market client."""
        self.base_url = base_url or settings.market_service_url
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=30.0
            )
        return self._client

    def close(self):
        """Close HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def get_price(self, type_id: int, region_id: int) -> Optional[float]:
        """
        Get price for a single item.

        Args:
            type_id: Item type ID
            region_id: Region ID

        Returns:
            Sell price or None if not found
        """
        try:
            response = self.client.get(
                f"/api/market/price/{type_id}",
                params={"region_id": region_id}
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("sell_price", 0.0)
            return None
        except Exception as e:
            logger.warning(f"Failed to get price for {type_id}: {e}")
            return None

    def get_prices_bulk(
        self,
        type_ids: List[int],
        region_id: int
    ) -> Dict[int, float]:
        """
        Get prices for multiple items.

        Args:
            type_ids: List of type IDs
            region_id: Region ID

        Returns:
            Dict mapping type_id to sell_price
        """
        if not type_ids:
            return {}

        try:
            response = self.client.post(
                "/api/market/prices",
                json={"type_ids": type_ids, "region_id": region_id}
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    int(tid): price_data.get("sell_price", 0.0)
                    for tid, price_data in data.items()
                }
            return {}
        except Exception as e:
            logger.warning(f"Failed to get bulk prices: {e}")
            return {}


class LocalMarketClient:
    """
    Local market client using database directly.

    Used when market-service is not available or for internal use.
    """

    def __init__(self, db):
        """Initialize with database pool."""
        self.db = db

    def get_prices_bulk(
        self,
        type_ids: List[int],
        region_id: int
    ) -> Dict[int, float]:
        """Get prices from local database cache."""
        if not type_ids:
            return {}

        try:
            with self.db.connection() as conn:
                with conn.cursor() as cur:
                    # Try regional prices first
                    cur.execute('''
                        SELECT type_id, lowest_sell
                        FROM market_prices
                        WHERE type_id = ANY(%s) AND region_id = %s
                    ''', (list(type_ids), region_id))
                    prices = {
                        row[0]: float(row[1]) if row[1] else 0.0
                        for row in cur.fetchall()
                    }

                    # Fall back to adjusted prices for missing items
                    missing = [tid for tid in type_ids if tid not in prices]
                    if missing:
                        cur.execute('''
                            SELECT type_id, adjusted_price
                            FROM market_prices_cache
                            WHERE type_id = ANY(%s)
                        ''', (missing,))
                        for row in cur.fetchall():
                            if row[0] not in prices:
                                prices[row[0]] = float(row[1]) if row[1] else 0.0

                    return prices
        except Exception as e:
            logger.warning(f"Failed to get local prices: {e}")
            return {}
