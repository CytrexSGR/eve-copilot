"""
Production Tax and Facility Profile router.

Endpoints for managing tax profiles, facility profiles, and system cost indices
used in production cost calculations.
"""

import logging
from fastapi import APIRouter, HTTPException, Query, Request, Response
from typing import Optional, List

from app.models.tax import (
    TaxProfile,
    TaxProfileCreate,
    TaxProfileUpdate,
    FacilityProfile,
    FacilityProfileCreate,
    FacilityProfileUpdate,
    SystemCostIndex,
)
from app.services.tax_repository import (
    TaxRepository,
    FacilityRepository,
    SystemCostIndexRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Tax Profile Endpoints
# =============================================================================

@router.get("/tax-profiles", response_model=List[TaxProfile])
def get_tax_profiles(
    request: Request,
    character_id: Optional[int] = Query(None, description="Filter by character ID")
) -> List[TaxProfile]:
    """Get all tax profiles.

    If character_id is provided, returns profiles for that character plus global profiles.
    If not provided, returns only global profiles (where character_id IS NULL).
    """
    db = request.app.state.db
    repo = TaxRepository(db)
    return repo.get_all(character_id=character_id)


@router.post("/tax-profiles", response_model=TaxProfile, status_code=201)
def create_tax_profile(
    request: Request,
    data: TaxProfileCreate
) -> TaxProfile:
    """Create a new tax profile.

    If is_default is True, all other profiles will have is_default set to False.
    """
    db = request.app.state.db
    repo = TaxRepository(db)
    return repo.create(data)


@router.get("/tax-profiles/default", response_model=TaxProfile)
def get_default_tax_profile(
    request: Request,
    character_id: Optional[int] = Query(None, description="Get character-specific default, falling back to global")
) -> TaxProfile:
    """Get the default tax profile.

    If character_id is provided, returns that character's default profile first,
    then falls back to the global default if no character-specific default exists.
    """
    db = request.app.state.db
    repo = TaxRepository(db)
    profile = repo.get_default(character_id=character_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="No default tax profile found")
    return profile


@router.get("/tax-profiles/{profile_id}", response_model=TaxProfile)
def get_tax_profile(
    request: Request,
    profile_id: int
) -> TaxProfile:
    """Get a tax profile by ID."""
    db = request.app.state.db
    repo = TaxRepository(db)
    profile = repo.get_by_id(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Tax profile {profile_id} not found")
    return profile


@router.patch("/tax-profiles/{profile_id}", response_model=TaxProfile)
def update_tax_profile(
    request: Request,
    profile_id: int,
    data: TaxProfileUpdate
) -> TaxProfile:
    """Update a tax profile.

    Only provided fields are updated. If is_default is set to True,
    all other profiles will have is_default set to False.
    """
    db = request.app.state.db
    repo = TaxRepository(db)
    profile = repo.update(profile_id, data)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Tax profile {profile_id} not found")
    return profile


@router.delete("/tax-profiles/{profile_id}", status_code=204)
def delete_tax_profile(
    request: Request,
    profile_id: int
) -> Response:
    """Delete a tax profile."""
    db = request.app.state.db
    repo = TaxRepository(db)
    deleted = repo.delete(profile_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Tax profile {profile_id} not found")
    return Response(status_code=204)


# =============================================================================
# Facility Profile Endpoints
# =============================================================================

@router.get("/facilities", response_model=List[FacilityProfile])
def get_facilities(request: Request) -> List[FacilityProfile]:
    """Get all facility profiles."""
    db = request.app.state.db
    repo = FacilityRepository(db)
    return repo.get_all()


@router.post("/facilities", response_model=FacilityProfile, status_code=201)
def create_facility(
    request: Request,
    data: FacilityProfileCreate
) -> FacilityProfile:
    """Create a new facility profile."""
    db = request.app.state.db
    repo = FacilityRepository(db)
    return repo.create(data)


@router.get("/facilities/{facility_id}", response_model=FacilityProfile)
def get_facility(
    request: Request,
    facility_id: int
) -> FacilityProfile:
    """Get a facility profile by ID."""
    db = request.app.state.db
    repo = FacilityRepository(db)
    facility = repo.get_by_id(facility_id)
    if facility is None:
        raise HTTPException(status_code=404, detail=f"Facility {facility_id} not found")
    return facility


@router.patch("/facilities/{facility_id}", response_model=FacilityProfile)
def update_facility(
    request: Request,
    facility_id: int,
    data: FacilityProfileUpdate
) -> FacilityProfile:
    """Update a facility profile.

    Only provided fields are updated.
    """
    db = request.app.state.db
    repo = FacilityRepository(db)
    facility = repo.update(facility_id, data)
    if facility is None:
        raise HTTPException(status_code=404, detail=f"Facility {facility_id} not found")
    return facility


@router.delete("/facilities/{facility_id}", status_code=204)
def delete_facility(
    request: Request,
    facility_id: int
) -> Response:
    """Delete a facility profile."""
    db = request.app.state.db
    repo = FacilityRepository(db)
    deleted = repo.delete(facility_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Facility {facility_id} not found")
    return Response(status_code=204)


# =============================================================================
# System Cost Index Endpoints
# =============================================================================

@router.get("/system-cost-index/{system_id}", response_model=SystemCostIndex)
def get_system_cost_index(
    request: Request,
    system_id: int
) -> SystemCostIndex:
    """Get the cost indices for a specific solar system.

    Returns cached cost indices from ESI. If the system has no cached data,
    returns 404.
    """
    try:
        db = request.app.state.db
        repo = SystemCostIndexRepository(db)
        index = repo.get_by_system(system_id)
        if index is None:
            raise HTTPException(
                status_code=404,
                detail=f"Cost indices for system {system_id} not found"
            )
        return index
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching system cost index for {system_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching system cost index: {str(e)}"
        )
