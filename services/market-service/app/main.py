"""Market Service - EVE Online Market Data with L1/L2/L3 caching."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eve_shared import setup_logging, get_db, get_redis, health_router
from eve_shared.middleware.metrics import MetricsMiddleware
from eve_shared.middleware.exception_handler import register_exception_handlers
from eve_shared.metrics_router import metrics_router
from eve_shared.metrics import service_info

from app.config import settings
from app.routers import (
    prices_router,
    stats_router,
    arbitrage_router,
    items_router,
    hunter_router,
    trading_router,
    market_heatmap_router,
    portfolio_router,
    alerts_router,
    goals_router,
    history_router,
    bookmarks_router,
    orders_router,
    trading_opportunities_router,
    trading_opportunities_v2_router,
    thera_router,
    internal_router,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger = setup_logging(settings.service_name, settings.log_level)
    logger.info(f"Starting {settings.service_name}")

    # Set service info for Prometheus
    service_info.info({
        'service': settings.service_name,
        'version': settings.service_version
    })

    # Initialize shared services
    db = get_db()
    redis = get_redis()

    db.initialize()
    redis.initialize()

    # Store in app state
    app.state.db = db
    app.state.redis = redis
    app.state.settings = settings

    yield

    db.close()
    redis.close()
    logger.info("Market service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="EVE Market Service",
    description="Market data service with L1 Redis → L2 PostgreSQL → L3 ESI caching",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(MetricsMiddleware, service_name=settings.service_name)

register_exception_handlers(app)

# Register routers
app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(prices_router, prefix="/api/market", tags=["Prices"])
app.include_router(stats_router, prefix="/api/market", tags=["Statistics"])
app.include_router(arbitrage_router, prefix="/api/market", tags=["Arbitrage"])

# Thera router (must be before items_router to take precedence over /api/route/{from}/{to})
app.include_router(thera_router, tags=["Thera Router"])

# Migrated routers from monolith
app.include_router(items_router, tags=["Items & Catalog"])
app.include_router(hunter_router, tags=["Market Hunter"])
app.include_router(trading_router, tags=["Trading Analytics"])
app.include_router(market_heatmap_router, tags=["Market Heatmap"])
app.include_router(portfolio_router, tags=["Portfolio"])
app.include_router(alerts_router, tags=["Trading Alerts"])
app.include_router(goals_router, tags=["Trading Goals"])
app.include_router(history_router, tags=["Trading History"])
app.include_router(bookmarks_router, tags=["Bookmarks"])
app.include_router(orders_router, tags=["Orders"])
app.include_router(trading_opportunities_router, tags=["Trading Opportunities"])
app.include_router(trading_opportunities_v2_router, tags=["Trading Opportunities V2"])
app.include_router(internal_router, tags=["Internal Jobs"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "status": "running"
    }
