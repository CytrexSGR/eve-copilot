"""
War Intel API Router Package.

This package provides modular endpoints for the War Intel service, split into:
- battles: Battle tracking and analysis endpoints
- systems: Solar system intelligence endpoints
- statistics: War summaries, heatmaps, and analytics
- map: Map and navigation endpoints
- alerts: War alerts and Telegram notifications
- live: Real-time combat intelligence
- items: Item combat statistics
- conflicts: Coalition conflict aggregation

All sub-routers are combined into a single router with the /war prefix.
"""

from fastapi import APIRouter

from .battles import router as battles_router
from .systems import router as systems_router
from .statistics import router as statistics_router
from .map import router as map_router
from .alerts import router as alerts_router
from .live import router as live_router
from .items import router as items_router
from .conflicts import router as conflicts_router
from .top_killers import router as top_killers_router

# Create main router
router = APIRouter()

# Include all sub-routers
router.include_router(battles_router, tags=["battles"])
router.include_router(systems_router, tags=["systems"])
router.include_router(statistics_router, tags=["statistics"])
router.include_router(map_router, tags=["map"])
router.include_router(alerts_router, tags=["alerts"])
router.include_router(live_router, tags=["live"])
router.include_router(items_router, tags=["items"])
router.include_router(conflicts_router, tags=["conflicts"])
router.include_router(top_killers_router, tags=["news"])

# Export the main router
__all__ = ["router"]
