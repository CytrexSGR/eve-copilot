"""EVE MCP Service - Model Context Protocol tools for AI agents."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eve_shared import setup_logging, get_db, get_redis, health_router
from eve_shared.middleware.metrics import MetricsMiddleware
from eve_shared.metrics_router import metrics_router
from eve_shared.metrics import service_info
from app.config import settings
from app.routers import tools_router
from app.domains.manager import DomainManager
from app.handlers.generic_api import GenericAPIHandler

logger = logging.getLogger(__name__)

# Global instances for dynamic tools
domain_manager = DomainManager()
api_handler = GenericAPIHandler()


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

    get_db().initialize()
    get_redis().initialize()

    # Initialize dynamic OpenAPI tools
    log.info("Loading OpenAPI specs for dynamic tools...")
    await domain_manager.initialize()
    total_tools = sum(len(tools) for tools in domain_manager.domain_tools.values())
    log.info(f"✅ Loaded {total_tools} dynamic endpoints from {len(domain_manager.SERVICES)} services")

    yield

    # Shutdown
    get_db().close()
    get_redis().close()
    log.info("Shutdown complete")


app = FastAPI(
    title="EVE MCP Service",
    description="Model Context Protocol tools for EVE Co-Pilot AI agents",
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

# Health endpoints
app.include_router(health_router)
app.include_router(metrics_router)

# MCP tools router
app.include_router(tools_router, prefix="/mcp", tags=["MCP Tools"])
