"""Character service routers."""
from app.routers.character import router as character_router
from app.routers.corporation import router as corporation_router
from app.routers.sync import router as sync_router
from app.routers.skills import router as skills_router
from app.routers.skill_analysis import router as skill_analysis_router
from app.routers.skill_plans import router as skill_plans_router
from app.routers.mastery import router as mastery_router
from app.routers.fittings import router as fittings_router
from app.routers.research import router as research_router
from app.routers.skill_prerequisites import router as skill_prerequisites_router
from app.routers.sde_browser import router as sde_browser_router
from app.routers.doctrine_stats import router as doctrine_stats_router
from app.routers.account_summary import router as account_summary_router

__all__ = [
    "character_router",
    "corporation_router",
    "sync_router",
    "skills_router",
    "skill_analysis_router",
    "skill_plans_router",
    "mastery_router",
    "fittings_router",
    "research_router",
    "skill_prerequisites_router",
    "sde_browser_router",
    "doctrine_stats_router",
    "account_summary_router",
]
