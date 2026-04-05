"""PI alert configuration and listing endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Request, Query, Depends

from app.services.pi.repository import PIRepository
from app.services.pi.models import PIAlertLog, PIAlertConfig, PIAlertConfigUpdate
from ._helpers import get_pi_repository

router = APIRouter()


# ==================== PI Alert Endpoints ====================

@router.get("/alerts", response_model=List[PIAlertLog])
def get_pi_alerts(
    request: Request,
    character_id: Optional[int] = Query(None, description="Filter by character"),
    unread_only: bool = Query(False, description="Only unread alerts"),
    limit: int = Query(50, ge=1, le=200),
    repo: PIRepository = Depends(get_pi_repository)
):
    """
    Get PI alerts for all characters or a specific character.

    Returns alerts sorted by creation time (newest first).
    """
    alerts = repo.get_alerts(
        character_id=character_id,
        unread_only=unread_only,
        limit=limit
    )
    return [PIAlertLog(**dict(a)) for a in alerts]


@router.post("/alerts/read")
def mark_alerts_read(
    request: Request,
    alert_ids: List[int],
    repo: PIRepository = Depends(get_pi_repository)
):
    """Mark alerts as read."""
    count = repo.mark_alerts_read(alert_ids)
    return {"status": "ok", "updated": count}


@router.get("/alerts/config/{character_id}", response_model=PIAlertConfig)
def get_alert_config(
    request: Request,
    character_id: int,
    repo: PIRepository = Depends(get_pi_repository)
):
    """Get alert configuration for a character."""
    config = repo.get_alert_config(character_id)
    if not config:
        # Return defaults
        return PIAlertConfig(
            character_id=character_id,
            discord_enabled=True,
            extractor_warning_hours=12,
            extractor_critical_hours=4,
            storage_warning_percent=75,
            storage_critical_percent=90,
        )
    return PIAlertConfig(**dict(config))


@router.put("/alerts/config/{character_id}", response_model=PIAlertConfig)
def update_alert_config(
    request: Request,
    character_id: int,
    config: PIAlertConfigUpdate,
    repo: PIRepository = Depends(get_pi_repository)
):
    """Update alert configuration for a character."""
    config_dict = config.model_dump(exclude_none=True)
    result = repo.upsert_alert_config(character_id, config_dict)
    return PIAlertConfig(**dict(result))
