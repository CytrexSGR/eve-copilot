"""PI Chain Planner — graph-based production chain management.

Endpoints for plan CRUD, target addition (auto-generates chain DAG),
node assignment (character + planet), and IST/SOLL status comparison.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Request, Query, HTTPException
from pydantic import BaseModel

from app.routers.pi._helpers import get_pi_repository, PISchematicService
from app.services.pi.chain_planner import ChainPlannerService
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request Models ────────────────────────────────────────

class PlanCreate(BaseModel):
    name: str


class PlanStatusUpdate(BaseModel):
    status: str


class TargetAdd(BaseModel):
    type_id: int
    quantity_per_hour: float = 1.0


class NodeAssign(BaseModel):
    character_id: Optional[int] = None
    planet_id: Optional[int] = None


# ── Plan CRUD ─────────────────────────────────────────────

@router.post("/plans")
@handle_endpoint_errors()
def create_plan(request: Request, body: PlanCreate):
    """Create a new PI chain plan."""
    svc = ChainPlannerService(request.app.state.db)
    plan = svc.create_plan(body.name)
    return plan


@router.get("/plans")
@handle_endpoint_errors()
def list_plans(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """List all plans with summary counts."""
    svc = ChainPlannerService(request.app.state.db)
    return svc.list_plans(status=status)


@router.get("/plans/{plan_id}")
@handle_endpoint_errors()
def get_plan(request: Request, plan_id: int):
    """Get a plan by ID including nodes and edges."""
    svc = ChainPlannerService(request.app.state.db)
    plan = svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    return plan


@router.delete("/plans/{plan_id}")
@handle_endpoint_errors()
def delete_plan(request: Request, plan_id: int):
    """Delete a plan (cascades to nodes and edges)."""
    svc = ChainPlannerService(request.app.state.db)
    deleted = svc.delete_plan(plan_id)
    if not deleted:
        raise HTTPException(404, "Plan not found")
    return {"status": "deleted"}


@router.patch("/plans/{plan_id}/status")
@handle_endpoint_errors()
def update_plan_status(
    request: Request, plan_id: int, body: PlanStatusUpdate,
):
    """Update a plan's status."""
    svc = ChainPlannerService(request.app.state.db)
    try:
        updated = svc.update_plan_status(plan_id, body.status)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not updated:
        raise HTTPException(404, "Plan not found")
    return {"status": body.status}


# ── Target Management ─────────────────────────────────────

@router.post("/plans/{plan_id}/targets")
@handle_endpoint_errors()
def add_target(request: Request, plan_id: int, body: TargetAdd):
    """Add a target product to the plan.

    Generates the full chain tree via PISchematicService and
    creates/merges nodes + edges into the plan DAG.
    """
    # Verify plan exists
    svc = ChainPlannerService(request.app.state.db)
    plan = svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")

    repo = get_pi_repository(request)
    schematic_svc = PISchematicService(repo)
    chain = schematic_svc.get_production_chain(body.type_id, body.quantity_per_hour)
    if not chain:
        raise HTTPException(404, "Not a PI product or no schematic found")

    stats = svc.add_target(plan_id, chain)
    return stats


@router.delete("/plans/{plan_id}/targets/{type_id}")
@handle_endpoint_errors()
def remove_target(request: Request, plan_id: int, type_id: int):
    """Remove a target product. Wipes plan graph and re-adds remaining targets.

    Since remove_target wipes ALL nodes, the caller must track which targets
    remain and re-add them. The frontend should call add_target for each
    remaining target after this endpoint returns.
    """
    svc = ChainPlannerService(request.app.state.db)

    # Get current targets before wiping
    plan = svc.get_plan(plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")

    remaining_targets = [
        n for n in plan["nodes"]
        if n["is_target"] and n["type_id"] != type_id
    ]

    # Wipe all nodes/edges
    svc.remove_target(plan_id)

    # Re-add remaining targets to rebuild the graph
    if remaining_targets:
        repo = get_pi_repository(request)
        schematic_svc = PISchematicService(repo)
        for target in remaining_targets:
            chain = schematic_svc.get_production_chain(
                target["type_id"], target["soll_qty_per_hour"],
            )
            if chain:
                svc.add_target(plan_id, chain)

    return {"status": "removed", "remaining_targets": len(remaining_targets)}


# ── Node Assignment ───────────────────────────────────────

@router.patch("/plans/{plan_id}/nodes/{node_id}/assign")
@handle_endpoint_errors()
def assign_node(
    request: Request, plan_id: int, node_id: int, body: NodeAssign,
):
    """Assign a character + planet to a plan node."""
    svc = ChainPlannerService(request.app.state.db)
    result = svc.assign_node(plan_id, node_id, body.character_id, body.planet_id)
    if not result:
        raise HTTPException(404, "Node not found in this plan")
    return result


# ── Status Check ──────────────────────────────────────────

@router.get("/plans/{plan_id}/status-check")
@handle_endpoint_errors()
def status_check(request: Request, plan_id: int):
    """IST/SOLL comparison: check actual ESI colony data against planned production."""
    svc = ChainPlannerService(request.app.state.db)
    return svc.get_status_check(plan_id)
