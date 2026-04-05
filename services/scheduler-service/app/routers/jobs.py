"""Job management API router."""

import logging
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.scheduler import scheduler_service
from app.jobs.definitions import get_job_definitions, get_job_by_id
from app.models.job import JobInfo, JobRun, JobStatus
from app.repositories.job_history import job_history_repo

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# Response Models
# ==============================================================================

class JobListResponse(BaseModel):
    """List of jobs response."""
    jobs: List[dict]
    total: int


class JobDetailResponse(BaseModel):
    """Job detail response."""
    id: str
    name: str
    description: Optional[str]
    trigger_type: str
    trigger_args: dict
    next_run_time: Optional[str]
    enabled: bool
    tags: List[str]
    history: List[JobRun]


class JobActionResponse(BaseModel):
    """Job action response."""
    success: bool
    message: str
    job_id: str


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get("/", response_model=JobListResponse)
def list_jobs(
    tag: Optional[str] = Query(None, description="Filter by tag"),
    enabled_only: bool = Query(False, description="Show only enabled jobs")
):
    """List all scheduled jobs."""
    try:
        definitions = get_job_definitions()
        scheduled_jobs = {j['id']: j for j in scheduler_service.get_jobs()}
        
        jobs = []
        for job_def in definitions:
            # Filter by tag
            if tag and tag not in job_def.tags:
                continue
            
            # Filter by enabled
            if enabled_only and not job_def.enabled:
                continue
            
            scheduled = scheduled_jobs.get(job_def.id, {})
            
            jobs.append({
                'id': job_def.id,
                'name': job_def.name,
                'description': job_def.description,
                'trigger_type': job_def.trigger_type.value,
                'next_run_time': scheduled.get('next_run_time'),
                'enabled': job_def.enabled,
                'tags': job_def.tags
            })
        
        return JobListResponse(jobs=jobs, total=len(jobs))
    except Exception as e:
        logger.exception("Failed to list jobs")
        raise HTTPException(status_code=500, detail="Failed to list jobs")


@router.get("/{job_id}", response_model=JobDetailResponse)
def get_job(job_id: str):
    """Get job details including execution history."""
    job_def = get_job_by_id(job_id)
    if not job_def:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    try:
        scheduled = scheduler_service.get_job(job_id) or {}
        history = scheduler_service.get_job_history(job_id, limit=20)
        
        return JobDetailResponse(
            id=job_def.id,
            name=job_def.name,
            description=job_def.description,
            trigger_type=job_def.trigger_type.value,
            trigger_args=job_def.trigger_args,
            next_run_time=scheduled.get('next_run_time'),
            enabled=job_def.enabled,
            tags=job_def.tags,
            history=history
        )
    except Exception as e:
        logger.exception(f"Failed to get job: {job_id}")
        raise HTTPException(status_code=500, detail="Failed to get job details")


@router.post("/{job_id}/run", response_model=JobActionResponse)
def run_job(job_id: str):
    """Trigger immediate job execution."""
    job_def = get_job_by_id(job_id)
    if not job_def:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    try:
        scheduler_service.run_job_now(job_id)
        return JobActionResponse(
            success=True,
            message=f"Job {job_id} triggered for immediate execution",
            job_id=job_id
        )
    except Exception as e:
        logger.exception(f"Failed to run job: {job_id}")
        raise HTTPException(status_code=500, detail="Failed to trigger job")


@router.post("/{job_id}/pause", response_model=JobActionResponse)
def pause_job(job_id: str):
    """Pause a scheduled job."""
    job_def = get_job_by_id(job_id)
    if not job_def:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    try:
        scheduler_service.pause_job(job_id)
        return JobActionResponse(
            success=True,
            message=f"Job {job_id} paused",
            job_id=job_id
        )
    except Exception as e:
        logger.exception(f"Failed to pause job: {job_id}")
        raise HTTPException(status_code=500, detail="Failed to pause job")


@router.post("/{job_id}/resume", response_model=JobActionResponse)
def resume_job(job_id: str):
    """Resume a paused job."""
    job_def = get_job_by_id(job_id)
    if not job_def:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    try:
        scheduler_service.resume_job(job_id)
        return JobActionResponse(
            success=True,
            message=f"Job {job_id} resumed",
            job_id=job_id
        )
    except Exception as e:
        logger.exception(f"Failed to resume job: {job_id}")
        raise HTTPException(status_code=500, detail="Failed to resume job")


@router.get("/{job_id}/history", response_model=List[JobRun])
def get_job_history(
    job_id: str,
    limit: int = Query(20, ge=1, le=100)
):
    """Get job execution history."""
    job_def = get_job_by_id(job_id)
    if not job_def:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    try:
        return scheduler_service.get_job_history(job_id, limit=limit)
    except Exception as e:
        logger.exception(f"Failed to get job history: {job_id}")
        raise HTTPException(status_code=500, detail="Failed to get job history")


@router.get("/tags/list")
def list_tags():
    """List all available job tags."""
    definitions = get_job_definitions()
    tags = set()
    for job_def in definitions:
        tags.update(job_def.tags)
    return {"tags": sorted(list(tags))}


@router.get("/stats/overview")
def get_jobs_stats_overview(days: int = Query(7, ge=1, le=30)):
    """Get overview statistics for all jobs."""
    try:
        definitions = get_job_definitions()
        stats = []

        for job_def in definitions:
            job_stats = job_history_repo.get_job_stats(job_def.id, days)
            if job_stats:
                stats.append({
                    "job_id": job_def.id,
                    "job_name": job_def.name,
                    "total_runs": job_stats.get('total_runs', 0),
                    "success_count": job_stats.get('success_count', 0),
                    "failed_count": job_stats.get('failed_count', 0),
                    "success_rate": (
                        job_stats.get('success_count', 0) / job_stats.get('total_runs', 1) * 100
                        if job_stats.get('total_runs', 0) > 0 else 0
                    ),
                    "avg_duration_ms": job_stats.get('avg_duration_ms'),
                    "max_duration_ms": job_stats.get('max_duration_ms'),
                })

        return {"stats": stats, "period_days": days}
    except Exception as e:
        logger.exception("Failed to get job stats")
        raise HTTPException(status_code=500, detail="Failed to get job stats")


@router.get("/history/recent-failures")
def get_recent_failures(
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200)
):
    """Get recent job failures."""
    try:
        failures = job_history_repo.get_recent_failures(hours, limit)
        return {
            "failures": [dict(f) for f in failures],
            "total": len(failures),
            "period_hours": hours
        }
    except Exception as e:
        logger.exception("Failed to get recent failures")
        raise HTTPException(status_code=500, detail="Failed to get failures")


@router.get("/{job_id}/stats")
def get_job_stats(job_id: str, days: int = Query(7, ge=1, le=30)):
    """Get statistics for a specific job."""
    job_def = get_job_by_id(job_id)
    if not job_def:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    try:
        stats = job_history_repo.get_job_stats(job_id, days)
        result = {
            "job_id": job_id,
            "job_name": job_def.name,
            "period_days": days,
        }
        if stats:
            result.update(dict(stats))
        return result
    except Exception as e:
        logger.exception(f"Failed to get stats for job: {job_id}")
        raise HTTPException(status_code=500, detail="Failed to get job stats")
