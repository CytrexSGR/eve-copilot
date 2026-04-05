#!/usr/bin/env python3
"""
War Economy Market Manipulation Scanner
Runs every 15 minutes to detect market manipulation patterns using Z-score analysis.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from datetime import datetime
import logging

from src.database import get_db_connection
from src.services.market.service import market_service
from services.war_economy.service import WarEconomyService
from src.notification_service import notification_service

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Trade hub regions to monitor
MONITORED_REGIONS = [
    10000002,  # The Forge (Jita)
    10000043,  # Domain (Amarr)
    10000030,  # Heimatar (Rens)
    10000032,  # Sinq Laison (Dodixie)
    10000042   # Metropolis (Hek)
]


class SimpleDBPool:
    """Simple DB pool using context manager"""
    @staticmethod
    def get_connection():
        return get_db_connection()


def main():
    """Main execution function"""
    try:
        logger.info("Starting War Economy manipulation scanning")
        start_time = datetime.utcnow()

        # Initialize service
        db_pool = SimpleDBPool()
        war_economy = WarEconomyService(db_pool, market_service)

        # Scan all regions
        all_alerts = []
        for region_id in MONITORED_REGIONS:
            logger.info(f"Scanning region {region_id} for manipulation")
            alerts = war_economy.scan_manipulation(region_id, days_lookback=30)
            all_alerts.extend(alerts)

        # Log results
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Manipulation scan complete: {len(all_alerts)} alerts in {duration:.1f}s")

        # Group and notify
        if all_alerts:
            # Group by severity
            confirmed = [a for a in all_alerts if a.severity == 'confirmed']
            probable = [a for a in all_alerts if a.severity == 'probable']
            suspicious = [a for a in all_alerts if a.severity == 'suspicious']

            # Send batched alert
            if confirmed or probable:
                alert_message = "**Market Manipulation Detected**\n\n"

                if confirmed:
                    alert_message += f"**Confirmed** ({len(confirmed)}): Z-score >= 4.0\n"
                    for alert in confirmed[:3]:
                        alert_message += f"  • {alert.type_name} in {alert.region_name}\n"
                        alert_message += f"    Price: {alert.price_change_percent:+.1f}% | Volume: {alert.volume_change_percent:+.1f}%\n"

                if probable:
                    alert_message += f"\n**Probable** ({len(probable)}): Z-score >= 3.0\n"
                    for alert in probable[:2]:
                        alert_message += f"  • {alert.type_name} in {alert.region_name}\n"

                # Send Discord notification (DISABLED 2026-01-19)
                # embed = {
                #     "title": "War Economy Manipulation Alert",
                #     "description": alert_message,
                #     "color": 0xFF0000 if confirmed else 0xFFA500,
                #     "timestamp": datetime.utcnow().isoformat()
                # }
                #
                # notification_service.send_discord_webhook(embeds=[embed])
                logger.info(f"Detected {len(confirmed)} confirmed + {len(probable)} probable manipulations (Discord disabled)")

        logger.info("Manipulation scanning job complete")
        return 0

    except Exception as e:
        logger.error(f"Fatal error in manipulation scanner: {e}", exc_info=True)

        # Send error notification
        try:
            embed = {
                "title": "War Economy Manipulation Scanner Error",
                "description": f"```{str(e)}```",
                "color": 0xFF0000,
                "timestamp": datetime.utcnow().isoformat()
            }
            notification_service.send_discord_webhook(embeds=[embed])
        except Exception as notify_error:
            logger.error(f"Failed to send error notification: {notify_error}")

        return 1


if __name__ == "__main__":
    sys.exit(main())
