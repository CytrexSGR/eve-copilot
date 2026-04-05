"""
Intelligence Router Package

Modular intelligence endpoints for alliance analysis.
"""

from fastapi import APIRouter

from .summary import router as summary_router
from .danger_activity import router as danger_router
from .economics import router as economics_router
from .combat_analysis import router as combat_router
from .equipment import router as equipment_router
from .dashboard import router as dashboard_router
from .wormhole import router as wormhole_router
from .capsuleers import router as capsuleers_router
from .alliance_insights import router as insights_router

# Alliance Insights Tab endpoints (new 4 intelligence features)
from .insights import router as alliance_insights_router

# Killmail Intelligence endpoints (threat, capital radar, logi, hunting, pilot risk)
from .threats import router as threats_router
from .capital_radar import router as capital_radar_router
from .logi_score import router as logi_score_router
from .hunting_intel import router as hunting_intel_router
from .pilot_risk import router as pilot_risk_router
from .map_intel import router as map_intel_router

# Alliance Corps Tab endpoints
from .alliance_corps import router as alliance_corps_router

# Corporation detail routers (split from corporations_detail.py)
from .corporations import (
    overview_router,
    hunting_router,
    offensive_router,
    defensive_router,
    capitals_router,
    pilots_router,
    geography_router,
    timeline_router,
)

# Alliance detail routers (Offensive, Defensive, Capitals, Geography tabs)
from .alliances import (
    offensive_router as alliance_offensive_router,
    defensive_router as alliance_defensive_router,
    capitals_router as alliance_capitals_router,
    geography_router as alliance_geography_router,
)

# Main router that includes all sub-routers
router = APIRouter()

# Include all sub-routers
router.include_router(summary_router)
router.include_router(danger_router)
router.include_router(economics_router)
router.include_router(combat_router)
router.include_router(equipment_router)
router.include_router(dashboard_router)
router.include_router(wormhole_router)
router.include_router(capsuleers_router)
router.include_router(insights_router)

# Alliance Insights Tab endpoints (4 intelligence features)
router.include_router(alliance_insights_router, prefix="/fast")

# Alliance Corps Tab endpoints (4 endpoints)
router.include_router(alliance_corps_router)

# Corporation detail routers (15 endpoints split across 8 files)
router.include_router(overview_router)
router.include_router(hunting_router)
router.include_router(offensive_router)
router.include_router(defensive_router)
router.include_router(capitals_router)
router.include_router(pilots_router)
router.include_router(geography_router)
router.include_router(timeline_router)

# Alliance detail routers (4 endpoints for Offensive, Defensive, Capitals, Geography tabs)
router.include_router(alliance_offensive_router)
router.include_router(alliance_defensive_router)
router.include_router(alliance_capitals_router)
router.include_router(alliance_geography_router)

# Killmail Intelligence endpoints
router.include_router(threats_router)
router.include_router(capital_radar_router)
router.include_router(logi_score_router)
router.include_router(hunting_intel_router)
router.include_router(pilot_risk_router)

# Map intelligence overlays (global, no entity filter)
router.include_router(map_intel_router)

__all__ = ["router"]
