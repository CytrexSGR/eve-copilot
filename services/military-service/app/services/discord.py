"""Discord Webhook Notification Service.

Sends embed notifications to Discord channels via webhooks.
Uses notification_configs table for per-corp config and notification_log
for idempotency (UNIQUE on config_id, event_type, reference_id).
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.database import db_cursor

logger = logging.getLogger(__name__)

IMPORTANCE_COLORS = {
    "normal": 0x3498DB,     # blue
    "important": 0xF1C40F,  # yellow
    "cta": 0xE74C3C,        # red
}


async def send_discord_embed(
    webhook_url: str,
    embed: dict,
    ping_role: Optional[str] = None,
) -> bool:
    """Send a Discord embed message via webhook.

    Args:
        webhook_url: Discord webhook URL
        embed: Discord embed dict (title, description, color, fields, ...)
        ping_role: Optional Discord role ID to ping (e.g. "123456789")

    Returns:
        True if sent successfully, False otherwise.
    """
    embed.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    embed.setdefault("footer", {"text": "EVE Co-Pilot Fleet Notifications"})

    payload: dict = {"embeds": [embed]}
    if ping_role:
        payload["content"] = f"<@&{ping_role}>"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(webhook_url, json=payload)
        if resp.status_code in (200, 204):
            return True
        logger.warning(
            "Discord webhook returned %s: %s", resp.status_code, resp.text[:300]
        )
        return False
    except httpx.RequestError as exc:
        logger.error("Discord webhook request failed: %s", exc)
        return False


async def notify_event(
    event_type: str,
    reference_id: int,
    corp_id: int,
    embed: dict,
) -> int:
    """Find matching notification_configs for corp and send embed.

    Uses idempotency check via notification_log table
    (UNIQUE on config_id, event_type, reference_id) to prevent duplicates.

    Args:
        event_type: One of op_created, op_reminder, fleet_started, fleet_closed
        reference_id: ID of the operation or fleet
        corp_id: Corporation ID to match configs
        embed: Discord embed dict

    Returns:
        Number of notifications successfully sent.
    """
    sent_count = 0

    with db_cursor() as cur:
        cur.execute(
            """
            SELECT id, webhook_url, ping_role
            FROM notification_configs
            WHERE corporation_id = %s
              AND is_active = TRUE
              AND %s = ANY(event_types)
            """,
            (corp_id, event_type),
        )
        configs = cur.fetchall()

    for cfg in configs:
        # Idempotency: skip if already logged
        with db_cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM notification_log
                WHERE config_id = %s AND event_type = %s AND reference_id = %s
                """,
                (cfg["id"], event_type, reference_id),
            )
            if cur.fetchone():
                logger.debug(
                    "Skipping duplicate notification config=%s event=%s ref=%s",
                    cfg["id"], event_type, reference_id,
                )
                continue

        success = await send_discord_embed(
            cfg["webhook_url"], embed.copy(), cfg.get("ping_role")
        )

        # Log the attempt (success or failure)
        error_msg = None if success else "Webhook delivery failed"
        with db_cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO notification_log
                        (config_id, event_type, reference_id, success, error_message)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (cfg["id"], event_type, reference_id, success, error_msg),
                )
            except Exception:
                # UNIQUE violation = already sent (race condition), just skip
                logger.debug("Duplicate notification log entry, skipping")

        if success:
            sent_count += 1

    if configs:
        logger.info(
            "Notified %d/%d configs for event=%s ref=%s corp=%s",
            sent_count, len(configs), event_type, reference_id, corp_id,
        )

    return sent_count


def build_op_created_embed(op: dict) -> dict:
    """Build Discord embed for a newly created scheduled operation.

    Color-coded by importance: normal=blue, important=yellow, CTA=red.
    """
    importance = op.get("importance", "normal")
    color = IMPORTANCE_COLORS.get(importance, 0x3498DB)

    fields = [
        {"name": "FC", "value": op.get("fc_name", "TBD"), "inline": True},
        {"name": "Type", "value": op.get("op_type", "fleet"), "inline": True},
        {"name": "Importance", "value": importance.upper(), "inline": True},
    ]

    if op.get("formup_system"):
        fields.append(
            {"name": "System", "value": op["formup_system"], "inline": True}
        )
    if op.get("formup_time"):
        ft = op["formup_time"]
        if isinstance(ft, datetime):
            ft = ft.strftime("%Y-%m-%d %H:%M UTC")
        fields.append({"name": "Formup Time", "value": str(ft), "inline": True})
    if op.get("doctrine_name"):
        fields.append(
            {"name": "Doctrine", "value": op["doctrine_name"], "inline": True}
        )
    if op.get("max_pilots"):
        fields.append(
            {"name": "Max Pilots", "value": str(op["max_pilots"]), "inline": True}
        )

    return {
        "title": f"New Op: {op.get('title', 'Unknown')}",
        "description": op.get("description") or "",
        "color": color,
        "fields": fields,
    }


def build_fleet_started_embed(
    fleet_name: str,
    fc_name: Optional[str] = None,
    member_count: int = 0,
) -> dict:
    """Build Discord embed for a fleet that just started. Green color."""
    fields = []
    if fc_name:
        fields.append({"name": "FC", "value": fc_name, "inline": True})
    if member_count:
        fields.append(
            {"name": "Pilots", "value": str(member_count), "inline": True}
        )

    return {
        "title": f"Fleet Up: {fleet_name}",
        "description": "A new fleet has been registered.",
        "color": 0x2ECC71,  # green
        "fields": fields,
    }


def build_fleet_closed_embed(
    fleet_name: str,
    total_pilots: int = 0,
    duration_min: float = 0,
) -> dict:
    """Build Discord embed for a fleet that was closed. Gray color."""
    duration_str = f"{int(duration_min)}min"
    if duration_min >= 60:
        hours = int(duration_min // 60)
        mins = int(duration_min % 60)
        duration_str = f"{hours}h {mins}min"

    fields = [
        {"name": "Duration", "value": duration_str, "inline": True},
        {"name": "Total Pilots", "value": str(total_pilots), "inline": True},
    ]

    return {
        "title": f"Fleet Closed: {fleet_name}",
        "description": "The fleet operation has ended.",
        "color": 0x95A5A6,  # gray
        "fields": fields,
    }
