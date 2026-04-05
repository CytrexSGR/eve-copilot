"""ESI API client for market data (L3 - fallback)."""
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import httpx

from app.config import settings
from app.models import MarketPrice, PriceSource
from eve_shared.constants import JITA_REGION_ID, TRADE_HUB_STATIONS, TRADE_HUB_REGIONS

logger = logging.getLogger(__name__)


class ESIClient:
    """EVE ESI API client for market data."""

    def __init__(self, redis_client=None):
        """Initialize ESI client."""
        self.base_url = settings.esi_base_url
        self.timeout = settings.esi_timeout
        self.user_agent = settings.esi_user_agent
        self.redis = redis_client
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"User-Agent": self.user_agent}
            )
        return self._client

    def close(self):
        """Close HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def get_market_prices(self) -> List[Dict[str, Any]]:
        """
        Get all market prices from ESI.

        Returns:
            List of price data dicts with type_id, adjusted_price, average_price
        """
        try:
            response = self.client.get("/markets/prices/")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"ESI market prices error: {e}")
            return []

    def get_market_orders(
        self,
        region_id: int,
        type_id: int,
        order_type: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        Get market orders for an item in a region.

        Args:
            region_id: Region ID
            type_id: Item type ID
            order_type: 'buy', 'sell', or 'all'

        Returns:
            List of market orders
        """
        try:
            params = {"type_id": type_id, "order_type": order_type}
            response = self.client.get(
                f"/markets/{region_id}/orders/",
                params=params
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"ESI market orders error for {type_id} in {region_id}: {e}")
            return []

    def get_market_stats(
        self,
        region_id: int,
        type_id: int
    ) -> Dict[str, Any]:
        """
        Calculate market statistics from orders.

        For trade hub regions, filters orders to the hub station only.

        Args:
            region_id: Region ID
            type_id: Item type ID

        Returns:
            Dict with lowest_sell, highest_buy, total_orders, etc.
        """
        cache_key = f"market-stats:{region_id}:{type_id}"

        # Check cache
        if self.redis:
            try:
                cached = self.redis.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception:
                pass

        orders = self.get_market_orders(region_id, type_id)
        if not orders:
            return {}

        # Filter to trade hub station if known
        hub_station = TRADE_HUB_STATIONS.get(region_id)
        if hub_station:
            hub_orders = [o for o in orders if o.get("location_id") == hub_station]
            if hub_orders:
                orders = hub_orders

        sell_orders = [o for o in orders if not o.get("is_buy_order")]
        buy_orders = [o for o in orders if o.get("is_buy_order")]

        stats = {
            "type_id": type_id,
            "region_id": region_id,
            "total_orders": len(orders),
            "sell_orders": len(sell_orders),
            "buy_orders": len(buy_orders),
            "lowest_sell": min((o["price"] for o in sell_orders), default=None),
            "highest_buy": max((o["price"] for o in buy_orders), default=None),
            "sell_volume": sum(o["volume_remain"] for o in sell_orders),
            "buy_volume": sum(o["volume_remain"] for o in buy_orders),
        }

        # Calculate spread
        if stats["lowest_sell"] and stats["highest_buy"]:
            stats["spread"] = stats["lowest_sell"] - stats["highest_buy"]
            stats["spread_percent"] = (
                (stats["spread"] / stats["lowest_sell"]) * 100
                if stats["lowest_sell"] > 0 else 0
            )

        # Cache result
        if self.redis and stats:
            try:
                self.redis.set(cache_key, json.dumps(stats), ex=60)
            except Exception:
                pass

        return stats

    def fetch_price(
        self,
        type_id: int,
        region_id: int = JITA_REGION_ID
    ) -> Optional[MarketPrice]:
        """
        Fetch price from ESI for a single item.

        For trade hub regions, filters orders to the hub station only
        (e.g. Jita 4-4) to avoid misleading prices from remote stations.

        Args:
            type_id: Item type ID
            region_id: Region ID

        Returns:
            MarketPrice if found, None otherwise
        """
        try:
            orders = self.get_market_orders(region_id, type_id)
            if not orders:
                return None

            # Filter to trade hub station if known, otherwise use all orders
            hub_station = TRADE_HUB_STATIONS.get(region_id)
            if hub_station:
                hub_orders = [o for o in orders if o.get("location_id") == hub_station]
                # Fall back to region-wide if no orders at hub station
                if hub_orders:
                    orders = hub_orders

            sell_prices = [o["price"] for o in orders if not o.get("is_buy_order")]
            buy_prices = [o["price"] for o in orders if o.get("is_buy_order")]

            return MarketPrice(
                type_id=type_id,
                sell_price=min(sell_prices) if sell_prices else 0.0,
                buy_price=max(buy_prices) if buy_prices else 0.0,
                region_id=region_id,
                source=PriceSource.ESI,
                last_updated=datetime.now(timezone.utc)
            )
        except Exception as e:
            logger.warning(f"ESI fetch failed for {type_id}: {e}")
            return None

    def fetch_prices_bulk(
        self,
        type_ids: List[int],
        region_id: int = JITA_REGION_ID
    ) -> List[MarketPrice]:
        """
        Fetch prices from ESI for multiple items.

        Note: ESI doesn't have a bulk endpoint, so we fetch one by one.

        Args:
            type_ids: List of type IDs
            region_id: Region ID

        Returns:
            List of MarketPrice objects
        """
        prices = []
        for type_id in type_ids:
            price = self.fetch_price(type_id, region_id)
            if price:
                prices.append(price)
        return prices

    def get_all_region_prices(self, type_id: int) -> Dict[str, Dict[str, Any]]:
        """
        Get prices for an item across all trade hub regions.

        Args:
            type_id: Item type ID

        Returns:
            Dict mapping region name to price stats
        """
        results = {}
        for region_name, region_id in TRADE_HUB_REGIONS.items():
            stats = self.get_market_stats(region_id, type_id)
            if stats:
                results[region_name] = {
                    "lowest_sell": stats.get("lowest_sell"),
                    "highest_buy": stats.get("highest_buy"),
                    "sell_volume": stats.get("sell_volume"),
                    "buy_volume": stats.get("buy_volume"),
                }
        return results

    def find_arbitrage_opportunities(
        self,
        type_id: int,
        min_profit_percent: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        Find arbitrage opportunities for an item between trade hubs.

        Args:
            type_id: Item type ID
            min_profit_percent: Minimum profit percentage to include

        Returns:
            List of arbitrage opportunities
        """
        prices = self.get_all_region_prices(type_id)
        opportunities = []

        regions = list(prices.keys())
        for i, buy_region in enumerate(regions):
            for sell_region in regions[i+1:]:
                buy_data = prices[buy_region]
                sell_data = prices[sell_region]

                # Check buy in region A, sell in region B
                if buy_data.get("lowest_sell") and sell_data.get("highest_buy"):
                    buy_price = buy_data["lowest_sell"]
                    sell_price = sell_data["highest_buy"]
                    profit = sell_price - buy_price
                    profit_pct = (profit / buy_price * 100) if buy_price > 0 else 0

                    if profit_pct >= min_profit_percent:
                        opportunities.append({
                            "buy_region": buy_region,
                            "buy_price": buy_price,
                            "sell_region": sell_region,
                            "sell_price": sell_price,
                            "profit_per_unit": profit,
                            "profit_percent": round(profit_pct, 2),
                        })

                # Check buy in region B, sell in region A
                if sell_data.get("lowest_sell") and buy_data.get("highest_buy"):
                    buy_price = sell_data["lowest_sell"]
                    sell_price = buy_data["highest_buy"]
                    profit = sell_price - buy_price
                    profit_pct = (profit / buy_price * 100) if buy_price > 0 else 0

                    if profit_pct >= min_profit_percent:
                        opportunities.append({
                            "buy_region": sell_region,
                            "buy_price": buy_price,
                            "sell_region": buy_region,
                            "sell_price": sell_price,
                            "profit_per_unit": profit,
                            "profit_percent": round(profit_pct, 2),
                        })

        # Sort by profit percent descending
        opportunities.sort(key=lambda x: x["profit_percent"], reverse=True)
        return opportunities
