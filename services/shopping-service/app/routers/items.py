"""Shopping items router."""
import logging
from typing import List

from fastapi import APIRouter, HTTPException, Request
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.models import (
    ShoppingItem, ShoppingItemCreate, ShoppingItemUpdate,
    ShoppingItemWithMaterials, BuildDecision
)
from app.services import ShoppingService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/lists/{list_id}/items")
@handle_endpoint_errors()
def create_item(
    request: Request,
    list_id: int,
    data: ShoppingItemCreate
) -> ShoppingItem:
    """Add an item to a shopping list."""
    try:
        db = request.app.state.db
        service = ShoppingService(db)

        # Verify list exists
        shopping_list = service.get_list(list_id)
        if not shopping_list:
            raise HTTPException(status_code=404, detail="List not found")

        return service.create_item(list_id, data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/items/{item_id}")
@handle_endpoint_errors()
def get_item(
    request: Request,
    item_id: int
) -> ShoppingItem:
    """Get a shopping item by ID."""
    try:
        db = request.app.state.db
        service = ShoppingService(db)
        result = service.get_item(item_id)
        if not result:
            raise HTTPException(status_code=404, detail="Item not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get item {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/items/{item_id}")
@handle_endpoint_errors()
def update_item(
    request: Request,
    item_id: int,
    data: ShoppingItemUpdate
) -> ShoppingItem:
    """Update a shopping item."""
    try:
        db = request.app.state.db
        service = ShoppingService(db)
        result = service.update_item(item_id, data)
        if not result:
            raise HTTPException(status_code=404, detail="Item not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update item {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/items/{item_id}")
@handle_endpoint_errors()
def delete_item(
    request: Request,
    item_id: int
) -> dict:
    """Delete a shopping item."""
    try:
        db = request.app.state.db
        service = ShoppingService(db)
        success = service.delete_item(item_id)
        if not success:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"deleted": True, "item_id": item_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete item {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/items/{item_id}/purchased")
@handle_endpoint_errors()
def mark_purchased(
    request: Request,
    item_id: int
) -> ShoppingItem:
    """Mark an item as purchased."""
    try:
        db = request.app.state.db
        service = ShoppingService(db)
        result = service.mark_purchased(item_id, True)
        if not result:
            raise HTTPException(status_code=404, detail="Item not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark item {item_id} purchased: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/items/{item_id}/purchased")
@handle_endpoint_errors()
def unmark_purchased(
    request: Request,
    item_id: int
) -> ShoppingItem:
    """Unmark an item as purchased."""
    try:
        db = request.app.state.db
        service = ShoppingService(db)
        result = service.mark_purchased(item_id, False)
        if not result:
            raise HTTPException(status_code=404, detail="Item not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unmark item {item_id} purchased: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/items/{item_id}/build-decision")
@handle_endpoint_errors()
def set_build_decision(
    request: Request,
    item_id: int,
    decision: BuildDecision
) -> ShoppingItem:
    """Set build or buy decision for an item."""
    try:
        db = request.app.state.db
        service = ShoppingService(db)
        result = service.update_item(
            item_id,
            ShoppingItemUpdate(build_decision=decision)
        )
        if not result:
            raise HTTPException(status_code=404, detail="Item not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set build decision for {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/items/{item_id}/with-materials")
@handle_endpoint_errors()
def get_item_with_materials(
    request: Request,
    item_id: int
) -> ShoppingItemWithMaterials:
    """Get a product item with its material requirements."""
    try:
        db = request.app.state.db
        service = ShoppingService(db)
        result = service.get_item_with_materials(item_id)
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Item not found or is not a product"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get materials for {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/items/{item_id}/calculate-materials")
@handle_endpoint_errors()
def calculate_materials(
    request: Request,
    item_id: int,
    include_sub_products: bool = False
) -> dict:
    """Calculate material requirements for a product."""
    try:
        db = request.app.state.db
        service = ShoppingService(db)
        result = service.calculate_materials(item_id, include_sub_products)
        if not result:
            raise HTTPException(status_code=404, detail="Item not found")
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to calculate materials for {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/items/{item_id}/apply-materials")
@handle_endpoint_errors()
def apply_materials(
    request: Request,
    item_id: int
) -> List[ShoppingItem]:
    """Add calculated materials to the shopping list."""
    try:
        db = request.app.state.db
        service = ShoppingService(db)
        result = service.apply_materials_to_list(item_id)
        if not result:
            raise HTTPException(
                status_code=400,
                detail="No materials found or item is not a product"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to apply materials for {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
