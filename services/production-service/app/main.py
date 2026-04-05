"""Production Service - Manufacturing simulation and cost calculations."""
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
    simulation_router,
    chains_router,
    economics_router,
    pi_router,
    pi_requirements_router,
    reaction_requirements_router,
    supply_chain_router,
    mining_router,
    optimize_router,
    reactions_router,
    ledger_router,
    tax_router,
    workflow_router,
    invention_router,
    compare_router,
    internal_router,
    projects_router,
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
    logger.info("Production service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="EVE Production Service",
    description="Manufacturing simulation, BOM calculation, and production economics",
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
app.include_router(simulation_router, prefix="/api/production", tags=["Simulation"])
app.include_router(chains_router, prefix="/api/production", tags=["Chains"])
app.include_router(economics_router, prefix="/api/production", tags=["Economics"])
app.include_router(optimize_router, prefix="/api/production", tags=["Optimize"])
app.include_router(pi_router, tags=["Planetary Industry"])
app.include_router(supply_chain_router, tags=["Supply Chain"])
app.include_router(mining_router, prefix="/api/mining", tags=["Mining"])
app.include_router(reactions_router, prefix="/api/reactions", tags=["Reactions"])
app.include_router(ledger_router, prefix="/api/production/ledgers", tags=["Production Ledgers"])
app.include_router(tax_router, prefix="/api/production", tags=["Tax Profiles"])
app.include_router(workflow_router, prefix="/api/production/workflow", tags=["Production Workflow"])
app.include_router(invention_router, prefix="/api/production", tags=["Invention"])
app.include_router(compare_router, prefix="/api/production", tags=["Facility Comparison"])
app.include_router(pi_requirements_router, prefix="/api/production", tags=["PI Requirements"])
app.include_router(reaction_requirements_router, prefix="/api/production", tags=["Reaction Requirements"])
app.include_router(internal_router, prefix="/api", tags=["Internal"])
app.include_router(projects_router, prefix="/api/production", tags=["Projects"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": "1.0.0",
        "status": "running"
    }
