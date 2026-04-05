"""Shopping lists router."""
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import PlainTextResponse

from app.models import (
    ShoppingList, ShoppingListCreate, ShoppingListUpdate,
    ShoppingItem, RegionalComparison,
    ItemsByRegionResponse, ApplyAssetsResponse,
    ListWithAssetsResponse, ProductionMaterialsResponse
)
from app.services import ShoppingService
from app.services.shopping import fetch_doctrine_bom
from eve_shared.utils.error_handling import handle_endpoint_errors

router = APIRouter()


@router.get("/lists")
@handle_endpoint_errors()
def get_lists(
    request: Request,
    character_id: Optional[int] = Query(None, description="Filter by character")
) -> List[ShoppingList]:
    """Get all shopping lists."""
    db = request.app.state.db
    service = ShoppingService(db)
    return service.get_lists(character_id)


@router.post("/lists")
@handle_endpoint_errors()
def create_list(
    request: Request,
    data: ShoppingListCreate
) -> ShoppingList:
    """Create a new shopping list."""
    db = request.app.state.db
    service = ShoppingService(db)
    return service.create_list(data)


@router.get("/lists/{list_id}")
@handle_endpoint_errors()
def get_list(
    request: Request,
    list_id: int
) -> ShoppingList:
    """Get a shopping list by ID."""
    db = request.app.state.db
    service = ShoppingService(db)
    result = service.get_list(list_id)
    if not result:
        raise HTTPException(status_code=404, detail="List not found")
    return result


@router.patch("/lists/{list_id}")
@handle_endpoint_errors()
def update_list(
    request: Request,
    list_id: int,
    data: ShoppingListUpdate
) -> ShoppingList:
    """Update a shopping list."""
    db = request.app.state.db
    service = ShoppingService(db)
    result = service.update_list(list_id, data)
    if not result:
        raise HTTPException(status_code=404, detail="List not found")
    return result


@router.delete("/lists/{list_id}")
@handle_endpoint_errors()
def delete_list(
    request: Request,
    list_id: int
) -> dict:
    """Delete a shopping list."""
    db = request.app.state.db
    service = ShoppingService(db)
    success = service.delete_list(list_id)
    if not success:
        raise HTTPException(status_code=404, detail="List not found")
    return {"deleted": True, "list_id": list_id}


@router.get("/lists/{list_id}/items")
@handle_endpoint_errors()
def get_list_items(
    request: Request,
    list_id: int
) -> List[ShoppingItem]:
    """Get all items in a shopping list."""
    db = request.app.state.db
    service = ShoppingService(db)

    # Verify list exists
    shopping_list = service.get_list(list_id)
    if not shopping_list:
        raise HTTPException(status_code=404, detail="List not found")

    return service.get_items(list_id)


@router.get("/lists/{list_id}/regional-comparison")
@handle_endpoint_errors()
def get_regional_comparison(
    request: Request,
    list_id: int
) -> RegionalComparison:
    """Compare shopping list prices across regions."""
    db = request.app.state.db
    service = ShoppingService(db)
    result = service.get_regional_comparison(list_id)
    if not result:
        raise HTTPException(status_code=404, detail="List not found")
    return result


@router.get("/lists/{list_id}/export")
@handle_endpoint_errors()
def export_list(
    request: Request,
    list_id: int,
    format: str = Query(default="eve", regex="^(eve|csv)$")
) -> PlainTextResponse:
    """Export shopping list to EVE multibuy or CSV format."""
    db = request.app.state.db
    service = ShoppingService(db)
    result = service.export_list(list_id, format)
    if result is None:
        raise HTTPException(status_code=404, detail="List not found or empty")

    content_type = "text/csv" if format == "csv" else "text/plain"
    return PlainTextResponse(content=result, media_type=content_type)


@router.get("/lists/{list_id}/by-region")
@handle_endpoint_errors()
def get_items_by_region(
    request: Request,
    list_id: int
) -> ItemsByRegionResponse:
    """Get shopping list items grouped by target region."""
    db = request.app.state.db
    service = ShoppingService(db)
    result = service.get_items_by_region(list_id)
    if not result:
        raise HTTPException(status_code=404, detail="List not found")
    return result


@router.post("/lists/{list_id}/add-production/{type_id}")
@handle_endpoint_errors()
def add_production_materials(
    request: Request,
    list_id: int,
    type_id: int,
    me: int = Query(default=10, ge=0, le=10, description="Material efficiency level"),
    runs: int = Query(default=1, ge=1, le=1000, description="Number of runs")
) -> ProductionMaterialsResponse:
    """Add all materials for producing an item to the shopping list."""
    db = request.app.state.db
    service = ShoppingService(db)
    result = service.add_production_materials(list_id, type_id, me, runs)
    if not result:
        raise HTTPException(
            status_code=404,
            detail="List not found or no blueprint found for this item"
        )
    return result


@router.post("/lists/{list_id}/apply-assets")
@handle_endpoint_errors()
def apply_assets(
    request: Request,
    list_id: int,
    character_id: int = Query(..., description="Character ID to check assets for")
) -> ApplyAssetsResponse:
    """
    Apply character assets to shopping list items.

    Matches shopping list items against character's cached assets and
    updates quantity_in_assets for each item.
    """
    db = request.app.state.db
    service = ShoppingService(db)
    result = service.apply_assets_to_list(list_id, character_id)
    if not result:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return result


@router.get("/lists/{list_id}/with-assets")
@handle_endpoint_errors()
def get_list_with_assets(
    request: Request,
    list_id: int
) -> ListWithAssetsResponse:
    """
    Get list with quantity_in_assets and quantity_to_buy calculated.

    Returns the shopping list with each item including:
    - quantity_needed (original quantity)
    - quantity_in_assets (from cached character assets)
    - quantity_to_buy (quantity_needed - quantity_in_assets)
    """
    db = request.app.state.db
    service = ShoppingService(db)
    result = service.get_list_with_assets(list_id)
    if not result:
        raise HTTPException(status_code=404, detail="Shopping list not found")
    return result


@router.post("/lists/{list_id}/add-doctrine/{doctrine_id}")
@handle_endpoint_errors()
def add_doctrine_to_list(
    request: Request,
    list_id: int,
    doctrine_id: int,
    quantity: int = Query(1, ge=1, le=100, description="Number of doctrine fits to add"),
) -> List[ShoppingItem]:
    """Add a doctrine BOM (Bill of Materials) to a shopping list.

    Fetches the BOM from character-service, then adds each item to the list.
    """
    db = request.app.state.db
    service = ShoppingService(db)

    # Verify list exists
    shopping_list = service.get_list(list_id)
    if not shopping_list:
        raise HTTPException(status_code=404, detail="Shopping list not found")

    # Fetch BOM from character-service
    bom = fetch_doctrine_bom(doctrine_id, quantity=quantity)
    if bom is None:
        raise HTTPException(
            status_code=502,
            detail="Failed to fetch doctrine BOM from character-service",
        )
    if not bom:
        raise HTTPException(
            status_code=404,
            detail="Doctrine BOM is empty or doctrine not found",
        )

    return service.add_bom_items(list_id, bom)
