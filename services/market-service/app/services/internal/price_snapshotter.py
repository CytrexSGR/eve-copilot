"""War economy price history snapshotter.

Captures periodic price snapshots for critical items to enable
manipulation detection via Z-score analysis over time.
"""

import logging
from datetime import datetime, timezone

from eve_shared.constants import TRADE_HUB_REGIONS

logger = logging.getLogger(__name__)

# Critical items to snapshot
CRITICAL_ITEMS = {
    "Interdiction Nullifier": 37615,
    "Nanite Repair Paste": 28668,
    "Warp Disrupt Probe": 23265,
    "Mobile Cyno Inhibitor": 36912,
    "Strontium Clathrates": 16275,
}

MONITORED_REGIONS = list(TRADE_HUB_REGIONS.values())


def take_snapshot(db) -> int:
    """Take a snapshot of current market_prices for critical items.

    Returns number of records inserted.
    """
    snapshot_time = datetime.now(timezone.utc)
    type_ids = list(CRITICAL_ITEMS.values())

    with db.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT region_id, type_id, lowest_sell, highest_buy, sell_volume, buy_volume
                FROM market_prices
                WHERE region_id = ANY(%s) AND type_id = ANY(%s)
            """, (MONITORED_REGIONS, type_ids))
            rows = cur.fetchall()

            if not rows:
                logger.warning("No market prices found for critical items")
                return 0

            inserted = 0
            for region_id, type_id, lowest_sell, highest_buy, sell_vol, buy_vol in rows:
                cur.execute("""
                    INSERT INTO war_economy_price_history (
                        snapshot_time, region_id, type_id,
                        lowest_sell, highest_buy, sell_volume, buy_volume
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (snapshot_time, region_id, type_id) DO NOTHING
                """, (snapshot_time, region_id, type_id,
                      lowest_sell, highest_buy, sell_vol, buy_vol))
                if cur.rowcount > 0:
                    inserted += 1

            conn.commit()
            return inserted


def snapshot_prices(db) -> dict:
    """Snapshot prices for critical war economy items.

    Args:
        db: eve_shared DatabasePool instance.

    Returns:
        Job result dict.
    """
    start = datetime.now(timezone.utc)
    inserted = take_snapshot(db)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()

    logger.info(f"Price snapshot: {inserted} records in {elapsed:.1f}s")

    return {
        "status": "completed",
        "job": "snapshot-prices",
        "details": {
            "records_inserted": inserted,
            "critical_items": len(CRITICAL_ITEMS),
            "regions": len(MONITORED_REGIONS),
            "elapsed_seconds": round(elapsed, 2),
        },
    }
