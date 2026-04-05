#!/usr/bin/env python3
"""
Backfill Fuel Baseline from ESI Market History

One-time script to populate war_economy_fuel_snapshots with historical data
for baseline calculation. Uses ESI /markets/{region_id}/history/ endpoint.

Usage:
    python3 jobs/backfill_fuel_baseline.py [--days 30]
"""

import sys
import os
import argparse
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db_connection
from config import REGIONS

# Isotope type IDs (Capital ship fuel)
ISOTOPES = {
    "Hydrogen": 17889,     # Minmatar
    "Helium": 16274,       # Amarr
    "Nitrogen": 17888,     # Caldari
    "Oxygen": 17887        # Gallente
}

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
            return []  # No history for this item in this region
        else:
            print(f"  Warning: ESI returned {response.status_code} for {type_id} in {region_id}")
            return []
    except Exception as e:
        print(f"  Error fetching {type_id} in {region_id}: {e}")
        return []


def calculate_baseline(history: List[Dict], target_date: str, days: int = 7) -> Tuple[int, float]:
    """Calculate 7-day baseline volume and price before a given date."""
    target = datetime.strptime(target_date, "%Y-%m-%d")
    baseline_start = target - timedelta(days=days)

    baseline_entries = [
        h for h in history
        if baseline_start <= datetime.strptime(h["date"], "%Y-%m-%d") < target
    ]

    if not baseline_entries:
        return 0, 0.0

    avg_volume = sum(h["volume"] for h in baseline_entries) / len(baseline_entries)
    avg_price = sum(h["average"] for h in baseline_entries) / len(baseline_entries)

    return int(avg_volume), avg_price


def backfill_region_isotope(region_id: int, isotope_name: str, type_id: int, days_back: int) -> int:
    """Backfill fuel snapshots for one region/isotope combination."""
    region_name = REGIONS.get(region_id, f"Region {region_id}")

    # Fetch ESI history
    history = fetch_market_history(region_id, type_id)
    if not history:
        print(f"  No history for {isotope_name} in {region_name}")
        return 0

    # Sort by date
    history.sort(key=lambda x: x["date"])

    # Get date range
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days_back)

    inserted = 0
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for entry in history:
                entry_date = datetime.strptime(entry["date"], "%Y-%m-%d").date()

                # Skip if outside our range
                if entry_date < start_date or entry_date > today:
                    continue

                # Calculate baseline (7-day average before this date)
                baseline_volume, baseline_price = calculate_baseline(history, entry["date"], 7)

                # Calculate delta
                if baseline_volume > 0:
                    delta_percent = ((entry["volume"] - baseline_volume) / baseline_volume) * 100
                else:
                    delta_percent = 0.0

                # Classify anomaly
                abs_delta = abs(delta_percent)
                if abs_delta >= 100:
                    anomaly, severity = True, 'critical'
                elif abs_delta >= 60:
                    anomaly, severity = True, 'high'
                elif abs_delta >= 30:
                    anomaly, severity = True, 'medium'
                elif abs_delta >= 15:
                    anomaly, severity = True, 'low'
                else:
                    anomaly, severity = False, 'normal'

                # Create timestamp at noon UTC for that day
                snapshot_time = datetime.combine(entry_date, datetime.min.time().replace(hour=12))

                # Insert (with conflict handling)
                cur.execute('''
                    INSERT INTO war_economy_fuel_snapshots (
                        snapshot_time, region_id, isotope_type_id,
                        total_volume, average_price, baseline_7d_volume,
                        volume_delta_percent, anomaly_detected, anomaly_severity
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (snapshot_time, region_id, isotope_type_id) DO NOTHING
                ''', (
                    snapshot_time, region_id, type_id,
                    entry["volume"], entry["average"], baseline_volume,
                    delta_percent, anomaly, severity
                ))

                if cur.rowcount > 0:
                    inserted += 1

            conn.commit()

    return inserted


def main():
    parser = argparse.ArgumentParser(description="Backfill fuel baseline from ESI")
    parser.add_argument("--days", type=int, default=30, help="Days of history to backfill (default: 30)")
    args = parser.parse_args()

    print(f"=== Fuel Baseline Backfill ===")
    print(f"Backfilling {args.days} days of history")
    print(f"Regions: {len(TRADE_HUB_REGIONS)}")
    print(f"Isotopes: {len(ISOTOPES)}")
    print()

    total_inserted = 0

    for region_id in TRADE_HUB_REGIONS:
        region_name = REGIONS.get(region_id, f"Region {region_id}")
        print(f"Processing {region_name}...")

        for isotope_name, type_id in ISOTOPES.items():
            inserted = backfill_region_isotope(region_id, isotope_name, type_id, args.days)
            total_inserted += inserted
            if inserted > 0:
                print(f"  {isotope_name}: {inserted} snapshots")

            # Rate limit ESI calls
            time.sleep(0.1)

        print()

    print(f"=== Complete ===")
    print(f"Total snapshots inserted: {total_inserted}")

    # Show current state
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*), MIN(snapshot_time), MAX(snapshot_time) FROM war_economy_fuel_snapshots")
            count, min_time, max_time = cur.fetchone()
            print(f"Database now has {count} fuel snapshots")
            print(f"Date range: {min_time} → {max_time}")


if __name__ == "__main__":
    main()
