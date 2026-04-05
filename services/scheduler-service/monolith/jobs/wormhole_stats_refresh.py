"""Refresh wormhole activity stats and resident detection."""
import logging
import sys

sys.path.insert(0, '/home/cytrex/eve_copilot/services/wormhole-service')
from app.services.resident_detector import ResidentDetector
from app.services.activity_tracker import ActivityTracker

logger = logging.getLogger(__name__)


def refresh_wormhole_stats() -> dict:
    """Refresh all computed wormhole statistics."""
    result = {}

    # Refresh residents
    try:
        detector = ResidentDetector()
        count = detector.refresh_residents(days=30)
        result['residents'] = count
        logger.info(f"Refreshed {count} resident records")
    except Exception as e:
        logger.error(f"Resident refresh failed: {e}")
        result['residents_error'] = str(e)

    # Refresh activity stats
    try:
        tracker = ActivityTracker()
        count = tracker.refresh_activity_stats()
        result['activity'] = count
        logger.info(f"Refreshed {count} activity records")
    except Exception as e:
        logger.error(f"Activity refresh failed: {e}")
        result['activity_error'] = str(e)

    return result


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print(refresh_wormhole_stats())
