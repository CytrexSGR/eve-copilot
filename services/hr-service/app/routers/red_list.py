"""Red List Management - CRUD + Bloom Filter pre-check."""

from typing import List, Optional

from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import JSONResponse
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.models import RedListEntity, RedListCreateRequest, RedListBulkRequest
from app.services.red_list_checker import RedListChecker

router = APIRouter(prefix="/redlist", tags=["Red List"])


def _get_checker() -> RedListChecker:
    return RedListChecker()


@router.get("", response_model=List[RedListEntity])
@handle_endpoint_errors()
def get_red_list(
    request: Request,
    category: Optional[str] = Query(None, pattern="^(character|corporation|alliance)$"),
    active_only: bool = Query(True),
):
    """List red list entries with optional filters."""
    checker = _get_checker()
    entries = checker.get_all(category=category, active_only=active_only)
    return entries


@router.post("", response_model=RedListEntity, status_code=201)
@handle_endpoint_errors()
def add_red_list_entry(request: Request, entry: RedListCreateRequest):
    """Add a single entity to the red list."""
    checker = _get_checker()
    result = checker.add_entry(entry.model_dump())
    return result


@router.post("/bulk", status_code=201)
@handle_endpoint_errors()
def bulk_import(request: Request, bulk: RedListBulkRequest):
    """Bulk import red list entries."""
    checker = _get_checker()
    entries = [e.model_dump() for e in bulk.entities]
    imported = checker.bulk_import(entries)
    return {"imported": imported}


@router.delete("/{entry_id}", status_code=204)
@handle_endpoint_errors()
def remove_red_list_entry(request: Request, entry_id: int):
    """Deactivate a red list entry."""
    checker = _get_checker()
    if not checker.deactivate(entry_id):
        raise HTTPException(status_code=404, detail="Entry not found or already inactive")


@router.get("/check/{entity_id}")
@handle_endpoint_errors()
def check_entity(request: Request, entity_id: int):
    """Quick Bloom Filter pre-check if entity is on red list."""
    checker = _get_checker()
    return checker.check_entity(entity_id)


@router.post("/intersect")
@handle_endpoint_errors()
def intersect_contacts(request: Request, contact_ids: List[int]):
    """Database-centric intersection of contact IDs against red list."""
    checker = _get_checker()
    hits = checker.intersect_contacts(contact_ids)
    return {"hits": hits, "count": len(hits)}
