"""EVE Co-Pilot Finance Service - Corp wallets, mining tax, invoicing."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from eve_shared import setup_logging, get_db, get_redis, health_router
from eve_shared.middleware.metrics import MetricsMiddleware
from eve_shared.middleware.exception_handler import register_exception_handlers
from eve_shared.metrics_router import metrics_router
from eve_shared.metrics import service_info

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan."""
    logger = setup_logging(settings.service_name, settings.log_level)
    logger.info(f"Starting {settings.service_name}")

    db = get_db()
    db.initialize()
    app.state.db = db

    redis = get_redis()
    redis.initialize()
    app.state.redis = redis

    service_info.info({
        "service": settings.service_name,
        "version": "1.0.0",
    })

    yield

    db.close()
    redis.close()


app = FastAPI(
    title="EVE Co-Pilot Finance Service",
    description="Corporation wallet sync, mining tax, invoicing, and financial reports",
    version="1.0.0",
    lifespan=lifespan,
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

# Standard routes
app.include_router(health_router)
app.include_router(metrics_router)

# Finance routes
from app.routers import wallet_router, mining_router, invoices_router, reports_router, srp_router, buyback_router

app.include_router(wallet_router, prefix="/api/finance")
app.include_router(mining_router, prefix="/api/finance")
app.include_router(invoices_router, prefix="/api/finance")
app.include_router(reports_router, prefix="/api/finance")
app.include_router(srp_router, prefix="/api/finance")
app.include_router(buyback_router, prefix="/api/finance", tags=["Buyback"])
