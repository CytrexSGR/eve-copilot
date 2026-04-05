"""
Settings Router - Global app settings including notifications.

Migrated from monolith to auth-service microservice.
"""

import json
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.database import db_cursor

logger = logging.getLogger(__name__)

router = APIRouter()


class NotificationAlerts(BaseModel):
    """Notification alert configuration."""
    market_undercuts: bool = False
    pi_expiry: bool = False
    skill_complete: bool = False
    low_wallet: bool = False


class NotificationSettings(BaseModel):
    """Notification settings model."""
    discord_webhook: Optional[str] = None
    alerts: NotificationAlerts = Field(default_factory=NotificationAlerts)
    check_frequency_minutes: int = Field(default=15, ge=5, le=60)
    low_wallet_threshold: int = Field(default=100000000, ge=0)


@router.get("/notifications", response_model=NotificationSettings)
def get_notification_settings():
    """
    Get current notification settings.

    Returns:
        NotificationSettings with webhook and alert config
    """
    with db_cursor() as cur:
        cur.execute("SELECT value FROM app_settings WHERE key = 'notifications'")
        row = cur.fetchone()

    if not row:
        return NotificationSettings()

    data = row['value']
    return NotificationSettings(
        discord_webhook=data.get('discord_webhook'),
        alerts=NotificationAlerts(**data.get('alerts', {})),
        check_frequency_minutes=data.get('check_frequency_minutes', 15),
        low_wallet_threshold=data.get('low_wallet_threshold', 100000000)
    )


@router.put("/notifications", response_model=NotificationSettings)
def update_notification_settings(settings: NotificationSettings):
    """
    Update notification settings.

    Args:
        settings: New notification settings

    Returns:
        Updated NotificationSettings
    """
    value = {
        "discord_webhook": settings.discord_webhook,
        "alerts": settings.alerts.model_dump(),
        "check_frequency_minutes": settings.check_frequency_minutes,
        "low_wallet_threshold": settings.low_wallet_threshold
    }

    with db_cursor() as cur:
        cur.execute('''
            INSERT INTO app_settings (key, value, updated_at)
            VALUES ('notifications', %s, NOW())
            ON CONFLICT (key) DO UPDATE SET
                value = EXCLUDED.value,
                updated_at = NOW()
        ''', (json.dumps(value),))

    logger.info("Notification settings updated")
    return settings


@router.post("/notifications/test")
def test_notification():
    """
    Send a test notification to configured webhook.

    Returns:
        Dict with success status
    """
    # Import locally to avoid circular imports and dependency issues
    try:
        from notification_service import NotificationService
    except ImportError:
        # Fallback: notification service not available in this microservice
        raise HTTPException(
            status_code=501,
            detail="Notification service not available in auth-service. Use the main API gateway."
        )

    # Get current settings
    with db_cursor() as cur:
        cur.execute("SELECT value FROM app_settings WHERE key = 'notifications'")
        row = cur.fetchone()

    if not row or not row['value'].get('discord_webhook'):
        raise HTTPException(status_code=400, detail="No webhook configured")

    webhook_url = row['value']['discord_webhook']

    service = NotificationService(webhook_url)
    result = service.send_test_message()

    if 'error' in result:
        raise HTTPException(status_code=500, detail=result['error'])

    return {"success": True, "message": "Test notification sent"}
