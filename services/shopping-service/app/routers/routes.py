"""Shopping routes and orders router."""
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Query
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.models import ShoppingRoute, OrderSnapshots
from app.services import ShoppingService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/route")
@handle_endpoint_errors()
def calculate_shopping_route(
    request: Request,
    regions: str = Query(..., description="Comma-separated region keys (e.g., 'the_forge,domain')"),
    home_system: str = Query(default='isikemi', description="Starting system"),
    include_systems: bool = Query(default=True, description="Include system names for each leg"),
    return_home: bool = Query(default=True, description="Include return trip to home system")
) -> ShoppingRoute:
    """
    Calculate optimal travel route through multiple trade hubs.

    Returns the best order to visit hubs to minimize total jumps.
    Optionally includes return trip to home system.
    """
    try:
        db = request.app.state.db
        service = ShoppingService(db)

        # Parse regions
        region_list = [r.strip() for r in regions.split(',') if r.strip()]

        if not region_list:
            return ShoppingRoute(
                home_system=home_system,
                total_jumps=0,
                stops=[],
                return_home=return_home,
                total_cost=0.0
            )

        return service.calculate_shopping_route(
            region_list,
            home_system=home_system,
            include_systems=include_systems,
            return_home=return_home
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to calculate route: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders/{type_id}")
@handle_endpoint_errors()
def get_order_snapshots(
    request: Request,
    type_id: int,
    region: Optional[str] = Query(default=None, description="Region key (e.g., 'the_forge')")
) -> OrderSnapshots:
    """
    Get top order snapshots for an item.

    Returns top 10 sell and buy orders per region.
    """
    try:
        db = request.app.state.db
        service = ShoppingService(db)
        return service.get_order_snapshots(type_id, region)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get orders for type {type_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
