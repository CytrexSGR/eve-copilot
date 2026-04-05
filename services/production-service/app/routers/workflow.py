"""
Production Workflow Router

API endpoints for production job management and tracking.
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query

from app.models.workflow import (
    WorkflowJobCreate,
    WorkflowJobUpdate,
    WorkflowJobCreated,
    WorkflowJobsResponse,
    WorkflowJobUpdated,
)
from app.services.workflow_repository import WorkflowRepository
from app.services.workflow_service import WorkflowService, WorkflowServiceError

logger = logging.getLogger(__name__)
router = APIRouter()


def get_workflow_service(request: Request) -> WorkflowService:
    """Create workflow service with database from app state."""
    db = request.app.state.db
    repository = WorkflowRepository(db)
    return WorkflowService(repository)


@router.post("/jobs", response_model=WorkflowJobCreated, status_code=201)
def create_production_job(
    request: Request,
    data: WorkflowJobCreate,
):
    """
    Create a new production job.

    Creates a job with material requirements and make-or-buy decisions.
    The job starts with 'planned' status.
    """
    try:
        service = get_workflow_service(request)
        result = service.create_job(
            character_id=data.character_id,
            item_type_id=data.item_type_id,
            blueprint_type_id=data.blueprint_type_id,
            me_level=data.me_level,
            te_level=data.te_level,
            runs=data.runs,
            materials=[m.model_dump() for m in data.materials],
            facility_id=data.facility_id,
            system_id=data.system_id
        )
        return result
    except WorkflowServiceError as e:
        logger.error(f"Failed to create production job: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating production job: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/jobs", response_model=WorkflowJobsResponse)
def get_production_jobs(
    request: Request,
    character_id: int = Query(..., description="Character ID"),
    status: Optional[str] = Query(
        None,
        description="Status filter (planned, active, completed, cancelled)"
    ),
):
    """
    Get production jobs for a character.

    Returns all jobs for the character, optionally filtered by status.
    Jobs are ordered by creation date (newest first).
    """
    try:
        service = get_workflow_service(request)
        result = service.get_jobs(character_id, status)
        return result
    except WorkflowServiceError as e:
        logger.error(f"Failed to get production jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error getting production jobs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.patch("/jobs/{job_id}", response_model=WorkflowJobUpdated)
def update_production_job(
    request: Request,
    job_id: int,
    data: WorkflowJobUpdate,
):
    """
    Update production job status.

    Can update:
    - status: planned -> active -> completed (or cancelled)
    - actual_revenue: Record actual revenue when job is sold

    Status transitions automatically update timestamps:
    - 'active' sets started_at
    - 'completed' sets completed_at
    """
    try:
        service = get_workflow_service(request)
        result = service.update_job(
            job_id=job_id,
            status=data.status,
            actual_revenue=data.actual_revenue
        )
        return result
    except WorkflowServiceError as e:
        logger.error(f"Failed to update production job: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error updating production job: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
