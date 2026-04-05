"""EVE Scheduler Service - Centralized Job Scheduling."""

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
from app.services.scheduler import scheduler_service
from app.jobs.definitions import get_job_definitions
from app.jobs import executors
from app.routers import jobs

logger = logging.getLogger(__name__)


def _register_jobs():
    """Register all job definitions with the scheduler."""
    definitions = get_job_definitions()
    
    # Map job IDs to executor functions
    executor_map = {
        # battle_event_detector moved to war-intel-service's own scheduler
        'token_refresh': executors.run_token_refresh,
        'aggregate_hourly_stats': executors.run_aggregate_hourly_stats,
        'aggregate_corp_hourly_stats': executors.run_aggregate_corp_hourly_stats,
        'batch_calculator': executors.run_batch_calculator,
        'economy_manipulation_scanner': executors.run_economy_manipulation_scanner,
        'regional_prices': executors.run_regional_prices,
        'sov_tracker': executors.run_sov_tracker,
        'fw_tracker': executors.run_fw_tracker,
        'character_sync': executors.run_character_sync,
        'economy_fuel_poller': executors.run_economy_fuel_poller,
        'economy_price_snapshotter': executors.run_economy_price_snapshotter,
        'coalition_refresh': executors.run_coalition_refresh,
        'battle_cleanup': executors.run_battle_cleanup,
        'pi_monitor': executors.run_pi_monitor,
        'portfolio_snapshotter': executors.run_portfolio_snapshotter,
        'arbitrage_calculator': executors.run_arbitrage_calculator,
        'market_undercut_checker': executors.run_market_undercut_checker,
        'wallet_poll': executors.run_wallet_poll,
        'telegram_report': executors.run_telegram_report,
        'alliance_wars': executors.run_alliance_wars,
        'war_profiteering': executors.run_war_profiteering,
        'report_generator': executors.run_report_generator,
        'capability_sync': executors.run_capability_sync,
        'market_history_sync': executors.run_market_history_sync,
        'skill_snapshot': executors.run_skill_snapshot,
        'alliance_fingerprints': executors.run_alliance_fingerprints,
        'wh_sov_threats': executors.run_wh_sov_threats,
        'pilot_skill_estimates': executors.run_pilot_skill_estimates,
        'corporation_sync': executors.run_corporation_sync,
        'killmail_fetcher': executors.run_killmail_fetcher,
        'doctrine_clustering': executors.run_doctrine_clustering,
        'everef_importer': executors.run_everef_importer,
        'wormhole_data_sync': executors.run_wormhole_data_sync,
        'wormhole_stats_refresh': executors.run_wormhole_stats_refresh,
        # DOTLAN scraping service
        'dotlan_activity_region': executors.run_dotlan_activity_region,
        'dotlan_activity_detail': executors.run_dotlan_activity_detail,
        'dotlan_sov_campaigns': executors.run_dotlan_sov_campaigns,
        'dotlan_sov_changes': executors.run_dotlan_sov_changes,
        'dotlan_alliance_rankings': executors.run_dotlan_alliance_rankings,
        'dotlan_cleanup': executors.run_dotlan_cleanup,
        # Management Suite
        'notification_sync': executors.run_notification_sync,
        'contract_sync': executors.run_contract_sync,
        'timer_expiry_check': executors.run_timer_expiry_check,
        'sov_asset_snapshot': executors.run_sov_asset_snapshot,
        'token_rekey': executors.run_token_rekey,
        'corp_wallet_sync': executors.run_corp_wallet_sync,
        'mining_observer_sync': executors.run_mining_observer_sync,
        # SaaS
        'payment_poll': executors.run_payment_poll,
        'subscription_expiry': executors.run_subscription_expiry,
    }
    
    for job_def in definitions:
        if not job_def.enabled:
            logger.info(f"Skipping disabled job: {job_def.id}")
            continue
            
        func = executor_map.get(job_def.id)
        if not func:
            logger.warning(f"No executor found for job: {job_def.id}")
            continue
            
        try:
            scheduler_service.add_job(job_def, func)
        except Exception as e:
            logger.error(f"Failed to register job {job_def.id}: {e}")


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

    # Initialize connections (Redis only - jobs handle their own DB access)
    get_redis().initialize()

    # Initialize and start scheduler
    scheduler_service.initialize(settings.redis_url)
    _register_jobs()
    scheduler_service.start()

    log.info(f"Scheduler started with {len(get_job_definitions())} jobs")

    yield

    # Shutdown
    scheduler_service.shutdown(wait=True)
    get_redis().close()
    log.info("Shutdown complete")


app = FastAPI(
    title="EVE Scheduler Service",
    description="Centralized Job Scheduling for EVE Co-Pilot",
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

# Health endpoints
app.include_router(health_router)

# Job management API
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])

# Prometheus Metrics Endpoint
app.include_router(metrics_router)


@app.get("/api/scheduler/status")
async def get_scheduler_status():
    """Get scheduler status and statistics."""
    jobs_list = scheduler_service.get_jobs()
    definitions = get_job_definitions()
    
    return {
        "running": True,
        "total_jobs_defined": len(definitions),
        "total_jobs_scheduled": len(jobs_list),
        "jobs": jobs_list
    }
