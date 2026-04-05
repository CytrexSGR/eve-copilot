"""Production repository - database access layer for production queries."""
import logging
from typing import Optional, List, Tuple, Dict, Any

from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class ProductionRepository:
    """Repository for production-related database queries."""

    def __init__(self, db):
        """Initialize repository with database pool."""
        self.db = db

    def get_blueprint_for_product(self, product_type_id: int) -> Optional[int]:
        """Find the blueprint that produces a given item."""
        try:
            with self.db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT "typeID" as blueprint_id
                        FROM "industryActivityProducts"
                        WHERE "productTypeID" = %s
                        AND "activityID" = 1
                        LIMIT 1
                    ''', (product_type_id,))
                    result = cur.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to get blueprint for product {product_type_id}: {e}")
            raise

    def get_blueprint_materials(self, blueprint_id: int) -> List[Tuple[int, int]]:
        """Get materials required for a blueprint."""
        try:
            with self.db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT "materialTypeID", "quantity"
                        FROM "industryActivityMaterials"
                        WHERE "typeID" = %s
                        AND "activityID" = 1
                    ''', (blueprint_id,))
                    return cur.fetchall()
        except Exception as e:
            logger.error(f"Failed to get materials for blueprint {blueprint_id}: {e}")
            raise

    def get_output_quantity(self, blueprint_id: int, product_type_id: int) -> int:
        """Get output quantity per run for a blueprint."""
        try:
            with self.db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT "quantity"
                        FROM "industryActivityProducts"
                        WHERE "typeID" = %s
                        AND "productTypeID" = %s
                        AND "activityID" = 1
                    ''', (blueprint_id, product_type_id))
                    result = cur.fetchone()
                    return result[0] if result else 1
        except Exception as e:
            logger.error(f"Failed to get output quantity for blueprint {blueprint_id}: {e}")
            raise

    def get_base_production_time(self, blueprint_id: int) -> int:
        """Get base production time for a blueprint in seconds."""
        try:
            with self.db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT "time"
                        FROM "industryActivity"
                        WHERE "typeID" = %s
                        AND "activityID" = 1
                    ''', (blueprint_id,))
                    result = cur.fetchone()
                    return result[0] if result else 0
        except Exception as e:
            logger.error(f"Failed to get production time for blueprint {blueprint_id}: {e}")
            raise

    def get_item_name(self, type_id: int) -> Optional[str]:
        """Get item name from SDE."""
        try:
            with self.db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT "typeName"
                        FROM "invTypes"
                        WHERE "typeID" = %s
                    ''', (type_id,))
                    result = cur.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logger.error(f"Failed to get item name for type {type_id}: {e}")
            raise

    def get_item_names_bulk(self, type_ids: List[int]) -> Dict[int, str]:
        """Get multiple item names at once."""
        if not type_ids:
            return {}

        try:
            with self.db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT "typeID", "typeName"
                        FROM "invTypes"
                        WHERE "typeID" = ANY(%s)
                    ''', (list(type_ids),))
                    return {row[0]: row[1] for row in cur.fetchall()}
        except Exception as e:
            logger.error(f"Failed to get item names bulk: {e}")
            raise

    def is_manufacturable(self, type_id: int) -> bool:
        """Check if an item can be manufactured."""
        try:
            with self.db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT 1
                        FROM "industryActivityProducts"
                        WHERE "productTypeID" = %s
                        AND "activityID" = 1
                        LIMIT 1
                    ''', (type_id,))
                    return cur.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check if type {type_id} is manufacturable: {e}")
            raise

    def get_market_prices(self, type_ids: List[int], region_id: int) -> Dict[int, float]:
        """Get market prices from cache table."""
        if not type_ids:
            return {}

        try:
            with self.db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT type_id, lowest_sell
                        FROM market_prices
                        WHERE type_id = ANY(%s) AND region_id = %s
                    ''', (list(type_ids), region_id))
                    return {
                        row[0]: float(row[1]) if row[1] else 0.0
                        for row in cur.fetchall()
                    }
        except Exception as e:
            logger.error(f"Failed to get market prices: {e}")
            raise

    def get_adjusted_prices(self, type_ids: List[int]) -> Dict[int, float]:
        """Get adjusted prices from ESI cache."""
        if not type_ids:
            return {}

        try:
            with self.db.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute('''
                        SELECT type_id, adjusted_price
                        FROM market_prices_cache
                        WHERE type_id = ANY(%s)
                    ''', (list(type_ids),))
                    return {
                        row[0]: float(row[1]) if row[1] else 0.0
                        for row in cur.fetchall()
                    }
        except Exception as e:
            logger.error(f"Failed to get adjusted prices: {e}")
            raise

    def get_manufacturable_items(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Get list of manufacturable items for opportunity scanning."""
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute('''
                        SELECT DISTINCT
                            iap."productTypeID" as type_id,
                            t."typeName" as name,
                            g."groupName" as group_name
                        FROM "industryActivityProducts" iap
                        JOIN "invTypes" t ON iap."productTypeID" = t."typeID"
                        JOIN "invGroups" g ON t."groupID" = g."groupID"
                        WHERE iap."activityID" = 1
                        AND t.published = 1
                        LIMIT %s
                    ''', (limit,))
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get manufacturable items: {e}")
            raise
