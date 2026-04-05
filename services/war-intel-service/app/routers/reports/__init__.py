"""Reports Router Package — pre-generated reports, power blocs, trade routes, power assessment."""

from fastapi import APIRouter

from .stored_reports import router as stored_reports_router, get_alliance_wars
from .power_blocs import router as power_blocs_router, get_power_blocs_live
from .trade_routes import router as trade_routes_router
from .power_assessment import router as power_assessment_router
from .text_summary import router as text_summary_router

router = APIRouter()

router.include_router(stored_reports_router)
router.include_router(power_blocs_router)
router.include_router(trade_routes_router)
router.include_router(power_assessment_router)
router.include_router(text_summary_router)


# ============================================================================
# Background Cache Refresh
# ============================================================================

async def refresh_expensive_caches():
    """
    Background task to refresh expensive cached endpoints before they expire.
    Prevents users from experiencing slow uncached requests.

    This function is called periodically by the background task in main.py.
    """
    import logging
    import httpx
    logger = logging.getLogger(__name__)

    try:
        from .power_blocs import get_power_blocs_live
        from .power_assessment import get_power_assessment

        # Refresh power-blocs/live for default timeframe (24h)
        logger.info("Background refresh: power-blocs/live (24h)")
        await get_power_blocs_live(minutes=1440)

        # Refresh power-assessment for default timeframe (24h)
        logger.info("Background refresh: power-assessment (24h)")
        await get_power_assessment(minutes=1440)

        # Warm top alliance intelligence endpoints (offensive is heaviest)
        # Top 5 alliances by activity
        TOP_ALLIANCE_IDS = [99003581, 1354830081, 99005338, 498125261, 99003214]
        DAYS = 7

        async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
            for alliance_id in TOP_ALLIANCE_IDS:
                try:
                    await client.get(f"/api/intelligence/alliance/{alliance_id}/offensive-stats?days={DAYS}")
                    logger.debug(f"Warmed offensive for alliance {alliance_id}")
                except Exception as e:
                    logger.warning(f"Failed to warm offensive for {alliance_id}: {e}")

        logger.info("Background cache refresh completed successfully")
    except Exception as e:
        logger.error(f"Background cache refresh failed: {e}")


def refresh_expensive_caches_sync():
    """Sync version for APScheduler background thread.

    Creates a dedicated event loop, runs the async refresh, then closes it.
    Avoids asyncio.run() which can conflict with the running FastAPI event loop.
    """
    import asyncio
    import logging
    logger = logging.getLogger(__name__)

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(refresh_expensive_caches())
    except Exception as e:
        logger.error(f"Sync cache refresh failed: {e}")
    finally:
        loop.close()


__all__ = ["router", "refresh_expensive_caches", "refresh_expensive_caches_sync", "get_power_blocs_live", "get_alliance_wars"]
