#!/usr/bin/env python3
"""
Backfill Price History from ESI Market History

One-time script to populate war_economy_price_history with historical data
for manipulation detection baseline calculation.

Usage:
    python3 jobs/backfill_price_history.py [--days 30]
"""

import sys
import os
import argparse
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db_connection
from config import REGIONS
from services.war_economy.config import CRITICAL_ITEMS

# Trade hub regions
TRADE_HUB_REGIONS = [
    10000002,  # The Forge (Jita)
    10000043,  # Domain (Amarr)
    10000030,  # Heimatar (Rens)
    10000032,  # Sinq Laison (Dodixie)
    10000042,  # Metropolis (Hek)
]

ESI_BASE = "https://esi.evetech.net/latest"


def fetch_market_history(region_id: int, type_id: int) -> List[Dict]:
    """Fetch market history from ESI."""
    url = f"{ESI_BASE}/markets/{region_id}/history/"
    params = {"type_id": type_id, "datasource": "tranquility"}

    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return []
        else:
            print(f"  Warning: ESI returned {response.status_code} for {type_id} in {region_id}")
            return []
    except Exception as e:
        print(f"  Error fetching {type_id} in {region_id}: {e}")
        return []


def backfill_region_item(region_id: int, type_id: int, item_name: str, days_back: int) -> int:
    """Backfill price history for one region/item combination."""
    region_name = REGIONS.get(region_id, f"Region {region_id}")

    history = fetch_market_history(region_id, type_id)
    if not history:
        print(f"  No history for {item_name} in {region_name}")
        return 0

    history.sort(key=lambda x: x["date"])

    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days_back)

    inserted = 0
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for entry in history:
                entry_date = datetime.strptime(entry["date"], "%Y-%m-%d").date()

                if entry_date < start_date or entry_date > today:
                    continue

                # Create timestamp at noon UTC for that day
                snapshot_time = datetime.combine(entry_date, datetime.min.time().replace(hour=12))

                # ESI history provides: average, highest, lowest, order_count, volume
                cur.execute('''
                    INSERT INTO war_economy_price_history (
                        snapshot_time, region_id, type_id,
                        lowest_sell, highest_buy, sell_volume, buy_volume
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (snapshot_time, region_id, type_id) DO NOTHING
                ''', (
                    snapshot_time, region_id, type_id,
                    entry.get("lowest", entry.get("average")),
                    entry.get("highest", entry.get("average")),
                    entry.get("volume", 0),
                    0  # ESI doesn't separate buy/sell volume
                ))

                if cur.rowcount > 0:
                    inserted += 1

            conn.commit()

    return inserted


def main():
    parser = argparse.ArgumentParser(description="Backfill price history from ESI")
    parser.add_argument("--days", type=int, default=30, help="Days of history to backfill (default: 30)")
    args = parser.parse_args()

    print(f"=== Price History Backfill ===")
    print(f"Backfilling {args.days} days of history")
    print(f"Regions: {len(TRADE_HUB_REGIONS)}")
    print(f"Critical Items: {len(CRITICAL_ITEMS)}")
    print()

    total_inserted = 0

    for region_id in TRADE_HUB_REGIONS:
        region_name = REGIONS.get(region_id, f"Region {region_id}")
        print(f"Processing {region_name}...")

        for item_name, type_id in CRITICAL_ITEMS.items():
            inserted = backfill_region_item(region_id, type_id, item_name, args.days)
            total_inserted += inserted
            if inserted > 0:
                print(f"  {item_name}: {inserted} snapshots")

            time.sleep(0.1)

        print()

    print(f"=== Complete ===")
    print(f"Total snapshots inserted: {total_inserted}")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), MIN(snapshot_time), MAX(snapshot_time) FROM war_economy_price_history")
            count, min_time, max_time = cur.fetchone()
            print(f"Database now has {count} price history records")
            print(f"Date range: {min_time} → {max_time}")


if __name__ == "__main__":
    main()
