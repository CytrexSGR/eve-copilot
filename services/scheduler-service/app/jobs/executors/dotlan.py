"""DOTLAN scraping service executor functions."""

import logging

from ._helpers import _trigger_dotlan_scrape

logger = logging.getLogger(__name__)

__all__ = [
    "run_dotlan_activity_region",
    "run_dotlan_activity_detail",
    "run_dotlan_sov_campaigns",
    "run_dotlan_sov_changes",
    "run_dotlan_alliance_rankings",
    "run_dotlan_cleanup",
]


def run_dotlan_activity_region():
    """Trigger DOTLAN activity region scan (all K-Space regions)."""
    logger.info("Starting dotlan_activity_region job")
    return _trigger_dotlan_scrape("activity_region", timeout=7200)


def run_dotlan_activity_detail():
    """Trigger DOTLAN activity detail scan (top active systems, 7-day history)."""
    logger.info("Starting dotlan_activity_detail job")
    return _trigger_dotlan_scrape("activity_detail", timeout=3600)


def run_dotlan_sov_campaigns():
    """Trigger DOTLAN sovereignty campaign scan."""
    logger.info("Starting dotlan_sov_campaigns job")
    return _trigger_dotlan_scrape("sov_campaigns", timeout=120)


def run_dotlan_sov_changes():
    """Trigger DOTLAN sovereignty changes scan."""
    logger.info("Starting dotlan_sov_changes job")
    return _trigger_dotlan_scrape("sov_changes", timeout=120)


def run_dotlan_alliance_rankings():
    """Trigger DOTLAN alliance ranking scan."""
    logger.info("Starting dotlan_alliance_rankings job")
    return _trigger_dotlan_scrape("alliance_rankings", timeout=120)


def run_dotlan_cleanup():
    """Trigger DOTLAN data retention cleanup."""
    logger.info("Starting dotlan_cleanup job")
    return _trigger_dotlan_scrape("cleanup", timeout=300)
