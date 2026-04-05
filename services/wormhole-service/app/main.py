"""
Wormhole Service - J-Space Intelligence API

Provides wormhole space data and intelligence for EVE Online.

Public API (no auth):
- WH type reference and lookup
- J-Space system information
- Resident detection
- Activity statistics
- Eviction tracking

Internal API (auth required, Phase 2):
- Personal chain mapping
- Signature tracking
- Bookmark sync
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eve_shared import get_db, health_router
from eve_shared.middleware.metrics import MetricsMiddleware
from eve_shared.middleware.exception_handler import register_exception_handlers
from eve_shared.metrics_router import metrics_router
from eve_shared.metrics import service_info

# Import routers
from app.config import settings
from app.routers import types, systems, residents, activity, evictions, stats, threats, opportunities, market, internal


@asynccontextmanager
async def lifespan(app):
    db = get_db()
    db.initialize(service_name="eve-wormhole-service")
    app.state.db = db
    yield
    db.close()


app = FastAPI(
    title="EVE Copilot - Wormhole Service",
    description="J-Space Intelligence API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(MetricsMiddleware, service_name="eve-wormhole-service")

register_exception_handlers(app)

# Set service info for Prometheus
service_info.info({
    'service': 'eve-wormhole-service',
    'version': '1.0.0'
})


# Health endpoints (shared: /health, /ready, /live)
app.include_router(health_router)


@app.get("/")
async def root():
    """Service info."""
    return {
        "service": "wormhole-service",
        "version": "1.0.0",
        "description": "J-Space Intelligence API",
        "endpoints": {
            "types": "/api/wormhole/types",
            "systems": "/api/wormhole/systems",
            "residents": "/api/wormhole/residents",
            "activity": "/api/wormhole/activity",
            "evictions": "/api/wormhole/evictions",
            "stats": "/api/wormhole/stats/summary"
        }
    }


# Router registration
app.include_router(metrics_router)
app.include_router(types.router, prefix="/api/wormhole")
app.include_router(systems.router, prefix="/api/wormhole")
app.include_router(residents.router, prefix="/api/wormhole")
app.include_router(activity.router, prefix="/api/wormhole")
app.include_router(evictions.router, prefix="/api/wormhole")
app.include_router(stats.router, prefix="/api/wormhole")
app.include_router(threats.router, prefix="/api/wormhole")
app.include_router(opportunities.router, prefix="/api/wormhole")
app.include_router(market.router, prefix="/api/wormhole")
app.include_router(internal.router, prefix="/api/wormhole")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
