"""
Battle endpoints package for War Intel API.

Split into modules:
- active: Battle listing and detail
- kills: Kill feed and ship class breakdown
- timeline: Battle timeline and reshipment analysis
- participants: Participant breakdown
- sides: Side determination with coalition consolidation
- commander_intel: Commander intel dashboard
- damage_analysis: Damage type analysis
"""

from fastapi import APIRouter

from .active import router as active_router
from .kills import router as kills_router
from .timeline import router as timeline_router
from .participants import router as participants_router
from .sides import router as sides_router
from .commander_intel import router as commander_intel_router
from .damage_analysis import router as damage_analysis_router
from .battle_context import router as battle_context_router
from .battle_dogma import router as battle_dogma_router
from .battle_loadouts import router as battle_loadouts_router

router = APIRouter()
router.include_router(active_router)
router.include_router(kills_router)
router.include_router(timeline_router)
router.include_router(participants_router)
router.include_router(sides_router)
router.include_router(commander_intel_router)
router.include_router(damage_analysis_router)
router.include_router(battle_context_router)
router.include_router(battle_dogma_router)
router.include_router(battle_loadouts_router)
