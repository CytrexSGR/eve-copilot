#!/usr/bin/env python3
"""
Update Killmail Item Flags from Everef Dumps

Updates existing killmail_items that have NULL flags with data from everef.net dumps.
This fixes historical data where the live processor didn't save flag/singleton fields.

Usage:
    python3 jobs/update_killmail_item_flags.py --days 14
    python3 jobs/update_killmail_item_flags.py --date 2026-01-15
"""

import sys
import os
import argparse
import json
import tarfile
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db_connection

EVEREF_BASE_URL = "https://data.everef.net/killmails"
USER_AGENT = "EVE-Copilot/1.0 (Flag Backfill)"


def get_killmails_needing_flags(date: datetime) -> Dict[int, List[Tuple[int, bool]]]:
    """Get killmail IDs that have items with NULL flags.

    Args:
        date: Date to check

    Returns:
        Dict mapping killmail_id to list of (item_type_id, was_destroyed) tuples
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ki.killmail_id, ki.item_type_id, ki.was_destroyed
                FROM killmail_items ki
                JOIN killmails k ON ki.killmail_id = k.killmail_id
                WHERE DATE(k.killmail_time) = %s
                  AND ki.flag IS NULL
            """, (date.date(),))

            result = defaultdict(list)
            for row in cur.fetchall():
                result[row[0]].append((row[1], row[2]))
            return dict(result)


def download_dump(date: datetime) -> Path | None:
    """Download killmail dump for a specific date."""
    year = date.strftime("%Y")
    filename = f"killmails-{date.strftime('%Y-%m-%d')}.tar.bz2"
    url = f"{EVEREF_BASE_URL}/{year}/{filename}"

    print(f"[FLAGS] Downloading {url}...")

    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=120,
            stream=True
        )

        if response.status_code == 404:
            print(f"[FLAGS] Dump not available for {date.strftime('%Y-%m-%d')}")
            return None

        response.raise_for_status()

        temp_path = Path(tempfile.gettempdir()) / filename

        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        size_mb = temp_path.stat().st_size / 1024 / 1024
        print(f"[FLAGS] Downloaded {size_mb:.2f} MB")

        return temp_path

    except requests.RequestException as e:
        print(f"[FLAGS] Download failed: {e}")
        return None


def extract_and_update_flags(tar_path: Path, killmail_ids: Dict[int, List]) -> Tuple[int, int]:
    """Extract flag data from tar.bz2 archive and update existing items.

    Args:
        tar_path: Path to tar.bz2 file
        killmail_ids: Dict of killmail_id -> [(item_type_id, was_destroyed), ...]

    Returns:
        Tuple of (killmails_updated, items_updated)
    """
    killmails_updated = 0
    items_updated = 0

    # Collect all updates first for batch processing
    updates = []

    with tarfile.open(tar_path, "r:bz2") as tar:
        members = tar.getmembers()
        total = len(members)
        target_count = len(killmail_ids)
        print(f"[FLAGS] Scanning {total} killmails for {target_count} targets...")

        found = 0
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

                found += 1

                # Found a matching killmail - extract item flags
                victim = data.get('victim', {})
                items = victim.get('items', [])

                for item in items:
                    item_type_id = item.get('item_type_id')
                    if not item_type_id:
                        continue

                    flag = item.get('flag')
                    singleton = item.get('singleton')
                    qty_destroyed = item.get('quantity_destroyed', 0)
                    qty_dropped = item.get('quantity_dropped', 0)

                    # Update destroyed items
                    if qty_destroyed > 0:
                        updates.append((
                            flag, singleton,
                            killmail_id, item_type_id, True
                        ))

                    # Update dropped items
                    if qty_dropped > 0:
                        updates.append((
                            flag, singleton,
                            killmail_id, item_type_id, False
                        ))

                killmails_updated += 1

                # Progress every 1000 found
                if found % 1000 == 0:
                    print(f"[FLAGS] Found {found}/{target_count} killmails ({i+1}/{total} scanned)")

            except Exception as e:
                continue

    # Batch update in database
    if updates:
        print(f"[FLAGS] Applying {len(updates)} updates to database...")

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Use batch update for performance
                batch_size = 5000
                for i in range(0, len(updates), batch_size):
                    batch = updates[i:i+batch_size]

                    # Build batch UPDATE query
                    for update in batch:
                        flag, singleton, killmail_id, item_type_id, was_destroyed = update
                        cur.execute("""
                            UPDATE killmail_items
                            SET flag = %s, singleton = %s
                            WHERE killmail_id = %s
                              AND item_type_id = %s
                              AND was_destroyed = %s
                              AND flag IS NULL
                        """, (flag, singleton, killmail_id, item_type_id, was_destroyed))
                        items_updated += cur.rowcount

                    conn.commit()
                    print(f"[FLAGS] Committed batch {i//batch_size + 1}/{(len(updates)-1)//batch_size + 1}")

    return killmails_updated, items_updated


def update_flags_for_date(date: datetime) -> Tuple[int, int]:
    """Update flags for a specific date.

    Args:
        date: Date to process

    Returns:
        Tuple of (killmails_updated, items_updated)
    """
    print(f"\n[FLAGS] === Processing {date.strftime('%Y-%m-%d')} ===")

    # Check which killmails need flag updates
    killmail_ids = get_killmails_needing_flags(date)
    if not killmail_ids:
        print(f"[FLAGS] No items need flag updates for this date")
        return 0, 0

    total_items = sum(len(items) for items in killmail_ids.values())
    print(f"[FLAGS] {len(killmail_ids)} killmails with {total_items} items need flag updates")

    # Download dump
    tar_path = download_dump(date)
    if not tar_path:
        return 0, 0

    try:
        # Extract and update flags
        killmails, items = extract_and_update_flags(tar_path, killmail_ids)
        print(f"[FLAGS] Completed: {killmails} killmails, {items} items updated")
        return killmails, items

    finally:
        # Clean up
        if tar_path.exists():
            tar_path.unlink()


def main():
    parser = argparse.ArgumentParser(description="Update killmail item flags from everef.net")
    parser.add_argument("--date", help="Specific date to process (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=14, help="Number of days to process (default: 14)")
    args = parser.parse_args()

    print("[FLAGS] Killmail Item Flag Updater Starting")
    print(f"[FLAGS] Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    total_killmails = 0
    total_items = 0

    if args.date:
        date = datetime.strptime(args.date, "%Y-%m-%d")
        killmails, items = update_flags_for_date(date)
        total_killmails += killmails
        total_items += items
    else:
        for i in range(args.days):
            date = datetime.now() - timedelta(days=i + 1)
            killmails, items = update_flags_for_date(date)
            total_killmails += killmails
            total_items += items

    print(f"\n[FLAGS] === Summary ===")
    print(f"[FLAGS] Total killmails processed: {total_killmails}")
    print(f"[FLAGS] Total items updated: {total_items}")
    print(f"[FLAGS] Done!")


if __name__ == "__main__":
    main()
