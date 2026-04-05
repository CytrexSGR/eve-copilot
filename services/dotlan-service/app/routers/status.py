"""Scraper status router - monitoring, manual triggers, execution log."""

import logging
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.database import db_cursor

logger = logging.getLogger(__name__)
router = APIRouter()

# Track running scrape tasks
_running_tasks: dict[str, asyncio.Task] = {}


@router.get("/")
@handle_endpoint_errors()
def get_scraper_status():
    """Get status of all scrapers including last run times."""
    with db_cursor() as cur:
        # Get latest run for each scraper
        cur.execute("""
            SELECT DISTINCT ON (scraper_name)
                   scraper_name, started_at, finished_at, status,
                   regions_scraped, systems_scraped, rows_inserted,
                   duration_seconds, error_message
            FROM dotlan_scraper_log
            ORDER BY scraper_name, started_at DESC
        """)
        latest_runs = cur.fetchall()

    # Check which tasks are currently running
    running = {name for name, task in _running_tasks.items() if not task.done()}

    return {
        "scrapers": [
            {
                **run,
                "currently_running": run["scraper_name"] in running,
            }
            for run in latest_runs
        ],
        "running_tasks": list(running),
    }


@router.post("/trigger/{scraper_name}")
@handle_endpoint_errors()
def trigger_scrape(scraper_name: str):
    """Manually trigger a scrape operation.

    Valid scraper names:
    - activity_region: Region scan for current activity values
    - activity_detail: Detail scan for top active systems (7-day history)
    - sov_campaigns: Sovereignty campaign scan
    - sov_changes: Sovereignty changes scan
    - alliance_rankings: Alliance ranking scan
    - cleanup: Data retention cleanup
    """
    valid_scrapers = {
        "activity_region", "activity_detail",
        "sov_campaigns", "sov_changes",
        "alliance_rankings", "cleanup",
    }

    if scraper_name not in valid_scrapers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scraper. Valid options: {sorted(valid_scrapers)}"
        )

    # Check if already running
    if scraper_name in _running_tasks and not _running_tasks[scraper_name].done():
        return {"status": "already_running", "scraper": scraper_name}

    # Launch as background task
    task = asyncio.create_task(_run_scraper(scraper_name))
    _running_tasks[scraper_name] = task

    return {"status": "started", "scraper": scraper_name}


async def _run_scraper(scraper_name: str):
    """Execute a scraper by name."""
    try:
        if scraper_name == "activity_region":
            from app.services.activity_scraper import ActivityScraper
            scraper = ActivityScraper()
            await scraper.run_region_scan()

        elif scraper_name == "activity_detail":
            from app.services.activity_scraper import ActivityScraper
            scraper = ActivityScraper()
            await scraper.run_detail_scan()

        elif scraper_name == "sov_campaigns":
            from app.services.sovereignty_scraper import SovereigntyScraper
            scraper = SovereigntyScraper()
            await scraper.run_campaign_scan()

        elif scraper_name == "sov_changes":
            from app.services.sovereignty_scraper import SovereigntyScraper
            scraper = SovereigntyScraper()
            await scraper.run_changes_scan()

        elif scraper_name == "alliance_rankings":
            from app.services.alliance_scraper import AllianceScraper
            scraper = AllianceScraper()
            await scraper.run_ranking_scan()

        elif scraper_name == "cleanup":
            await _run_cleanup()

    except Exception as e:
        logger.error(f"Scraper '{scraper_name}' failed: {e}")


async def _run_cleanup():
    """Clean up old data based on retention settings."""
    from app.config import settings

    with db_cursor() as cur:
        # Activity data
        cur.execute("""
            DELETE FROM dotlan_system_activity
            WHERE timestamp < NOW() - INTERVAL '%s days'
        """, (settings.retention_activity_days,))
        activity_deleted = cur.rowcount

        # Sov changes
        cur.execute("""
            DELETE FROM dotlan_sov_changes
            WHERE changed_at < NOW() - INTERVAL '%s days'
        """, (settings.retention_sov_changes_days,))
        sov_deleted = cur.rowcount

        # Alliance stats
        cur.execute("""
            DELETE FROM dotlan_alliance_stats
            WHERE snapshot_date < CURRENT_DATE - %s
        """, (settings.retention_alliance_stats_days,))
        alliance_deleted = cur.rowcount

        # ADM history
        cur.execute("""
            DELETE FROM dotlan_adm_history
            WHERE timestamp < NOW() - INTERVAL '%s days'
        """, (settings.retention_adm_history_days,))
        adm_deleted = cur.rowcount

        # Scraper log
        cur.execute("""
            DELETE FROM dotlan_scraper_log
            WHERE started_at < NOW() - INTERVAL '%s days'
        """, (settings.retention_scraper_log_days,))
        log_deleted = cur.rowcount

    logger.info(f"Cleanup: activity={activity_deleted}, sov={sov_deleted}, "
                f"alliance={alliance_deleted}, adm={adm_deleted}, log={log_deleted}")


@router.get("/log")
@handle_endpoint_errors()
def get_scraper_log(
    scraper_name: Optional[str] = None,
    limit: int = 50,
):
    """Get scraper execution log."""
    with db_cursor() as cur:
        if scraper_name:
            cur.execute("""
                SELECT * FROM dotlan_scraper_log
                WHERE scraper_name = %s
                ORDER BY started_at DESC
                LIMIT %s
            """, (scraper_name, limit))
        else:
            cur.execute("""
                SELECT * FROM dotlan_scraper_log
                ORDER BY started_at DESC
                LIMIT %s
            """, (limit,))
        return cur.fetchall()
