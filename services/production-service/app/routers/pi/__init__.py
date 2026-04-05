"""PI router package -- split from monolithic pi.py."""
from fastapi import APIRouter

from .formulas import router as formulas_router
from .profitability import router as profitability_router
from .empire import router as empire_router
from .colonies import router as colonies_router
from .projects import router as projects_router
from .recommendations import router as recommendations_router
from .alerts import router as alerts_router
from .multi_character import router as multi_character_router
from .advisor import router as advisor_router
from .chain_planner import router as chain_planner_router

router = APIRouter(prefix="/api/pi", tags=["Planetary Industry"])

router.include_router(formulas_router)
router.include_router(profitability_router)
router.include_router(empire_router)
router.include_router(colonies_router)
router.include_router(projects_router)
router.include_router(recommendations_router)
router.include_router(alerts_router)
router.include_router(multi_character_router)
router.include_router(advisor_router)
router.include_router(chain_planner_router)
