"""EVE Co-Pilot API Gateway - Main application."""
import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eve_shared.logging import setup_logging
from eve_shared import get_db
from eve_shared.middleware.metrics import MetricsMiddleware
from eve_shared.metrics_router import metrics_router
from eve_shared.metrics import service_info

from app.settings import settings
from app.middleware import ProxyMiddleware, RateLimitMiddleware
from app.routers import health_router, dashboard_router
from app.routers.feedback import router as feedback_router


def _parse_cors_origins(origins_str: str | None) -> list[str]:
    """Parse comma-separated CORS origins string."""
    if not origins_str or origins_str.strip() == "*" or origins_str.strip() == "":
        return ["*"]
    return [o.strip() for o in origins_str.split(",") if o.strip()]

# Setup logging
setup_logging(settings.service_name, settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    logger.info(f"Starting {settings.service_name}")
    logger.info(f"Environment: {settings.environment}")

    # Set service info for Prometheus
    service_info.info({
        'service': settings.service_name,
        'version': getattr(settings, 'service_version', '1.0.0')
    })

    logger.info("Proxy routes configured:")
    from app.settings import SERVICE_ROUTES
    for prefix, url in SERVICE_ROUTES.items():
        logger.info(f"  {prefix} -> {url}")

    # Initialize database connection for local routers (e.g., dashboard)
    db = get_db()
    db.initialize()
    app.state.db = db
    logger.info("Database connection initialized")

    yield

    db.close()
    logger.info(f"Shutting down {settings.service_name}")


# Create FastAPI app
app = FastAPI(
    title="EVE Co-Pilot API Gateway",
    description="API Gateway for EVE Co-Pilot microservices",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware (must be added before proxy middleware)
cors_origins = _parse_cors_origins(settings.cors_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add metrics middleware (before proxy to capture all requests)
app.add_middleware(MetricsMiddleware, service_name=settings.service_name)

# Add rate limiting middleware (optional, can be disabled via env)
rate_limit_enabled = os.environ.get("RATE_LIMIT_ENABLED", "false").lower() == "true"
app.add_middleware(RateLimitMiddleware, enabled=rate_limit_enabled)

# Add feature-gate middleware (SaaS tier enforcement)
from app.middleware.feature_gate import FeatureGateMiddleware
feature_gate_enabled = os.environ.get("FEATURE_GATE_ENABLED", "false").lower() == "true"
app.add_middleware(FeatureGateMiddleware, enabled=feature_gate_enabled)

# Add proxy middleware for routing to microservices
# NOTE: ProxyMiddleware must be registered BEFORE CharacterContextMiddleware
# because Starlette executes the last-registered middleware first (outermost).
# ProxyMiddleware does not call call_next() for proxied routes, so any
# middleware registered before it (inner) would be skipped.
app.add_middleware(ProxyMiddleware)

# Add character context middleware (validate X-Character-Id against JWT)
# Registered after ProxyMiddleware so it runs first (outermost layer).
from app.middleware.character_context import CharacterContextMiddleware
app.add_middleware(CharacterContextMiddleware)

# Register local routers
app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(metrics_router)
app.include_router(feedback_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
