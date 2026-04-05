"""Role Synchronization - ESI roles to web permissions mapping."""

from typing import List

from fastapi import APIRouter, Request, HTTPException
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.models import RoleMapping, RoleMappingCreate, RoleSyncResult
from app.services.role_sync import RoleSyncService

router = APIRouter(prefix="/roles", tags=["Role Sync"])


def _get_service() -> RoleSyncService:
    return RoleSyncService()


@router.get("/mappings", response_model=List[RoleMapping])
@handle_endpoint_errors()
def get_role_mappings(request: Request):
    """List all ESI role to web permission mappings."""
    service = _get_service()
    return service.get_mappings()


@router.post("/mappings", response_model=RoleMapping, status_code=201)
@handle_endpoint_errors()
def create_role_mapping(request: Request, mapping: RoleMappingCreate):
    """Create a new role mapping."""
    service = _get_service()
    return service.create_mapping(mapping.model_dump())


@router.delete("/mappings/{mapping_id}", status_code=204)
@handle_endpoint_errors()
def delete_role_mapping(request: Request, mapping_id: int):
    """Delete a role mapping."""
    service = _get_service()
    if not service.delete_mapping(mapping_id):
        raise HTTPException(status_code=404, detail="Mapping not found or already inactive")


@router.post("/sync/{character_id}", response_model=RoleSyncResult)
@handle_endpoint_errors()
async def sync_character_roles(request: Request, character_id: int):
    """Sync ESI roles for a character and detect escalation."""
    service = _get_service()
    return await service.sync_character(character_id)


@router.post("/sync/all")
@handle_endpoint_errors()
async def sync_all_roles(request: Request):
    """Sync roles for all authenticated characters."""
    service = _get_service()
    return await service.sync_all()
