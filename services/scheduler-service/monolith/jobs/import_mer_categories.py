#!/usr/bin/env python3
"""
Import MER Categories from EVE Monthly Economic Report.

Imports item categories from the MER ZIP file's index_baskets.csv.
This categorizes items into 4 primary indices and 65 sub-indices.

Usage:
    python3 jobs/import_mer_categories.py /path/to/EVEOnline_MER_YYYYMM.zip
    python3 jobs/import_mer_categories.py /path/to/EVEOnline_MER_YYYYMM.zip --dry-run
"""

import sys
import os
import argparse
import zipfile
import csv
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db_connection


def import_categories(zip_path: str, dry_run: bool = False) -> int:
    """Import MER index_baskets.csv into mer_item_categories table."""

    if not os.path.exists(zip_path):
        print(f"Error: File not found: {zip_path}")
        return 0

    print(f"Reading {zip_path}...")

    with zipfile.ZipFile(zip_path) as z:
        if 'index_baskets.csv' not in z.namelist():
            print("Error: index_baskets.csv not found in ZIP")
            print(f"Available files: {z.namelist()}")
            return 0

        with z.open('index_baskets.csv') as f:
            content = io.TextIOWrapper(f, encoding='utf-8')
            reader = csv.DictReader(content)

            # Verify columns
            expected_cols = ['type_id', 'primary_index', 'sub_index']
            if not all(col in reader.fieldnames for col in expected_cols):
                print(f"Error: Expected columns {expected_cols}")
                print(f"Found columns: {reader.fieldnames}")
                return 0

            # Use dict to deduplicate by type_id (last occurrence wins)
            items = {}
            for row in reader:
                type_id = int(row['type_id'])
                items[type_id] = (
                    type_id,
                    row['primary_index'],
                    row['sub_index'],
                    row.get('category_name', row.get('group_name', ''))
                )
            batch = list(items.values())

    print(f"Parsed {len(batch)} items")

    if dry_run:
        print("Dry run - no changes made")
        print("\nSample items:")
        for item in batch[:5]:
            print(f"  {item[0]}: {item[2]} ({item[1]})")
        return len(batch)

    print("Importing to database...")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Clear existing data
            cur.execute("TRUNCATE mer_item_categories")

            # Batch insert
            from psycopg2.extras import execute_values
            execute_values(
                cur,
                """
                INSERT INTO mer_item_categories
                    (type_id, primary_index, sub_index, category_name)
                VALUES %s
                ON CONFLICT (type_id) DO UPDATE SET
                    primary_index = EXCLUDED.primary_index,
                    sub_index = EXCLUDED.sub_index,
                    category_name = EXCLUDED.category_name,
                    imported_at = NOW()
                """,
                batch
            )

            conn.commit()

            # Verify
            cur.execute("SELECT COUNT(*) FROM mer_item_categories")
            count = cur.fetchone()[0]

    print(f"Imported {count} items")

    # Show category breakdown
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT primary_index, COUNT(*)
                FROM mer_item_categories
                GROUP BY primary_index
                ORDER BY COUNT(*) DESC
            """)
            print("\nPrimary Index breakdown:")
            for row in cur.fetchall():
                print(f"  {row[0]}: {row[1]} items")

    return count


def main():
    parser = argparse.ArgumentParser(description="Import MER categories from EVE Monthly Economic Report")
    parser.add_argument("zip_path", help="Path to MER ZIP file (EVEOnline_MER_YYYYMM.zip)")
    parser.add_argument("--dry-run", action="store_true", help="Parse only, don't import to database")
    args = parser.parse_args()

    count = import_categories(args.zip_path, args.dry_run)

    if count > 0:
        print("\nImport complete!")
    else:
        print("\nImport failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
