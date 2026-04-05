"""Market repository - data access layer."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from psycopg2.extras import RealDictCursor, execute_values

from src.core.database import DatabasePool
from src.core.exceptions import EVECopilotError
from src.services.market.models import MarketPrice, CacheStats, PriceSource, JITA_REGION_ID
from src.services.market.cache import MarketCache
from src.services.market.hot_items import get_hot_items

logger = logging.getLogger(__name__)


class MarketRepository:
    """Data access for market prices."""

    def __init__(self, db_pool: DatabasePool):
        """Initialize repository with database pool."""
        self.db = db_pool

    def bulk_upsert_prices(self, prices: List[MarketPrice]) -> int:
        """
        Bulk upsert market prices using ON CONFLICT.

        Args:
            prices: List of MarketPrice objects to upsert

        Returns:
            Number of rows affected

        Raises:
            EVECopilotError: If database operation fails
        """
        if not prices:
            return 0

        try:
            # Prepare values for bulk insert
            values = [
                (
                    price.type_id,
                    price.adjusted_price,
                    price.average_price,
                    price.last_updated
                )
                for price in prices
            ]

            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    execute_values(
                        cur,
                        """
                        INSERT INTO market_prices_cache (type_id, adjusted_price, average_price, last_updated)
                        VALUES %s
                        ON CONFLICT (type_id)
                        DO UPDATE SET
                            adjusted_price = EXCLUDED.adjusted_price,
                            average_price = EXCLUDED.average_price,
                            last_updated = EXCLUDED.last_updated
                        """,
                        values,
                        page_size=1000
                    )
                    conn.commit()
                    return cur.rowcount
        except EVECopilotError:
            raise
        except Exception as e:
            raise EVECopilotError(f"Failed to bulk upsert prices: {str(e)}")

    def get_cache_stats(self) -> CacheStats:
        """
        Get statistics about the price cache.

        Returns:
            CacheStats object with cache statistics

        Raises:
            EVECopilotError: If database operation fails
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT
                            COUNT(*) as total_items,
                            MIN(last_updated) as oldest_entry,
                            MAX(last_updated) as newest_entry
                        FROM market_prices_cache
                    """)
                    row = cur.fetchone()

                    if row and row["total_items"] > 0:
                        total_items = row["total_items"]
                        oldest_entry = row["oldest_entry"]
                        newest_entry = row["newest_entry"]

                        # Calculate cache age
                        cache_age_seconds = None
                        is_stale = True

                        if newest_entry:
                            age = datetime.now() - newest_entry
                            cache_age_seconds = age.total_seconds()
                            is_stale = cache_age_seconds > 3600  # Stale if > 1 hour

                        return CacheStats(
                            total_items=total_items,
                            oldest_entry=oldest_entry,
                            newest_entry=newest_entry,
                            cache_age_seconds=cache_age_seconds,
                            is_stale=is_stale
                        )

                    # Cache is empty
                    return CacheStats(
                        total_items=0,
                        oldest_entry=None,
                        newest_entry=None,
                        cache_age_seconds=None,
                        is_stale=True
                    )
        except EVECopilotError:
            raise
        except Exception as e:
            raise EVECopilotError(f"Failed to get cache stats: {str(e)}")

    def get_price(self, type_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single price by type_id.

        Args:
            type_id: EVE type ID to lookup

        Returns:
            Price data as dict or None if not found

        Raises:
            EVECopilotError: If database operation fails
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM market_prices_cache WHERE type_id = %s",
                        (type_id,)
                    )
                    result = cur.fetchone()
                    return dict(result) if result else None
        except EVECopilotError:
            raise
        except Exception as e:
            raise EVECopilotError(f"Failed to get price for type_id {type_id}: {str(e)}")

    def get_prices_bulk(self, type_ids: List[int]) -> List[Dict[str, Any]]:
        """
        Get multiple prices at once using ANY clause.

        Args:
            type_ids: List of type IDs to fetch (empty list fetches all)

        Returns:
            List of price dicts (may be less than requested if some don't exist)

        Raises:
            EVECopilotError: If database operation fails
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # If empty list, fetch all prices
                    if not type_ids:
                        cur.execute(
                            """
                            SELECT *
                            FROM market_prices_cache
                            WHERE adjusted_price > 0
                            """
                        )
                    else:
                        cur.execute(
                            """
                            SELECT *
                            FROM market_prices_cache
                            WHERE type_id = ANY(%s)
                            """,
                            (list(type_ids),)
                        )
                    return [dict(row) for row in cur.fetchall()]
        except EVECopilotError:
            raise
        except Exception as e:
            raise EVECopilotError(f"Failed to get prices bulk: {str(e)}")


class UnifiedMarketRepository:
    """
    Unified Market Repository with hybrid L1/L2/L3 caching.

    Cache hierarchy:
    - L1: Redis (5 min TTL) - fastest, in-memory
    - L2: PostgreSQL (1 hour TTL) - persistent
    - L3: ESI API - fallback, fresh data

    The caller never knows where data came from - just calls get_price().
    """

    # Cache TTL constants
    REDIS_TTL_SECONDS = 300  # 5 minutes
    POSTGRES_TTL_SECONDS = 3600  # 1 hour

    def __init__(self, redis_client, db_pool, esi_client):
        """
        Initialize unified repository with all data sources.

        Args:
            redis_client: Redis client for L1 cache
            db_pool: PostgreSQL connection pool for L2 cache
            esi_client: ESI API client for L3 fallback
        """
        self.redis = redis_client
        self.db = db_pool
        self.esi = esi_client
        self.cache = MarketCache(redis_client)
        self._hot_items = get_hot_items()

    def get_price(
        self,
        type_id: int,
        region_id: int = JITA_REGION_ID
    ) -> Optional[MarketPrice]:
        """
        Get price for a single item using L1 -> L2 -> L3 fallback chain.

        Args:
            type_id: EVE type ID
            region_id: Region ID (default: Jita)

        Returns:
            MarketPrice if found, None otherwise
        """
        # L1: Try Redis first
        price = self._get_from_redis(type_id, region_id)
        if price:
            return price

        # L2: Try PostgreSQL
        price = self._get_from_postgres(type_id, region_id)
        if price:
            # Promote to L1 (Redis)
            self._promote_to_redis(price)
            return price

        # L3: Fetch from ESI
        price = self._fetch_from_esi(type_id, region_id)
        if price:
            # Write to both L1 and L2
            self._write_to_caches(price)
            return price

        return None

    def get_prices(
        self,
        type_ids: List[int],
        region_id: int = JITA_REGION_ID
    ) -> Dict[int, MarketPrice]:
        """
        Get prices for multiple items efficiently.

        Uses batch operations to minimize round-trips.

        Args:
            type_ids: List of EVE type IDs
            region_id: Region ID (default: Jita)

        Returns:
            Dict mapping type_id to MarketPrice
        """
        if not type_ids:
            return {}

        # Prevent memory explosion from massive lists
        if len(type_ids) > 10000:
            raise ValueError(f"Too many type IDs ({len(type_ids)}). Maximum is 10000.")

        result: Dict[int, MarketPrice] = {}
        missing_from_redis: List[int] = []

        # L1: Batch fetch from Redis
        cached = self.cache.get_prices(type_ids, region_id)
        for type_id, price in cached.items():
            result[type_id] = price

        missing_from_redis = [tid for tid in type_ids if tid not in result]

        if not missing_from_redis:
            return result

        # L2: Batch fetch from PostgreSQL for misses
        postgres_prices = self._get_bulk_from_postgres(missing_from_redis, region_id)
        prices_to_promote: List[MarketPrice] = []

        for price in postgres_prices:
            result[price.type_id] = price
            prices_to_promote.append(price)

        # Promote PostgreSQL hits to Redis
        if prices_to_promote:
            self.cache.set_prices(prices_to_promote, ttl=self.REDIS_TTL_SECONDS)

        # L3: Fetch remaining from ESI
        missing_from_postgres = [
            tid for tid in missing_from_redis
            if tid not in result
        ]

        if missing_from_postgres:
            esi_prices = self._fetch_bulk_from_esi(missing_from_postgres, region_id)
            for price in esi_prices:
                result[price.type_id] = price
            # Write ESI results to both caches
            if esi_prices:
                self._write_bulk_to_caches(esi_prices)

        return result

    def is_hot_item(self, type_id: int) -> bool:
        """
        Check if an item is considered "hot" (frequently accessed).

        Hot items are proactively cached and have shorter refresh intervals.

        Args:
            type_id: EVE type ID to check

        Returns:
            True if the item is in the hot items list
        """
        return type_id in self._hot_items

    def _get_from_redis(
        self,
        type_id: int,
        region_id: int
    ) -> Optional[MarketPrice]:
        """Get price from L1 Redis cache."""
        try:
            return self.cache.get_price(type_id, region_id)
        except Exception as e:
            logger.warning(f"Redis get failed for {type_id}: {e}")
            return None

    def _get_from_postgres(
        self,
        type_id: int,
        region_id: int
    ) -> Optional[MarketPrice]:
        """Get price from L2 PostgreSQL cache."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT type_id, lowest_sell, highest_buy,
                               adjusted_price, average_price, last_updated
                        FROM market_prices
                        WHERE type_id = %s AND region_id = %s
                          AND last_updated > NOW() - INTERVAL '1 hour'
                        """,
                        (type_id, region_id)
                    )
                    row = cur.fetchone()
                    if row:
                        return MarketPrice(
                            type_id=row["type_id"],
                            sell_price=row.get("lowest_sell") or 0.0,
                            buy_price=row.get("highest_buy") or 0.0,
                            adjusted_price=row.get("adjusted_price") or 0.0,
                            average_price=row.get("average_price") or 0.0,
                            region_id=region_id,
                            source=PriceSource.CACHE,
                            last_updated=row["last_updated"]
                        )
                    return None
        except Exception as e:
            logger.warning(f"PostgreSQL get failed for {type_id}: {e}")
            return None

    def _get_bulk_from_postgres(
        self,
        type_ids: List[int],
        region_id: int
    ) -> List[MarketPrice]:
        """Get multiple prices from L2 PostgreSQL cache."""
        if not type_ids:
            return []

        try:
            with self.db.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT type_id, lowest_sell, highest_buy,
                               adjusted_price, average_price, last_updated
                        FROM market_prices
                        WHERE type_id = ANY(%s) AND region_id = %s
                          AND last_updated > NOW() - INTERVAL '1 hour'
                        """,
                        (list(type_ids), region_id)
                    )
                    rows = cur.fetchall()
                    return [
                        MarketPrice(
                            type_id=row["type_id"],
                            sell_price=row.get("lowest_sell") or 0.0,
                            buy_price=row.get("highest_buy") or 0.0,
                            adjusted_price=row.get("adjusted_price") or 0.0,
                            average_price=row.get("average_price") or 0.0,
                            region_id=region_id,
                            source=PriceSource.CACHE,
                            last_updated=row["last_updated"]
                        )
                        for row in rows
                    ]
        except Exception as e:
            logger.warning(f"PostgreSQL bulk get failed: {e}")
            return []

    def _fetch_from_esi(
        self,
        type_id: int,
        region_id: int
    ) -> Optional[MarketPrice]:
        """Fetch price from L3 ESI API."""
        try:
            orders = self.esi.get_market_orders(region_id, type_id)
            if not orders:
                return None

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

    def _fetch_bulk_from_esi(
        self,
        type_ids: List[int],
        region_id: int
    ) -> List[MarketPrice]:
        """Fetch multiple prices from L3 ESI API."""
        prices = []
        for type_id in type_ids:
            price = self._fetch_from_esi(type_id, region_id)
            if price:
                prices.append(price)
        return prices

    def _promote_to_redis(self, price: MarketPrice) -> None:
        """Promote a PostgreSQL cache hit to Redis (L1)."""
        try:
            self.cache.set_price(price, ttl=self.REDIS_TTL_SECONDS)
        except Exception as e:
            logger.warning(f"Redis promotion failed for {price.type_id}: {e}")

    def _write_to_caches(self, price: MarketPrice) -> None:
        """Write ESI result to both L1 and L2 caches."""
        # Write to L1 (Redis)
        try:
            self.cache.set_price(price, ttl=self.REDIS_TTL_SECONDS)
        except Exception as e:
            logger.warning(f"Redis write failed for {price.type_id}: {e}")

        # Write to L2 (PostgreSQL)
        self._write_to_postgres(price)

    def _write_bulk_to_caches(self, prices: List[MarketPrice]) -> None:
        """Write multiple ESI results to both caches."""
        if not prices:
            return

        # Write to L1 (Redis)
        try:
            self.cache.set_prices(prices, ttl=self.REDIS_TTL_SECONDS)
        except Exception as e:
            logger.warning(f"Redis bulk write failed: {e}")

        # Write to L2 (PostgreSQL)
        for price in prices:
            self._write_to_postgres(price)

    def _write_to_postgres(self, price: MarketPrice) -> None:
        """Write price to L2 PostgreSQL cache."""
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO market_prices
                            (type_id, region_id, lowest_sell, highest_buy,
                             adjusted_price, average_price, last_updated)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (type_id, region_id)
                        DO UPDATE SET
                            lowest_sell = EXCLUDED.lowest_sell,
                            highest_buy = EXCLUDED.highest_buy,
                            adjusted_price = EXCLUDED.adjusted_price,
                            average_price = EXCLUDED.average_price,
                            last_updated = EXCLUDED.last_updated
                        """,
                        (
                            price.type_id,
                            price.region_id,
                            price.sell_price,
                            price.buy_price,
                            price.adjusted_price,
                            price.average_price,
                            price.last_updated
                        )
                    )
                    conn.commit()
        except Exception as e:
            logger.warning(f"PostgreSQL write failed for {price.type_id}: {e}")

    def refresh_hot_items(self) -> Dict[str, Any]:
        """
        Refresh all hot items in cache.

        Called by background job to proactively cache hot items.

        Returns:
            Dict with refresh statistics
        """
        hot_items = list(self._hot_items)
        logger.info(f"Refreshing {len(hot_items)} hot items")

        refreshed = 0
        errors = 0

        # Batch fetch from ESI and write to caches
        for type_id in hot_items:
            try:
                price = self._fetch_from_esi(type_id, JITA_REGION_ID)
                if price:
                    self._write_to_caches(price)
                    refreshed += 1
                else:
                    errors += 1
            except Exception as e:
                logger.warning(f"Failed to refresh {type_id}: {e}")
                errors += 1

        return {
            "refreshed": refreshed,
            "errors": errors,
            "total": len(hot_items)
        }
