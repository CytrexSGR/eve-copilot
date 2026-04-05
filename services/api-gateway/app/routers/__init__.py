"""API Gateway routers."""
from app.routers.health import router as health_router
from app.routers.dashboard import router as dashboard_router

__all__ = ["health_router", "dashboard_router"]
