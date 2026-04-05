"""Shopping service main application."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eve_shared import setup_logging, get_db, get_redis, health_router
from eve_shared.middleware.metrics import MetricsMiddleware
from eve_shared.middleware.exception_handler import register_exception_handlers
from eve_shared.metrics_router import metrics_router
from eve_shared.metrics import service_info

from app.config import settings
from app.routers import lists_router, items_router, wizard_router, transport_router, routes_router, freight_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger = setup_logging(settings.service_name, settings.log_level)
    logger.info(f"Starting {settings.service_name}")

    # Set service info for Prometheus
    service_info.info({
        'service': settings.service_name,
        'version': getattr(settings, 'service_version', '1.0.0')
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
    logger.info("Shopping service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="EVE Shopping Service",
    description="Shopping list management for EVE Online manufacturing",
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
app.include_router(lists_router, prefix="/api/shopping", tags=["Shopping Lists"])
app.include_router(items_router, prefix="/api/shopping", tags=["Shopping Items"])
app.include_router(wizard_router, prefix="/api/shopping/wizard", tags=["Shopping Wizard"])
app.include_router(transport_router, prefix="/api/shopping", tags=["Transport"])
app.include_router(routes_router, prefix="/api/shopping", tags=["Routes & Orders"])
app.include_router(freight_router, prefix="/api/shopping", tags=["Freight"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.service_name,
        "version": "0.1.0",
        "status": "running"
    }
