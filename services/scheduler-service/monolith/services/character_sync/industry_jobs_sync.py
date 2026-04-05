"""Industry jobs sync operation."""
from typing import Any, List, Dict, Optional
from datetime import datetime

from src.database import get_item_info
from .base import BaseSyncOperation

# Activity ID to name mapping for industry jobs
ACTIVITY_NAMES = {
    1: "Manufacturing",
    3: "Researching Time Efficiency",
    4: "Researching Material Efficiency",
    5: "Copying",
    7: "Reverse Engineering",
    8: "Invention",
    9: "Reactions"
}


class IndustryJobsSync(BaseSyncOperation):
    """Sync character industry jobs.

    Note: Uses UPSERT (ON CONFLICT DO UPDATE) instead of delete+insert
    to preserve job history while updating status.
    """

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
        """Fetch industry jobs from ESI including completed jobs."""
        return self.character_service.get_industry_jobs(character_id, include_completed=True)

    def transform_data(self, raw_data: Any) -> List[Dict]:
        """Convert industry job models to dicts with type names."""
        jobs = []
        for j in raw_data.jobs:
            job_dict = j.model_dump()

            # Add blueprint name
            blueprint_type_id = job_dict.get("blueprint_type_id")
            blueprint_info = get_item_info(blueprint_type_id) if blueprint_type_id else None
            job_dict["blueprint_type_name"] = blueprint_info.get("typeName") if isinstance(blueprint_info, dict) else None

            # Add product name
            product_type_id = job_dict.get("product_type_id")
            product_info = get_item_info(product_type_id) if product_type_id else None
            job_dict["product_type_name"] = product_info.get("typeName") if isinstance(product_info, dict) else None

            # Add activity name
            activity_id = job_dict.get("activity_id")
            job_dict["activity_name"] = ACTIVITY_NAMES.get(activity_id, "Unknown")

            jobs.append(job_dict)
        return jobs

    def save_to_db(self, character_id: int, jobs: List[Dict], conn) -> None:
        """Upsert character industry jobs in database.

        Uses ON CONFLICT DO UPDATE to preserve job history while updating
        status fields for jobs that have changed.
        """
        with conn.cursor() as cursor:
            # Upsert jobs (ON CONFLICT UPDATE)
            for job in jobs:
                cursor.execute("""
                    INSERT INTO character_industry_jobs
                    (character_id, job_id, installer_id, facility_id, facility_name,
                     activity_id, activity_name, blueprint_id, blueprint_type_id, blueprint_type_name,
                     blueprint_location_id, output_location_id, product_type_id, product_type_name,
                     runs, cost, licensed_runs, probability, status, start_date, end_date,
                     pause_date, completed_date, completed_character_id, successful_runs)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (character_id, job_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        pause_date = EXCLUDED.pause_date,
                        completed_date = EXCLUDED.completed_date,
                        completed_character_id = EXCLUDED.completed_character_id,
                        successful_runs = EXCLUDED.successful_runs,
                        last_synced = NOW()
                """, (
                    character_id,
                    job.get("job_id"),
                    job.get("installer_id"),
                    job.get("facility_id"),
                    None,  # facility_name
                    job.get("activity_id"),
                    job.get("activity_name"),
                    job.get("blueprint_id"),
                    job.get("blueprint_type_id"),
                    job.get("blueprint_type_name"),
                    job.get("blueprint_location_id"),
                    job.get("output_location_id"),
                    job.get("product_type_id"),
                    job.get("product_type_name"),
                    job.get("runs", 1),
                    job.get("cost"),
                    job.get("licensed_runs"),
                    job.get("probability"),
                    job.get("status"),
                    self._parse_datetime(job.get("start_date")),
                    self._parse_datetime(job.get("end_date")),
                    self._parse_datetime(job.get("pause_date")),
                    self._parse_datetime(job.get("completed_date")),
                    job.get("completed_character_id"),
                    job.get("successful_runs")
                ))

    def get_sync_column(self) -> str:
        """Return the sync timestamp column name."""
        return "industry_jobs_synced_at"

    def get_result_key(self) -> str:
        """Return key for result count."""
        return "job_count"
