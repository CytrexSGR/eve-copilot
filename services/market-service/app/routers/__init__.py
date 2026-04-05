"""Market service routers."""
from app.routers.prices import router as prices_router
from app.routers.stats import router as stats_router
from app.routers.arbitrage import router as arbitrage_router
from app.routers.items import router as items_router
from app.routers.hunter import router as hunter_router
from app.routers.trading import router as trading_router
from app.routers.market_heatmap import router as market_heatmap_router
from app.routers.portfolio import router as portfolio_router
from app.routers.alerts import router as alerts_router
from app.routers.goals import router as goals_router
from app.routers.history import router as history_router
from app.routers.bookmarks import router as bookmarks_router
from app.routers.orders import router as orders_router
from app.routers.trading_opportunities import router as trading_opportunities_router
from app.routers.trading_opportunities_v2 import router as trading_opportunities_v2_router
from app.routers.thera import router as thera_router
from app.routers.internal import router as internal_router

__all__ = [
    "prices_router",
    "stats_router",
    "arbitrage_router",
    "items_router",
    "hunter_router",
    "trading_router",
    "market_heatmap_router",
    "portfolio_router",
    "alerts_router",
    "goals_router",
    "history_router",
    "bookmarks_router",
    "orders_router",
    "trading_opportunities_router",
    "trading_opportunities_v2_router",
    "thera_router",
    "internal_router",
]
