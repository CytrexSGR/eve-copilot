"""Alliance Intelligence Router Package."""

from .offensive import router as offensive_router
from .defensive import router as defensive_router
from .capitals import router as capitals_router
from .geography import router as geography_router

__all__ = [
    "offensive_router",
    "defensive_router",
    "capitals_router",
    "geography_router",
]
