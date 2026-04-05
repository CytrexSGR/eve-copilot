"""
Battle Event Detector Job

Scheduled job that runs the battle event detector to identify
capital kills, hot zone changes, and high-value kills.

Called by scheduler-service every minute.
"""

import logging
import sys
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_battle_event_detection() -> Dict[str, Any]:
    """
    Run the battle event detection cycle.

    Returns:
        Dict with detection results including event counts and any errors.
    """
    logger.info("Starting battle event detection")

    try:
        # Import detector here to avoid circular imports and ensure
        # fresh database connections
        from app.services.events.detector import battle_event_detector

        # Run detection
        events = battle_event_detector.run_detection()

        # Categorize events for logging
        event_counts = {}
        for event in events:
            et = event.event_type
            event_type = et.value if hasattr(et, 'value') else str(et)
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        result = {
            "success": True,
            "events_detected": len(events),
            "event_counts": event_counts,
            "errors": 0
        }

        if events:
            logger.info(f"Detection complete: {len(events)} events - {event_counts}")
        else:
            logger.debug("Detection complete: no new events")

        return result

    except Exception as e:
        logger.error(f"Battle event detection failed: {e}", exc_info=True)
        return {
            "success": False,
            "events_detected": 0,
            "event_counts": {},
            "errors": 1,
            "error_message": str(e)
        }


if __name__ == "__main__":
    # Allow running directly for testing
    result = run_battle_event_detection()
    print(f"Result: {result}")
    sys.exit(0 if result["success"] else 1)
