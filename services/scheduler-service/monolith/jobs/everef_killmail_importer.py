#!/usr/bin/env python3
"""
Everef Killmail Importer - Daily dump processor

Downloads and imports killmail dumps from data.everef.net to fill gaps
in our live RedisQ stream.

Usage:
    python3 jobs/everef_killmail_importer.py [--date YYYY-MM-DD] [--days N]

    --date: Specific date to import (default: yesterday)
    --days: Import N days back (default: 1)

Schedule: Run daily at 06:00 UTC via cron
"""

import sys
import os
import argparse
import json
import tarfile
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import requests

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db_connection

EVEREF_BASE_URL = "https://data.everef.net/killmails"
USER_AGENT = "EVE-Copilot/1.0 (Killmail Backfill)"


def download_dump(date: datetime) -> Path | None:
    """Download killmail dump for a specific date.

    Args:
        date: Date to download

    Returns:
        Path to downloaded file or None if not found
    """
    year = date.strftime("%Y")
    filename = f"killmails-{date.strftime('%Y-%m-%d')}.tar.bz2"
    url = f"{EVEREF_BASE_URL}/{year}/{filename}"

    print(f"[EVEREF] Downloading {url}...")

    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=60,
            stream=True
        )

        if response.status_code == 404:
            print(f"[EVEREF] Dump not available yet for {date.strftime('%Y-%m-%d')}")
            return None

        response.raise_for_status()

        # Save to temp file
        temp_path = Path(tempfile.gettempdir()) / filename

        with open(temp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        size_mb = temp_path.stat().st_size / 1024 / 1024
        print(f"[EVEREF] Downloaded {size_mb:.2f} MB")

        return temp_path

    except requests.RequestException as e:
        print(f"[EVEREF] Download failed: {e}")
        return None


def extract_and_import(tar_path: Path) -> tuple[int, int, int]:
    """Extract and import killmails from tar.bz2 archive.

    The archive contains JSON files, one per killmail.

    Args:
        tar_path: Path to tar.bz2 file

    Returns:
        Tuple of (imported_count, skipped_count, items_count)
    """
    imported = 0
    skipped = 0
    items_imported = 0

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            with tarfile.open(tar_path, "r:bz2") as tar:
                members = tar.getmembers()
                total = len(members)
                print(f"[EVEREF] Processing {total} killmails...")

                for i, member in enumerate(members):
                    if not member.name.endswith('.json'):
                        continue

                    try:
                        f = tar.extractfile(member)
                        if f is None:
                            continue

                        data = json.loads(f.read().decode('utf-8'))

                        # Extract killmail data
                        killmail_id = data.get('killmail_id')
                        if not killmail_id:
                            skipped += 1
                            continue

                        # Check if already exists
                        cur.execute(
                            "SELECT 1 FROM killmails WHERE killmail_id = %s",
                            (killmail_id,)
                        )
                        if cur.fetchone():
                            skipped += 1
                            continue

                        # Parse killmail data
                        killmail_time = data.get('killmail_time')
                        solar_system_id = data.get('solar_system_id')

                        victim = data.get('victim', {})
                        victim_ship_type_id = victim.get('ship_type_id')
                        victim_character_id = victim.get('character_id')
                        victim_corporation_id = victim.get('corporation_id')
                        victim_alliance_id = victim.get('alliance_id')

                        # Get zkb data if available
                        zkb = data.get('zkb', {})
                        ship_value = zkb.get('totalValue', 0)

                        # Get attackers
                        attackers = data.get('attackers', [])
                        attacker_count = len(attackers)

                        # Find final blow attacker
                        final_blow = next(
                            (a for a in attackers if a.get('final_blow')),
                            attackers[0] if attackers else {}
                        )
                        final_blow_character_id = final_blow.get('character_id')
                        final_blow_corporation_id = final_blow.get('corporation_id')
                        final_blow_alliance_id = final_blow.get('alliance_id')

                        # Get region from system
                        cur.execute(
                            'SELECT region_id FROM system_region_map WHERE solar_system_id = %s',
                            (solar_system_id,)
                        )
                        row = cur.fetchone()
                        region_id = row[0] if row else None

                        # Insert killmail
                        cur.execute("""
                            INSERT INTO killmails (
                                killmail_id, killmail_time, solar_system_id, region_id,
                                ship_type_id, ship_value,
                                victim_character_id, victim_corporation_id, victim_alliance_id,
                                final_blow_character_id, final_blow_corporation_id, final_blow_alliance_id,
                                attacker_count
                            ) VALUES (
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                            )
                            ON CONFLICT (killmail_id) DO NOTHING
                        """, (
                            killmail_id, killmail_time, solar_system_id, region_id,
                            victim_ship_type_id, ship_value,
                            victim_character_id, victim_corporation_id, victim_alliance_id,
                            final_blow_character_id, final_blow_corporation_id, final_blow_alliance_id,
                            attacker_count
                        ))

                        # Import items (destroyed and dropped)
                        items = victim.get('items', [])
                        for item in items:
                            item_type_id = item.get('item_type_id')
                            if not item_type_id:
                                continue

                            qty_destroyed = item.get('quantity_destroyed', 0)
                            qty_dropped = item.get('quantity_dropped', 0)
                            flag = item.get('flag')
                            singleton = item.get('singleton')

                            if qty_destroyed > 0:
                                cur.execute("""
                                    INSERT INTO killmail_items
                                        (killmail_id, item_type_id, quantity, was_destroyed, flag, singleton)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    ON CONFLICT DO NOTHING
                                """, (killmail_id, item_type_id, qty_destroyed, True, flag, singleton))
                                items_imported += 1

                            if qty_dropped > 0:
                                cur.execute("""
                                    INSERT INTO killmail_items
                                        (killmail_id, item_type_id, quantity, was_destroyed, flag, singleton)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    ON CONFLICT DO NOTHING
                                """, (killmail_id, item_type_id, qty_dropped, False, flag, singleton))
                                items_imported += 1

                        imported += 1

                        # Progress every 1000
                        if (i + 1) % 1000 == 0:
                            conn.commit()
                            print(f"[EVEREF] Progress: {i+1}/{total} ({imported} imported, {skipped} skipped, {items_imported} items)")

                    except Exception as e:
                        skipped += 1
                        if skipped <= 5:
                            print(f"[EVEREF] Error processing {member.name}: {e}")
                        continue

                conn.commit()

    return imported, skipped, items_imported


def import_date(date: datetime) -> tuple[int, int, int]:
    """Import killmails for a specific date.

    Args:
        date: Date to import

    Returns:
        Tuple of (imported_count, skipped_count, items_count)
    """
    print(f"\n[EVEREF] === Importing {date.strftime('%Y-%m-%d')} ===")

    # Download
    tar_path = download_dump(date)
    if not tar_path:
        return 0, 0, 0

    try:
        # Extract and import
        imported, skipped, items = extract_and_import(tar_path)
        print(f"[EVEREF] Completed: {imported} imported, {skipped} skipped, {items} items")
        return imported, skipped, items

    finally:
        # Clean up
        if tar_path.exists():
            tar_path.unlink()


def main():
    parser = argparse.ArgumentParser(description="Import killmail dumps from everef.net")
    parser.add_argument("--date", help="Specific date to import (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=1, help="Number of days to import (default: 1)")
    args = parser.parse_args()

    print("[EVEREF] Killmail Importer Starting")
    print(f"[EVEREF] Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    total_imported = 0
    total_skipped = 0
    total_items = 0

    if args.date:
        # Import specific date
        date = datetime.strptime(args.date, "%Y-%m-%d")
        imported, skipped, items = import_date(date)
        total_imported += imported
        total_skipped += skipped
        total_items += items
    else:
        # Import N days back (default: yesterday)
        for i in range(args.days):
            # Start from yesterday and go back
            date = datetime.now() - timedelta(days=i + 1)
            imported, skipped, items = import_date(date)
            total_imported += imported
            total_skipped += skipped
            total_items += items

    print(f"\n[EVEREF] === Summary ===")
    print(f"[EVEREF] Total imported: {total_imported}")
    print(f"[EVEREF] Total skipped: {total_skipped}")
    print(f"[EVEREF] Total items: {total_items}")
    print(f"[EVEREF] Done!")


if __name__ == "__main__":
    main()
