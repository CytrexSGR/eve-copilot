"""Blueprints sync operation."""
from typing import Any, List, Dict
from psycopg2.extras import execute_values

from src.database import get_item_info
from .base import BaseSyncOperation


class BlueprintsSync(BaseSyncOperation):
    """Sync character blueprints."""

    def fetch_from_esi(self, character_id: int) -> Any:
        """Fetch blueprints from ESI."""
        return self.character_service.get_blueprints(character_id)

    def transform_data(self, raw_data: Any) -> List[Dict]:
        """Convert blueprint models to dicts with type names."""
        blueprints = []
        for bp in raw_data.blueprints:
            bp_dict = bp.model_dump()
            type_id = bp_dict.get("type_id")
            type_info = get_item_info(type_id) if type_id else None
            bp_dict["type_name"] = type_info.get("typeName") if isinstance(type_info, dict) else None
            blueprints.append(bp_dict)
        return blueprints

    def save_to_db(self, character_id: int, blueprints: List[Dict], conn) -> None:
        """Replace character blueprints in database."""
        with conn.cursor() as cursor:
            # Delete existing blueprints for this character
            cursor.execute(
                "DELETE FROM character_blueprints WHERE character_id = %s",
                (character_id,)
            )

            # Insert new blueprints
            if blueprints:
                bp_data = [
                    (
                        character_id,
                        bp.get("item_id"),
                        bp.get("type_id"),
                        bp.get("type_name"),
                        bp.get("location_id"),
                        None,  # location_name
                        bp.get("location_flag"),
                        bp.get("quantity", -1),
                        bp.get("time_efficiency", 0),
                        bp.get("material_efficiency", 0),
                        bp.get("runs", -1)
                    )
                    for bp in blueprints
                ]

                execute_values(
                    cursor,
                    """
                    INSERT INTO character_blueprints
                    (character_id, item_id, type_id, type_name, location_id, location_name,
                     location_flag, quantity, time_efficiency, material_efficiency, runs)
                    VALUES %s
                    """,
                    bp_data
                )

    def get_sync_column(self) -> str:
        """Return the sync timestamp column name."""
        return "blueprints_synced_at"

    def get_result_key(self) -> str:
        """Return key for result count."""
        return "blueprint_count"
