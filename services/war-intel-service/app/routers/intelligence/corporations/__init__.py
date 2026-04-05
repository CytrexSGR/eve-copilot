"""Corporation Intelligence Router Package."""

from .overview import router as overview_router
from .hunting import router as hunting_router
from .offensive import router as offensive_router
from .defensive import router as defensive_router
from .capitals import router as capitals_router
from .pilots import router as pilots_router
from .geography import router as geography_router
from .timeline import router as timeline_router

__all__ = [
    "overview_router",
    "hunting_router",
    "offensive_router",
    "defensive_router",
    "capitals_router",
    "pilots_router",
    "geography_router",
    "timeline_router",
]
