"""Notification service for scheduler alerts."""

import logging
import requests
from datetime import datetime
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def send_job_failure_alert(
    job_id: str,
    error_message: str,
    job_name: Optional[str] = None
) -> bool:
    """Send Discord alert for a failed job.

    Args:
        job_id: The job identifier
        error_message: Error message from the failure
        job_name: Human-readable job name

    Returns:
        True if alert sent successfully
    """
    webhook_url = settings.discord_webhook_url
    if not webhook_url:
        logger.warning("Discord webhook URL not configured, skipping alert")
        return False

    embed = {
        "title": "Scheduler Job Failed",
        "description": f"**{job_name or job_id}** failed to execute",
        "color": 0xFF0000,  # Red
        "fields": [
            {
                "name": "Job ID",
                "value": f"`{job_id}`",
                "inline": True
            },
            {
                "name": "Time",
                "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "inline": True
            },
            {
                "name": "Error",
                "value": f"```{error_message[:500]}```" if error_message else "Unknown error",
                "inline": False
            }
        ],
        "footer": {
            "text": "EVE Co-Pilot Scheduler"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        response = requests.post(
            webhook_url,
            json={
                "username": "EVE Scheduler",
                "embeds": [embed]
            },
            timeout=10
        )

        if response.status_code in (200, 204):
            logger.info(f"Failure alert sent for job: {job_id}")
            return True
        else:
            logger.error(f"Discord API error: {response.status_code}")
            return False

    except Exception as e:
        logger.error(f"Failed to send Discord alert: {e}")
        return False


def send_job_recovery_alert(job_id: str, job_name: Optional[str] = None) -> bool:
    """Send Discord alert when a previously failed job succeeds.

    Args:
        job_id: The job identifier
        job_name: Human-readable job name

    Returns:
        True if alert sent successfully
    """
    webhook_url = settings.discord_webhook_url
    if not webhook_url:
        return False

    embed = {
        "title": "Job Recovered",
        "description": f"**{job_name or job_id}** is running again",
        "color": 0x00FF00,  # Green
        "fields": [
            {
                "name": "Job ID",
                "value": f"`{job_id}`",
                "inline": True
            },
            {
                "name": "Time",
                "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "inline": True
            }
        ],
        "footer": {
            "text": "EVE Co-Pilot Scheduler"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    try:
        response = requests.post(
            webhook_url,
            json={
                "username": "EVE Scheduler",
                "embeds": [embed]
            },
            timeout=10
        )
        return response.status_code in (200, 204)
    except Exception as e:
        logger.error(f"Failed to send recovery alert: {e}")
        return False
