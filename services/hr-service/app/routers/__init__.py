"""HR Service routers."""

from app.routers.red_list import router as red_list_router
from app.routers.vetting import router as vetting_router
from app.routers.roles import router as roles_router
from app.routers.activity import router as activity_router

__all__ = [
    "red_list_router",
    "vetting_router",
    "roles_router",
    "activity_router",
]
