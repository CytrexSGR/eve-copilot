"""Production projects router — multi-item manufacturing project management."""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from app.services.project_service import ProjectService
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Pydantic Models ---

class ProjectCreate(BaseModel):
    creator_character_id: int
    corporation_id: Optional[int] = None
    name: str
    description: str = ""


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class ItemAdd(BaseModel):
    type_id: int
    quantity: int = 1
    me_level: int = 0
    te_level: int = 0


class ItemUpdate(BaseModel):
    quantity: Optional[int] = None
    me_level: Optional[int] = None
    te_level: Optional[int] = None
    status: Optional[str] = None


class MaterialDecision(BaseModel):
    material_type_id: int
    decision: str
    quantity: int


class DecisionsBatch(BaseModel):
    decisions: List[MaterialDecision]


# --- Project Endpoints ---

@router.get("/projects")
@handle_endpoint_errors()
def list_projects(
    request: Request,
    character_id: int = Query(..., description="Character ID"),
    corporation_id: Optional[int] = Query(default=None, description="Corporation ID"),
):
    """List all projects visible to a character (own + corporation)."""
    db = request.app.state.db
    service = ProjectService(db)
    return service.list_projects(character_id, corporation_id)


@router.post("/projects")
@handle_endpoint_errors()
def create_project(request: Request, body: ProjectCreate):
    """Create a new production project."""
    db = request.app.state.db
    service = ProjectService(db)
    return service.create_project(
        creator_character_id=body.creator_character_id,
        name=body.name,
        description=body.description,
        corporation_id=body.corporation_id,
    )


@router.get("/projects/{project_id}")
@handle_endpoint_errors()
def get_project(request: Request, project_id: int):
    """Get project detail with all items."""
    db = request.app.state.db
    service = ProjectService(db)
    project = service.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/projects/{project_id}")
@handle_endpoint_errors()
def update_project(request: Request, project_id: int, body: ProjectUpdate):
    """Update a project (name, description, status)."""
    db = request.app.state.db
    service = ProjectService(db)
    project = service.update_project(
        project_id,
        name=body.name,
        description=body.description,
        status=body.status,
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/projects/{project_id}")
@handle_endpoint_errors()
def delete_project(request: Request, project_id: int):
    """Delete a project and all its items."""
    db = request.app.state.db
    service = ProjectService(db)
    deleted = service.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"status": "deleted", "project_id": project_id}


# --- Item Endpoints ---

@router.post("/projects/{project_id}/items")
@handle_endpoint_errors()
def add_item(request: Request, project_id: int, body: ItemAdd):
    """Add an item to a project."""
    db = request.app.state.db
    service = ProjectService(db)
    item = service.add_item(
        project_id=project_id,
        type_id=body.type_id,
        quantity=body.quantity,
        me_level=body.me_level,
        te_level=body.te_level,
    )
    if not item:
        raise HTTPException(status_code=404, detail="Project not found")
    return item


@router.put("/projects/{project_id}/items/{item_id}")
@handle_endpoint_errors()
def update_item(
    request: Request, project_id: int, item_id: int, body: ItemUpdate
):
    """Update an item in a project."""
    db = request.app.state.db
    service = ProjectService(db)
    item = service.update_item(
        item_id,
        quantity=body.quantity,
        me_level=body.me_level,
        te_level=body.te_level,
        status=body.status,
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/projects/{project_id}/items/{item_id}")
@handle_endpoint_errors()
def delete_item(request: Request, project_id: int, item_id: int):
    """Delete an item from a project."""
    db = request.app.state.db
    service = ProjectService(db)
    deleted = service.delete_item(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "deleted", "item_id": item_id}


# --- Decision Endpoints ---

@router.get("/projects/items/{item_id}/decisions")
@handle_endpoint_errors()
def get_decisions(request: Request, item_id: int):
    """Get material buy/build decisions for a project item."""
    db = request.app.state.db
    service = ProjectService(db)
    return service.get_decisions(item_id)


@router.put("/projects/items/{item_id}/decisions")
@handle_endpoint_errors()
def save_decisions(request: Request, item_id: int, body: DecisionsBatch):
    """Replace all material decisions for a project item."""
    db = request.app.state.db
    service = ProjectService(db)
    decisions_dicts = [d.model_dump() for d in body.decisions]
    return service.save_decisions(item_id, decisions_dicts)


# --- Shopping List ---

@router.get("/projects/{project_id}/shopping-list")
@handle_endpoint_errors()
def get_shopping_list(request: Request, project_id: int):
    """Get aggregated shopping list of all 'buy' decisions across project items."""
    db = request.app.state.db
    service = ProjectService(db)
    return service.get_shopping_list(project_id)
