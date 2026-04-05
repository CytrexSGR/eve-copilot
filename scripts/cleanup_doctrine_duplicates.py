#!/usr/bin/env python3
"""
Doctrine Duplicate Cleanup Script

Merges duplicate doctrines (same name + region) into a single record,
preserving the one with the highest observation_count and aggregating
statistics from all duplicates.

Usage:
    python scripts/cleanup_doctrine_duplicates.py [--dry-run]
"""

import argparse
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, '/home/cytrex/eve_copilot')

from src.database import get_db_connection


def get_duplicate_groups(cur):
    """Find all duplicate doctrine groups (same name + region)."""
    cur.execute("""
        SELECT doctrine_name, region_id, COUNT(*) as count,
               array_agg(id ORDER BY observation_count DESC) as ids
        FROM doctrine_templates
        GROUP BY doctrine_name, region_id
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """)
    return cur.fetchall()


def merge_doctrines(cur, keeper_id: int, duplicate_ids: list, dry_run: bool):
    """Merge duplicate doctrines into the keeper."""
    if not duplicate_ids:
        return 0

    # Get all doctrines to merge
    placeholders = ','.join(['%s'] * (len(duplicate_ids) + 1))
    all_ids = [keeper_id] + duplicate_ids

    cur.execute(f"""
        SELECT id, observation_count, first_seen, last_seen, total_pilots_avg
        FROM doctrine_templates
        WHERE id IN ({placeholders})
    """, all_ids)

    rows = cur.fetchall()

    # Calculate merged stats
    total_observations = sum(r[1] for r in rows)
    earliest_first_seen = min(r[2] for r in rows)
    latest_last_seen = max(r[3] for r in rows)
    avg_pilots = int(sum(r[4] or 0 for r in rows) / len(rows)) if rows else 0

    # Update confidence score based on merged observations
    confidence = min(1.0, 1.0 - (1.0 / (total_observations ** 0.5)))

    if not dry_run:
        # Update keeper with merged stats
        cur.execute("""
            UPDATE doctrine_templates
            SET observation_count = %s,
                first_seen = %s,
                last_seen = %s,
                total_pilots_avg = %s,
                confidence_score = %s,
                updated_at = %s
            WHERE id = %s
        """, (
            total_observations,
            earliest_first_seen,
            latest_last_seen,
            avg_pilots,
            confidence,
            datetime.now(),
            keeper_id
        ))

        # Handle doctrine_items_of_interest FK constraints
        # First, delete items from duplicates that would conflict with keeper
        dup_placeholders = ','.join(['%s'] * len(duplicate_ids))
        cur.execute(f"""
            DELETE FROM doctrine_items_of_interest
            WHERE doctrine_id IN ({dup_placeholders})
        """, duplicate_ids)

        # Delete duplicate doctrines
        cur.execute(f"""
            DELETE FROM doctrine_templates
            WHERE id IN ({dup_placeholders})
        """, duplicate_ids)

    return total_observations


def main():
    parser = argparse.ArgumentParser(description='Clean up duplicate doctrines')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without making changes')
    args = parser.parse_args()

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Doctrine Duplicate Cleanup")
    print("=" * 60)

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get duplicate groups
            groups = get_duplicate_groups(cur)

            if not groups:
                print("No duplicate doctrines found!")
                return

            print(f"Found {len(groups)} duplicate groups")
            print()

            total_deleted = 0
            total_merged_observations = 0

            for doctrine_name, region_id, count, ids in groups:
                keeper_id = ids[0]  # Highest observation_count
                duplicate_ids = ids[1:]

                print(f"  {doctrine_name} (region {region_id})")
                print(f"    - {count} duplicates, keeping id={keeper_id}")
                print(f"    - Deleting ids: {duplicate_ids[:5]}{'...' if len(duplicate_ids) > 5 else ''}")

                merged_obs = merge_doctrines(cur, keeper_id, duplicate_ids, args.dry_run)
                if merged_obs:
                    print(f"    - Merged to {merged_obs} total observations")

                total_deleted += len(duplicate_ids)
                total_merged_observations += merged_obs or 0

            if not args.dry_run:
                conn.commit()

            print()
            print("=" * 60)
            print(f"{'[DRY RUN] ' if args.dry_run else ''}Summary:")
            print(f"  - Duplicate groups processed: {len(groups)}")
            print(f"  - Doctrines deleted: {total_deleted}")
            print(f"  - Total merged observations: {total_merged_observations}")

            if args.dry_run:
                print()
                print("Run without --dry-run to apply changes.")


if __name__ == '__main__':
    main()
