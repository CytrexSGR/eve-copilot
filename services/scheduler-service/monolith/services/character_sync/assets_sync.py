"""Assets sync operation."""
from typing import Any, List, Dict
from psycopg2.extras import execute_values

from src.database import get_item_info
from .base import BaseSyncOperation


class AssetsSync(BaseSyncOperation):
    """Sync character assets."""

    def fetch_from_esi(self, character_id: int) -> Any:
        """Fetch assets from ESI."""
        return self.character_service.get_assets(character_id)

    def transform_data(self, raw_data: Any) -> List[Dict]:
        """Convert asset models to dicts with type names."""
        assets = []
        for a in raw_data.assets:
            asset_dict = a.model_dump()
            type_id = asset_dict.get("type_id")
            type_info = get_item_info(type_id) if type_id else None
            asset_dict["type_name"] = type_info.get("typeName") if isinstance(type_info, dict) else None
            assets.append(asset_dict)
        return assets

    def save_to_db(self, character_id: int, assets: List[Dict], conn) -> None:
        """Replace character assets in database."""
        with conn.cursor() as cursor:
            # Delete existing assets for this character
            cursor.execute(
                "DELETE FROM character_assets WHERE character_id = %s",
                (character_id,)
            )

            # Insert new assets
            if assets:
                asset_data = [
                    (
                        character_id,
                        a.get("item_id"),
                        a.get("type_id"),
                        a.get("type_name"),
                        a.get("location_id"),
                        None,  # location_name - would need additional lookup
                        a.get("location_flag"),
                        a.get("location_type"),
                        a.get("quantity", 1),
                        a.get("is_singleton", False),
                        a.get("is_blueprint_copy")
                    )
                    for a in assets
                ]

                execute_values(
                    cursor,
                    """
                    INSERT INTO character_assets
                    (character_id, item_id, type_id, type_name, location_id, location_name,
                     location_flag, location_type, quantity, is_singleton, is_blueprint_copy)
                    VALUES %s
                    ON CONFLICT (character_id, item_id) DO UPDATE SET
                        type_id = EXCLUDED.type_id,
                        type_name = EXCLUDED.type_name,
                        location_id = EXCLUDED.location_id,
                        location_flag = EXCLUDED.location_flag,
                        location_type = EXCLUDED.location_type,
                        quantity = EXCLUDED.quantity,
                        is_singleton = EXCLUDED.is_singleton,
                        is_blueprint_copy = EXCLUDED.is_blueprint_copy,
                        last_synced = NOW()
                    """,
                    asset_data
                )

    def get_sync_column(self) -> str:
        """Return the sync timestamp column name."""
        return "assets_synced_at"

    def get_result_key(self) -> str:
        """Return key for result count."""
        return "asset_count"
