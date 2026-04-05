"""Shopping service routers."""
from app.routers.lists import router as lists_router
from app.routers.items import router as items_router
from app.routers.wizard import router as wizard_router
from app.routers.transport import router as transport_router
from app.routers.routes import router as routes_router
from app.routers.freight import router as freight_router

__all__ = ["lists_router", "items_router", "wizard_router", "transport_router", "routes_router", "freight_router"]
