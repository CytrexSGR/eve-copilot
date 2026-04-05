# app/routers/dogma.py
"""Dogma Engine API - Ship tank analysis and killmail fitting analysis."""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from app.services.dogma import (
    DogmaRepository,
    TankCalculatorService,
    FittingAnalyzer,
    ShipBaseStats,
    TankResult,
    KillmailAnalysis,
    FittingRequest,
)
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()

# Singleton instances
_repository: Optional[DogmaRepository] = None
_tank_calculator: Optional[TankCalculatorService] = None
_fitting_analyzer: Optional[FittingAnalyzer] = None


def _get_repository() -> DogmaRepository:
    """Get singleton repository instance."""
    global _repository
    if _repository is None:
        _repository = DogmaRepository()
    return _repository


def _get_tank_calculator() -> TankCalculatorService:
    """Get singleton tank calculator instance."""
    global _tank_calculator
    if _tank_calculator is None:
        _tank_calculator = TankCalculatorService(_get_repository())
    return _tank_calculator


def _get_fitting_analyzer() -> FittingAnalyzer:
    """Get singleton fitting analyzer instance."""
    global _fitting_analyzer
    if _fitting_analyzer is None:
        _fitting_analyzer = FittingAnalyzer(_get_repository(), _get_tank_calculator())
    return _fitting_analyzer


# =============================================================================
# Ship Base Stats
# =============================================================================

@router.get("/ship/{ship_type_id}/base", response_model=ShipBaseStats)
@handle_endpoint_errors()
def get_ship_base_stats(ship_type_id: int):
    """Get base ship stats (HP, resistances) without any modules.

    Args:
        ship_type_id: EVE type ID of the ship

    Returns:
        ShipBaseStats with base HP and resistances
    """
    repo = _get_repository()
    stats = repo.get_ship_base_stats(ship_type_id)

    if not stats:
        raise HTTPException(status_code=404, detail=f"Ship type {ship_type_id} not found")

    return stats


# =============================================================================
# Tank Calculation
# =============================================================================

@router.post("/fitting/ehp", response_model=TankResult)
@handle_endpoint_errors()
def calculate_fitting_ehp(request: FittingRequest):
    """Calculate EHP for a fitting.

    Args:
        request: FittingRequest with ship_type_id and module_type_ids

    Returns:
        TankResult with EHP calculations
    """
    from app.services.dogma.models import FittedModule

    calculator = _get_tank_calculator()

    # Convert module IDs to FittedModule objects (assume mid/low slots)
    fitted_modules = []
    for i, type_id in enumerate(request.module_type_ids):
        # Alternate between mid (19+) and low (11+) slots
        flag = 19 + (i % 8) if i % 2 == 0 else 11 + (i % 8)
        fitted_modules.append(FittedModule(
            type_id=type_id,
            flag=flag,
            quantity=1,
            was_destroyed=False
        ))

    result = calculator.calculate_tank(
        ship_type_id=request.ship_type_id,
        fitted_modules=fitted_modules,
        skill_level=request.skill_level
    )

    if not result:
        raise HTTPException(status_code=404, detail=f"Ship type {request.ship_type_id} not found")

    return result


@router.get("/ship/{ship_type_id}/ehp", response_model=TankResult)
@handle_endpoint_errors()
def get_ship_base_ehp(
    ship_type_id: int,
    modules: Optional[str] = Query(None, description="Comma-separated module type IDs"),
    skill_level: int = Query(4, ge=0, le=5, description="Assumed skill level (0-5)")
):
    """Calculate EHP for a ship with optional modules.

    Args:
        ship_type_id: EVE type ID of the ship
        modules: Comma-separated module type IDs (optional)
        skill_level: Assumed skill level (default 4)

    Returns:
        TankResult with EHP calculations
    """
    from app.services.dogma.models import FittedModule

    calculator = _get_tank_calculator()

    # Parse modules if provided
    fitted_modules = []
    if modules:
        module_ids = [int(x.strip()) for x in modules.split(',') if x.strip()]
        for i, type_id in enumerate(module_ids):
            flag = 19 + (i % 8) if i % 2 == 0 else 11 + (i % 8)
            fitted_modules.append(FittedModule(
                type_id=type_id,
                flag=flag,
                quantity=1,
                was_destroyed=False
            ))

    result = calculator.calculate_tank(
        ship_type_id=ship_type_id,
        fitted_modules=fitted_modules,
        skill_level=skill_level
    )

    if not result:
        raise HTTPException(status_code=404, detail=f"Ship type {ship_type_id} not found")

    return result


# =============================================================================
# Killmail Analysis
# =============================================================================

@router.get("/killmail/{killmail_id}/analysis", response_model=KillmailAnalysis)
@handle_endpoint_errors()
async def analyze_killmail(killmail_id: int):
    """Analyze a killmail - victim tank and attacker DPS.

    Args:
        killmail_id: Killmail ID from zKillboard/ESI

    Returns:
        KillmailAnalysis with tank and DPS breakdown
    """
    analyzer = _get_fitting_analyzer()
    result = await analyzer.analyze_killmail(killmail_id)

    if not result:
        raise HTTPException(status_code=404, detail=f"Killmail {killmail_id} not found")

    return result


@router.get("/killmail/{killmail_id}/tank", response_model=TankResult)
@handle_endpoint_errors()
async def analyze_killmail_tank(killmail_id: int):
    """Analyze only the victim's tank from a killmail.

    Args:
        killmail_id: Killmail ID

    Returns:
        TankResult with victim's EHP
    """
    analyzer = _get_fitting_analyzer()
    result = await analyzer.analyze_victim_tank(killmail_id)

    if not result:
        raise HTTPException(status_code=404, detail=f"Killmail {killmail_id} not found or has no fitting data")

    return result


# =============================================================================
# Utility Endpoints
# =============================================================================

@router.get("/type/{type_id}/name")
@handle_endpoint_errors()
def get_type_name(type_id: int):
    """Get type name for an EVE type ID.

    Args:
        type_id: EVE type ID

    Returns:
        Type name or 404
    """
    repo = _get_repository()
    name = repo.get_type_name(type_id)

    if not name:
        raise HTTPException(status_code=404, detail=f"Type {type_id} not found")

    return {"type_id": type_id, "type_name": name}


@router.get("/types/names")
@handle_endpoint_errors()
def get_type_names_bulk(
    ids: str = Query(..., description="Comma-separated type IDs")
):
    """Get type names for multiple type IDs.

    Args:
        ids: Comma-separated type IDs

    Returns:
        Dict mapping type_id to name
    """
    type_ids = [int(x.strip()) for x in ids.split(',') if x.strip()]

    if not type_ids:
        return {"types": {}}

    repo = _get_repository()
    names = repo.get_type_names_bulk(type_ids)

    return {"types": names}
