"""Shopping repository for database operations."""
import logging
from typing import Optional, List

from psycopg2.extras import RealDictCursor

from app.models import (
    ShoppingList, ShoppingListCreate, ShoppingListUpdate,
    ShoppingItem, ShoppingItemCreate, ShoppingItemUpdate,
    BuildDecision
)

logger = logging.getLogger(__name__)


class ShoppingRepository:
    """Repository for shopping list database operations."""

    def __init__(self, db):
        self.db = db

    # Shopping Lists

    def get_lists(self, character_id: Optional[int] = None) -> List[ShoppingList]:
        """Get all shopping lists, optionally filtered by character."""
        with self.db.cursor() as cur:
            if character_id:
                cur.execute("""
                    SELECT l.id, l.name, l.description, l.character_id,
                           l.created_at, l.updated_at,
                           COUNT(i.id) as item_count,
                           COALESCE(SUM(i.quantity * COALESCE(mp.lowest_sell, 0)), 0) as total_cost
                    FROM shopping_lists l
                    LEFT JOIN shopping_list_items i ON l.id = i.list_id
                    LEFT JOIN market_prices mp ON i.type_id = mp.type_id AND mp.region_id = 10000002
                    WHERE l.character_id = %s
                    GROUP BY l.id
                    ORDER BY l.updated_at DESC
                """, (character_id,))
            else:
                cur.execute("""
                    SELECT l.id, l.name, l.description, l.character_id,
                           l.created_at, l.updated_at,
                           COUNT(i.id) as item_count,
                           COALESCE(SUM(i.quantity * COALESCE(mp.lowest_sell, 0)), 0) as total_cost
                    FROM shopping_lists l
                    LEFT JOIN shopping_list_items i ON l.id = i.list_id
                    LEFT JOIN market_prices mp ON i.type_id = mp.type_id AND mp.region_id = 10000002
                    GROUP BY l.id
                    ORDER BY l.updated_at DESC
                """)
            rows = cur.fetchall()
            return [ShoppingList(**dict(row)) for row in rows]

    def get_list(self, list_id: int) -> Optional[ShoppingList]:
        """Get a shopping list by ID."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT l.id, l.name, l.description, l.character_id,
                       l.created_at, l.updated_at,
                       COUNT(i.id) as item_count,
                       COALESCE(SUM(i.quantity * COALESCE(mp.lowest_sell, 0)), 0) as total_cost
                FROM shopping_lists l
                LEFT JOIN shopping_list_items i ON l.id = i.list_id
                LEFT JOIN market_prices mp ON i.type_id = mp.type_id AND mp.region_id = 10000002
                WHERE l.id = %s
                GROUP BY l.id
            """, (list_id,))
            row = cur.fetchone()
            return ShoppingList(**dict(row)) if row else None

    def create_list(self, data: ShoppingListCreate) -> ShoppingList:
        """Create a new shopping list."""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO shopping_lists (name, description, character_id, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                RETURNING id, name, description, character_id, created_at, updated_at
            """, (data.name, data.description, data.character_id))
            row = cur.fetchone()
            return ShoppingList(**dict(row), item_count=0, total_cost=0.0)

    def update_list(self, list_id: int, data: ShoppingListUpdate) -> Optional[ShoppingList]:
        """Update a shopping list."""
        updates = []
        values = []

        if data.name is not None:
            updates.append("name = %s")
            values.append(data.name)

        if data.description is not None:
            updates.append("description = %s")
            values.append(data.description)

        if not updates:
            return self.get_list(list_id)

        updates.append("updated_at = NOW()")
        values.append(list_id)

        with self.db.cursor() as cur:
            cur.execute(f"""
                UPDATE shopping_lists
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING id
            """, tuple(values))
            row = cur.fetchone()
            if row:
                return self.get_list(list_id)
            return None

    def delete_list(self, list_id: int) -> bool:
        """Delete a shopping list and its items."""
        with self.db.cursor() as cur:
            # Delete items first (foreign key)
            cur.execute("DELETE FROM shopping_list_items WHERE list_id = %s", (list_id,))
            cur.execute("DELETE FROM shopping_lists WHERE id = %s", (list_id,))
            return cur.rowcount > 0

    # Shopping Items

    def get_items(self, list_id: int) -> List[ShoppingItem]:
        """Get all items in a shopping list."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT i.id, i.list_id, i.type_id, t."typeName" as type_name,
                       i.quantity, i.is_product, i.blueprint_runs, i.me_level,
                       i.region_id, r."regionName" as region_name,
                       i.build_decision, i.is_purchased, i.parent_item_id,
                       COALESCE(i.quantity_in_assets, 0) as quantity_in_assets,
                       i.created_at, i.updated_at,
                       COALESCE(mp.lowest_sell, 0) as unit_price,
                       i.quantity * COALESCE(mp.lowest_sell, 0) as total_price,
                       COALESCE(t.volume, 0) as volume,
                       i.quantity * COALESCE(t.volume, 0) as total_volume
                FROM shopping_list_items i
                JOIN "invTypes" t ON i.type_id = t."typeID"
                LEFT JOIN "mapRegions" r ON i.region_id = r."regionID"
                LEFT JOIN market_prices mp ON i.type_id = mp.type_id
                    AND mp.region_id = COALESCE(i.region_id, 10000002)
                WHERE i.list_id = %s
                ORDER BY i.is_product DESC, t."typeName"
            """, (list_id,))
            rows = cur.fetchall()
            return [ShoppingItem(**dict(row)) for row in rows]

    def get_item(self, item_id: int) -> Optional[ShoppingItem]:
        """Get a shopping item by ID."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT i.id, i.list_id, i.type_id, t."typeName" as type_name,
                       i.quantity, i.is_product, i.blueprint_runs, i.me_level,
                       i.region_id, r."regionName" as region_name,
                       i.build_decision, i.is_purchased, i.parent_item_id,
                       COALESCE(i.quantity_in_assets, 0) as quantity_in_assets,
                       i.created_at, i.updated_at,
                       COALESCE(mp.lowest_sell, 0) as unit_price,
                       i.quantity * COALESCE(mp.lowest_sell, 0) as total_price,
                       COALESCE(t.volume, 0) as volume,
                       i.quantity * COALESCE(t.volume, 0) as total_volume
                FROM shopping_list_items i
                JOIN "invTypes" t ON i.type_id = t."typeID"
                LEFT JOIN "mapRegions" r ON i.region_id = r."regionID"
                LEFT JOIN market_prices mp ON i.type_id = mp.type_id
                    AND mp.region_id = COALESCE(i.region_id, 10000002)
                WHERE i.id = %s
            """, (item_id,))
            row = cur.fetchone()
            return ShoppingItem(**dict(row)) if row else None

    def create_item(self, list_id: int, data: ShoppingItemCreate) -> ShoppingItem:
        """Create a new shopping item."""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO shopping_list_items
                    (list_id, type_id, quantity, is_product, blueprint_runs,
                     me_level, region_id, build_decision, parent_item_id,
                     created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                RETURNING id
            """, (
                list_id,
                data.type_id,
                data.quantity,
                data.is_product,
                data.blueprint_runs,
                data.me_level,
                data.region_id,
                data.build_decision.value,
                data.parent_item_id
            ))
            row = cur.fetchone()

            # Update list timestamp
            cur.execute(
                "UPDATE shopping_lists SET updated_at = NOW() WHERE id = %s",
                (list_id,)
            )

            return self.get_item(row["id"])

    def update_item(self, item_id: int, data: ShoppingItemUpdate) -> Optional[ShoppingItem]:
        """Update a shopping item."""
        updates = []
        values = []

        if data.quantity is not None:
            updates.append("quantity = %s")
            values.append(data.quantity)

        if data.blueprint_runs is not None:
            updates.append("blueprint_runs = %s")
            values.append(data.blueprint_runs)

        if data.me_level is not None:
            updates.append("me_level = %s")
            values.append(data.me_level)

        if data.region_id is not None:
            updates.append("region_id = %s")
            values.append(data.region_id)

        if data.build_decision is not None:
            updates.append("build_decision = %s")
            values.append(data.build_decision.value)

        if data.is_purchased is not None:
            updates.append("is_purchased = %s")
            values.append(data.is_purchased)

        if not updates:
            return self.get_item(item_id)

        updates.append("updated_at = NOW()")
        values.append(item_id)

        with self.db.cursor() as cur:
            cur.execute(f"""
                UPDATE shopping_list_items
                SET {', '.join(updates)}
                WHERE id = %s
                RETURNING list_id
            """, tuple(values))
            row = cur.fetchone()
            if row:
                # Update list timestamp
                cur.execute(
                    "UPDATE shopping_lists SET updated_at = NOW() WHERE id = %s",
                    (row["list_id"],)
                )
                return self.get_item(item_id)
            return None

    def delete_item(self, item_id: int) -> bool:
        """Delete a shopping item and its child materials."""
        item = self.get_item(item_id)
        if not item:
            return False

        with self.db.cursor() as cur:
            # Delete child items (materials)
            cur.execute(
                "DELETE FROM shopping_list_items WHERE parent_item_id = %s",
                (item_id,)
            )

            # Delete the item
            cur.execute(
                "DELETE FROM shopping_list_items WHERE id = %s",
                (item_id,)
            )
            deleted = cur.rowcount > 0

            # Update list timestamp
            cur.execute(
                "UPDATE shopping_lists SET updated_at = NOW() WHERE id = %s",
                (item.list_id,)
            )

            return deleted

    def mark_purchased(self, item_id: int, purchased: bool) -> Optional[ShoppingItem]:
        """Mark an item as purchased or not."""
        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE shopping_list_items
                SET is_purchased = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING list_id
            """, (purchased, item_id))
            row = cur.fetchone()
            if row:
                cur.execute(
                    "UPDATE shopping_lists SET updated_at = NOW() WHERE id = %s",
                    (row["list_id"],)
                )
                return self.get_item(item_id)
            return None

    # Material management

    def get_child_items(self, parent_item_id: int) -> List[ShoppingItem]:
        """Get child items (materials) for a product."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT i.id, i.list_id, i.type_id, t."typeName" as type_name,
                       i.quantity, i.is_product, i.blueprint_runs, i.me_level,
                       i.region_id, r."regionName" as region_name,
                       i.build_decision, i.is_purchased, i.parent_item_id,
                       COALESCE(i.quantity_in_assets, 0) as quantity_in_assets,
                       i.created_at, i.updated_at,
                       COALESCE(mp.lowest_sell, 0) as unit_price,
                       i.quantity * COALESCE(mp.lowest_sell, 0) as total_price,
                       COALESCE(t.volume, 0) as volume,
                       i.quantity * COALESCE(t.volume, 0) as total_volume
                FROM shopping_list_items i
                JOIN "invTypes" t ON i.type_id = t."typeID"
                LEFT JOIN "mapRegions" r ON i.region_id = r."regionID"
                LEFT JOIN market_prices mp ON i.type_id = mp.type_id
                    AND mp.region_id = COALESCE(i.region_id, 10000002)
                WHERE i.parent_item_id = %s
                ORDER BY t."typeName"
            """, (parent_item_id,))
            rows = cur.fetchall()
            return [ShoppingItem(**dict(row)) for row in rows]

    def delete_child_items(self, parent_item_id: int) -> int:
        """Delete all child items for a parent."""
        with self.db.cursor() as cur:
            cur.execute(
                "DELETE FROM shopping_list_items WHERE parent_item_id = %s",
                (parent_item_id,)
            )
            return cur.rowcount

    # Type lookups

    def get_type_info(self, type_id: int) -> Optional[dict]:
        """Get type information."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT t."typeID" as type_id, t."typeName" as type_name,
                       t.volume, g."groupID" as group_id, g."groupName" as group_name,
                       c."categoryID" as category_id, c."categoryName" as category_name
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                JOIN "invCategories" c ON g."categoryID" = c."categoryID"
                WHERE t."typeID" = %s
            """, (type_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def is_manufacturable(self, type_id: int) -> bool:
        """Check if a type can be manufactured."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM "industryActivityMaterials" iam
                    JOIN "industryBlueprints" ib ON iam."typeID" = ib."typeID"
                    WHERE ib."productTypeID" = %s AND iam."activityID" = 1
                )
            """, (type_id,))
            row = cur.fetchone()
            return row[0] if row else False

    # Regional data

    def get_regions(self) -> List[dict]:
        """Get trade hub regions."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT r."regionID" as region_id, r."regionName" as region_name,
                       CASE r."regionID"
                           WHEN 10000002 THEN 'Jita'
                           WHEN 10000043 THEN 'Amarr'
                           WHEN 10000030 THEN 'Rens'
                           WHEN 10000032 THEN 'Dodixie'
                           WHEN 10000042 THEN 'Hek'
                       END as hub_system
                FROM "mapRegions" r
                WHERE r."regionID" IN (10000002, 10000043, 10000030, 10000032, 10000042)
                ORDER BY r."regionName"
            """)
            rows = cur.fetchall()
            return [dict(row) for row in rows]

    def get_regional_prices(self, type_ids: List[int]) -> List[dict]:
        """Get prices for items across all trade hub regions."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT mp.type_id, mp.region_id, r."regionName" as region_name,
                       mp.lowest_sell, mp.highest_buy, mp.volume, mp.order_count,
                       CASE mp.region_id
                           WHEN 10000002 THEN 'Jita'
                           WHEN 10000043 THEN 'Amarr'
                           WHEN 10000030 THEN 'Rens'
                           WHEN 10000032 THEN 'Dodixie'
                           WHEN 10000042 THEN 'Hek'
                       END as hub_system
                FROM market_prices mp
                JOIN "mapRegions" r ON mp.region_id = r."regionID"
                WHERE mp.type_id = ANY(%s)
                  AND mp.region_id IN (10000002, 10000043, 10000030, 10000032, 10000042)
            """, (type_ids,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]

    # Market orders

    def get_order_snapshots(self, type_id: int, region_id: Optional[int] = None) -> List[dict]:
        """Get market order snapshots for an item."""
        with self.db.cursor() as cur:
            if region_id:
                cur.execute("""
                    SELECT type_id, region_id, is_buy_order, price, volume_remain,
                           location_id, issued, rank, updated_at
                    FROM market_order_snapshots
                    WHERE type_id = %s AND region_id = %s
                    ORDER BY is_buy_order, rank
                """, (type_id, region_id))
            else:
                cur.execute("""
                    SELECT type_id, region_id, is_buy_order, price, volume_remain,
                           location_id, issued, rank, updated_at
                    FROM market_order_snapshots
                    WHERE type_id = %s
                    ORDER BY region_id, is_buy_order, rank
                """, (type_id,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]

    # Route calculation

    def get_system_info(self, system_name: str) -> Optional[dict]:
        """Get solar system info by name."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT s."solarSystemID" as solar_system_id,
                       s."solarSystemName" as solar_system_name,
                       r."regionID" as region_id,
                       r."regionName" as region_name
                FROM "mapSolarSystems" s
                JOIN "mapRegions" r ON s."regionID" = r."regionID"
                WHERE LOWER(s."solarSystemName") = LOWER(%s)
            """, (system_name,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_hub_system_id(self, region_key: str) -> Optional[int]:
        """Get system ID for a trade hub by region key."""
        hub_systems = {
            'the_forge': 30000142,  # Jita
            'domain': 30002187,     # Amarr
            'heimatar': 30002510,   # Rens
            'sinq_laison': 30002659,  # Dodixie
            'metropolis': 30002053,   # Hek
        }
        return hub_systems.get(region_key)

    def get_route(self, from_system_id: int, to_system_id: int) -> Optional[List[int]]:
        """Get route between two systems using jump data."""
        # Simple BFS for route finding
        with self.db.cursor() as cur:
            # Check if tables exist and have data
            cur.execute("""
                SELECT COUNT(*) FROM "mapSolarSystemJumps"
            """)
            count = cur.fetchone()[0]
            if count == 0:
                return None

            # BFS to find shortest path
            cur.execute("""
                WITH RECURSIVE route AS (
                    -- Start from source
                    SELECT
                        "fromSolarSystemID" as current,
                        "toSolarSystemID" as next_system,
                        ARRAY["fromSolarSystemID", "toSolarSystemID"] as path,
                        1 as depth
                    FROM "mapSolarSystemJumps"
                    WHERE "fromSolarSystemID" = %s

                    UNION ALL

                    -- Expand
                    SELECT
                        r.next_system,
                        j."toSolarSystemID",
                        r.path || j."toSolarSystemID",
                        r.depth + 1
                    FROM route r
                    JOIN "mapSolarSystemJumps" j ON r.next_system = j."fromSolarSystemID"
                    WHERE NOT j."toSolarSystemID" = ANY(r.path)
                      AND r.depth < 50
                      AND r.next_system != %s
                )
                SELECT path
                FROM route
                WHERE next_system = %s
                ORDER BY depth
                LIMIT 1
            """, (from_system_id, to_system_id, to_system_id))
            row = cur.fetchone()
            return row[0] if row else None

    # Character assets

    def get_character_assets(self, character_id: int) -> List[dict]:
        """Get cached character assets."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT type_id, quantity, location_id, location_flag
                FROM character_asset_cache
                WHERE character_id = %s
            """, (character_id,))
            rows = cur.fetchall()
            return [dict(row) for row in rows]

    def update_item_quantity_in_assets(self, item_id: int, quantity_in_assets: int) -> bool:
        """Update the quantity_in_assets for a shopping item."""
        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE shopping_list_items
                SET quantity_in_assets = %s, updated_at = NOW()
                WHERE id = %s
            """, (quantity_in_assets, item_id))
            return cur.rowcount > 0

    # Blueprint materials

    def get_blueprint_materials(self, type_id: int, me_level: int = 10, runs: int = 1) -> List[dict]:
        """Get materials needed to manufacture an item."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT iam."materialTypeID" as type_id,
                       t."typeName" as type_name,
                       iam.quantity as base_quantity,
                       CEIL(iam.quantity * %s * (1 - %s / 100.0)) as adjusted_quantity
                FROM "industryActivityMaterials" iam
                JOIN "industryBlueprints" ib ON iam."typeID" = ib."typeID"
                JOIN "invTypes" t ON iam."materialTypeID" = t."typeID"
                WHERE ib."productTypeID" = %s
                  AND iam."activityID" = 1
            """, (runs, me_level, type_id))
            rows = cur.fetchall()
            return [dict(row) for row in rows]

    def get_blueprint_for_product(self, type_id: int) -> Optional[dict]:
        """Get blueprint info for a product type."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT ib."typeID" as blueprint_type_id,
                       t."typeName" as blueprint_name,
                       ib."productTypeID" as product_type_id,
                       pt."typeName" as product_name
                FROM "industryBlueprints" ib
                JOIN "invTypes" t ON ib."typeID" = t."typeID"
                JOIN "invTypes" pt ON ib."productTypeID" = pt."typeID"
                WHERE ib."productTypeID" = %s
            """, (type_id,))
            row = cur.fetchone()
            return dict(row) if row else None
