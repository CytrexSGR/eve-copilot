#!/usr/bin/env python3
"""
War Economy Price History Snapshotter
Runs every 30 minutes to capture price history for manipulation detection.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from datetime import datetime
import logging

from src.database import get_db_connection
from services.war_economy.config import CRITICAL_ITEMS

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


def snapshot_prices():
    """Snapshot current prices for critical items."""
    snapshot_time = datetime.utcnow()
    type_ids = list(CRITICAL_ITEMS.values())

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get current prices from market_prices table
            cur.execute('''
                SELECT
                    region_id, type_id,
                    lowest_sell, highest_buy,
                    sell_volume, buy_volume
                FROM market_prices
                WHERE region_id = ANY(%s)
                AND type_id = ANY(%s)
            ''', (MONITORED_REGIONS, type_ids))

            rows = cur.fetchall()

            if not rows:
                logger.warning("No market prices found for critical items")
                return 0

            # Insert snapshots
            inserted = 0
            for row in rows:
                region_id, type_id, lowest_sell, highest_buy, sell_vol, buy_vol = row

                cur.execute('''
                    INSERT INTO war_economy_price_history (
                        snapshot_time, region_id, type_id,
                        lowest_sell, highest_buy, sell_volume, buy_volume
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (snapshot_time, region_id, type_id) DO NOTHING
                ''', (
                    snapshot_time, region_id, type_id,
                    lowest_sell, highest_buy, sell_vol, buy_vol
                ))

                if cur.rowcount > 0:
                    inserted += 1

            conn.commit()
            return inserted


def main():
    """Main execution function"""
    try:
        logger.info("Starting War Economy price snapshot")
        start_time = datetime.utcnow()

        inserted = snapshot_prices()

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Price snapshot complete: {inserted} records in {duration:.1f}s")

        return 0

    except Exception as e:
        logger.error(f"Fatal error in price snapshot job: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
