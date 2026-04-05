#!/usr/bin/env python3
"""
Wormhole Commodity Price History Snapshotter
Runs daily to capture WH commodity prices for sparklines and trend analysis.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))

from datetime import datetime, date
import logging

from src.database import get_db_connection

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Jita region for price data
JITA_REGION_ID = 10000002

# WH Commodities to track
FULLERITE_GAS = {
    30378: 'Fullerite-C540',
    30377: 'Fullerite-C320',
    30374: 'Fullerite-C84',
    30373: 'Fullerite-C72',
    30372: 'Fullerite-C70',
    30371: 'Fullerite-C60',
    30370: 'Fullerite-C50',
    30376: 'Fullerite-C32',
    30375: 'Fullerite-C28',
}

BLUE_LOOT = {
    30259: 'Melted Nanoribbons',
    30022: 'Heuristic Selfassemblers',
    30270: 'Central System Controller',
    30018: 'Fused Nanomechanical Engines',
    30024: 'Cartesian Temporal Coordinator',
    30019: 'Powdered C-540 Graphite',
}

HYBRID_POLYMERS = {
    30309: 'Graphene Nanoribbons',
    30310: 'C3-FTM Acid',
    30311: 'PPD Fullerene Fibers',
    30312: 'Nanotori Polymers',
    30313: 'Lanthanum Metallofullerene',
    30314: 'Scandium Metallofullerene',
    30305: 'Fullerene Intercalated Sheets',
    30306: 'Carbon-86 Epoxy Resin',
}


def snapshot_prices():
    """Snapshot current prices for WH commodities."""
    snapshot_date = date.today()

    # All type IDs
    all_types = {
        **{tid: ('gas', name) for tid, name in FULLERITE_GAS.items()},
        **{tid: ('blue_loot', name) for tid, name in BLUE_LOOT.items()},
        **{tid: ('polymer', name) for tid, name in HYBRID_POLYMERS.items()},
    }

    type_ids = list(all_types.keys())

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get current prices from market_prices table
            cur.execute('''
                SELECT
                    type_id,
                    lowest_sell,
                    highest_buy,
                    avg_daily_volume
                FROM market_prices
                WHERE region_id = %s
                AND type_id = ANY(%s)
            ''', (JITA_REGION_ID, type_ids))

            rows = cur.fetchall()

            if not rows:
                logger.warning("No market prices found for WH commodities")
                return 0

            # Insert snapshots
            inserted = 0
            for row in rows:
                type_id, lowest_sell, highest_buy, daily_volume = row
                category = all_types.get(type_id, ('unknown', 'Unknown'))[0]

                cur.execute('''
                    INSERT INTO wh_commodity_price_history (
                        snapshot_date, type_id, category,
                        sell_price, buy_price, daily_volume
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (type_id, snapshot_date) DO UPDATE SET
                        sell_price = EXCLUDED.sell_price,
                        buy_price = EXCLUDED.buy_price,
                        daily_volume = EXCLUDED.daily_volume
                ''', (
                    snapshot_date, type_id, category,
                    lowest_sell, highest_buy, daily_volume
                ))

                inserted += 1

            conn.commit()
            return inserted


def backfill_from_current():
    """
    Backfill historical data by inserting today's prices.
    Call this once to bootstrap the history table.
    """
    return snapshot_prices()


def main():
    """Main execution function"""
    try:
        logger.info("Starting WH Commodity price snapshot")
        start_time = datetime.utcnow()

        inserted = snapshot_prices()

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"WH Commodity snapshot complete: {inserted} records in {duration:.1f}s")

        return 0

    except Exception as e:
        logger.error(f"Fatal error in WH commodity snapshot job: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
