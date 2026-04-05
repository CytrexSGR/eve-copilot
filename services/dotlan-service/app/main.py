"""EVE DOTLAN Scraping Service - System activity, sovereignty, and alliance data from DOTLAN."""

import asyncio
import logging
from contextlib import asynccontextmanager

from eve_shared.metrics import service_info
from eve_shared.metrics_router import metrics_router
from eve_shared.middleware.metrics import MetricsMiddleware
from eve_shared.middleware.exception_handler import register_exception_handlers
from eve_shared import setup_logging, health_router

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import DatabasePool

logger = logging.getLogger(__name__)

# Initialize database pool
_db = DatabasePool()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    log = setup_logging(settings.service_name, settings.log_level)
    log.info(f"Starting {settings.service_name} v{settings.service_version}")

    # Set service info for Prometheus
    service_info.info({
        'service': settings.service_name,
        'version': settings.service_version
    })

    _db.initialize()
    log.info("Database pool initialized")

    # Initialize scraper infrastructure
    from app.services.scraper_base import init_scraper_infrastructure
    init_scraper_infrastructure(_db)
    log.info("Scraper infrastructure initialized")

    yield

    # Shutdown
    from app.services.scraper_base import shutdown_scraper_infrastructure
    await shutdown_scraper_infrastructure()
    log.info("Shutdown complete")


app = FastAPI(
    title="EVE DOTLAN Scraping Service",
    description="Scrapes system activity, sovereignty campaigns, and alliance data from DOTLAN EveMaps",
    version=settings.service_version,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(MetricsMiddleware, service_name=settings.service_name)

register_exception_handlers(app)

# Health endpoints (shared: /health, /ready, /live)
app.include_router(health_router)

# DOTLAN data routers
from app.routers import activity, sovereignty, alliances, status

app.include_router(activity.router, prefix="/api/dotlan/activity", tags=["System Activity"])
app.include_router(sovereignty.router, prefix="/api/dotlan/sovereignty", tags=["Sovereignty"])
app.include_router(alliances.router, prefix="/api/dotlan/alliances", tags=["Alliances"])
app.include_router(status.router, prefix="/api/dotlan/status", tags=["Scraper Status"])

# Prometheus Metrics Endpoint
app.include_router(metrics_router)
