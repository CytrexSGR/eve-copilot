#!/usr/bin/env python3
"""
War Economy Fuel Market Poller
Runs every 5 minutes to track isotope market anomalies for capital movement prediction.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from datetime import datetime
import logging
from typing import List

from src.database import get_db_connection
from src.services.market.service import market_service
from services.war_economy.service import WarEconomyService
from src.notification_service import notification_service
from config import REGIONS

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
        logger.info("Starting War Economy fuel market polling")
        start_time = datetime.utcnow()

        # Initialize service
        db_pool = SimpleDBPool()
        war_economy = WarEconomyService(db_pool, market_service)

        # Scan fuel markets
        logger.info(f"Scanning {len(MONITORED_REGIONS)} regions for fuel anomalies")
        anomalies = war_economy.scan_fuel_markets(MONITORED_REGIONS)

        # Log results
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Fuel scan complete: {len(anomalies)} anomalies detected in {duration:.1f}s")

        # Alert on critical anomalies
        critical_anomalies = [a for a in anomalies if a.severity in ('critical', 'high')]
        if critical_anomalies:
            alert_message = f"**War Economy Alert**: {len(critical_anomalies)} critical fuel anomalies detected!\n\n"
            for anomaly in critical_anomalies[:5]:  # Limit to top 5
                alert_message += f"• **{anomaly.severity.upper()}**: {anomaly.isotope_type} in {anomaly.region_name}\n"
                alert_message += f"  Volume: {anomaly.volume_delta_percent:+.1f}% change\n"

            # Send Discord notification
            embed = {
                "title": "War Economy Fuel Alert",
                "description": alert_message,
                "color": 0xFF0000 if any(a.severity == 'critical' for a in critical_anomalies) else 0xFFA500,
                "timestamp": datetime.utcnow().isoformat()
            }

            notification_service.send_discord_webhook(embeds=[embed])
            logger.info(f"Sent Discord alert for {len(critical_anomalies)} critical anomalies")

        logger.info("Fuel polling job complete")
        return 0

    except Exception as e:
        logger.error(f"Fatal error in fuel polling job: {e}", exc_info=True)

        # Send error notification
        try:
            embed = {
                "title": "War Economy Fuel Poller Error",
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
