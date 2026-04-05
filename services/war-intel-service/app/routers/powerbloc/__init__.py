"""Power Bloc Detail Router Package."""

from fastapi import APIRouter

from .hunting import router as hunting_router
from .details import router as details_router
from .offensive import router as offensive_router
from .defensive import router as defensive_router
from .capitals import router as capitals_router
from .wormhole import router as wormhole_router
from .capsuleers import router as capsuleers_router
from .pilot_intel import router as pilot_intel_router
from .geography import router as geography_router
from .alliances_ranking import router as alliances_ranking_router
from .alliances_trends import router as alliances_trends_router
from .alliances_ships import router as alliances_ships_router
from .alliances_regions import router as alliances_regions_router
from .victim_tank import router as victim_tank_router

router = APIRouter()

router.include_router(hunting_router)
router.include_router(details_router)
router.include_router(offensive_router)
router.include_router(defensive_router)
router.include_router(capitals_router)
router.include_router(wormhole_router)
router.include_router(capsuleers_router)
router.include_router(pilot_intel_router)
router.include_router(geography_router)
router.include_router(alliances_ranking_router)
router.include_router(alliances_trends_router)
router.include_router(alliances_ships_router)
router.include_router(alliances_regions_router)
router.include_router(victim_tank_router)

__all__ = ["router"]
