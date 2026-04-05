"""Skills sync operation."""
from typing import Any, List, Dict
from psycopg2.extras import execute_values

from .base import BaseSyncOperation


class SkillsSync(BaseSyncOperation):
    """Sync character skills."""

    def __init__(self, character_service):
        """Initialize with CharacterService and SP tracking vars."""
        super().__init__(character_service)
        self._total_sp = 0
        self._unallocated_sp = 0

    def fetch_from_esi(self, character_id: int) -> Any:
        """Fetch skills from ESI."""
        return self.character_service.get_skills(character_id)

    def transform_data(self, raw_data: Any) -> List[Dict]:
        """Convert skill models to dicts and store SP values."""
        self._total_sp = raw_data.total_sp
        self._unallocated_sp = raw_data.unallocated_sp
        return [s.model_dump() for s in raw_data.skills]

    def save_to_db(self, character_id: int, skills: List[Dict], conn) -> None:
        """Replace character skills in database."""
        with conn.cursor() as cursor:
            # Delete existing skills for this character
            cursor.execute(
                "DELETE FROM character_skills WHERE character_id = %s",
                (character_id,)
            )

            # Insert new skills
            if skills:
                skill_data = [
                    (
                        character_id,
                        s["skill_id"],
                        s.get("skill_name", "Unknown"),
                        s.get("level", 0),
                        s.get("trained_level", 0),
                        s.get("skillpoints", 0)
                    )
                    for s in skills
                ]

                execute_values(
                    cursor,
                    """
                    INSERT INTO character_skills
                    (character_id, skill_id, skill_name, active_skill_level,
                     trained_skill_level, skillpoints_in_skill)
                    VALUES %s
                    """,
                    skill_data
                )

            # Record SP history
            cursor.execute("""
                INSERT INTO character_sp_history (character_id, total_sp, unallocated_sp)
                VALUES (%s, %s, %s)
            """, (character_id, self._total_sp, self._unallocated_sp))

    def get_sync_column(self) -> str:
        """Return the sync timestamp column name."""
        return "skills_synced_at"

    def get_result_key(self) -> str:
        """Return key for result count."""
        return "skill_count"
