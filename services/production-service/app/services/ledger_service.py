"""
Production Ledger Service
Business logic layer for multi-stage manufacturing project tracking
"""

import logging
from typing import List, Optional

from app.models.ledger import (
    LedgerCreate,
    LedgerUpdate,
    Ledger,
    LedgerWithDetails,
    StageCreate,
    StageUpdate,
    Stage,
    StageWithJobs,
    JobCreate,
    JobUpdate,
    Job,
    MaterialUpsert,
    Material,
)
from app.services.ledger_repository import LedgerRepository

logger = logging.getLogger(__name__)


class LedgerNotFoundError(Exception):
    """Raised when a ledger resource is not found."""

    def __init__(self, resource_type: str, resource_id: int):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} not found: {resource_id}")


class LedgerService:
    """
    Production Ledger Service provides business logic for managing multi-stage
    manufacturing projects.

    This service orchestrates the creation and tracking of production ledgers,
    which represent complex manufacturing projects that may involve multiple
    stages (e.g., component manufacturing, sub-assembly, final assembly).

    Responsibilities:
    - Create and manage production ledgers
    - Organize production into stages with proper sequencing
    - Track individual production jobs within stages
    - Aggregate material requirements across all jobs
    - Calculate and recalculate costs
    - Provide detailed project views with nested data

    Pattern: Dependency Injection
    - No direct database access (delegates to repository)
    - Returns Pydantic models for type safety
    """

    def __init__(self, repository: LedgerRepository):
        """
        Initialize Ledger Service with dependencies.

        Args:
            repository: Ledger repository for database operations
        """
        self.repository = repository

    # =========================================================================
    # Ledger Operations
    # =========================================================================

    def create_ledger(self, data: LedgerCreate) -> Ledger:
        """
        Create a new production ledger.

        Args:
            data: Ledger creation data

        Returns:
            Created ledger
        """
        result = self.repository.create(data)
        return Ledger(**result)

    def get_ledger(self, ledger_id: int) -> Ledger:
        """
        Get a ledger by ID.

        Args:
            ledger_id: Ledger ID

        Returns:
            Ledger

        Raises:
            LedgerNotFoundError: If ledger not found
        """
        result = self.repository.get_by_id(ledger_id)
        if not result:
            raise LedgerNotFoundError("Ledger", ledger_id)
        return Ledger(**result)

    def get_ledgers_by_character(self, character_id: int) -> List[Ledger]:
        """
        Get all ledgers for a character.

        Args:
            character_id: Character ID

        Returns:
            List of ledgers
        """
        results = self.repository.get_by_character(character_id)
        return [Ledger(**r) for r in results]

    def update_ledger(self, ledger_id: int, data: LedgerUpdate) -> Ledger:
        """
        Update a ledger.

        Args:
            ledger_id: Ledger ID
            data: Update data

        Returns:
            Updated ledger

        Raises:
            LedgerNotFoundError: If ledger not found
        """
        result = self.repository.update(ledger_id, data)
        if not result:
            raise LedgerNotFoundError("Ledger", ledger_id)
        return Ledger(**result)

    def delete_ledger(self, ledger_id: int) -> bool:
        """
        Delete a ledger and all related data.

        Args:
            ledger_id: Ledger ID

        Returns:
            True if deleted

        Raises:
            LedgerNotFoundError: If ledger not found
        """
        result = self.repository.delete(ledger_id)
        if not result:
            raise LedgerNotFoundError("Ledger", ledger_id)
        return True

    def get_ledger_with_details(self, ledger_id: int) -> LedgerWithDetails:
        """
        Get a ledger with all nested details (stages, jobs, materials).

        Args:
            ledger_id: Ledger ID

        Returns:
            Ledger with full details

        Raises:
            LedgerNotFoundError: If ledger not found
        """
        result = self.repository.get_with_details(ledger_id)
        if not result:
            raise LedgerNotFoundError("Ledger", ledger_id)

        # Convert nested stages to StageWithJobs
        stages = []
        for stage_data in result.get("stages", []):
            jobs = [Job(**j) for j in stage_data.get("jobs", [])]
            stage = StageWithJobs(
                **{k: v for k, v in stage_data.items() if k != "jobs"},
                jobs=jobs
            )
            stages.append(stage)

        # Convert materials
        materials = [Material(**m) for m in result.get("materials", [])]

        # Build final result
        ledger_data = {k: v for k, v in result.items() if k not in ("stages", "materials")}
        return LedgerWithDetails(**ledger_data, stages=stages, materials=materials)

    # =========================================================================
    # Stage Operations
    # =========================================================================

    def add_stage(self, ledger_id: int, data: StageCreate) -> Stage:
        """
        Add a stage to a ledger.

        Args:
            ledger_id: Ledger ID
            data: Stage creation data

        Returns:
            Created stage

        Raises:
            LedgerNotFoundError: If ledger not found
        """
        # Verify ledger exists
        ledger = self.repository.get_by_id(ledger_id)
        if not ledger:
            raise LedgerNotFoundError("Ledger", ledger_id)

        result = self.repository.add_stage(ledger_id, data)
        return Stage(**result)

    def get_stages(self, ledger_id: int) -> List[Stage]:
        """
        Get all stages for a ledger.

        Args:
            ledger_id: Ledger ID

        Returns:
            List of stages ordered by stage_order
        """
        results = self.repository.get_stages(ledger_id)
        return [Stage(**r) for r in results]

    def update_stage(self, stage_id: int, data: StageUpdate) -> Stage:
        """
        Update a stage.

        Args:
            stage_id: Stage ID
            data: Update data

        Returns:
            Updated stage

        Raises:
            LedgerNotFoundError: If stage not found
        """
        result = self.repository.update_stage(stage_id, data)
        if not result:
            raise LedgerNotFoundError("Stage", stage_id)
        return Stage(**result)

    # =========================================================================
    # Job Operations
    # =========================================================================

    def add_job(self, ledger_id: int, stage_id: int, data: JobCreate) -> Job:
        """
        Add a job to a stage.

        Args:
            ledger_id: Ledger ID
            stage_id: Stage ID
            data: Job creation data

        Returns:
            Created job

        Raises:
            LedgerNotFoundError: If stage not found
        """
        # Verify stage exists
        stage = self.repository._get_stage_by_id(stage_id)
        if not stage:
            raise LedgerNotFoundError("Stage", stage_id)

        result = self.repository.add_job(ledger_id, stage_id, data)
        return Job(**result)

    def get_jobs(self, stage_id: int) -> List[Job]:
        """
        Get all jobs for a stage.

        Args:
            stage_id: Stage ID

        Returns:
            List of jobs
        """
        results = self.repository.get_jobs(stage_id)
        return [Job(**r) for r in results]

    def update_job(self, job_id: int, data: JobUpdate) -> Job:
        """
        Update a job.

        Args:
            job_id: Job ID
            data: Update data

        Returns:
            Updated job

        Raises:
            LedgerNotFoundError: If job not found
        """
        result = self.repository.update_job(job_id, data)
        if not result:
            raise LedgerNotFoundError("Job", job_id)
        return Job(**result)

    # =========================================================================
    # Material Operations
    # =========================================================================

    def upsert_material(self, ledger_id: int, data: MaterialUpsert) -> Material:
        """
        Upsert (insert or update) a material requirement.

        Args:
            ledger_id: Ledger ID
            data: Material data

        Returns:
            Upserted material

        Raises:
            LedgerNotFoundError: If ledger not found
        """
        # Verify ledger exists
        ledger = self.repository.get_by_id(ledger_id)
        if not ledger:
            raise LedgerNotFoundError("Ledger", ledger_id)

        result = self.repository.upsert_material(ledger_id, data)
        return Material(**result)

    def get_materials(self, ledger_id: int) -> List[Material]:
        """
        Get all materials for a ledger.

        Args:
            ledger_id: Ledger ID

        Returns:
            List of materials
        """
        results = self.repository.get_materials(ledger_id)
        return [Material(**r) for r in results]

    # =========================================================================
    # Cost Operations
    # =========================================================================

    def recalculate_costs(self, ledger_id: int) -> Ledger:
        """
        Recalculate and update ledger costs from jobs and materials.

        This method aggregates costs from:
        - Material estimated costs
        - Job costs

        Args:
            ledger_id: Ledger ID

        Returns:
            Updated ledger with recalculated costs

        Raises:
            LedgerNotFoundError: If ledger not found
        """
        result = self.repository.recalculate_costs(ledger_id)
        return Ledger(**result)
