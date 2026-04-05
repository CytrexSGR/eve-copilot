"""EVE War Intel Service - Combat Intelligence and zkillboard Integration."""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from contextlib import asynccontextmanager
from eve_shared.metrics import service_info
from eve_shared.metrics_router import metrics_router
from eve_shared.middleware.metrics import MetricsMiddleware
from eve_shared.middleware.exception_handler import register_exception_handlers
from eve_shared import setup_logging, health_router
import eve_shared.monitoring.business_metrics  # noqa: F401
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import DatabasePool
from app.routers import dps, risk, reports, doctrine, sovereignty
logger = logging.getLogger(__name__)

# Initialize database pool
_db = DatabasePool()

# Initialize scheduler
_scheduler = BackgroundScheduler()

def _monitor_connection_pool():
    """Monitor database connection pool metrics."""
    from eve_shared.monitoring.db_instrumentation import monitor_connection_pool
    monitor_connection_pool(_db, settings.service_name)

def _update_active_battles_count():
    """Update active battles count metric."""
    from eve_shared.monitoring.business_metrics import update_active_battles_count

    try:
        with _db.cursor() as cur:
            # Count battles active in last 2 hours
            cur.execute("""
                SELECT COUNT(*) as count
                FROM battles
                WHERE status = 'active'
                  AND last_kill_at > NOW() - INTERVAL '2 hours'
            """)
            result = cur.fetchone()
            # Handle both tuple and dict cursor results
            if isinstance(result, dict):
                count = result.get('count', 0)
            elif isinstance(result, tuple):
                count = result[0]
            else:
                count = 0

            update_active_battles_count(int(count))
            logger.debug(f"Updated active battles count: {count}")
    except Exception as e:
        import traceback
        logger.error(f"Error updating active battles count: {e}\n{traceback.format_exc()}")

def _refresh_caches():
    """
    Background task to refresh expensive cached endpoints.
    Prevents users from experiencing slow uncached requests by keeping
    the cache warm (refreshing before expiry).

    Runs every 4 minutes (cache TTL is 5 minutes).
    """
    from app.routers.reports import refresh_expensive_caches_sync

    try:
        refresh_expensive_caches_sync()
    except Exception as e:
        logger.error(f"Cache refresh task failed: {e}")

def _register_jobs():
    """Register scheduled jobs for this service."""
    from app.jobs.battle_event_detector import run_battle_event_detection
    from apscheduler.triggers.interval import IntervalTrigger

    # Battle Event Detector - runs every minute
    _scheduler.add_job(
        func=run_battle_event_detection,
        trigger=CronTrigger(minute="*"),
        id="battle_event_detector",
        name="Battle Event Detector",
        replace_existing=True
    )

    # Connection Pool Monitor - runs every 30 seconds
    _scheduler.add_job(
        func=_monitor_connection_pool,
        trigger=IntervalTrigger(seconds=30),
        id="connection_pool_monitor",
        name="Connection Pool Monitor",
        replace_existing=True
    )

    # Active Battles Counter - runs every 60 seconds
    _scheduler.add_job(
        func=_update_active_battles_count,
        trigger=IntervalTrigger(seconds=60),
        id="active_battles_counter",
        name="Active Battles Counter",
        replace_existing=True
    )

    # Cache Refresh - runs every 4 minutes (cache TTL is 5 minutes)
    _scheduler.add_job(
        func=_refresh_caches,
        trigger=IntervalTrigger(minutes=4),
        id="cache_refresh",
        name="Cache Refresh",
        replace_existing=True
    )

    logger.info("Registered 4 scheduled jobs: battle_event_detector, connection_pool_monitor, active_battles_counter, cache_refresh")

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

    # Start scheduler
    _register_jobs()
    _scheduler.start()
    log.info("Background scheduler started")

    yield

    # Shutdown
    _scheduler.shutdown(wait=True)
    log.info("Shutdown complete")

app = FastAPI(
    title="EVE War Intel Service",
    description="Combat Intelligence, zkillboard Integration, Battle Tracking",
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

# War intelligence routers
from app.routers import war, intelligence
app.include_router(war.router, prefix="/api/war", tags=["War Intelligence"])
app.include_router(doctrine.router, prefix="/api/war", tags=["Doctrine Detection"])
app.include_router(intelligence.router, prefix="/api/intelligence/fast", tags=["Fast Intelligence"])

# Combat routers (migrated from monolith)
app.include_router(dps.router, prefix="/api/dps", tags=["DPS Calculator"])
app.include_router(risk.router, prefix="/api/risk", tags=["Risk Management"])
app.include_router(reports.router, prefix="/api/reports", tags=["Combat Reports"])

# Sovereignty & Capital Ops
app.include_router(sovereignty.router, prefix="/api/sovereignty", tags=["Sovereignty Operations"])

# Contracts Scanner
from app.routers import contracts
app.include_router(contracts.router, prefix="/api/contracts", tags=["Public Contracts"])

# Jump Planner (Range, Fatigue, Routes)
from app.routers import jump_planner
app.include_router(jump_planner.router, prefix="/api/jump", tags=["Jump Planner"])

# Structure Timers
from app.routers import structure_timers
app.include_router(structure_timers.router, prefix="/api/timers", tags=["Structure Timers"])

# Moon Mining Intel
from app.routers import moon_mining
app.include_router(moon_mining.router, prefix="/api/moon", tags=["Moon Mining"])

# Fuel Tracking
from app.routers import fuel_tracking
app.include_router(fuel_tracking.router, prefix="/api/fuel", tags=["Fuel Tracking"])

# Corp Wallet Analysis
from app.routers import corp_wallet
app.include_router(corp_wallet.router, prefix="/api/wallet", tags=["Corp Wallet"])

# Corp Contract Monitor
from app.routers import corp_contracts
app.include_router(corp_contracts.router, prefix="/api/corp-contracts", tags=["Corp Contracts"])

# Live Doctrine Operations (time-filtered) - MUST be before alliance_fingerprints to avoid /{alliance_id} catching /live-ops
from app.routers import fingerprints_live_ops
app.include_router(fingerprints_live_ops.router, prefix="/api", tags=["Doctrine Live Ops"])

# Alliance Doctrine Fingerprints
from app.routers import alliance_fingerprints
app.include_router(alliance_fingerprints.router, prefix="/api", tags=["Alliance Fingerprints"])

# Alliance Info & Corporations
from app.routers import alliances
app.include_router(alliances.router, prefix="/api/alliances", tags=["Alliances"])

# War Economy (Fuel Trends, Manipulation Alerts, Supercap Timers)
from app.routers import economy
app.include_router(economy.router, prefix="/api/war", tags=["War Economy"])

# Battle Events (Detection, Alerts, Event Feed)
from app.routers import events
app.include_router(events.router, prefix="/api/events", tags=["Battle Events"])

# Intelligence (Alliance Analysis - Combat, Economics, Equipment)
from app.routers.intelligence import router as intelligence_router
app.include_router(intelligence_router, prefix="/api/intelligence", tags=["Alliance Intelligence"])

# Power Bloc Detail (deep tab endpoints)
from app.routers.powerbloc import router as powerbloc_router
app.include_router(powerbloc_router, prefix="/api/powerbloc", tags=["Power Bloc Detail"])

# MCP (Model Context Protocol) - AI-Agent-Friendly APIs
from app.routers.mcp import mcp_router
app.include_router(mcp_router, prefix="/api/mcp", tags=["MCP"])

# Dogma Engine - Tank/EHP Calculations & Killmail Fitting Analysis
from app.routers import dogma
app.include_router(dogma.router, prefix="/api/dogma", tags=["Dogma Engine"])

# Sovereignty Resources (Equinox Power/Workforce/Reagent Topology)
from app.routers import sovereignty_resources
app.include_router(sovereignty_resources.router, prefix="/api/sov", tags=["Sovereignty Resources"])

# Skyhook & Metenox Management
from app.routers import skyhook_metenox
app.include_router(skyhook_metenox.router, prefix="/api/sov", tags=["Skyhook & Metenox"])

# ESI Notifications
from app.routers import notifications
app.include_router(notifications.router, prefix="/api", tags=["Notifications"])

# Sovereignty Asset Snapshots
from app.routers import sov_assets
app.include_router(sov_assets.router, prefix="/api", tags=["Sovereignty Assets"])

# Internal endpoints (scheduler-triggered jobs)
from app.routers import internal as internal_router
app.include_router(internal_router.router, prefix="/api", tags=["Internal"])

# Prometheus Metrics Endpoint
app.include_router(metrics_router)

