#!/usr/bin/env python3
# jobs/market_undercut_checker.py
"""
Market undercut checker job.
Checks orders for undercuts and sends Discord notifications.

Runs: */15 * * * * (every 15 minutes)
"""

import sys
import os
import logging
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_settings():
    """Get notification settings from database."""
    from src.database import get_db_connection
    from psycopg2.extras import RealDictCursor

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT value FROM app_settings WHERE key = 'notifications'")
            row = cur.fetchone()

    if not row:
        return None
    return row['value']


def get_active_characters():
    """Get all authenticated character IDs."""
    from src.services.auth.repository import AuthRepository
    auth_repo = AuthRepository()
    auths = auth_repo.get_all_character_auths()
    return [a.character_id for a in auths]


def was_already_notified(character_id: int, order_id: int) -> bool:
    """Check if we already notified about this order today."""
    from src.database import get_db_connection

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT 1 FROM undercut_notifications
                WHERE character_id = %s AND order_id = %s
                  AND DATE(notified_at) = %s
            ''', (character_id, order_id, date.today()))
            return cur.fetchone() is not None


def mark_notified(character_id: int, order_id: int, type_id: int, your_price: float, market_price: float, undercut_percent: float):
    """Record that we notified about this order."""
    from src.database import get_db_connection

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO undercut_notifications
                (character_id, order_id, type_id, your_price, competitor_price, undercut_percent)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            ''', (character_id, order_id, type_id, your_price, market_price, undercut_percent))
            conn.commit()


def send_discord_notification(webhook_url: str, char_name: str, undercuts: list):
    """Send undercut notification to Discord."""
    from src.notification_service import NotificationService

    service = NotificationService(webhook_url)

    # Build embed fields
    fields = []
    for order in undercuts[:10]:  # Max 10 per message
        if order['is_buy_order']:
            emoji = "📈"
            status = "Outbid"
            diff = f"+{order['undercut_percent']:.1f}%"
        else:
            emoji = "📉"
            status = "Undercut"
            diff = f"-{order['undercut_percent']:.1f}%"

        fields.append({
            "name": f"{emoji} {order['type_name']}",
            "value": f"Your: {order['your_price']:,.2f} ISK\nMarket: {order['market_price']:,.2f} ISK\n{status} by {diff}",
            "inline": True
        })

    embed = {
        "title": "🔔 Market Alert: Orders Need Attention",
        "description": f"**{char_name}** has {len(undercuts)} order(s) that need updating",
        "color": 0xFF6B6B,  # Red-ish
        "fields": fields,
        "footer": {
            "text": "EVE Co-Pilot Market Monitor"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    return service.send_discord_webhook(embeds=[embed])


def main():
    """Check for undercuts and send notifications."""
    logger.info("Starting undercut checker")

    # Check settings
    settings = get_settings()
    if not settings:
        logger.info("No notification settings configured")
        return

    if not settings.get('alerts', {}).get('market_undercuts'):
        logger.info("Undercut alerts disabled")
        return

    webhook_url = settings.get('discord_webhook')
    if not webhook_url:
        logger.info("No Discord webhook configured")
        return

    # Get characters
    character_ids = get_active_characters()
    if not character_ids:
        logger.info("No authenticated characters")
        return

    logger.info(f"Checking {len(character_ids)} characters")

    # Check each character
    import requests

    for char_id in character_ids:
        try:
            # Get undercut report
            response = requests.get(
                f"{os.environ.get('API_GATEWAY_URL', 'http://api-gateway:8000')}/api/character/{char_id}/orders/undercuts",
                timeout=60
            )

            if response.status_code != 200:
                logger.warning(f"Failed to get undercuts for {char_id}")
                continue

            report = response.json()

            # Filter to new undercuts only
            new_undercuts = []
            for order in report.get('orders', []):
                if order.get('is_undercut'):
                    if not was_already_notified(char_id, order['order_id']):
                        new_undercuts.append(order)
                        mark_notified(
                            char_id, order['order_id'], order['type_id'],
                            order['your_price'], order['market_price'], order['undercut_percent']
                        )

            if new_undercuts:
                # Get character name
                char_response = requests.get(
                    f"{os.environ.get('API_GATEWAY_URL', 'http://api-gateway:8000')}/api/character/{char_id}/info",
                    timeout=30
                )
                char_name = char_response.json().get('name', f'Character {char_id}') if char_response.status_code == 200 else f'Character {char_id}'

                result = send_discord_notification(webhook_url, char_name, new_undercuts)
                if 'error' in result:
                    logger.error(f"Discord notification failed: {result['error']}")
                else:
                    logger.info(f"Notified about {len(new_undercuts)} undercuts for {char_name}")

        except Exception as e:
            logger.error(f"Error checking character {char_id}: {e}")

    logger.info("Undercut checker complete")


if __name__ == "__main__":
    main()
