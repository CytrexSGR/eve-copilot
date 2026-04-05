"""
Battle Events Router - API endpoints for battle event detection and retrieval.

Provides endpoints for:
- GET /battle - Get recent events with filters
- GET /battle/summary - Event summary statistics
- POST /battle/detect - Manual trigger for event detection
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Query

from app.services.events.models import (
    BattleEvent,
    BattleEventResponse,
    BattleEventType,
    BattleEventSeverity,
)
from app.repository.battle_events import battle_events_repo
from app.services.events.detector import battle_event_detector

logger = logging.getLogger(__name__)

router = APIRouter()


# ==============================================================================
# Models
# ==============================================================================

# Using models from app.services.events.models


# ==============================================================================
# Endpoints
# ==============================================================================

@router.get("/battle", response_model=BattleEventResponse)
def get_recent_events(
    since: Optional[datetime] = Query(
        None, description="Return events detected after this datetime (UTC)"
    ),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of events to return"),
    severity: Optional[BattleEventSeverity] = Query(
        None, description="Filter by severity level"
    ),
    event_types: Optional[List[BattleEventType]] = Query(
        None, description="Filter by event types"
    ),
) -> BattleEventResponse:
    """
    Get recent battle events with optional filters.

    - **since**: Only return events detected after this timestamp
    - **limit**: Maximum number of events (default 50, max 500)
    - **severity**: Filter by severity (critical, high, medium, low)
    - **event_types**: Filter by one or more event types
    """
    events = battle_events_repo.get_recent_events(
        since=since,
        limit=limit,
        severity=severity,
        event_types=event_types,
    )

    return BattleEventResponse(
        events=events,
        total=len(events),
        since=since,
    )


@router.get("/battle/summary")
def get_event_summary() -> Dict[str, Any]:
    """
    Get summary statistics for recent battle events.

    Returns counts by severity and event type for the last 24 hours.
    """
    # Get all events from last 24 hours (use a high limit)
    events = battle_events_repo.get_recent_events(limit=1000)

    # Count by severity
    by_severity: Dict[str, int] = {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
    }

    # Count by event type
    by_type: Dict[str, int] = {}

    for event in events:
        # Severity count
        sev = event.severity
        if hasattr(sev, 'value'):
            sev = sev.value
        if sev in by_severity:
            by_severity[sev] += 1

        # Type count
        evt_type = event.event_type
        if hasattr(evt_type, 'value'):
            evt_type = evt_type.value
        by_type[evt_type] = by_type.get(evt_type, 0) + 1

    return {
        "total_events": len(events),
        "by_severity": by_severity,
        "by_type": by_type,
    }


@router.get("/battle/last-supercaps")
def get_last_supercaps() -> Dict[str, Any]:
    """
    Get info about last Titan and Supercarrier kills.

    Returns when the last Titan and Supercarrier were killed,
    useful for displaying "Last Titan: X ago" in tickers.
    """
    supercap_events = battle_event_detector._detect_last_supercaps()

    result = {}
    for event in supercap_events:
        event_type = event.event_type.value if hasattr(event.event_type, 'value') else event.event_type
        result[event_type] = {
            "title": event.title,
            "description": event.description,
            "system_name": event.system_name,
            "region_name": event.region_name,
            "alliance_name": event.alliance_name,
            "event_time": event.event_time.isoformat() if event.event_time else None,
            "event_data": event.event_data,
        }

    return result


@router.post("/battle/detect")
def trigger_detection() -> Dict[str, Any]:
    """
    Manually trigger event detection.

    Runs the detection cycle immediately and returns the count of detected events.
    This is useful for testing or forcing an immediate scan outside the normal schedule.
    """
    logger.info("Manual event detection triggered")

    detected_events = battle_event_detector.run_detection()

    return {
        "status": "completed",
        "detected": len(detected_events),
        "events": [
            {
                "type": e.event_type.value if hasattr(e.event_type, 'value') else e.event_type,
                "severity": e.severity.value if hasattr(e.severity, 'value') else e.severity,
                "title": e.title,
            }
            for e in detected_events
        ],
    }
