#!/usr/bin/env python3
"""
Backfill Killmail Items from Everef Dumps

Downloads everef dumps and imports item data for existing killmails
that are missing item entries.

Usage:
    python3 jobs/backfill_killmail_items.py --days 30
    python3 jobs/backfill_killmail_items.py --date 2026-01-15
"""

import sys
import os
import argparse
import json
import tarfile
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Set

import requests
from psycopg2.extras import execute_values

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db_connection

EVEREF_BASE_URL = "https://data.everef.net/killmails"
USER_AGENT = "EVE-Copilot/1.0 (Item Backfill)"


def get_killmails_needing_items(date: datetime) -> Set[int]:
    """Get killmail IDs that exist but have no items.

    Args:
        date: Date to check

    Returns:
        Set of killmail_ids that need items
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT k.killmail_id
                FROM killmails k
                LEFT JOIN killmail_items ki ON k.killmail_id = ki.killmail_id
                WHERE DATE(k.killmail_time) = %s
                  AND ki.killmail_id IS NULL
            """, (date.date(),))
            return {row[0] for row in cur.fetchall()}


def download_dump(date: datetime) -> Path | None:
    """Download killmail dump for a specific date."""
    year = date.strftime("%Y")
    filename = f"killmails-{date.strftime('%Y-%m-%d')}.tar.bz2"
    url = f"{EVEREF_BASE_URL}/{year}/{filename}"

    print(f"[ITEMS] Downloading {url}...")

    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=120,
            stream=True
        )

        if response.status_code == 404:
            print(f"[ITEMS] Dump not available for {date.strftime('%Y-%m-%d')}")
            return None

        response.raise_for_status()

        temp_path = Path(tempfile.gettempdir()) / filename

        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        size_mb = temp_path.stat().st_size / 1024 / 1024
        print(f"[ITEMS] Downloaded {size_mb:.2f} MB")

        return temp_path

    except requests.RequestException as e:
        print(f"[ITEMS] Download failed: {e}")
        return None


def extract_and_import_items(tar_path: Path, killmail_ids: Set[int]) -> tuple[int, int, int]:
    """Extract items from tar.bz2 archive for specific killmails.

    Args:
        tar_path: Path to tar.bz2 file
        killmail_ids: Set of killmail_ids to import items for

    Returns:
        Tuple of (killmails_processed, items_imported, items_skipped)
    """
    killmails_processed = 0
    items_imported = 0
    items_skipped = 0

    item_batch = []  # Batch insert for performance
    BATCH_SIZE = 5000

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            with tarfile.open(tar_path, "r:bz2") as tar:
                members = tar.getmembers()
                total = len(members)
                print(f"[ITEMS] Scanning {total} killmails for {len(killmail_ids)} targets...")

                for i, member in enumerate(members):
                    if not member.name.endswith('.json'):
                        continue

                    try:
                        f = tar.extractfile(member)
                        if f is None:
                            continue

                        data = json.loads(f.read().decode('utf-8'))
                        killmail_id = data.get('killmail_id')

                        if not killmail_id or killmail_id not in killmail_ids:
                            continue

                        # Found a matching killmail - extract items
                        victim = data.get('victim', {})
                        items = victim.get('items', [])

                        if not items:
                            items_skipped += 1
                            continue

                        for item in items:
                            item_type_id = item.get('item_type_id')
                            if not item_type_id:
                                continue

                            qty_destroyed = item.get('quantity_destroyed', 0)
                            qty_dropped = item.get('quantity_dropped', 0)
                            flag = item.get('flag')
                            singleton = item.get('singleton')

                            if qty_destroyed > 0:
                                item_batch.append((
                                    killmail_id,
                                    item_type_id,
                                    qty_destroyed,
                                    True,
                                    flag,
                                    singleton
                                ))
                                items_imported += 1

                            if qty_dropped > 0:
                                item_batch.append((
                                    killmail_id,
                                    item_type_id,
                                    qty_dropped,
                                    False,
                                    flag,
                                    singleton
                                ))
                                items_imported += 1

                        killmails_processed += 1

                        # Batch insert
                        if len(item_batch) >= BATCH_SIZE:
                            execute_values(
                                cur,
                                """
                                INSERT INTO killmail_items
                                    (killmail_id, item_type_id, quantity, was_destroyed, flag, singleton)
                                VALUES %s
                                ON CONFLICT DO NOTHING
                                """,
                                item_batch,
                                page_size=1000
                            )
                            conn.commit()
                            item_batch = []

                        # Progress every 5000
                        if (i + 1) % 5000 == 0:
                            print(f"[ITEMS] Progress: {i+1}/{total} ({killmails_processed} killmails, {items_imported} items)")

                    except Exception as e:
                        if items_skipped <= 5:
                            print(f"[ITEMS] Error processing {member.name}: {e}")
                        items_skipped += 1
                        continue

                # Final batch
                if item_batch:
                    execute_values(
                        cur,
                        """
                        INSERT INTO killmail_items
                            (killmail_id, item_type_id, quantity, was_destroyed, flag, singleton)
                        VALUES %s
                        ON CONFLICT DO NOTHING
                        """,
                        item_batch,
                        page_size=1000
                    )
                    conn.commit()

    return killmails_processed, items_imported, items_skipped


def import_items_for_date(date: datetime) -> tuple[int, int]:
    """Import items for a specific date.

    Args:
        date: Date to import

    Returns:
        Tuple of (killmails_processed, items_imported)
    """
    print(f"\n[ITEMS] === Processing {date.strftime('%Y-%m-%d')} ===")

    # Check which killmails need items
    killmail_ids = get_killmails_needing_items(date)
    if not killmail_ids:
        print(f"[ITEMS] No killmails need items for this date")
        return 0, 0

    print(f"[ITEMS] {len(killmail_ids)} killmails need items")

    # Download dump
    tar_path = download_dump(date)
    if not tar_path:
        return 0, 0

    try:
        # Extract and import items
        killmails, items, skipped = extract_and_import_items(tar_path, killmail_ids)
        print(f"[ITEMS] Completed: {killmails} killmails, {items} items imported, {skipped} skipped")
        return killmails, items

    finally:
        # Clean up
        if tar_path.exists():
            tar_path.unlink()


def main():
    parser = argparse.ArgumentParser(description="Backfill killmail items from everef.net")
    parser.add_argument("--date", help="Specific date to import (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=1, help="Number of days to import (default: 1)")
    args = parser.parse_args()

    print("[ITEMS] Killmail Items Backfiller Starting")
    print(f"[ITEMS] Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    total_killmails = 0
    total_items = 0

    if args.date:
        date = datetime.strptime(args.date, "%Y-%m-%d")
        killmails, items = import_items_for_date(date)
        total_killmails += killmails
        total_items += items
    else:
        for i in range(args.days):
            date = datetime.now() - timedelta(days=i + 1)
            killmails, items = import_items_for_date(date)
            total_killmails += killmails
            total_items += items

    print(f"\n[ITEMS] === Summary ===")
    print(f"[ITEMS] Total killmails processed: {total_killmails}")
    print(f"[ITEMS] Total items imported: {total_items}")
    print(f"[ITEMS] Done!")


if __name__ == "__main__":
    main()
