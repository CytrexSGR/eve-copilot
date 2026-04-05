"""Character service main application."""
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
    character_router,
    corporation_router,
    sync_router,
    skills_router,
    skill_analysis_router,
    skill_plans_router,
    mastery_router,
    fittings_router,
    research_router,
    skill_prerequisites_router,
    sde_browser_router,
    doctrine_stats_router,
    account_summary_router,
)
from app.routers.internal import router as internal_router
from app.routers.skillfarm import router as skillfarm_router
from app.routers.mail import router as mail_router


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
    logger.info("Character service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="EVE Character Service",
    description="Character and corporation data management for EVE Online",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.add_middleware(MetricsMiddleware, service_name=settings.service_name
)

register_exception_handlers(app)

# Health check router
app.include_router(health_router)
app.include_router(metrics_router)

# API routers
app.include_router(character_router, prefix="/api/character", tags=["Character"])
app.include_router(corporation_router, prefix="/api/character", tags=["Corporation"])
app.include_router(sync_router, prefix="/api/character", tags=["Sync"])

# Skills-related routers (migrated from monolith)
app.include_router(skills_router, prefix="/api/skills", tags=["Skills"])
app.include_router(skill_analysis_router, prefix="/api/skills", tags=["Skill Analysis"])
app.include_router(skill_plans_router, prefix="/api/skills/plans", tags=["Skill Plans"])
app.include_router(mastery_router, prefix="/api/mastery", tags=["Mastery"])
app.include_router(fittings_router, prefix="/api/fittings", tags=["Fittings"])
app.include_router(research_router, prefix="/api/research", tags=["Research"])
app.include_router(skill_prerequisites_router, prefix="/api/skills/prerequisites", tags=["Skill Prerequisites"])
app.include_router(sde_browser_router, prefix="/api/sde", tags=["SDE Browser"])
app.include_router(doctrine_stats_router, prefix="/api/doctrines", tags=["Doctrine Engine"])
app.include_router(account_summary_router, prefix="/api/characters", tags=["Account Summary"])

# Internal endpoints (scheduler-triggered jobs)
app.include_router(internal_router, prefix="/api", tags=["Internal"])
app.include_router(skillfarm_router, prefix="/api/skills", tags=["Skillfarm"])
app.include_router(mail_router, prefix="/api/character", tags=["Mail"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": "0.1.0",
        "status": "running"
    }
