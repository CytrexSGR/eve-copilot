"""PI formula and chain endpoints."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, Query

from app.services.pi.models import PISchematic, PIChainNode
from ._helpers import get_pi_repository, PISchematicService

router = APIRouter()


# ==================== Formula Endpoints ====================

@router.get("/formulas")
def list_formulas(
    request: Request,
    tier: Optional[int] = Query(None, ge=1, le=4, description="Filter by tier (1-4)")
) -> List[PISchematic]:
    """List all PI schematics (formulas) with inputs."""
    repo = get_pi_repository(request)
    return repo.get_all_schematics(tier=tier)


@router.get("/formulas/search")
def search_formulas(
    request: Request,
    q: str = Query(..., min_length=1, description="Search term"),
    limit: int = Query(50, ge=1, le=200)
) -> List[PISchematic]:
    """Search PI schematics by name."""
    repo = get_pi_repository(request)
    return repo.search_schematics(q, limit=limit)


@router.get("/formulas/{schematic_id}")
def get_formula(request: Request, schematic_id: int) -> PISchematic:
    """Get a specific PI schematic by ID."""
    repo = get_pi_repository(request)
    schematic = repo.get_schematic(schematic_id)
    if not schematic:
        raise HTTPException(status_code=404, detail="Schematic not found")
    return schematic


# ==================== Chain Endpoints ====================

@router.get("/chain/{type_id}")
def get_production_chain(
    request: Request,
    type_id: int,
    quantity: float = Query(1.0, ge=0.1, description="Output quantity")
) -> PIChainNode:
    """Get full production chain tree from P0 to target product."""
    repo = get_pi_repository(request)
    service = PISchematicService(repo)

    chain = service.get_production_chain(type_id, quantity)
    if not chain:
        raise HTTPException(status_code=404, detail="Not a PI product or no schematic found")
    return chain


@router.get("/chain/{type_id}/inputs")
def get_flat_inputs(
    request: Request,
    type_id: int,
    quantity: float = Query(1.0, ge=0.1)
) -> List[dict]:
    """Get flat list of P0 raw materials needed for a PI product."""
    repo = get_pi_repository(request)
    service = PISchematicService(repo)

    inputs = service.get_flat_inputs(type_id, quantity)
    if not inputs:
        raise HTTPException(status_code=404, detail="Not a PI product")
    return inputs
