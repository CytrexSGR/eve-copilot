"""Internal endpoints for scheduler-triggered jobs."""
import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.services.importer import WormholeImporter
from app.services.repository import WormholeRepository
from app.services.resident_detector import ResidentDetector
from app.services.activity_tracker import ActivityTracker

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])
detector = ResidentDetector()
tracker = ActivityTracker()


@router.post("/sync-pathfinder")
@handle_endpoint_errors()
async def sync_pathfinder():
    """Sync wormhole static data from Pathfinder CSV with checksum-based change detection.

    Called by scheduler-service on a periodic basis.
    """
    started = datetime.utcnow()
    importer = WormholeImporter()
    repo = WormholeRepository()
    details = {"statics": 0, "wormholes": 0, "skipped": []}
    errors = []

    # Sync statics
    try:
        last = repo.get_last_import("pathfinder", "statics")
        checksum, data = await importer.fetch_statics()

        if checksum is None:
            errors.append("Failed to fetch statics")
        elif last and last["checksum"] == checksum:
            details["skipped"].append("statics")
        else:
            count = await asyncio.to_thread(repo.upsert_statics, data)
            await asyncio.to_thread(repo.record_import, "pathfinder", "statics", count, checksum)
            details["statics"] = count
            logger.info(f"Imported {count} system statics")
    except Exception as e:
        logger.error(f"Statics sync failed: {e}")
        errors.append(f"statics: {e}")

    # Sync wormhole extended
    try:
        last = repo.get_last_import("pathfinder", "wormholes")
        checksum, data = await importer.fetch_wormholes()

        if checksum is None:
            errors.append("Failed to fetch wormholes")
        elif last and last["checksum"] == checksum:
            details["skipped"].append("wormholes")
        else:
            count = await asyncio.to_thread(repo.upsert_wormhole_extended, data)
            await asyncio.to_thread(repo.record_import, "pathfinder", "wormholes", count, checksum)
            details["wormholes"] = count
            logger.info(f"Imported {count} wormhole types")
    except Exception as e:
        logger.error(f"Wormholes sync failed: {e}")
        errors.append(f"wormholes: {e}")

    elapsed = (datetime.utcnow() - started).total_seconds()
    status = "completed" if not errors else "partial"

    return {
        "status": status,
        "elapsed_seconds": round(elapsed, 2),
        "details": details,
        "errors": errors,
    }


@router.post("/refresh-stats")
@handle_endpoint_errors()
async def refresh_stats():
    """Refresh wormhole resident detection and activity statistics.

    Called by scheduler-service on a periodic basis.
    """
    started = datetime.utcnow()
    details = {}
    errors = []

    # Refresh residents
    try:
        count = await asyncio.to_thread(detector.refresh_residents, days=30)
        details["residents"] = count
        logger.info(f"Refreshed {count} resident records")
    except Exception as e:
        logger.error(f"Resident refresh failed: {e}")
        errors.append(f"residents: {e}")

    # Refresh activity stats
    try:
        count = await asyncio.to_thread(tracker.refresh_activity_stats)
        details["activity"] = count
        logger.info(f"Refreshed {count} activity records")
    except Exception as e:
        logger.error(f"Activity refresh failed: {e}")
        errors.append(f"activity: {e}")

    elapsed = (datetime.utcnow() - started).total_seconds()
    status = "completed" if not errors else "partial"

    return {
        "status": status,
        "elapsed_seconds": round(elapsed, 2),
        "details": details,
        "errors": errors,
    }
