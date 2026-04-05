#!/usr/bin/env python3
"""
Import reactions from EVE SDE into reaction_formulas and reaction_formula_inputs tables.

This script reads reaction data from the EVE Static Data Export (SDE) tables:
- industryActivityProducts (activityID = 11 for reactions)
- industryActivityMaterials (activityID = 11 for reaction inputs)
- industryActivity (for reaction time)
- invTypes (for item names)

And populates:
- reaction_formulas: Main reaction info with product details
- reaction_formula_inputs: Input materials for each reaction

Usage:
    python scripts/import_reactions.py [--dry-run]
"""

import argparse
import logging
import os
import sys
from typing import Dict, List, Tuple, Optional

import psycopg2
from psycopg2.extras import execute_values

# Database connection settings - read from config in production
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "eve_sde",
    "user": "eve",
    "password": os.environ.get("DB_PASSWORD", "")
}

# Activity ID for reactions in EVE SDE
REACTION_ACTIVITY_ID = 11

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_connection():
    """Create database connection."""
    return psycopg2.connect(**DB_CONFIG)


def fetch_reactions(conn) -> List[Dict]:
    """
    Fetch all reaction formulas from SDE.

    Returns list of dicts with reaction_type_id, reaction_name, product_type_id,
    product_name, product_quantity, and reaction_time.
    """
    query = """
        SELECT DISTINCT
            p."typeID" as reaction_type_id,
            t."typeName" as reaction_name,
            p."productTypeID" as product_type_id,
            pt."typeName" as product_name,
            p.quantity as product_quantity,
            COALESCE(a.time, 3600) as reaction_time
        FROM "industryActivityProducts" p
        JOIN "invTypes" t ON p."typeID" = t."typeID"
        JOIN "invTypes" pt ON p."productTypeID" = pt."typeID"
        LEFT JOIN "industryActivity" a
            ON p."typeID" = a."typeID" AND a."activityID" = %s
        WHERE p."activityID" = %s
        ORDER BY t."typeName"
    """

    with conn.cursor() as cur:
        cur.execute(query, (REACTION_ACTIVITY_ID, REACTION_ACTIVITY_ID))
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


def fetch_reaction_inputs(conn) -> List[Dict]:
    """
    Fetch all reaction input materials from SDE.

    Returns list of dicts with reaction_type_id, input_type_id, input_name, quantity.
    """
    query = """
        SELECT
            m."typeID" as reaction_type_id,
            m."materialTypeID" as input_type_id,
            t."typeName" as input_name,
            m.quantity
        FROM "industryActivityMaterials" m
        JOIN "invTypes" t ON m."materialTypeID" = t."typeID"
        WHERE m."activityID" = %s
        ORDER BY m."typeID", t."typeName"
    """

    with conn.cursor() as cur:
        cur.execute(query, (REACTION_ACTIVITY_ID,))
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


def categorize_reaction(reaction_name: str) -> Optional[str]:
    """
    Determine reaction category based on name patterns.

    Categories:
    - 'biochemical': Boosters and biochemical reactions
    - 'composite': Composite reactions (T2 component materials)
    - 'polymer': Polymer reactions
    - 'simple': Simple reactions (processed materials)
    - 'hybrid': Hybrid reactions
    - 'moon': Moon material reactions
    """
    name_lower = reaction_name.lower()

    if 'booster' in name_lower or 'drug' in name_lower:
        return 'biochemical'
    elif 'composite' in name_lower:
        return 'composite'
    elif 'polymer' in name_lower:
        return 'polymer'
    elif 'hybrid' in name_lower:
        return 'hybrid'
    elif any(x in name_lower for x in ['neurolink', 'stabilizer', 'enhancer']):
        return 'biochemical'
    elif any(x in name_lower for x in ['carbon fiber', 'solvents', 'crystallite']):
        return 'polymer'
    elif 'reaction' in name_lower:
        if any(x in name_lower for x in ['fulleride', 'silicate', 'titanium', 'tungsten', 'cobalt', 'chromium']):
            return 'simple'
        return 'composite'

    return None


def insert_reactions(conn, reactions: List[Dict], dry_run: bool = False) -> int:
    """
    Insert or update reaction formulas.

    Returns number of rows affected.
    """
    if not reactions:
        return 0

    # Add category to each reaction
    for reaction in reactions:
        reaction['reaction_category'] = categorize_reaction(reaction['reaction_name'])

    values = [
        (
            r['reaction_type_id'],
            r['reaction_name'],
            r['product_type_id'],
            r['product_name'],
            r['product_quantity'],
            r['reaction_time'],
            r['reaction_category']
        )
        for r in reactions
    ]

    if dry_run:
        logger.info(f"[DRY RUN] Would insert/update {len(values)} reaction formulas")
        return len(values)

    query = """
        INSERT INTO reaction_formulas
            (reaction_type_id, reaction_name, product_type_id, product_name,
             product_quantity, reaction_time, reaction_category)
        VALUES %s
        ON CONFLICT (reaction_type_id)
        DO UPDATE SET
            reaction_name = EXCLUDED.reaction_name,
            product_type_id = EXCLUDED.product_type_id,
            product_name = EXCLUDED.product_name,
            product_quantity = EXCLUDED.product_quantity,
            reaction_time = EXCLUDED.reaction_time,
            reaction_category = EXCLUDED.reaction_category,
            created_at = now()
    """

    with conn.cursor() as cur:
        execute_values(cur, query, values, page_size=100)
        conn.commit()
        return cur.rowcount


def insert_reaction_inputs(conn, inputs: List[Dict], dry_run: bool = False) -> int:
    """
    Insert reaction inputs, clearing existing data first.

    Returns number of rows affected.
    """
    if not inputs:
        return 0

    if dry_run:
        logger.info(f"[DRY RUN] Would insert {len(inputs)} reaction inputs")
        return len(inputs)

    # Clear existing inputs first
    with conn.cursor() as cur:
        cur.execute("DELETE FROM reaction_formula_inputs")
        logger.info(f"Cleared {cur.rowcount} existing reaction inputs")

    values = [
        (
            i['reaction_type_id'],
            i['input_type_id'],
            i['input_name'],
            i['quantity']
        )
        for i in inputs
    ]

    query = """
        INSERT INTO reaction_formula_inputs
            (reaction_type_id, input_type_id, input_name, quantity)
        VALUES %s
    """

    with conn.cursor() as cur:
        execute_values(cur, query, values, page_size=1000)
        conn.commit()
        return cur.rowcount


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Import reactions from EVE SDE")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without making changes"
    )
    args = parser.parse_args()

    logger.info("Starting reaction import from EVE SDE")

    try:
        conn = get_connection()

        # Fetch reactions
        logger.info("Fetching reactions from SDE...")
        reactions = fetch_reactions(conn)
        logger.info(f"Found {len(reactions)} reactions")

        if reactions:
            # Show sample
            sample = reactions[0]
            logger.info(f"Sample reaction: {sample['reaction_name']} -> {sample['product_name']}")

        # Fetch inputs
        logger.info("Fetching reaction inputs from SDE...")
        inputs = fetch_reaction_inputs(conn)
        logger.info(f"Found {len(inputs)} reaction inputs")

        # Insert reactions
        logger.info("Inserting reaction formulas...")
        reaction_count = insert_reactions(conn, reactions, args.dry_run)
        logger.info(f"{'Would insert' if args.dry_run else 'Inserted/updated'} {reaction_count} reaction formulas")

        # Insert inputs
        logger.info("Inserting reaction inputs...")
        input_count = insert_reaction_inputs(conn, inputs, args.dry_run)
        logger.info(f"{'Would insert' if args.dry_run else 'Inserted'} {input_count} reaction inputs")

        # Summary
        logger.info("=" * 50)
        logger.info("Import complete!")
        logger.info(f"  Reactions: {len(reactions)}")
        logger.info(f"  Inputs: {len(inputs)}")

        # Show category breakdown
        categories = {}
        for r in reactions:
            cat = r.get('reaction_category') or 'unknown'
            categories[cat] = categories.get(cat, 0) + 1
        logger.info("Categories:")
        for cat, count in sorted(categories.items()):
            logger.info(f"  {cat}: {count}")

        conn.close()

    except Exception as e:
        logger.error(f"Import failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
