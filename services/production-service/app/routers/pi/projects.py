"""PI project CRUD, material assignments, auto-assign, and SOLL planning."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, Query

from app.services.pi.models import (
    PIProject,
    PIProjectCreate,
    PIProjectListItem,
    PIMaterialAssignment,
    PIMaterialAssignmentUpdate,
    PIMaterialAssignmentSollUpdate,
    PIProjectSollSummary,
)
from ._helpers import get_pi_repository, PISchematicService, P0_PLANET_MAP

router = APIRouter()


# ==================== Project Endpoints ====================

@router.get("/projects")
def list_projects(
    request: Request,
    character_id: Optional[int] = None,
    status: Optional[str] = None
) -> List[PIProjectListItem]:
    """List PI projects."""
    repo = get_pi_repository(request)

    if character_id:
        projects = repo.get_projects_by_character(character_id, status)
    else:
        projects = repo.get_all_projects(status)

    return [
        PIProjectListItem(
            project_id=p["project_id"],
            character_id=p["character_id"],
            character_name=p.get("character_name"),
            name=p["name"],
            target_product_type_id=p.get("target_product_type_id"),
            target_product_name=p.get("target_product_name"),
            target_tier=p.get("target_tier"),
            status=p["status"],
            created_at=p["created_at"],
            assigned_count=p.get("assigned_count", 0),
            total_materials=p.get("total_materials", 0),
        )
        for p in projects
    ]


@router.post("/projects")
def create_project(
    request: Request,
    project: PIProjectCreate
) -> PIProject:
    """Create a new PI project."""
    repo = get_pi_repository(request)

    project_id = repo.create_project(
        character_id=project.character_id,
        name=project.name,
        strategy=project.strategy,
        target_product_type_id=project.target_product_type_id,
        target_profit_per_hour=project.target_profit_per_hour,
    )

    project_data = repo.get_project(project_id)
    return PIProject(**project_data)


@router.get("/projects/{project_id}")
def get_project(
    request: Request,
    project_id: int
) -> dict:
    """Get project with full details."""
    repo = get_pi_repository(request)

    project_data = repo.get_project(project_id)
    if not project_data:
        raise HTTPException(status_code=404, detail="Project not found")

    colonies = repo.get_project_colonies(project_id)

    return {
        "project": project_data,
        "colonies": colonies
    }


@router.patch("/projects/{project_id}/status")
def update_project_status(
    request: Request,
    project_id: int,
    status: str = Query(..., description="New status: planning, active, paused, completed")
) -> dict:
    """Update project status."""
    repo = get_pi_repository(request)

    if status not in ["planning", "active", "paused", "completed"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    success = repo.update_project_status(project_id, status)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"status": "updated", "new_status": status}


@router.delete("/projects/{project_id}")
def delete_project(
    request: Request,
    project_id: int
) -> dict:
    """Delete a PI project."""
    repo = get_pi_repository(request)

    success = repo.delete_project(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"status": "deleted"}


# ==================== Material Assignment Endpoints ====================

@router.get("/projects/{project_id}/assignments")
def get_assignments(
    request: Request,
    project_id: int
) -> List[PIMaterialAssignment]:
    """Get material assignments for a project."""
    repo = get_pi_repository(request)

    # Check project exists
    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    assignments = repo.get_material_assignments(project_id)

    return [
        PIMaterialAssignment(
            id=a["id"],
            project_id=a["project_id"],
            material_type_id=a["material_type_id"],
            material_name=a.get("material_name"),
            tier=a["tier"],
            colony_id=a.get("colony_id"),
            colony_name=a.get("colony_name"),
            planet_type=a.get("planet_type"),
            status=a.get("status", "unassigned"),
            is_auto_assigned=a.get("is_auto_assigned", True),
            soll_output_per_hour=a.get("soll_output_per_hour"),
            soll_notes=a.get("soll_notes"),
        )
        for a in assignments
    ]


@router.put("/projects/{project_id}/assignments/{material_type_id}")
def update_assignment(
    request: Request,
    project_id: int,
    material_type_id: int,
    update: PIMaterialAssignmentUpdate
) -> dict:
    """Update a material assignment (manual override)."""
    repo = get_pi_repository(request)

    success = repo.update_material_assignment(
        project_id=project_id,
        material_type_id=material_type_id,
        colony_id=update.colony_id
    )

    if not success:
        raise HTTPException(status_code=404, detail="Assignment not found")

    return {"status": "updated"}


@router.post("/projects/{project_id}/assignments/auto")
async def auto_assign(
    request: Request,
    project_id: int
) -> List[PIMaterialAssignment]:
    """Auto-assign materials to colonies."""
    repo = get_pi_repository(request)

    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not project.get("target_product_type_id"):
        raise HTTPException(status_code=400, detail="Project has no target product")

    # Clear existing assignments
    repo.delete_project_assignments(project_id)

    # Build production chain and auto-assign
    service = PISchematicService(repo)
    target_type_id = project["target_product_type_id"]

    flat_inputs = service.get_flat_inputs(target_type_id, quantity=1.0)
    chain_node = service.get_production_chain(target_type_id)

    all_materials = []
    if chain_node:
        all_materials.append({
            "type_id": chain_node.type_id,
            "type_name": chain_node.type_name,
            "tier": chain_node.tier
        })

    for mat in flat_inputs:
        all_materials.append({
            "type_id": mat["type_id"],
            "type_name": mat["type_name"],
            "tier": mat.get("tier", 0)
        })

    colonies = repo.get_project_colonies(project_id)

    tier_colony_map = {}

    for material in all_materials:
        type_id = material["type_id"]
        type_name = material["type_name"]
        tier = material["tier"]

        colony_id = None

        if tier in tier_colony_map and tier > 0:
            colony_id = tier_colony_map[tier]
        elif tier == 0 and colonies:
            valid_planets = P0_PLANET_MAP.get(type_name, [])
            for colony in colonies:
                planet_type = colony.get("planet_type", "").lower()
                if planet_type in valid_planets:
                    colony_id = colony["id"]
                    break
        elif colonies:
            best_colony = max(colonies, key=lambda c: c.get("upgrade_level", 0) or 0, default=None)
            if best_colony:
                colony_id = best_colony["id"]

        repo.upsert_material_assignment(
            project_id=project_id,
            material_type_id=type_id,
            tier=tier,
            colony_id=colony_id,
            is_auto_assigned=True
        )

        if colony_id and tier not in tier_colony_map:
            tier_colony_map[tier] = colony_id

    return await get_assignments(request, project_id)


# ==================== SOLL Planning Endpoints ====================

@router.patch("/projects/{project_id}/assignments/{material_type_id}/soll")
def update_soll(
    request: Request,
    project_id: int,
    material_type_id: int,
    update: PIMaterialAssignmentSollUpdate
) -> dict:
    """Update SOLL planning values for a material."""
    repo = get_pi_repository(request)

    success = repo.update_material_soll(
        project_id=project_id,
        material_type_id=material_type_id,
        soll_output_per_hour=update.soll_output_per_hour,
        soll_notes=update.soll_notes
    )

    if not success:
        raise HTTPException(status_code=404, detail="Assignment not found")

    return {"status": "updated"}


@router.get("/projects/{project_id}/soll-summary")
def get_soll_summary(
    request: Request,
    project_id: int
) -> PIProjectSollSummary:
    """Get SOLL vs IST summary for a project."""
    repo = get_pi_repository(request)

    project = repo.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    summary = repo.get_project_soll_summary(project_id)

    total_soll = float(summary['total_soll'] or 0)
    total_ist = float(summary['total_ist'] or 0)

    if total_soll > 0:
        overall_variance = ((total_ist - total_soll) / total_soll) * 100
    else:
        overall_variance = 0.0

    return PIProjectSollSummary(
        project_id=project_id,
        total_soll_output=total_soll,
        total_ist_output=total_ist,
        overall_variance_percent=round(overall_variance, 1),
        materials_on_target=summary['on_target'] or 0,
        materials_under_target=summary['under_target'] or 0,
        materials_over_target=summary['over_target'] or 0,
        materials_no_soll=summary['no_soll'] or 0,
    )
