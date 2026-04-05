"""War Economy Router Package."""

from fastapi import APIRouter

from .hot_items import router as hot_items_router
from .warzone_routes import router as warzone_routes_router
from .fuel_trends import router as fuel_trends_router
from .manipulation import router as manipulation_router
from .supercap_timers import router as supercap_timers_router
from .capital_intel import router as capital_intel_router
from .overview import router as overview_router

router = APIRouter()

router.include_router(hot_items_router)
router.include_router(warzone_routes_router)
router.include_router(fuel_trends_router)
router.include_router(manipulation_router)
router.include_router(supercap_timers_router)
router.include_router(capital_intel_router)
router.include_router(overview_router)

__all__ = ["router"]
