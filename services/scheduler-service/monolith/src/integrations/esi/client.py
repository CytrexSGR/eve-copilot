"""ESI API Client for EVE Online."""

import time
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

import requests
from requests.exceptions import RequestException, Timeout

from src.core.config import get_settings
from src.core.exceptions import ExternalAPIError
from src.integrations.esi.shared_rate_state import shared_rate_state
from src.integrations.esi.etag_cache import etag_cache

logger = logging.getLogger(__name__)

# Trade hub regions
REGIONS = {
    "the_forge": 10000002,      # Jita
    "domain": 10000043,         # Amarr
    "heimatar": 10000030,       # Rens
    "sinq_laison": 10000032,    # Dodixie
    "metropolis": 10000042,     # Hek
}


@dataclass
class RateLimitState:
    """Track rate limit status across requests."""
    token_limit: int = 0
    token_remaining: int = 0
    error_limit_remain: int = 100
    error_limit_reset: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    cached_requests: int = 0
    error_requests: int = 0
    is_rate_limited: bool = False
    rate_limit_until: Optional[datetime] = None
    is_error_banned: bool = False

    def update_from_headers(self, headers: Dict[str, str]) -> None:
        """Update state from response headers."""
        if "X-Ratelimit-Limit" in headers:
            self.token_limit = int(headers["X-Ratelimit-Limit"])
        if "X-Ratelimit-Remaining" in headers:
            self.token_remaining = int(headers["X-Ratelimit-Remaining"])
        if "X-ESI-Error-Limit-Remain" in headers:
            self.error_limit_remain = int(headers["X-ESI-Error-Limit-Remain"])
        if "X-ESI-Error-Limit-Reset" in headers:
            self.error_limit_reset = int(headers["X-ESI-Error-Limit-Reset"])

    def get_summary(self) -> Dict[str, Any]:
        """Get current state as dict."""
        return {
            "token_limit": self.token_limit,
            "token_remaining": self.token_remaining,
            "error_limit_remain": self.error_limit_remain,
            "error_limit_reset": self.error_limit_reset,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "cached_requests": self.cached_requests,
            "error_requests": self.error_requests,
            "is_rate_limited": self.is_rate_limited,
            "is_error_banned": self.is_error_banned
        }


class ESIClient:
    """
    Client for interacting with EVE Online's ESI API.

    This client handles all direct API calls to ESI, including proper
    error handling, rate limiting awareness, and consistent response formatting.

    Features:
    - Automatic rate limit monitoring
    - Price caching (5 minutes)
    - Throttling when limits are low
    - Emergency shutdown on HTTP 420 (error banned)
    """

    # Rate limiting thresholds
    TOKEN_THROTTLE_THRESHOLD = 50
    ERROR_LIMIT_THRESHOLD = 30
    BASE_DELAY = 0.5
    THROTTLE_DELAY = 3.0

    def __init__(self):
        """
        Initialize ESI client with configuration from settings.

        Sets up a requests.Session with appropriate headers for ESI API calls.
        """
        settings = get_settings()
        self.base_url = settings.esi_base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": settings.esi_user_agent,
            "Accept": "application/json"
        })

        # Rate limit tracking
        self.rate_state = RateLimitState()

        # Price cache (5 minute TTL)
        self._price_cache: Dict[str, Tuple[Any, datetime]] = {}
        self._cache_duration = timedelta(minutes=5)

        # Last request time for throttling
        self._last_request_time: float = 0

    def _should_throttle(self) -> bool:
        """Check if we should throttle requests."""
        if shared_rate_state.is_globally_banned():
            return True
        if shared_rate_state.should_throttle():
            return True
        if self.rate_state.token_remaining > 0 and \
           self.rate_state.token_remaining < self.TOKEN_THROTTLE_THRESHOLD:
            return True
        if self.rate_state.error_limit_remain < self.ERROR_LIMIT_THRESHOLD:
            return True
        return False

    def _wait_if_needed(self) -> None:
        """Apply throttling delay if needed."""
        now = time.time()
        elapsed = now - self._last_request_time

        # Check if rate limited
        if self.rate_state.is_rate_limited:
            if self.rate_state.rate_limit_until and \
               datetime.now() < self.rate_state.rate_limit_until:
                wait_time = (self.rate_state.rate_limit_until - datetime.now()).total_seconds()
                logger.info(f"Rate limited, waiting {wait_time:.1f}s")
                time.sleep(wait_time)
                self.rate_state.is_rate_limited = False

        # Apply throttle delay if needed
        if self._should_throttle():
            delay = self.THROTTLE_DELAY
            if elapsed < delay:
                time.sleep(delay - elapsed)
        elif elapsed < self.BASE_DELAY:
            time.sleep(self.BASE_DELAY - elapsed)

        self._last_request_time = time.time()

    def _handle_rate_limit_response(self, response: requests.Response, endpoint: str) -> Tuple[bool, Optional[Any]]:
        """Process response and update rate limit state."""
        self.rate_state.total_requests += 1
        self.rate_state.update_from_headers(dict(response.headers))
        shared_rate_state.update_from_headers(dict(response.headers))

        status = response.status_code

        # Success (2XX)
        if 200 <= status < 300:
            self.rate_state.successful_requests += 1
            return True, response.json()

        # Not Modified (304)
        if status == 304:
            self.rate_state.cached_requests += 1
            return True, None

        # Rate Limited (429)
        if status == 429:
            self.rate_state.error_requests += 1
            self.rate_state.is_rate_limited = True
            retry_after = int(response.headers.get("Retry-After", 60))
            self.rate_state.rate_limit_until = datetime.now() + timedelta(seconds=retry_after)
            logger.warning(f"ESI Rate Limited (429)! Waiting {retry_after}s. Endpoint: {endpoint}")
            return False, {"error": "rate_limited", "retry_after": retry_after}

        # Error Banned (420)
        if status == 420:
            self.rate_state.error_requests += 1
            self.rate_state.is_error_banned = True
            shared_rate_state.set_global_ban()
            logger.critical(f"ESI ERROR BANNED (420)! All requests blocked. Endpoint: {endpoint}")
            return False, {"error": "error_banned", "fatal": True}

        # Other errors
        if status >= 400:
            self.rate_state.error_requests += 1
            if self.rate_state.error_limit_remain < 30:
                logger.warning(f"ESI Error {status} on {endpoint}. Error limit: {self.rate_state.error_limit_remain}")
            return False, {"error": f"http_{status}", "details": response.text[:200]}

        return False, None

    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status."""
        return self.rate_state.get_summary()

    def is_safe_to_continue(self) -> bool:
        """Check if it's safe to continue making requests."""
        if self.rate_state.is_error_banned:
            return False
        if self.rate_state.error_limit_remain < 10:
            return False
        if self.rate_state.token_remaining > 0 and self.rate_state.token_remaining < 10:
            return False
        return True

    def clear_cache(self) -> None:
        """Clear price cache."""
        self._price_cache.clear()

    def reset_rate_state(self) -> None:
        """Reset rate limit state (use after error ban expires)."""
        self.rate_state = RateLimitState()

    def get_market_prices(self) -> List[Dict[str, Any]]:
        """
        Fetch global market prices from ESI.

        This endpoint returns adjusted and average prices for all tradeable items
        in EVE Online. Typically returns ~15,000+ items.

        Returns:
            List[Dict[str, Any]]: List of market price data with structure:
                [
                    {
                        "type_id": int,
                        "adjusted_price": float,
                        "average_price": float  # Optional, may be missing
                    },
                    ...
                ]

        Raises:
            ExternalAPIError: If the API request fails, times out, or returns
                an error status code.

        Example:
            >>> client = ESIClient()
            >>> prices = client.get_market_prices()
            >>> print(f"Fetched {len(prices)} market prices")
            Fetched 15234 market prices
        """
        url = f"{self.base_url}/markets/prices/"

        try:
            response = self.session.get(
                url,
                params={"datasource": "tranquility"},
                timeout=60
            )

            if response.status_code != 200:
                raise ExternalAPIError(
                    service_name="ESI",
                    status_code=response.status_code,
                    message=f"Failed to fetch market prices: {response.text}"
                )

            try:
                return response.json()
            except ValueError as e:
                raise ExternalAPIError(
                    service_name="ESI",
                    status_code=response.status_code,
                    message=f"Invalid JSON response: {str(e)}"
                )

        except Timeout as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Request timeout: {str(e)}"
            )
        except RequestException as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Request failed: {str(e)}"
            )
        except ExternalAPIError:
            # Re-raise our own exceptions
            raise
        except Exception as e:
            # Catch any other unexpected errors
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Unexpected error: {str(e)}"
            )

    def get(self, endpoint: str, timeout: int = 30) -> List[Dict[str, Any]]:
        """
        Generic GET request to ESI API.

        Args:
            endpoint: API endpoint path (e.g., "/sovereignty/campaigns/")
            timeout: Request timeout in seconds (default: 30)

        Returns:
            List[Dict[str, Any]]: JSON response from ESI

        Raises:
            ExternalAPIError: If the API request fails

        Example:
            >>> client = ESIClient()
            >>> campaigns = client.get("/sovereignty/campaigns/")
            >>> print(f"Fetched {len(campaigns)} campaigns")
        """
        url = f"{self.base_url}{endpoint}"

        # ETag conditional request
        headers = {}
        cached_etag = etag_cache.get_etag(endpoint)
        if cached_etag:
            headers["If-None-Match"] = cached_etag

        try:
            response = self.session.get(
                url,
                params={"datasource": "tranquility"},
                headers=headers,
                timeout=timeout
            )

            # Update shared rate state
            shared_rate_state.update_from_headers(dict(response.headers))

            if response.status_code == 200:
                data = response.json()
                response_etag = response.headers.get("ETag")
                if response_etag:
                    etag_cache.store(endpoint, response_etag, data)
                return data

            if response.status_code == 304:
                cached = etag_cache.get_cached_data(endpoint)
                if cached is not None:
                    return cached
                return []

            if response.status_code != 200:
                raise ExternalAPIError(
                    service_name="ESI",
                    status_code=response.status_code,
                    message=f"Failed to fetch {endpoint}: {response.text}"
                )

        except Timeout as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Request timeout: {str(e)}"
            )
        except RequestException as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Request failed: {str(e)}"
            )
        except ExternalAPIError:
            raise
        except Exception as e:
            raise ExternalAPIError(
                service_name="ESI",
                status_code=0,
                message=f"Unexpected error: {str(e)}"
            )

    # ========== MARKET METHODS ==========

    def get_market_orders(
        self,
        region_id: int,
        type_id: int,
        max_pages: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get all market orders for an item in a region.

        Args:
            region_id: Region ID (e.g., 10000002 for The Forge)
            type_id: Item type ID
            max_pages: Maximum pages to fetch (safety limit)

        Returns:
            List of order dicts with keys: order_id, type_id, price,
            volume_remain, is_buy_order, location_id, etc.
        """
        if self.rate_state.is_error_banned:
            logger.error("ESI client is error banned, refusing request")
            return []

        all_orders = []
        page = 1

        while page <= max_pages:
            self._wait_if_needed()

            url = f"{self.base_url}/markets/{region_id}/orders/"
            params = {
                "datasource": "tranquility",
                "order_type": "all",
                "type_id": type_id,
                "page": page
            }

            try:
                response = self.session.get(url, params=params, timeout=30)
                success, data = self._handle_rate_limit_response(response, f"/markets/{region_id}/orders/")

                if not success:
                    if data and data.get("error") == "rate_limited":
                        time.sleep(data.get("retry_after", 60))
                        continue  # Retry same page
                    break

                if not data:
                    break

                all_orders.extend(data)

                # Check pagination (1000 per page)
                if len(data) < 1000:
                    break
                page += 1

            except Timeout:
                self.rate_state.error_requests += 1
                logger.warning(f"ESI timeout on /markets/{region_id}/orders/")
                break
            except RequestException as e:
                self.rate_state.error_requests += 1
                logger.error(f"ESI request error: {e}")
                break

        return all_orders

    def get_lowest_sell_price(self, region_id: int, type_id: int) -> Optional[float]:
        """Get lowest sell price for an item (with caching)."""
        cache_key = f"sell_{region_id}_{type_id}"

        # Check cache
        if cache_key in self._price_cache:
            price, cached_at = self._price_cache[cache_key]
            if datetime.now() - cached_at < self._cache_duration:
                return price

        orders = self.get_market_orders(region_id, type_id)
        sell_orders = [o for o in orders if not o.get("is_buy_order", True)]

        if not sell_orders:
            return None

        lowest = min(o["price"] for o in sell_orders)
        self._price_cache[cache_key] = (lowest, datetime.now())
        return lowest

    def get_highest_buy_price(self, region_id: int, type_id: int) -> Optional[float]:
        """Get highest buy price for an item (with caching)."""
        cache_key = f"buy_{region_id}_{type_id}"

        # Check cache
        if cache_key in self._price_cache:
            price, cached_at = self._price_cache[cache_key]
            if datetime.now() - cached_at < self._cache_duration:
                return price

        orders = self.get_market_orders(region_id, type_id)
        buy_orders = [o for o in orders if o.get("is_buy_order", False)]

        if not buy_orders:
            return None

        highest = max(o["price"] for o in buy_orders)
        self._price_cache[cache_key] = (highest, datetime.now())
        return highest

    def get_market_depth(self, region_id: int, type_id: int) -> Dict[str, Any]:
        """
        Get market depth (volume available at price points) for an item.

        Returns detailed volume information for availability analysis.
        """
        orders = self.get_market_orders(region_id, type_id)

        if not orders:
            return {
                "type_id": type_id,
                "region_id": region_id,
                "sell_volume": 0,
                "buy_volume": 0,
                "lowest_sell_price": None,
                "lowest_sell_volume": 0,
                "highest_buy_price": None,
                "highest_buy_volume": 0,
                "sell_orders": 0,
                "buy_orders": 0
            }

        sell_orders = [o for o in orders if not o.get("is_buy_order", True)]
        buy_orders = [o for o in orders if o.get("is_buy_order", False)]

        # Sort by price
        sell_orders.sort(key=lambda x: x.get("price", float('inf')))
        buy_orders.sort(key=lambda x: x.get("price", 0), reverse=True)

        return {
            "type_id": type_id,
            "region_id": region_id,
            "sell_volume": sum(o.get("volume_remain", 0) for o in sell_orders),
            "buy_volume": sum(o.get("volume_remain", 0) for o in buy_orders),
            "lowest_sell_price": sell_orders[0]["price"] if sell_orders else None,
            "lowest_sell_volume": sell_orders[0]["volume_remain"] if sell_orders else 0,
            "highest_buy_price": buy_orders[0]["price"] if buy_orders else None,
            "highest_buy_volume": buy_orders[0]["volume_remain"] if buy_orders else 0,
            "sell_orders": len(sell_orders),
            "buy_orders": len(buy_orders)
        }

    def get_market_stats(self, region_id: int, type_id: int) -> Dict[str, Any]:
        """Get comprehensive market statistics for an item."""
        orders = self.get_market_orders(region_id, type_id)

        sell_orders = [o for o in orders if not o.get("is_buy_order", True)]
        buy_orders = [o for o in orders if o.get("is_buy_order", False)]

        stats: Dict[str, Any] = {
            "type_id": type_id,
            "region_id": region_id,
            "total_orders": len(orders),
            "sell_order_count": len(sell_orders),
            "buy_order_count": len(buy_orders),
        }

        if sell_orders:
            sell_prices = [o["price"] for o in sell_orders]
            sell_volumes = [o["volume_remain"] for o in sell_orders]
            stats["lowest_sell"] = min(sell_prices)
            stats["highest_sell"] = max(sell_prices)
            stats["avg_sell"] = sum(sell_prices) / len(sell_prices)
            stats["total_sell_volume"] = sum(sell_volumes)

        if buy_orders:
            buy_prices = [o["price"] for o in buy_orders]
            buy_volumes = [o["volume_remain"] for o in buy_orders]
            stats["highest_buy"] = max(buy_prices)
            stats["lowest_buy"] = min(buy_prices)
            stats["avg_buy"] = sum(buy_prices) / len(buy_prices)
            stats["total_buy_volume"] = sum(buy_volumes)

        if sell_orders and buy_orders:
            stats["spread"] = stats["lowest_sell"] - stats["highest_buy"]
            stats["spread_percent"] = (
                (stats["spread"] / stats["highest_buy"]) * 100
                if stats["highest_buy"] > 0 else 0
            )

        return stats

    def get_all_region_prices(self, type_id: int) -> Dict[str, Dict[str, Any]]:
        """
        Get prices for an item across all trade hubs.

        Returns:
            Dict with region names as keys containing buy/sell prices
        """
        results = {}

        for region_name, region_id in REGIONS.items():
            stats = self.get_market_stats(region_id, type_id)

            results[region_name] = {
                "region_id": region_id,
                "lowest_sell": stats.get("lowest_sell"),
                "highest_buy": stats.get("highest_buy"),
                "sell_volume": stats.get("total_sell_volume", 0),
                "buy_volume": stats.get("total_buy_volume", 0),
                "spread_percent": stats.get("spread_percent", 0)
            }

        return results

    def find_arbitrage_opportunities(
        self,
        type_id: int,
        min_profit_percent: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        Find arbitrage opportunities for an item between regions.

        Args:
            type_id: Item type ID
            min_profit_percent: Minimum profit percentage to consider

        Returns:
            List of arbitrage opportunities sorted by profit
        """
        prices = self.get_all_region_prices(type_id)
        opportunities = []

        region_names = list(prices.keys())
        for i, buy_region in enumerate(region_names):
            buy_data = prices[buy_region]
            buy_price = buy_data.get("lowest_sell")

            if not buy_price:
                continue

            for sell_region in region_names[i+1:] + region_names[:i]:
                if sell_region == buy_region:
                    continue

                sell_data = prices[sell_region]
                sell_price = sell_data.get("highest_buy")

                if not sell_price:
                    continue

                profit = sell_price - buy_price
                profit_percent = (profit / buy_price) * 100 if buy_price > 0 else 0

                if profit_percent >= min_profit_percent:
                    opportunities.append({
                        "type_id": type_id,
                        "buy_region": buy_region,
                        "buy_region_id": buy_data["region_id"],
                        "buy_price": buy_price,
                        "sell_region": sell_region,
                        "sell_region_id": sell_data["region_id"],
                        "sell_price": sell_price,
                        "profit_per_unit": profit,
                        "profit_percent": round(profit_percent, 2),
                        "buy_volume_available": buy_data["sell_volume"],
                        "sell_volume_demand": sell_data["buy_volume"]
                    })

        opportunities.sort(key=lambda x: x["profit_percent"], reverse=True)
        return opportunities


# Global ESI client instance
esi_client = ESIClient()
