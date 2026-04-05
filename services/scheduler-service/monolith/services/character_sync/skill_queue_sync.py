"""Skill queue sync operation."""
from typing import Any, List, Dict, Optional
from datetime import datetime
from psycopg2.extras import execute_values

from src.database import get_item_info
from .base import BaseSyncOperation


class SkillQueueSync(BaseSyncOperation):
    """Sync character skill queue."""

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
        """Fetch skill queue from ESI."""
        return self.character_service.get_skill_queue(character_id)

    def transform_data(self, raw_data: Any) -> List[Dict]:
        """Convert skill queue models to dicts."""
        return [q.model_dump() for q in raw_data.queue]

    def save_to_db(self, character_id: int, queue: List[Dict], conn) -> None:
        """Replace character skill queue in database."""
        with conn.cursor() as cursor:
            # Delete existing queue for this character
            cursor.execute(
                "DELETE FROM character_skill_queue WHERE character_id = %s",
                (character_id,)
            )

            # Insert new queue items
            if queue:
                queue_data = []
                for item in queue:
                    skill_id = item.get("skill_id")
                    skill_info = get_item_info(skill_id) if skill_id else None
                    skill_name = skill_info.get("typeName") if isinstance(skill_info, dict) else "Unknown"

                    queue_data.append((
                        character_id,
                        item.get("queue_position", 0),
                        skill_id,
                        skill_name,
                        item.get("finished_level", 0),
                        self._parse_datetime(item.get("start_date")),
                        self._parse_datetime(item.get("finish_date")),
                        item.get("training_start_sp"),
                        item.get("level_start_sp"),
                        item.get("level_end_sp")
                    ))

                execute_values(
                    cursor,
                    """
                    INSERT INTO character_skill_queue
                    (character_id, queue_position, skill_id, skill_name, finished_level,
                     start_date, finish_date, training_start_sp, level_start_sp, level_end_sp)
                    VALUES %s
                    """,
                    queue_data
                )

    def get_sync_column(self) -> str:
        """Return the sync timestamp column name."""
        return "skill_queue_synced_at"

    def get_result_key(self) -> str:
        """Return key for result count."""
        return "queue_length"
