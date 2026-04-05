"""
Production Workflow Repository

Handles database operations for production job management.
Manages job tracking, material requirements, and make-or-buy decisions.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class WorkflowRepositoryError(Exception):
    """Base exception for workflow repository errors"""
    pass


class WorkflowRepository:
    """Repository for production workflow data access"""

    def __init__(self, db):
        """
        Initialize repository with database connection.

        Args:
            db: Database instance from eve_shared (request.app.state.db)
        """
        self.db = db

    def create_job(
        self,
        character_id: int,
        item_type_id: int,
        blueprint_type_id: int,
        me_level: int,
        te_level: int,
        runs: int,
        facility_id: Optional[int] = None,
        system_id: Optional[int] = None,
        total_cost: Optional[float] = None,
        expected_revenue: Optional[float] = None
    ) -> Optional[int]:
        """
        Create a new production job.

        Returns:
            Job ID if successful, None otherwise
        """
        try:
            with self.db.cursor() as cur:
                cur.execute("""
                    INSERT INTO production_jobs
                    (character_id, item_type_id, blueprint_type_id,
                     me_level, te_level, runs, facility_id, system_id,
                     total_cost, expected_revenue, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'planned')
                    RETURNING id
                """, (character_id, item_type_id, blueprint_type_id,
                      me_level, te_level, runs, facility_id, system_id,
                      total_cost, expected_revenue))

                result = cur.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Error creating job: {e}")
            raise WorkflowRepositoryError(f"Failed to create job: {e}")

    def add_job_material(
        self,
        job_id: int,
        material_type_id: int,
        quantity_needed: int,
        decision: str,
        cost_per_unit: Optional[float] = None,
        total_cost: Optional[float] = None
    ) -> Optional[int]:
        """Add a material requirement to a job."""
        try:
            with self.db.cursor() as cur:
                cur.execute("""
                    INSERT INTO production_job_materials
                    (job_id, material_type_id, quantity_needed, decision,
                     cost_per_unit, total_cost)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (job_id, material_type_id, quantity_needed, decision,
                      cost_per_unit, total_cost))

                result = cur.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Error adding job material: {e}")
            raise WorkflowRepositoryError(f"Failed to add job material: {e}")

    def get_jobs(
        self,
        character_id: int,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get jobs for a character, optionally filtered by status."""
        try:
            with self.db.cursor() as cur:
                if status:
                    cur.execute("""
                        SELECT
                            pj.id,
                            pj.item_type_id,
                            t."typeName",
                            pj.runs,
                            pj.status,
                            pj.me_level,
                            pj.te_level,
                            pj.total_cost,
                            pj.expected_revenue,
                            pj.actual_revenue,
                            pj.started_at,
                            pj.completed_at,
                            pj.created_at
                        FROM production_jobs pj
                        JOIN "invTypes" t ON pj.item_type_id = t."typeID"
                        WHERE pj.character_id = %s AND pj.status = %s
                        ORDER BY pj.created_at DESC
                    """, (character_id, status))
                else:
                    cur.execute("""
                        SELECT
                            pj.id,
                            pj.item_type_id,
                            t."typeName",
                            pj.runs,
                            pj.status,
                            pj.me_level,
                            pj.te_level,
                            pj.total_cost,
                            pj.expected_revenue,
                            pj.actual_revenue,
                            pj.started_at,
                            pj.completed_at,
                            pj.created_at
                        FROM production_jobs pj
                        JOIN "invTypes" t ON pj.item_type_id = t."typeID"
                        WHERE pj.character_id = %s
                        ORDER BY pj.created_at DESC
                    """, (character_id,))

                rows = cur.fetchall()
                return [
                    {
                        'job_id': row[0],
                        'item_type_id': row[1],
                        'item_name': row[2],
                        'runs': row[3],
                        'status': row[4],
                        'me_level': row[5],
                        'te_level': row[6],
                        'total_cost': float(row[7]) if row[7] else None,
                        'expected_revenue': float(row[8]) if row[8] else None,
                        'actual_revenue': float(row[9]) if row[9] else None,
                        'started_at': row[10],
                        'completed_at': row[11],
                        'created_at': row[12]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error getting jobs: {e}")
            raise WorkflowRepositoryError(f"Failed to get jobs: {e}")

    def update_job(
        self,
        job_id: int,
        status: Optional[str] = None,
        actual_revenue: Optional[float] = None
    ) -> bool:
        """Update job status and/or actual revenue."""
        try:
            with self.db.cursor() as cur:
                updates = []
                params = []

                if status:
                    updates.append("status = %s")
                    params.append(status)

                    if status == 'active':
                        updates.append("started_at = NOW()")
                    elif status == 'completed':
                        updates.append("completed_at = NOW()")

                if actual_revenue is not None:
                    updates.append("actual_revenue = %s")
                    params.append(actual_revenue)

                if not updates:
                    return False

                params.append(job_id)
                query = f"""
                    UPDATE production_jobs
                    SET {', '.join(updates)}
                    WHERE id = %s
                """

                cur.execute(query, params)
                return True
        except Exception as e:
            logger.error(f"Error updating job: {e}")
            raise WorkflowRepositoryError(f"Failed to update job: {e}")

    def get_job_materials(self, job_id: int) -> List[Dict[str, Any]]:
        """Get materials for a specific job."""
        try:
            with self.db.cursor() as cur:
                cur.execute("""
                    SELECT
                        pjm.id,
                        pjm.material_type_id,
                        t."typeName",
                        pjm.quantity_needed,
                        pjm.decision,
                        pjm.cost_per_unit,
                        pjm.total_cost
                    FROM production_job_materials pjm
                    JOIN "invTypes" t ON pjm.material_type_id = t."typeID"
                    WHERE pjm.job_id = %s
                    ORDER BY t."typeName"
                """, (job_id,))

                rows = cur.fetchall()
                return [
                    {
                        'id': row[0],
                        'material_type_id': row[1],
                        'material_name': row[2],
                        'quantity_needed': row[3],
                        'decision': row[4],
                        'cost_per_unit': float(row[5]) if row[5] else None,
                        'total_cost': float(row[6]) if row[6] else None
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error getting job materials: {e}")
            raise WorkflowRepositoryError(f"Failed to get job materials: {e}")
