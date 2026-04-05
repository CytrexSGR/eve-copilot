"""Market-related executor functions."""

import logging
import os

from ._helpers import _call_service

logger = logging.getLogger(__name__)

__all__ = [
    "run_batch_calculator",
    "run_economy_manipulation_scanner",
    "run_regional_prices",
    "run_arbitrage_calculator",
    "run_market_undercut_checker",
    "run_market_history_sync",
    "run_economy_fuel_poller",
    "run_economy_price_snapshotter",
]


def run_batch_calculator():
    """Trigger manufacturing opportunities recalculation via production-service."""
    prod_url = os.environ.get("PRODUCTION_SERVICE_URL", "http://production-service:8000")
    logger.info("Starting batch_calculator job")
    try:
        result = _call_service(f"{prod_url}/api/internal/batch-calculate", timeout=180)
        details = result.get("details", {})
        logger.info(
            f"batch_calculator: {details.get('opportunities_saved', 0)} opportunities "
            f"from {details.get('blueprints_scanned', 0)} blueprints "
            f"in {details.get('elapsed_seconds', 0)}s"
        )
        return result.get("status") == "completed"
    except Exception as e:
        logger.error(f"batch_calculator failed: {e}")
        return False


def run_economy_manipulation_scanner():
    """Trigger market manipulation scanner via market-service."""
    mkt_url = os.environ.get("MARKET_SERVICE_URL", "http://market-service:8000")
    logger.info("Starting economy_manipulation_scanner job")
    try:
        result = _call_service(f"{mkt_url}/api/internal/scan-manipulation", timeout=120)
        details = result.get("details", {})
        logger.info(
            f"manipulation_scanner: {details.get('total_alerts', 0)} alerts "
            f"({details.get('confirmed', 0)} confirmed) "
            f"in {details.get('elapsed_seconds', 0)}s"
        )
        return result.get("status") == "completed"
    except Exception as e:
        logger.error(f"economy_manipulation_scanner failed: {e}")
        return False


def run_regional_prices():
    """Trigger regional price fetch via market-service."""
    mkt_url = os.environ.get("MARKET_SERVICE_URL", "http://market-service:8000")
    logger.info("Starting regional_prices job")
    try:
        result = _call_service(f"{mkt_url}/api/internal/refresh-regional-prices", timeout=300)
        details = result.get("details", {})
        logger.info(
            f"regional_prices: {details.get('prices_saved', 0)} prices "
            f"from {details.get('total_orders_fetched', 0)} orders "
            f"in {details.get('elapsed_seconds', 0)}s"
        )
        return result.get("status") == "completed"
    except Exception as e:
        logger.error(f"regional_prices failed: {e}")
        return False


def run_arbitrage_calculator():
    """Trigger arbitrage route calculation via market-service."""
    mkt_url = os.environ.get("MARKET_SERVICE_URL", "http://market-service:8000")
    logger.info("Starting arbitrage_calculator job")
    try:
        result = _call_service(f"{mkt_url}/api/internal/calculate-arbitrage", timeout=600)
        details = result.get("details", {})
        logger.info(
            f"arbitrage_calculator: {details.get('routes_found', 0)} routes "
            f"in {details.get('elapsed_seconds', 0)}s"
        )
        return result.get("status") == "completed"
    except Exception as e:
        logger.error(f"arbitrage_calculator failed: {e}")
        return False


def run_market_undercut_checker():
    """Trigger undercut checker via market-service."""
    mkt_url = os.environ.get("MARKET_SERVICE_URL", "http://market-service:8000")
    logger.info("Starting market_undercut_checker job")
    try:
        result = _call_service(f"{mkt_url}/api/internal/check-undercuts", timeout=120)
        details = result.get("details", {})
        logger.info(
            f"undercut_checker: {details.get('total_new_undercuts', 0)} new undercuts "
            f"for {details.get('characters_checked', 0)} characters "
            f"in {details.get('elapsed_seconds', 0)}s"
        )
        return result.get("status") == "completed"
    except Exception as e:
        logger.error(f"market_undercut_checker failed: {e}")
        return False


def run_market_history_sync():
    """Sync market history from ESI and calculate trading metrics."""
    logger.info("Starting market_history_sync job")
    try:
        from app.jobs.market_history_sync import run_market_history_sync as sync
        result = sync()
        logger.info(f"Market history sync: {result} items updated")
        return result > 0
    except Exception as e:
        logger.exception(f"Market history sync error: {e}")
        return False


def run_economy_fuel_poller():
    """Trigger fuel market scan via market-service."""
    mkt_url = os.environ.get("MARKET_SERVICE_URL", "http://market-service:8000")
    logger.info("Starting economy_fuel_poller job")
    try:
        result = _call_service(f"{mkt_url}/api/internal/scan-fuel-markets", timeout=120)
        details = result.get("details", {})
        logger.info(
            f"fuel_poller: {details.get('anomalies_detected', 0)} anomalies "
            f"({details.get('critical_high', 0)} critical/high) "
            f"in {details.get('elapsed_seconds', 0)}s"
        )
        return result.get("status") == "completed"
    except Exception as e:
        logger.error(f"economy_fuel_poller failed: {e}")
        return False


def run_economy_price_snapshotter():
    """Trigger price snapshot via market-service."""
    mkt_url = os.environ.get("MARKET_SERVICE_URL", "http://market-service:8000")
    logger.info("Starting economy_price_snapshotter job")
    try:
        result = _call_service(f"{mkt_url}/api/internal/snapshot-prices", timeout=120)
        details = result.get("details", {})
        logger.info(
            f"price_snapshotter: {details.get('records_inserted', 0)} records "
            f"in {details.get('elapsed_seconds', 0)}s"
        )
        return result.get("status") == "completed"
    except Exception as e:
        logger.error(f"economy_price_snapshotter failed: {e}")
        return False
