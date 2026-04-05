"""War Intel service routers."""

from app.routers.war import router as war_router
from app.routers.dps import router as dps_router
from app.routers.risk import router as risk_router
from app.routers.reports import router as reports_router
from app.routers.doctrine import router as doctrine_router
from app.routers.sovereignty import router as sovereignty_router
from app.routers.intelligence import router as intelligence_router

__all__ = ["war_router", "dps_router", "risk_router", "reports_router", "doctrine_router", "sovereignty_router", "intelligence_router"]
