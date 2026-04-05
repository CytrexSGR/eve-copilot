"""Thera route API endpoints."""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query, Request, HTTPException

from app.models.thera import (
    TheraRoute,
    TheraConnectionList,
    TheraStatus,
    TheraConnection,
)
from app.services.thera_client import EveScoutClient
from app.services.thera_cache import TheraCache
from app.services.thera_router import TheraRouter
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/route/thera", tags=["Thera Router"])


def get_thera_router(request: Request) -> TheraRouter:
    """Get TheraRouter instance with dependencies."""
    redis = request.app.state.redis.client
    cache = TheraCache(redis)
    client = EveScoutClient()
    return TheraRouter(cache, client)


@router.get(
    "/connections",
    response_model=TheraConnectionList,
    summary="Get active Thera/Turnur connections",
    description="Returns all currently active wormhole connections from Thera and/or Turnur."
)
async def get_connections(
    request: Request,
    hub: str = Query(
        "thera",
        description="Hub to query: thera, turnur, or all",
        enum=["thera", "turnur", "all"]
    ),
    ship_size: Optional[str] = Query(
        None,
        description="Filter by ship size: medium, large, xlarge, capital",
        enum=["medium", "large", "xlarge", "capital"]
    ),
) -> TheraConnectionList:
    """Get active wormhole connections."""
    thera_router = get_thera_router(request)
    connections = thera_router.get_connections(hub=hub, ship_size=ship_size)

    cache = TheraCache(request.app.state.redis.client)
    last_fetch = cache.get_last_fetch() or datetime.now(timezone.utc)

    return TheraConnectionList(
        count=len(connections),
        hub=hub,
        last_updated=last_fetch,
        connections=connections,
    )


@router.get(
    "/status",
    response_model=TheraStatus,
    summary="Get Thera service status",
    description="Returns health status of the Thera routing service."
)
async def get_status(request: Request) -> TheraStatus:
    """Get Thera service status."""
    thera_router = get_thera_router(request)
    return thera_router.get_status()


@router.get(
    "/{from_system}/{to_system}",
    response_model=TheraRoute,
    summary="Calculate optimal route via Thera",
    description="Compares direct K-Space route with Thera shortcut and recommends the best option."
)
@handle_endpoint_errors()
async def find_route(
    request: Request,
    from_system: str,
    to_system: str,
    ship_size: str = Query(
        "large",
        description="Ship size class",
        enum=["medium", "large", "xlarge", "capital"]
    ),
    hub: str = Query(
        "thera",
        description="Hub to use for shortcuts",
        enum=["thera", "turnur", "all"]
    ),
) -> TheraRoute:
    """
    Calculate optimal route, comparing direct vs Thera.

    Returns route comparison with:
    - Direct K-Space jumps
    - Thera route (if beneficial)
    - Savings in jumps and estimated time
    - Recommendation (direct or thera)
    """
    thera_router = get_thera_router(request)

    route = thera_router.find_route(
        from_system=from_system,
        to_system=to_system,
        ship_size=ship_size,
        hub=hub,
    )
    return route


@router.post(
    "/refresh",
    summary="Force refresh connections cache",
    description="Invalidates cache and fetches fresh data from EVE-Scout."
)
def refresh_connections(request: Request) -> dict:
    """Force refresh the connections cache."""
    cache = TheraCache(request.app.state.redis.client)
    cache.invalidate()

    thera_router = get_thera_router(request)
    connections = thera_router._get_connections(force_refresh=True)

    return {
        "status": "refreshed",
        "connections_count": len(connections),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
