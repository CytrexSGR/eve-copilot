"""Freight pricing and route management router."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.services.freight import FreightService

logger = logging.getLogger(__name__)
router = APIRouter()


class FreightCalculateRequest(BaseModel):
    """Request model for freight price calculation."""
    route_id: int
    volume_m3: float
    collateral_isk: float = 0


class FreightRouteCreate(BaseModel):
    """Request model for creating a freight route."""
    name: str
    start_system_id: int
    end_system_id: int
    route_type: str = "jf"
    base_price: float = 0
    rate_per_m3: float = 0
    collateral_pct: float = 1.0
    max_volume: Optional[float] = 360000
    max_collateral: Optional[float] = 3000000000
    notes: Optional[str] = None


class FreightRouteUpdate(BaseModel):
    """Request model for updating a freight route."""
    name: Optional[str] = None
    route_type: Optional[str] = None
    base_price: Optional[float] = None
    rate_per_m3: Optional[float] = None
    collateral_pct: Optional[float] = None
    max_volume: Optional[float] = None
    max_collateral: Optional[float] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


@router.get("/freight/routes")
@handle_endpoint_errors()
def list_routes(
    request: Request,
    active_only: bool = Query(default=True, description="Only show active routes"),
) -> dict:
    """List all configured freight routes."""
    try:
        db = request.app.state.db
        service = FreightService(db)
        routes = service.list_routes(active_only)
        return {"routes": routes, "count": len(routes)}
    except Exception as e:
        logger.error(f"Failed to list freight routes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/freight/routes/search")
@handle_endpoint_errors()
def find_routes(
    request: Request,
    start_system_id: int = Query(..., description="Origin system ID"),
    end_system_id: int = Query(..., description="Destination system ID"),
) -> dict:
    """Find freight routes between two systems."""
    try:
        db = request.app.state.db
        service = FreightService(db)
        routes = service.find_routes(start_system_id, end_system_id)
        return {"routes": routes, "count": len(routes)}
    except Exception as e:
        logger.error(f"Failed to find routes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/freight/routes/{route_id}")
@handle_endpoint_errors()
def get_route(request: Request, route_id: int) -> dict:
    """Get a specific freight route."""
    db = request.app.state.db
    service = FreightService(db)
    route = service.get_route(route_id)
    if not route:
        raise HTTPException(status_code=404, detail=f"Route {route_id} not found")
    return route


@router.post("/freight/calculate")
@handle_endpoint_errors()
def calculate_freight(
    request: Request,
    body: FreightCalculateRequest,
) -> dict:
    """Calculate freight price for a shipment.

    Formula: base_price + (volume × rate_per_m3) + (collateral × collateral_pct%)
    """
    try:
        db = request.app.state.db
        service = FreightService(db)
        result = service.calculate_price(
            body.route_id, body.volume_m3, body.collateral_isk
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Route not found")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Freight calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/freight/routes", status_code=201)
@handle_endpoint_errors()
def create_route(
    request: Request,
    body: FreightRouteCreate,
) -> dict:
    """Create a new freight route."""
    try:
        db = request.app.state.db
        service = FreightService(db)
        route = service.create_route(body.model_dump())
        return route
    except Exception as e:
        logger.error(f"Failed to create freight route: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/freight/routes/{route_id}")
@handle_endpoint_errors()
def update_route(
    request: Request,
    route_id: int,
    body: FreightRouteUpdate,
) -> dict:
    """Update an existing freight route."""
    try:
        db = request.app.state.db
        service = FreightService(db)
        route = service.update_route(route_id, body.model_dump(exclude_none=True))
        if route is None:
            raise HTTPException(status_code=404, detail=f"Route {route_id} not found")
        return route
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update freight route: {e}")
        raise HTTPException(status_code=500, detail=str(e))
