"""Production chains router."""
import logging

from fastapi import APIRouter, HTTPException, Request, Query

from app.services import ProductionChainService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/chains/{type_id}")
def get_production_chain(
    request: Request,
    type_id: int,
    quantity: int = Query(default=1, ge=1),
    format: str = Query(default="tree", regex="^(tree|flat)$")
) -> dict:
    """
    Get complete production chain for an item.

    Args:
        type_id: Item type ID
        quantity: Quantity to produce
        format: Output format - 'tree' for hierarchical, 'flat' for simple list

    Returns:
        Production chain in requested format
    """
    try:
        db = request.app.state.db
        service = ProductionChainService(db)

        result = service.get_chain_tree(type_id, quantity, format)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chain for {type_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chains/{type_id}/materials")
def get_materials_list(
    request: Request,
    type_id: int,
    me: int = Query(default=0, ge=0, le=10, description="Material Efficiency (0-10)"),
    runs: int = Query(default=1, ge=1, description="Number of production runs")
) -> dict:
    """
    Get flattened material list with ME adjustments.

    Args:
        type_id: Item type ID
        me: Material Efficiency level (0-10)
        runs: Number of production runs

    Returns:
        List of materials with base and adjusted quantities
    """
    try:
        db = request.app.state.db
        service = ProductionChainService(db)

        result = service.get_materials_list(type_id, me=me, runs=runs)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get materials for {type_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/chains/{type_id}/direct")
def get_direct_dependencies(
    request: Request,
    type_id: int
) -> dict:
    """
    Get only direct material dependencies (1 level).

    Args:
        type_id: Item type ID

    Returns:
        List of direct material requirements
    """
    try:
        db = request.app.state.db
        service = ProductionChainService(db)

        result = service.get_direct_dependencies(type_id)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get direct deps for {type_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
