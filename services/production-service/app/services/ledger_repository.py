"""
Production Ledger Repository
Database access layer for production ledger operations using eve_shared pattern
"""

import logging
from typing import Any, Dict, List, Optional

from psycopg2.extras import RealDictCursor

from app.models.ledger import (
    LedgerCreate,
    LedgerUpdate,
    StageCreate,
    StageUpdate,
    JobCreate,
    JobUpdate,
    MaterialUpsert,
)

logger = logging.getLogger(__name__)


class LedgerRepositoryError(Exception):
    """Custom exception for ledger repository errors."""
    pass


class LedgerRepository:
    """Data access for production ledgers using eve_shared database pattern."""

    def __init__(self, db):
        """Initialize repository with eve_shared database instance."""
        self.db = db

    # =========================================================================
    # Ledger CRUD Operations
    # =========================================================================

    def create(self, data: LedgerCreate) -> Dict[str, Any]:
        """Create a new production ledger."""
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        INSERT INTO production_ledger (
                            character_id, name, target_type_id, target_quantity,
                            tax_profile_id, facility_id, status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, 'planning')
                        RETURNING *
                        """,
                        (
                            data.character_id,
                            data.name,
                            data.target_type_id,
                            data.target_quantity,
                            data.tax_profile_id,
                            data.facility_id,
                        )
                    )
                    conn.commit()
                    result = cur.fetchone()
                    if result is None:
                        raise LedgerRepositoryError("Failed to create ledger: No result returned")
                    return dict(result)
        except LedgerRepositoryError:
            raise
        except Exception as e:
            logger.error(f"Failed to create ledger: {e}")
            raise LedgerRepositoryError(f"Failed to create ledger: {str(e)}")

    def get_by_id(self, ledger_id: int) -> Optional[Dict[str, Any]]:
        """Get ledger by ID."""
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM production_ledger WHERE id = %s",
                        (ledger_id,)
                    )
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get ledger by ID: {e}")
            raise LedgerRepositoryError(f"Failed to get ledger by ID: {str(e)}")

    def get_by_character(self, character_id: int) -> List[Dict[str, Any]]:
        """Get all ledgers for a character."""
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT * FROM production_ledger
                        WHERE character_id = %s
                        ORDER BY created_at DESC
                        """,
                        (character_id,)
                    )
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get ledgers by character: {e}")
            raise LedgerRepositoryError(f"Failed to get ledgers by character: {str(e)}")

    def update(self, ledger_id: int, data: LedgerUpdate) -> Optional[Dict[str, Any]]:
        """Update a ledger."""
        updates = data.model_dump(exclude_unset=True, exclude_none=True)
        if not updates:
            return self.get_by_id(ledger_id)

        # Whitelist allowed fields
        ALLOWED_FIELDS = {"name", "status"}
        for key in updates.keys():
            if key not in ALLOWED_FIELDS:
                raise ValueError(f"Cannot update field: {key}")

        try:
            set_clauses = ", ".join(f"{key} = %s" for key in updates.keys())
            query = f"""
                UPDATE production_ledger
                SET {set_clauses}, updated_at = NOW()
                WHERE id = %s
                RETURNING *
            """

            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, (*updates.values(), ledger_id))
                    conn.commit()
                    result = cur.fetchone()
                    return dict(result) if result else None
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to update ledger: {e}")
            raise LedgerRepositoryError(f"Failed to update ledger: {str(e)}")

    def delete(self, ledger_id: int) -> bool:
        """Delete a ledger and all related data (cascading)."""
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "DELETE FROM production_ledger WHERE id = %s",
                        (ledger_id,)
                    )
                    conn.commit()
                    return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete ledger: {e}")
            raise LedgerRepositoryError(f"Failed to delete ledger: {str(e)}")

    # =========================================================================
    # Stage Operations
    # =========================================================================

    def add_stage(self, ledger_id: int, data: StageCreate) -> Dict[str, Any]:
        """Add a stage to a ledger."""
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        INSERT INTO ledger_stages (
                            ledger_id, name, stage_order, status
                        )
                        VALUES (%s, %s, %s, 'pending')
                        RETURNING *
                        """,
                        (ledger_id, data.name, data.stage_order)
                    )
                    conn.commit()
                    result = cur.fetchone()
                    if result is None:
                        raise LedgerRepositoryError("Failed to add stage: No result returned")
                    return dict(result)
        except LedgerRepositoryError:
            raise
        except Exception as e:
            logger.error(f"Failed to add stage: {e}")
            raise LedgerRepositoryError(f"Failed to add stage: {str(e)}")

    def get_stages(self, ledger_id: int) -> List[Dict[str, Any]]:
        """Get all stages for a ledger."""
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT * FROM ledger_stages
                        WHERE ledger_id = %s
                        ORDER BY stage_order ASC
                        """,
                        (ledger_id,)
                    )
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get stages: {e}")
            raise LedgerRepositoryError(f"Failed to get stages: {str(e)}")

    def update_stage(self, stage_id: int, data: StageUpdate) -> Optional[Dict[str, Any]]:
        """Update a stage."""
        updates = data.model_dump(exclude_unset=True, exclude_none=True)
        if not updates:
            return self._get_stage_by_id(stage_id)

        # Whitelist allowed fields
        ALLOWED_FIELDS = {"name", "status"}
        for key in updates.keys():
            if key not in ALLOWED_FIELDS:
                raise ValueError(f"Cannot update field: {key}")

        try:
            set_clauses = ", ".join(f"{key} = %s" for key in updates.keys())
            query = f"""
                UPDATE ledger_stages
                SET {set_clauses}, updated_at = NOW()
                WHERE id = %s
                RETURNING *
            """

            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, (*updates.values(), stage_id))
                    conn.commit()
                    result = cur.fetchone()
                    return dict(result) if result else None
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to update stage: {e}")
            raise LedgerRepositoryError(f"Failed to update stage: {str(e)}")

    def _get_stage_by_id(self, stage_id: int) -> Optional[Dict[str, Any]]:
        """Get a stage by ID (internal helper)."""
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM ledger_stages WHERE id = %s",
                        (stage_id,)
                    )
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get stage by ID: {e}")
            raise LedgerRepositoryError(f"Failed to get stage by ID: {str(e)}")

    # =========================================================================
    # Job Operations
    # =========================================================================

    def add_job(self, ledger_id: int, stage_id: int, data: JobCreate) -> Dict[str, Any]:
        """Add a job to a stage."""
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        INSERT INTO ledger_jobs (
                            ledger_id, stage_id, type_id, quantity, runs,
                            me_level, te_level, status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
                        RETURNING *
                        """,
                        (
                            ledger_id,
                            stage_id,
                            data.type_id,
                            data.quantity,
                            data.runs,
                            data.me_level,
                            data.te_level,
                        )
                    )
                    conn.commit()
                    result = cur.fetchone()
                    if result is None:
                        raise LedgerRepositoryError("Failed to add job: No result returned")
                    return dict(result)
        except LedgerRepositoryError:
            raise
        except Exception as e:
            logger.error(f"Failed to add job: {e}")
            raise LedgerRepositoryError(f"Failed to add job: {str(e)}")

    def get_jobs(self, stage_id: int) -> List[Dict[str, Any]]:
        """Get all jobs for a stage."""
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT * FROM ledger_jobs
                        WHERE stage_id = %s
                        ORDER BY created_at ASC
                        """,
                        (stage_id,)
                    )
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get jobs: {e}")
            raise LedgerRepositoryError(f"Failed to get jobs: {str(e)}")

    def get_jobs_for_ledger(self, ledger_id: int) -> List[Dict[str, Any]]:
        """Get all jobs for a ledger."""
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT * FROM ledger_jobs
                        WHERE ledger_id = %s
                        ORDER BY stage_id, created_at ASC
                        """,
                        (ledger_id,)
                    )
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get jobs for ledger: {e}")
            raise LedgerRepositoryError(f"Failed to get jobs for ledger: {str(e)}")

    def update_job(self, job_id: int, data: JobUpdate) -> Optional[Dict[str, Any]]:
        """Update a job."""
        updates = data.model_dump(exclude_unset=True, exclude_none=True)
        if not updates:
            return self._get_job_by_id(job_id)

        # Whitelist allowed fields
        ALLOWED_FIELDS = {"status", "esi_job_id", "started_at", "completed_at"}
        for key in updates.keys():
            if key not in ALLOWED_FIELDS:
                raise ValueError(f"Cannot update field: {key}")

        try:
            set_clauses = ", ".join(f"{key} = %s" for key in updates.keys())
            query = f"""
                UPDATE ledger_jobs
                SET {set_clauses}
                WHERE id = %s
                RETURNING *
            """

            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(query, (*updates.values(), job_id))
                    conn.commit()
                    result = cur.fetchone()
                    return dict(result) if result else None
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to update job: {e}")
            raise LedgerRepositoryError(f"Failed to update job: {str(e)}")

    def _get_job_by_id(self, job_id: int) -> Optional[Dict[str, Any]]:
        """Get a job by ID (internal helper)."""
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT * FROM ledger_jobs WHERE id = %s",
                        (job_id,)
                    )
                    result = cur.fetchone()
                    return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get job by ID: {e}")
            raise LedgerRepositoryError(f"Failed to get job by ID: {str(e)}")

    # =========================================================================
    # Material Operations
    # =========================================================================

    def upsert_material(self, ledger_id: int, data: MaterialUpsert) -> Dict[str, Any]:
        """Upsert (insert or update) a material requirement."""
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        INSERT INTO ledger_materials (
                            ledger_id, type_id, type_name, total_needed,
                            total_acquired, estimated_cost, source
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (ledger_id, type_id) DO UPDATE SET
                            type_name = EXCLUDED.type_name,
                            total_needed = EXCLUDED.total_needed,
                            total_acquired = EXCLUDED.total_acquired,
                            estimated_cost = EXCLUDED.estimated_cost,
                            source = EXCLUDED.source
                        RETURNING *
                        """,
                        (
                            ledger_id,
                            data.type_id,
                            data.type_name,
                            data.total_needed,
                            data.total_acquired,
                            data.estimated_cost,
                            data.source,
                        )
                    )
                    conn.commit()
                    result = cur.fetchone()
                    if result is None:
                        raise LedgerRepositoryError("Failed to upsert material: No result returned")
                    return dict(result)
        except LedgerRepositoryError:
            raise
        except Exception as e:
            logger.error(f"Failed to upsert material: {e}")
            raise LedgerRepositoryError(f"Failed to upsert material: {str(e)}")

    def get_materials(self, ledger_id: int) -> List[Dict[str, Any]]:
        """Get all materials for a ledger."""
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """
                        SELECT * FROM ledger_materials
                        WHERE ledger_id = %s
                        ORDER BY type_name ASC
                        """,
                        (ledger_id,)
                    )
                    return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get materials: {e}")
            raise LedgerRepositoryError(f"Failed to get materials: {str(e)}")

    # =========================================================================
    # Composite Operations
    # =========================================================================

    def get_with_details(self, ledger_id: int) -> Optional[Dict[str, Any]]:
        """Get ledger with all nested details (stages, jobs, materials)."""
        try:
            # Get the ledger
            ledger = self.get_by_id(ledger_id)
            if not ledger:
                return None

            # Get stages
            stages = self.get_stages(ledger_id)

            # Get jobs for each stage
            for stage in stages:
                stage["jobs"] = self.get_jobs(stage["id"])

            # Get materials
            materials = self.get_materials(ledger_id)

            # Compose result
            ledger["stages"] = stages
            ledger["materials"] = materials

            return ledger
        except LedgerRepositoryError:
            raise
        except Exception as e:
            logger.error(f"Failed to get ledger with details: {e}")
            raise LedgerRepositoryError(f"Failed to get ledger with details: {str(e)}")

    def recalculate_costs(self, ledger_id: int) -> Dict[str, Any]:
        """Recalculate and update ledger costs from jobs and materials."""
        try:
            with self.db.connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    # Calculate material cost from materials table
                    cur.execute(
                        """
                        SELECT COALESCE(SUM(estimated_cost), 0) as material_cost
                        FROM ledger_materials
                        WHERE ledger_id = %s
                        """,
                        (ledger_id,)
                    )
                    mat_result = cur.fetchone()
                    material_cost = mat_result["material_cost"] if mat_result else 0

                    # Calculate job cost from jobs table
                    cur.execute(
                        """
                        SELECT COALESCE(SUM(job_cost), 0) as job_cost
                        FROM ledger_jobs
                        WHERE ledger_id = %s
                        """,
                        (ledger_id,)
                    )
                    job_result = cur.fetchone()
                    job_cost = job_result["job_cost"] if job_result else 0

                    # Calculate total cost
                    total_cost = material_cost + job_cost

                    # Update the ledger
                    cur.execute(
                        """
                        UPDATE production_ledger
                        SET total_material_cost = %s,
                            total_job_cost = %s,
                            total_cost = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        RETURNING *
                        """,
                        (material_cost, job_cost, total_cost, ledger_id)
                    )
                    conn.commit()
                    result = cur.fetchone()
                    if result is None:
                        raise LedgerRepositoryError("Failed to recalculate costs: Ledger not found")
                    return dict(result)
        except LedgerRepositoryError:
            raise
        except Exception as e:
            logger.error(f"Failed to recalculate costs: {e}")
            raise LedgerRepositoryError(f"Failed to recalculate costs: {str(e)}")
