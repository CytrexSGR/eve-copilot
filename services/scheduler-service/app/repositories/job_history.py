"""Job history repository for persistent storage."""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from eve_shared import get_db
from app.models.job import JobRun, JobStatus

logger = logging.getLogger(__name__)


class JobHistoryRepository:
    """Repository for job execution history."""

    def __init__(self):
        self.db = get_db()

    def save_run(self, run: JobRun) -> int:
        """Save a job run to the database. Returns the ID."""
        try:
            with self.db.cursor() as cur:
                cur.execute("""
                    INSERT INTO scheduler_job_history (
                        job_id, job_name, status, started_at, finished_at,
                        duration_ms, error_message, retry_count
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    run.job_id,
                    run.job_id,  # Use job_id as name for now
                    run.status.value,
                    run.started_at,
                    run.finished_at,
                    int(run.duration_seconds * 1000) if run.duration_seconds else None,
                    run.error_message,
                    run.retry_count
                ))
                result = cur.fetchone()
                return result['id'] if result else 0
        except Exception as e:
            logger.error(f"Failed to save job run for {run.job_id}: {e}")
            raise

    def get_history(
        self,
        job_id: Optional[str] = None,
        status: Optional[JobStatus] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get job execution history with optional filters."""
        try:
            with self.db.cursor() as cur:
                where_clauses = []
                params = []

                if job_id:
                    where_clauses.append("job_id = %s")
                    params.append(job_id)

                if status:
                    where_clauses.append("status = %s")
                    params.append(status.value)

                where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

                cur.execute(f"""
                    SELECT id, job_id, job_name, status, started_at, finished_at,
                           duration_ms, error_message, retry_count, created_at
                    FROM scheduler_job_history
                    {where_sql}
                    ORDER BY started_at DESC
                    LIMIT %s
                """, params + [limit])
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Failed to get job history (job_id={job_id}, status={status}): {e}")
            raise

    def get_recent_failures(self, hours: int = 24, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent failed job runs."""
        try:
            start_time = datetime.utcnow() - timedelta(hours=hours)
            with self.db.cursor() as cur:
                cur.execute("""
                    SELECT id, job_id, job_name, status, started_at, finished_at,
                           duration_ms, error_message, retry_count
                    FROM scheduler_job_history
                    WHERE status = %s
                      AND started_at > %s
                    ORDER BY started_at DESC
                    LIMIT %s
                """, (JobStatus.FAILED.value, start_time, limit))
                return cur.fetchall()
        except Exception as e:
            logger.error(f"Failed to get recent failures (hours={hours}): {e}")
            raise

    def get_job_stats(self, job_id: str, days: int = 7) -> Dict[str, Any]:
        """Get statistics for a specific job."""
        try:
            start_time = datetime.utcnow() - timedelta(days=days)
            with self.db.cursor() as cur:
                cur.execute("""
                    SELECT
                        COUNT(*) as total_runs,
                        COUNT(*) FILTER (WHERE status = 'success') as success_count,
                        COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
                        AVG(duration_ms) as avg_duration_ms,
                        MAX(duration_ms) as max_duration_ms,
                        MIN(duration_ms) as min_duration_ms
                    FROM scheduler_job_history
                    WHERE job_id = %s
                      AND started_at > %s
                """, (job_id, start_time))
                return cur.fetchone()
        except Exception as e:
            logger.error(f"Failed to get job stats for {job_id}: {e}")
            raise

    def cleanup_old_history(self, days: int = 30) -> int:
        """Remove history older than specified days. Returns count deleted."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)
            with self.db.cursor() as cur:
                cur.execute("""
                    DELETE FROM scheduler_job_history
                    WHERE created_at < %s
                """, (cutoff,))
                return cur.rowcount
        except Exception as e:
            logger.error(f"Failed to cleanup old history (days={days}): {e}")
            raise


# Global instance
job_history_repo = JobHistoryRepository()
