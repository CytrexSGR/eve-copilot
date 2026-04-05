"""
Asset Service for EVE Co-Pilot.

Provides character asset caching and lookup capabilities:
- refresh_character_assets: Fetch assets from ESI and cache them
- get_asset_summary: Get aggregated asset summary grouped by type
- find_assets_for_types: Find available quantities for specific item types
- get_cache_status: Get cache status for a character
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from src.database import get_db_connection, get_item_info
from src.character import character_api

logger = logging.getLogger(__name__)


class AssetService:
    """
    Service for caching and querying character assets.

    Uses the character_asset_cache table to store assets fetched from ESI,
    enabling fast lookups without hitting the ESI API on every request.
    """

    def __init__(self):
        """Initialize the AssetService."""
        pass

    def refresh_character_assets(self, character_id: int) -> int:
        """
        Fetch assets from ESI and cache them in the database.

        Clears existing cached assets for the character before inserting
        new ones to ensure cache freshness.

        Args:
            character_id: EVE Online character ID

        Returns:
            Number of assets cached, or 0 on error
        """
        # Fetch assets from ESI
        result = character_api.get_assets(character_id)

        # Check for errors
        if isinstance(result, dict) and "error" in result:
            logger.error(f"Failed to fetch assets for character {character_id}: {result['error']}")
            return 0

        assets = result.get("assets", [])
        if not assets:
            logger.info(f"No assets found for character {character_id}")
            # Still clear the cache and return 0
            self._clear_character_cache(character_id)
            return 0

        # Resolve type names and prepare for insertion
        asset_records = []
        for asset in assets:
            type_id = asset.get("type_id")
            quantity = asset.get("quantity", 1)
            location_id = asset.get("location_id")
            location_type = asset.get("location_type")

            # Get type name from SDE
            item_info = get_item_info(type_id)
            type_name = item_info.get("typeName") if item_info else None

            # Get location name (could be resolved from ESI, but keeping it simple)
            location_name = None

            asset_records.append({
                "character_id": character_id,
                "type_id": type_id,
                "type_name": type_name,
                "quantity": quantity,
                "location_id": location_id,
                "location_name": location_name,
                "location_type": location_type
            })

        # Insert into database
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Clear existing cache for this character
                    cursor.execute(
                        "DELETE FROM character_asset_cache WHERE character_id = %s",
                        (character_id,)
                    )

                    # Insert new assets
                    for record in asset_records:
                        cursor.execute("""
                            INSERT INTO character_asset_cache
                            (character_id, type_id, type_name, quantity,
                             location_id, location_name, location_type, cached_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                            ON CONFLICT (character_id, type_id, location_id)
                            DO UPDATE SET
                                type_name = EXCLUDED.type_name,
                                quantity = EXCLUDED.quantity,
                                location_name = EXCLUDED.location_name,
                                location_type = EXCLUDED.location_type,
                                cached_at = NOW()
                        """, (
                            record["character_id"],
                            record["type_id"],
                            record["type_name"],
                            record["quantity"],
                            record["location_id"],
                            record["location_name"],
                            record["location_type"]
                        ))

                    conn.commit()

            logger.info(f"Cached {len(asset_records)} assets for character {character_id}")
            return len(asset_records)

        except Exception as e:
            logger.error(f"Database error caching assets: {e}")
            return 0

    def _clear_character_cache(self, character_id: int) -> None:
        """Clear cached assets for a character."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM character_asset_cache WHERE character_id = %s",
                        (character_id,)
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"Error clearing asset cache: {e}")

    def get_asset_summary(self, character_id: int) -> List[Dict]:
        """
        Get aggregated asset summary grouped by type_id.

        Sums quantities across all locations for each item type.

        Args:
            character_id: EVE Online character ID

        Returns:
            List of dicts with type_id, type_name, and total_quantity
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            type_id,
                            type_name,
                            SUM(quantity) as total_quantity
                        FROM character_asset_cache
                        WHERE character_id = %s
                        GROUP BY type_id, type_name
                        ORDER BY total_quantity DESC
                    """, (character_id,))

                    rows = cursor.fetchall()

                    return [
                        {
                            "type_id": row[0],
                            "type_name": row[1],
                            "total_quantity": row[2]
                        }
                        for row in rows
                    ]

        except Exception as e:
            logger.error(f"Error getting asset summary: {e}")
            return []

    def find_assets_for_types(self, character_id: int, type_ids: List[int]) -> Dict[int, int]:
        """
        Find available quantities for specific item types.

        Looks up cached assets for the given type_ids and returns
        total quantities available across all locations.

        Args:
            character_id: EVE Online character ID
            type_ids: List of item type IDs to look up

        Returns:
            Dict mapping type_id to total quantity available.
            Types not found in cache will have quantity 0.
        """
        if not type_ids:
            return {}

        # Initialize result with all requested types set to 0
        result = {type_id: 0 for type_id in type_ids}

        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # Use ANY to match multiple type_ids
                    cursor.execute("""
                        SELECT
                            type_id,
                            SUM(quantity) as total_quantity
                        FROM character_asset_cache
                        WHERE character_id = %s
                          AND type_id = ANY(%s)
                        GROUP BY type_id
                    """, (character_id, type_ids))

                    rows = cursor.fetchall()

                    # Update result with found quantities
                    for row in rows:
                        result[row[0]] = row[1]

                    return result

        except Exception as e:
            logger.error(f"Error finding assets for types: {e}")
            return result

    def get_cache_status(self, character_id: int) -> Dict:
        """
        Get cache status for a character.

        Returns information about when assets were last cached
        and how many items are in the cache.

        Args:
            character_id: EVE Online character ID

        Returns:
            Dict with 'last_cached' (datetime or None) and 'total_items' (int)
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            MAX(cached_at) as last_cached,
                            COUNT(*) as total_items
                        FROM character_asset_cache
                        WHERE character_id = %s
                    """, (character_id,))

                    row = cursor.fetchone()

                    if row and row[1] > 0:
                        return {
                            "last_cached": row[0],
                            "total_items": row[1]
                        }

                    return {
                        "last_cached": None,
                        "total_items": 0
                    }

        except Exception as e:
            logger.error(f"Error getting cache status: {e}")
            return {
                "last_cached": None,
                "total_items": 0
            }


# Global service instance
asset_service = AssetService()
