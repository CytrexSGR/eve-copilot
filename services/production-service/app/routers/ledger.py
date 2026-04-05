"""
Production Ledger Router
API endpoints for multi-stage manufacturing project tracking
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, Request, Query

from app.models.ledger import (
    LedgerCreate,
    LedgerUpdate,
    Ledger,
    LedgerWithDetails,
    StageCreate,
    StageUpdate,
    Stage,
    JobCreate,
    JobUpdate,
    Job,
    MaterialUpsert,
    Material,
)
from app.services.ledger_repository import LedgerRepository, LedgerRepositoryError
from app.services.ledger_service import LedgerService, LedgerNotFoundError

logger = logging.getLogger(__name__)
router = APIRouter()


def get_ledger_service(request: Request) -> LedgerService:
    """Create ledger service with database from app state."""
    db = request.app.state.db
    repository = LedgerRepository(db)
    return LedgerService(repository)


# =============================================================================
# Ledger Endpoints
# =============================================================================

@router.get("", response_model=List[Ledger])
def list_ledgers(
    request: Request,
    character_id: int = Query(..., description="Character ID to list ledgers for"),
):
    """
    List all production ledgers for a character.

    Returns ledgers ordered by creation date (newest first).
    """
    try:
        service = get_ledger_service(request)
        return service.get_ledgers_by_character(character_id)
    except LedgerRepositoryError as e:
        logger.error(f"Failed to list ledgers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=Ledger, status_code=201)
def create_ledger(
    request: Request,
    data: LedgerCreate,
):
    """
    Create a new production ledger.

    A ledger represents a multi-stage manufacturing project.
    """
    try:
        service = get_ledger_service(request)
        return service.create_ledger(data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LedgerRepositoryError as e:
        logger.error(f"Failed to create ledger: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ledger_id}", response_model=LedgerWithDetails)
def get_ledger(
    request: Request,
    ledger_id: int,
):
    """
    Get a production ledger with all details.

    Returns ledger with nested stages, jobs, and materials.
    """
    try:
        service = get_ledger_service(request)
        return service.get_ledger_with_details(ledger_id)
    except LedgerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except LedgerRepositoryError as e:
        logger.error(f"Failed to get ledger: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{ledger_id}", response_model=Ledger)
def update_ledger(
    request: Request,
    ledger_id: int,
    data: LedgerUpdate,
):
    """
    Update a production ledger.

    Can update name and status (planning, active, completed, cancelled).
    """
    try:
        service = get_ledger_service(request)
        return service.update_ledger(ledger_id, data)
    except LedgerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LedgerRepositoryError as e:
        logger.error(f"Failed to update ledger: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{ledger_id}", status_code=204)
def delete_ledger(
    request: Request,
    ledger_id: int,
):
    """
    Delete a production ledger.

    This will cascade delete all stages, jobs, and materials.
    """
    try:
        service = get_ledger_service(request)
        service.delete_ledger(ledger_id)
        return None
    except LedgerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except LedgerRepositoryError as e:
        logger.error(f"Failed to delete ledger: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Stage Endpoints
# =============================================================================

@router.get("/{ledger_id}/stages", response_model=List[Stage])
def list_stages(
    request: Request,
    ledger_id: int,
):
    """
    List all stages for a ledger.

    Returns stages ordered by stage_order.
    """
    try:
        service = get_ledger_service(request)
        return service.get_stages(ledger_id)
    except LedgerRepositoryError as e:
        logger.error(f"Failed to list stages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ledger_id}/stages", response_model=Stage, status_code=201)
def add_stage(
    request: Request,
    ledger_id: int,
    data: StageCreate,
):
    """
    Add a stage to a ledger.

    Stages represent phases of production (e.g., component manufacturing, assembly).
    """
    try:
        service = get_ledger_service(request)
        return service.add_stage(ledger_id, data)
    except LedgerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LedgerRepositoryError as e:
        logger.error(f"Failed to add stage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{ledger_id}/stages/{stage_id}", response_model=Stage)
def update_stage(
    request: Request,
    ledger_id: int,
    stage_id: int,
    data: StageUpdate,
):
    """
    Update a stage.

    Can update name and status (pending, in_progress, completed).
    """
    try:
        service = get_ledger_service(request)
        return service.update_stage(stage_id, data)
    except LedgerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LedgerRepositoryError as e:
        logger.error(f"Failed to update stage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Job Endpoints
# =============================================================================

@router.post("/{ledger_id}/stages/{stage_id}/jobs", response_model=Job, status_code=201)
def add_job(
    request: Request,
    ledger_id: int,
    stage_id: int,
    data: JobCreate,
):
    """
    Add a production job to a stage.

    Jobs represent individual manufacturing tasks within a stage.
    """
    try:
        service = get_ledger_service(request)
        return service.add_job(ledger_id, stage_id, data)
    except LedgerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LedgerRepositoryError as e:
        logger.error(f"Failed to add job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ledger_id}/stages/{stage_id}/jobs", response_model=List[Job])
def list_jobs(
    request: Request,
    ledger_id: int,
    stage_id: int,
):
    """
    List all jobs for a stage.
    """
    try:
        service = get_ledger_service(request)
        return service.get_jobs(stage_id)
    except LedgerRepositoryError as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{ledger_id}/jobs/{job_id}", response_model=Job)
def update_job(
    request: Request,
    ledger_id: int,
    job_id: int,
    data: JobUpdate,
):
    """
    Update a job.

    Can update status, esi_job_id, started_at, and completed_at.
    """
    try:
        service = get_ledger_service(request)
        return service.update_job(job_id, data)
    except LedgerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LedgerRepositoryError as e:
        logger.error(f"Failed to update job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Material Endpoints
# =============================================================================

@router.get("/{ledger_id}/materials", response_model=List[Material])
def list_materials(
    request: Request,
    ledger_id: int,
):
    """
    Get aggregated materials for a ledger.

    Returns all material requirements across all jobs.
    """
    try:
        service = get_ledger_service(request)
        return service.get_materials(ledger_id)
    except LedgerRepositoryError as e:
        logger.error(f"Failed to list materials: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{ledger_id}/materials", response_model=Material, status_code=201)
def upsert_material(
    request: Request,
    ledger_id: int,
    data: MaterialUpsert,
):
    """
    Upsert (insert or update) a material requirement.

    If material with same type_id exists, it will be updated.
    """
    try:
        service = get_ledger_service(request)
        return service.upsert_material(ledger_id, data)
    except LedgerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LedgerRepositoryError as e:
        logger.error(f"Failed to upsert material: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Cost Recalculation
# =============================================================================

@router.post("/{ledger_id}/recalculate", response_model=Ledger)
def recalculate_costs(
    request: Request,
    ledger_id: int,
):
    """
    Recalculate ledger costs from jobs and materials.

    Aggregates material costs and job costs to update total costs.
    """
    try:
        service = get_ledger_service(request)
        return service.recalculate_costs(ledger_id)
    except LedgerNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except LedgerRepositoryError as e:
        logger.error(f"Failed to recalculate costs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
