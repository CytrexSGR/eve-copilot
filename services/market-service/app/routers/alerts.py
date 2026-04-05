"""
Trading Alerts Router.
Migrated from monolith to market-service.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Body

from app.services.trading.alerts import (
    TradingAlertsService,
    AlertEntry,
    AlertConfig,
    AlertsResponse,
)
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["Trading Alerts"])


def get_alerts_service(request: Request) -> TradingAlertsService:
    """Dependency injection for alerts service."""
    db = request.app.state.db
    return TradingAlertsService(db)


@router.get("/{character_id}", response_model=AlertsResponse)
@handle_endpoint_errors()
def get_alerts(
    request: Request,
    character_id: int,
    limit: int = Query(50, ge=1, le=200),
    unread_only: bool = Query(False),
    alert_type: Optional[str] = Query(None),
):
    """
    Get trading alerts for a character.

    Args:
        character_id: EVE Online character ID
        limit: Maximum alerts to return
        unread_only: Only return unread alerts
        alert_type: Filter by alert type

    Returns:
        AlertsResponse with alerts and counts
    """
    service = get_alerts_service(request)
    return service.get_alerts(character_id, limit, unread_only, alert_type)


@router.post("/{character_id}/mark-read")
@handle_endpoint_errors()
def mark_alerts_read(
    request: Request,
    character_id: int,
    alert_ids: Optional[List[int]] = Body(None),
):
    """
    Mark alerts as read.

    Args:
        character_id: EVE Online character ID
        alert_ids: Specific alert IDs (None = mark all)

    Returns:
        Number of alerts marked
    """
    service = get_alerts_service(request)
    count = service.mark_read(character_id, alert_ids)
    return {"marked_count": count}


@router.get("/{character_id}/config", response_model=AlertConfig)
@handle_endpoint_errors()
def get_alert_config(
    request: Request,
    character_id: int,
):
    """
    Get alert configuration for a character.

    Args:
        character_id: EVE Online character ID

    Returns:
        AlertConfig with Discord settings
    """
    service = get_alerts_service(request)
    return service.get_config(character_id)


@router.put("/{character_id}/config", response_model=AlertConfig)
@handle_endpoint_errors()
def update_alert_config(
    request: Request,
    character_id: int,
    discord_webhook_url: Optional[str] = Body(None),
    discord_enabled: bool = Body(False),
    alert_margin_threshold: float = Body(10.0),
    alert_undercut_enabled: bool = Body(True),
    alert_velocity_enabled: bool = Body(True),
    alert_goals_enabled: bool = Body(True),
    min_alert_interval_minutes: int = Body(15),
    quiet_hours_start: Optional[int] = Body(None),
    quiet_hours_end: Optional[int] = Body(None),
):
    """
    Update alert configuration.

    Args:
        character_id: EVE Online character ID
        Various config options

    Returns:
        Updated AlertConfig
    """
    service = get_alerts_service(request)
    config = AlertConfig(
        character_id=character_id,
        discord_webhook_url=discord_webhook_url,
        discord_enabled=discord_enabled,
        alert_margin_threshold=alert_margin_threshold,
        alert_undercut_enabled=alert_undercut_enabled,
        alert_velocity_enabled=alert_velocity_enabled,
        alert_goals_enabled=alert_goals_enabled,
        min_alert_interval_minutes=min_alert_interval_minutes,
        quiet_hours_start=quiet_hours_start,
        quiet_hours_end=quiet_hours_end
    )
    return service.update_config(config)


@router.post("/{character_id}/test-discord")
@handle_endpoint_errors()
def test_discord_webhook(
    request: Request,
    character_id: int,
):
    """
    Test Discord webhook by sending a test message.

    Args:
        character_id: EVE Online character ID

    Returns:
        Success status
    """
    service = get_alerts_service(request)
    success = service.test_discord_webhook(character_id)
    return {
        "success": success,
        "message": "Test notification sent!" if success else "Failed to send notification"
    }
