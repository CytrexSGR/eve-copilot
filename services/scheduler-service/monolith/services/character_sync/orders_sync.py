"""Market orders sync operation."""
from typing import Any, List, Dict, Optional
from datetime import datetime
from psycopg2.extras import execute_values

from src.database import get_item_info
from .base import BaseSyncOperation


class OrdersSync(BaseSyncOperation):
    """Sync character market orders."""

    @staticmethod
    def _parse_datetime(date_str: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string to datetime object.

        Args:
            date_str: ISO datetime string (may end with 'Z' or '+00:00')

        Returns:
            datetime object or None if parsing fails
        """
        if not date_str:
            return None
        try:
            # Handle both formats: with 'Z' and with '+00:00'
            if date_str.endswith('Z'):
                date_str = date_str[:-1] + '+00:00'
            return datetime.fromisoformat(date_str.replace('+00:00', ''))
        except (ValueError, TypeError):
            return None

    def fetch_from_esi(self, character_id: int) -> Any:
        """Fetch market orders from ESI."""
        return self.character_service.get_market_orders(character_id)

    def transform_data(self, raw_data: Any) -> List[Dict]:
        """Convert order models to dicts with type names."""
        orders = []
        for o in raw_data.orders:
            order_dict = o.model_dump()
            type_id = order_dict.get("type_id")
            type_info = get_item_info(type_id) if type_id else None
            order_dict["type_name"] = type_info.get("typeName") if isinstance(type_info, dict) else None
            orders.append(order_dict)
        return orders

    def save_to_db(self, character_id: int, orders: List[Dict], conn) -> None:
        """Replace character market orders in database."""
        with conn.cursor() as cursor:
            # Delete existing orders for this character
            cursor.execute(
                "DELETE FROM character_orders WHERE character_id = %s",
                (character_id,)
            )

            # Insert new orders
            if orders:
                order_data = [
                    (
                        character_id,
                        o.get("order_id"),
                        o.get("type_id"),
                        o.get("type_name"),
                        o.get("location_id"),
                        None,  # location_name
                        o.get("region_id"),
                        o.get("is_buy_order", False),
                        o.get("price", 0),
                        o.get("volume_total", 0),
                        o.get("volume_remain", 0),
                        o.get("min_volume", 1),
                        o.get("range"),
                        o.get("duration"),
                        o.get("escrow"),
                        o.get("is_corporation", False),
                        self._parse_datetime(o.get("issued")),
                        o.get("state", "active")
                    )
                    for o in orders
                ]

                execute_values(
                    cursor,
                    """
                    INSERT INTO character_orders
                    (character_id, order_id, type_id, type_name, location_id, location_name,
                     region_id, is_buy_order, price, volume_total, volume_remain, min_volume,
                     range, duration, escrow, is_corporation, issued, state)
                    VALUES %s
                    """,
                    order_data
                )

    def get_sync_column(self) -> str:
        """Return the sync timestamp column name."""
        return "orders_synced_at"

    def get_result_key(self) -> str:
        """Return key for result count."""
        return "order_count"
