"""Scrape task functions called by the scheduler-service via HTTP triggers.

These functions are also available for direct import if needed.
"""

import logging

logger = logging.getLogger(__name__)


async def run_activity_region_scan():
    """Run activity region scan (all K-Space regions)."""
    from app.services.activity_scraper import ActivityScraper
    scraper = ActivityScraper()
    await scraper.run_region_scan()


async def run_activity_detail_scan():
    """Run activity detail scan (top active systems)."""
    from app.services.activity_scraper import ActivityScraper
    scraper = ActivityScraper()
    await scraper.run_detail_scan()


async def run_sov_campaign_scan():
    """Run sovereignty campaign scan."""
    from app.services.sovereignty_scraper import SovereigntyScraper
    scraper = SovereigntyScraper()
    await scraper.run_campaign_scan()


async def run_sov_changes_scan():
    """Run sovereignty changes scan."""
    from app.services.sovereignty_scraper import SovereigntyScraper
    scraper = SovereigntyScraper()
    await scraper.run_changes_scan()


async def run_alliance_ranking_scan():
    """Run alliance ranking scan."""
    from app.services.alliance_scraper import AllianceScraper
    scraper = AllianceScraper()
    await scraper.run_ranking_scan()
