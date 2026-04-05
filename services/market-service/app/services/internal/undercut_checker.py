"""Market undercut checker.

Checks character sell/buy orders for undercuts and records
notifications to avoid duplicate alerts.
"""

import logging
import os
from datetime import date, datetime, timezone

import httpx

logger = logging.getLogger(__name__)

AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:8000")
API_GATEWAY_URL = os.environ.get("API_GATEWAY_URL", "http://api-gateway:8000")


def get_notification_settings(db) -> dict | None:
    """Fetch notification settings from app_settings."""
    with db.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM app_settings WHERE key = 'notifications'")
            row = cur.fetchone()
            return row[0] if row else None


def get_active_character_ids() -> list[int]:
    """Fetch authenticated character IDs from auth-service."""
    try:
        resp = httpx.get(f"{AUTH_SERVICE_URL}/api/auth/characters", timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return [c["character_id"] for c in data if "character_id" in c]
    except Exception as e:
        logger.error(f"Failed to fetch characters: {e}")
    return []


def was_already_notified(db, character_id: int, order_id: int) -> bool:
    """Check if this order was already notified today."""
    with db.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM undercut_notifications
                WHERE character_id = %s AND order_id = %s AND DATE(notified_at) = %s
                """,
                (character_id, order_id, date.today()),
            )
            return cur.fetchone() is not None


def mark_notified(db, character_id: int, order_id: int, type_id: int,
                  your_price: float, market_price: float, undercut_pct: float):
    """Record notification for dedup."""
    with db.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO undercut_notifications
                (character_id, order_id, type_id, your_price, competitor_price, undercut_percent)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (character_id, order_id, type_id, your_price, market_price, undercut_pct),
            )
            conn.commit()


def check_undercuts(db) -> dict:
    """Check all characters for undercut orders.

    Args:
        db: eve_shared DatabasePool instance.

    Returns:
        Job result dict.
    """
    start = datetime.now(timezone.utc)

    # Check settings
    settings = get_notification_settings(db)
    if not settings:
        return {
            "status": "completed",
            "job": "check-undercuts",
            "details": {"skipped": True, "reason": "no_settings"},
        }

    if not settings.get("alerts", {}).get("market_undercuts"):
        return {
            "status": "completed",
            "job": "check-undercuts",
            "details": {"skipped": True, "reason": "alerts_disabled"},
        }

    character_ids = get_active_character_ids()
    if not character_ids:
        return {
            "status": "completed",
            "job": "check-undercuts",
            "details": {"skipped": True, "reason": "no_characters"},
        }

    total_undercuts = 0
    characters_checked = 0

    for char_id in character_ids:
        try:
            resp = httpx.get(
                f"{API_GATEWAY_URL}/api/character/{char_id}/orders/undercuts",
                timeout=60,
            )
            if resp.status_code != 200:
                logger.warning(f"Undercut check failed for {char_id}: HTTP {resp.status_code}")
                continue

            characters_checked += 1
            report = resp.json()
            new_undercuts = []

            for order in report.get("orders", []):
                if order.get("is_undercut"):
                    if not was_already_notified(db, char_id, order["order_id"]):
                        new_undercuts.append(order)
                        mark_notified(
                            db, char_id, order["order_id"], order["type_id"],
                            order["your_price"], order["market_price"],
                            order["undercut_percent"],
                        )

            total_undercuts += len(new_undercuts)
            if new_undercuts:
                logger.info(f"Character {char_id}: {len(new_undercuts)} new undercuts")

        except Exception as e:
            logger.error(f"Error checking character {char_id}: {e}")

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()

    return {
        "status": "completed",
        "job": "check-undercuts",
        "details": {
            "characters_checked": characters_checked,
            "total_new_undercuts": total_undercuts,
            "elapsed_seconds": round(elapsed, 2),
        },
    }
