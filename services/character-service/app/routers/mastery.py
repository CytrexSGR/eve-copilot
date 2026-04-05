"""
Ship Mastery REST API
Direct REST endpoints for ship mastery calculations.
Migrated from monolith to character-service.
"""

from fastapi import APIRouter, HTTPException, Query, Request
from typing import Optional, Dict, Any

from app.services.mastery_service import (
    handle_get_ship_mastery,
    handle_get_flyable_ships,
    handle_search_ship,
    handle_compare_ship_mastery
)

router = APIRouter()


@router.get(
    "/character/{character_id}/ship/{ship_type_id}",
    summary="Get ship mastery for character",
    description="Calculate a character's mastery level (0-4) for a specific ship."
)
def get_ship_mastery(
    request: Request,
    character_id: int,
    ship_type_id: int
) -> Dict[str, Any]:
    """
    Get mastery level for a specific character and ship combination.

    - **character_id**: EVE character ID
    - **ship_type_id**: Ship type ID (e.g., 28710 for Golem)

    Returns mastery level, missing skills, and recommendation.
    """
    result = handle_get_ship_mastery(request, {
        "character_id": character_id,
        "ship_type_id": ship_type_id
    })

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    # Parse the response text back to dict
    import ast
    text = result["content"][0]["text"]
    return ast.literal_eval(text)


@router.get(
    "/character/{character_id}/flyable",
    summary="Get flyable ships for character",
    description="List all ships a character can fly at mastery level 1 or higher."
)
def get_flyable_ships(
    request: Request,
    character_id: int,
    ship_class: Optional[str] = Query(
        None,
        description="Filter by ship class (e.g., 'Battleship', 'Marauder', 'Heavy Assault Cruiser')"
    )
) -> Dict[str, Any]:
    """
    Get all ships a character can fly effectively (mastery 1+).

    - **character_id**: EVE character ID
    - **ship_class**: Optional filter by ship class

    Returns ships grouped by class with mastery levels.
    """
    args = {"character_id": character_id}
    if ship_class:
        args["ship_class"] = ship_class

    result = handle_get_flyable_ships(request, args)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    import ast
    text = result["content"][0]["text"]
    return ast.literal_eval(text)


@router.get(
    "/search",
    summary="Search ships by name",
    description="Search for ships by name to get their type IDs."
)
def search_ship(
    request: Request,
    name: str = Query(..., description="Ship name to search for (e.g., 'Golem', 'Ishtar')")
) -> Dict[str, Any]:
    """
    Search for ships by name.

    - **name**: Ship name (partial match supported)

    Returns matching ships with type IDs.
    """
    result = handle_search_ship(request, {"ship_name": name})

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    import ast
    text = result["content"][0]["text"]
    return ast.literal_eval(text)


@router.get(
    "/compare/{ship_type_id}",
    summary="Compare mastery across all characters",
    description="Compare mastery levels for all authenticated characters on a specific ship."
)
def compare_ship_mastery(
    request: Request,
    ship_type_id: int
) -> Dict[str, Any]:
    """
    Compare all characters' mastery levels for a specific ship.

    - **ship_type_id**: Ship type ID to compare

    Returns ranked list of characters by mastery level.
    """
    result = handle_compare_ship_mastery(request, {"ship_type_id": ship_type_id})

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    import ast
    text = result["content"][0]["text"]
    return ast.literal_eval(text)


@router.get(
    "/ships/{ship_name}",
    summary="Get mastery for ship by name",
    description="Search ship and compare mastery across all characters in one call."
)
def get_mastery_by_ship_name(
    request: Request,
    ship_name: str
) -> Dict[str, Any]:
    """
    Convenience endpoint: Search ship by name and compare all characters.

    - **ship_name**: Ship name (e.g., 'Golem')

    Returns ship info and character comparisons.
    """
    # First search for the ship
    search_result = handle_search_ship(request, {"ship_name": ship_name})

    if "error" in search_result:
        raise HTTPException(status_code=404, detail=search_result["error"])

    import ast
    search_data = ast.literal_eval(search_result["content"][0]["text"])

    if not search_data.get("results"):
        raise HTTPException(status_code=404, detail=f"No ships found matching '{ship_name}'")

    # Get the first match
    ship = search_data["results"][0]
    ship_type_id = ship["typeID"]

    # Compare mastery for this ship
    compare_result = handle_compare_ship_mastery(request, {"ship_type_id": ship_type_id})

    if "error" in compare_result:
        raise HTTPException(status_code=400, detail=compare_result["error"])

    compare_data = ast.literal_eval(compare_result["content"][0]["text"])

    return {
        "search_term": ship_name,
        "matched_ship": ship,
        **compare_data
    }
