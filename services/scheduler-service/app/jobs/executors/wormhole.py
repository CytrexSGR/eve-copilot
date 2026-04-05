"""Wormhole-related executor functions."""

import logging
import os

from ._helpers import _call_service

logger = logging.getLogger(__name__)

__all__ = [
    "run_wormhole_data_sync",
    "run_wormhole_stats_refresh",
    "run_wh_sov_threats",
]


def run_wormhole_data_sync():
    """Sync wormhole static data from Pathfinder via wormhole-service API."""
    wh_url = os.environ.get("WORMHOLE_SERVICE_URL", "http://wormhole-service:8000")
    logger.info("Starting wormhole_data_sync job")
    try:
        result = _call_service(f"{wh_url}/api/wormhole/internal/sync-pathfinder", timeout=300)
        logger.info(f"wormhole_data_sync: {result.get('details', {})}")
        return result.get("status") == "completed"
    except Exception as e:
        logger.error(f"wormhole_data_sync failed: {e}")
        return False


def run_wormhole_stats_refresh():
    """Refresh wormhole resident and activity stats via wormhole-service API."""
    wh_url = os.environ.get("WORMHOLE_SERVICE_URL", "http://wormhole-service:8000")
    logger.info("Starting wormhole_stats_refresh job")
    try:
        result = _call_service(f"{wh_url}/api/wormhole/internal/refresh-stats", timeout=300)
        logger.info(f"wormhole_stats_refresh: {result.get('details', {})}")
        return result.get("status") == "completed"
    except Exception as e:
        logger.error(f"wormhole_stats_refresh failed: {e}")
        return False


def run_wh_sov_threats():
    """Calculate WH threat analysis for all sov-holding alliances.

    Analyzes wormhole activity in alliance sovereignty space:
    - Which WH systems are attacking sov space
    - Threat levels (CRITICAL/HIGH/MODERATE/LOW)
    - Top attacking alliances and their WH systems
    - Regional distribution and timezone patterns
    - Attacker ship doctrines

    Only ~80 alliances hold sov, so this is a lightweight daily job.
    """
    logger.info("Starting wh_sov_threats job")
    try:
        from app.jobs.wh_sov_threats import refresh_wh_sov_threats
        result = refresh_wh_sov_threats(days=30)
        logger.info(
            f"WH SOV threats: {result['alliances_with_threats']}/{result['alliances_processed']} "
            f"alliances with threats, {result['errors']} errors"
        )
        return result["errors"] == 0
    except Exception as e:
        logger.exception(f"WH SOV threats error: {e}")
        return False
