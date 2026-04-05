# copilot_server/api/ai_plans_routes.py
"""
API routes for AI Copilot plans and context.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
import asyncpg

from ..models.ai_plans import (
    CreatePlanRequest,
    UpdatePlanRequest,
    CreateMilestoneRequest,
    UpdateMilestoneRequest,
    LinkResourceRequest,
    SetContextRequest,
    CreateSummaryRequest,
    PlanResponse,
    PlanListResponse,
    MilestoneResponse,
    ResourceResponse,
    ContextResponse,
    ContextListResponse,
    SessionSummaryResponse,
    GoalType,
    PlanStatus,
    MilestoneStatus,
    TrackingType,
    ResourceType,
)
from ..db.ai_plans_repository import (
    AIPlanRepository,
    AIContextRepository,
    AISessionSummaryRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent/plans", tags=["ai-plans"])
context_router = APIRouter(prefix="/api/agent/context", tags=["ai-context"])
summary_router = APIRouter(prefix="/api/agent/session", tags=["ai-session"])

# Global pool reference (set in main.py)
db_pool: Optional[asyncpg.Pool] = None


def get_plan_repo() -> AIPlanRepository:
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return AIPlanRepository(db_pool)


def get_context_repo() -> AIContextRepository:
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return AIContextRepository(db_pool)


def get_summary_repo() -> AISessionSummaryRepository:
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return AISessionSummaryRepository(db_pool)


# ==================== PLANS ====================

@router.post("", response_model=PlanResponse)
async def create_plan(request: CreatePlanRequest):
    """Create a new plan."""
    repo = get_plan_repo()
    plan_id = await repo.create_plan(
        character_id=request.character_id,
        title=request.title,
        goal_type=request.goal_type.value,
        description=request.description,
        target_data=request.target_data,
        target_date=request.target_date,
    )
    plan = await repo.get_plan(plan_id)
    return _plan_to_response(plan)


@router.get("", response_model=PlanListResponse)
async def list_plans(
    character_id: int,
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100),
):
    """List plans for a character."""
    repo = get_plan_repo()
    plans = await repo.list_plans(character_id, status, limit)
    return PlanListResponse(
        plans=[_plan_to_response(p) for p in plans],
        total=len(plans),
    )


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: int):
    """Get a plan by ID."""
    repo = get_plan_repo()
    plan = await repo.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return _plan_to_response(plan)


@router.patch("/{plan_id}", response_model=PlanResponse)
async def update_plan(plan_id: int, request: UpdatePlanRequest):
    """Update a plan."""
    repo = get_plan_repo()

    update_data = request.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"]:
        update_data["status"] = update_data["status"].value

    success = await repo.update_plan(plan_id, **update_data)
    if not success:
        raise HTTPException(status_code=404, detail="Plan not found or no changes")

    plan = await repo.get_plan(plan_id)
    return _plan_to_response(plan)


@router.delete("/{plan_id}")
async def delete_plan(plan_id: int):
    """Delete a plan."""
    repo = get_plan_repo()
    success = await repo.delete_plan(plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"message": "Plan deleted", "plan_id": plan_id}


# ==================== MILESTONES ====================

@router.post("/{plan_id}/milestones", response_model=MilestoneResponse)
async def add_milestone(plan_id: int, request: CreateMilestoneRequest):
    """Add a milestone to a plan."""
    repo = get_plan_repo()

    # Verify plan exists
    plan = await repo.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    milestone_id = await repo.add_milestone(
        plan_id=plan_id,
        title=request.title,
        description=request.description,
        sequence_order=request.sequence_order,
        tracking_type=request.tracking_type.value if request.tracking_type else None,
        tracking_config=request.tracking_config,
        target_value=request.target_value,
    )

    # Fetch the created milestone
    plan = await repo.get_plan(plan_id)
    milestone = next((m for m in plan["milestones"] if m["id"] == milestone_id), None)
    return _milestone_to_response(milestone)


@router.patch("/{plan_id}/milestones/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(plan_id: int, milestone_id: int, request: UpdateMilestoneRequest):
    """Update a milestone."""
    repo = get_plan_repo()

    update_data = request.model_dump(exclude_unset=True)
    if "status" in update_data and update_data["status"]:
        update_data["status"] = update_data["status"].value

    success = await repo.update_milestone(milestone_id, **update_data)
    if not success:
        raise HTTPException(status_code=404, detail="Milestone not found or no changes")

    plan = await repo.get_plan(plan_id)
    milestone = next((m for m in plan["milestones"] if m["id"] == milestone_id), None)
    return _milestone_to_response(milestone)


@router.delete("/{plan_id}/milestones/{milestone_id}")
async def delete_milestone(plan_id: int, milestone_id: int):
    """Delete a milestone."""
    repo = get_plan_repo()
    success = await repo.delete_milestone(milestone_id)
    if not success:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return {"message": "Milestone deleted", "milestone_id": milestone_id}


# ==================== RESOURCES ====================

@router.post("/{plan_id}/resources", response_model=ResourceResponse)
async def link_resource(plan_id: int, request: LinkResourceRequest):
    """Link a resource to a plan."""
    repo = get_plan_repo()

    # Verify plan exists
    plan = await repo.get_plan(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    link_id = await repo.link_resource(
        plan_id=plan_id,
        resource_type=request.resource_type.value,
        resource_id=request.resource_id,
    )

    return ResourceResponse(
        id=link_id,
        plan_id=plan_id,
        resource_type=request.resource_type,
        resource_id=request.resource_id,
        created_at=plan["created_at"],  # Approximate
    )


@router.delete("/{plan_id}/resources/{resource_id}")
async def unlink_resource(plan_id: int, resource_id: int):
    """Unlink a resource from a plan."""
    repo = get_plan_repo()
    success = await repo.unlink_resource(resource_id)
    if not success:
        raise HTTPException(status_code=404, detail="Resource link not found")
    return {"message": "Resource unlinked", "resource_id": resource_id}


# ==================== CONTEXT ====================

@context_router.get("/{character_id}", response_model=ContextListResponse)
async def get_context(character_id: int):
    """Get all context for a character."""
    repo = get_context_repo()
    contexts = await repo.get_context(character_id)
    return ContextListResponse(
        contexts=[_context_to_response(c) for c in contexts]
    )


@context_router.post("/{character_id}", response_model=ContextResponse)
async def set_context(character_id: int, request: SetContextRequest):
    """Set a context value."""
    repo = get_context_repo()
    context_id = await repo.set_context(
        character_id=character_id,
        context_key=request.context_key,
        context_value=request.context_value,
        source=request.source,
        expires_at=request.expires_at,
    )

    contexts = await repo.get_context(character_id)
    context = next((c for c in contexts if c["id"] == context_id), None)
    return _context_to_response(context)


@context_router.delete("/{character_id}/{context_key}")
async def delete_context(character_id: int, context_key: str):
    """Delete a context key."""
    repo = get_context_repo()
    success = await repo.delete_context(character_id, context_key)
    if not success:
        raise HTTPException(status_code=404, detail="Context not found")
    return {"message": "Context deleted", "context_key": context_key}


# ==================== SESSION SUMMARIES ====================

@summary_router.post("/summarize", response_model=SessionSummaryResponse)
async def create_summary(request: CreateSummaryRequest):
    """Create a session summary."""
    repo = get_summary_repo()
    summary_id = await repo.create_summary(
        session_id=request.session_id,
        character_id=request.character_id,
        summary=request.summary,
        key_decisions=request.key_decisions,
        open_questions=request.open_questions,
        active_plan_ids=request.active_plan_ids,
    )

    summary = await repo.get_session_summary(request.session_id)
    return _summary_to_response(summary)


@summary_router.get("/restore/{character_id}", response_model=SessionSummaryResponse)
async def restore_context(character_id: int):
    """Get the latest session summary for context restoration."""
    repo = get_summary_repo()
    summary = await repo.get_latest_summary(character_id)
    if not summary:
        raise HTTPException(status_code=404, detail="No previous session found")
    return _summary_to_response(summary)


# ==================== HELPERS ====================

def _plan_to_response(plan: dict) -> PlanResponse:
    return PlanResponse(
        id=plan["id"],
        character_id=plan["character_id"],
        title=plan["title"],
        description=plan["description"],
        goal_type=GoalType(plan["goal_type"]),
        target_data=plan["target_data"] or {},
        target_date=plan["target_date"],
        status=PlanStatus(plan["status"]),
        progress_pct=plan["progress_pct"],
        created_at=plan["created_at"],
        updated_at=plan["updated_at"],
        completed_at=plan["completed_at"],
        milestones=[_milestone_to_response(m) for m in plan.get("milestones", [])],
        resources=[_resource_to_response(r) for r in plan.get("resources", [])],
    )


def _milestone_to_response(m: dict) -> MilestoneResponse:
    return MilestoneResponse(
        id=m["id"],
        plan_id=m["plan_id"],
        title=m["title"],
        description=m["description"],
        sequence_order=m["sequence_order"],
        tracking_type=TrackingType(m["tracking_type"]) if m["tracking_type"] else None,
        tracking_config=m["tracking_config"] or {},
        target_value=m["target_value"],
        current_value=m["current_value"] or 0,
        status=MilestoneStatus(m["status"]),
        created_at=m["created_at"],
        completed_at=m["completed_at"],
    )


def _resource_to_response(r: dict) -> ResourceResponse:
    return ResourceResponse(
        id=r["id"],
        plan_id=r["plan_id"],
        resource_type=ResourceType(r["resource_type"]),
        resource_id=r["resource_id"],
        created_at=r["created_at"],
    )


def _context_to_response(c: dict) -> ContextResponse:
    return ContextResponse(
        id=c["id"],
        character_id=c["character_id"],
        context_key=c["context_key"],
        context_value=c["context_value"],
        source=c["source"],
        confidence=float(c["confidence"]),
        created_at=c["created_at"],
        updated_at=c["updated_at"],
        expires_at=c["expires_at"],
    )


def _summary_to_response(s: dict) -> SessionSummaryResponse:
    return SessionSummaryResponse(
        id=s["id"],
        session_id=s["session_id"],
        character_id=s["character_id"],
        summary=s["summary"],
        key_decisions=s["key_decisions"] or [],
        open_questions=s["open_questions"] or [],
        active_plan_ids=s["active_plan_ids"] or [],
        created_at=s["created_at"],
    )
