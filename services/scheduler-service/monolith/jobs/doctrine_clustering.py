#!/usr/bin/env python3
"""
Doctrine Clustering Background Job

Daily background job that:
1. Clusters last 7 days of fleet snapshots using DBSCAN
2. Creates/updates doctrine templates
3. Derives items of interest (ammunition, fuel, modules) for each doctrine
4. Logs execution results

Schedule: Daily at 06:00 UTC via cron

Usage:
    python3 doctrine_clustering.py [--hours-back 168]

Exit Codes:
    0 - Success
    1 - Failure (exception occurred)
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from typing import List

# Add parent directory to sys.path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db_connection
from services.war_economy.doctrine.clustering_service import DoctrineClusteringService
from services.war_economy.doctrine.items_deriver import ItemsDeriver
from services.war_economy.doctrine.models import DoctrineTemplate, ItemOfInterest

# Configure logging to stdout/stderr for cron capture
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def fetch_recent_doctrines(hours_back: int) -> List[DoctrineTemplate]:
    """Fetch recently created/updated doctrine templates.

    Args:
        hours_back: Only fetch doctrines updated in last N hours

    Returns:
        List of DoctrineTemplate objects
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    id, doctrine_name, alliance_id, region_id,
                    composition, confidence_score, observation_count,
                    first_seen, last_seen, total_pilots_avg,
                    primary_doctrine_type, created_at, updated_at
                FROM doctrine_templates
                WHERE updated_at > NOW() - INTERVAL '%s hours'
                ORDER BY updated_at DESC
            """, (hours_back,))

            rows = cur.fetchall()

            doctrines = []
            for row in rows:
                doctrine = DoctrineTemplate(
                    id=row[0],
                    doctrine_name=row[1],
                    alliance_id=row[2],
                    region_id=row[3],
                    composition=row[4],
                    confidence_score=row[5],
                    observation_count=row[6],
                    first_seen=row[7],
                    last_seen=row[8],
                    total_pilots_avg=row[9],
                    primary_doctrine_type=row[10],
                    created_at=row[11],
                    updated_at=row[12]
                )
                doctrines.append(doctrine)

            return doctrines


def save_items_to_database(items: List[ItemOfInterest]) -> int:
    """Save derived items to doctrine_items_of_interest table.

    Uses INSERT ... ON CONFLICT DO UPDATE to handle duplicates.

    Args:
        items: List of ItemOfInterest objects to save

    Returns:
        Number of items saved
    """
    if not items:
        return 0

    saved_count = 0

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            for item in items:
                try:
                    cur.execute("""
                        INSERT INTO doctrine_items_of_interest (
                            doctrine_id, type_id, item_name, item_category,
                            consumption_rate, priority, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (doctrine_id, type_id)
                        DO UPDATE SET
                            item_name = EXCLUDED.item_name,
                            item_category = EXCLUDED.item_category,
                            consumption_rate = EXCLUDED.consumption_rate,
                            priority = EXCLUDED.priority
                    """, (
                        item.doctrine_id,
                        item.type_id,
                        item.item_name,
                        item.item_category,
                        item.consumption_rate,
                        item.priority,
                        item.created_at
                    ))
                    saved_count += 1
                except Exception as e:
                    logger.error(
                        f"Failed to save item {item.item_name} (type_id={item.type_id}) "
                        f"for doctrine {item.doctrine_id}: {e}"
                    )

            conn.commit()

    return saved_count


def main(hours_back: int = 168) -> int:
    """Main execution function for doctrine clustering job.

    Args:
        hours_back: How many hours of historical data to cluster (default: 168 = 7 days)

    Returns:
        Exit code (0=success, 1=failure)
    """
    try:
        logger.info("=" * 80)
        logger.info("Starting doctrine clustering job")
        logger.info(f"Clustering window: Last {hours_back} hours ({hours_back / 24:.1f} days)")

        start_time = datetime.now()

        # Step 1: Cluster fleet snapshots
        logger.info("Step 1: Clustering fleet snapshots...")
        clustering_service = DoctrineClusteringService()
        doctrines_created = clustering_service.cluster_snapshots(hours_back=hours_back)

        logger.info(f"Clustering complete: {doctrines_created} doctrines created/updated")

        if doctrines_created == 0:
            logger.info("No doctrines created (insufficient data or no new patterns detected)")
            logger.info("Doctrine clustering job complete")
            logger.info("=" * 80)
            return 0

        # Step 2: Fetch recently updated doctrines
        logger.info("Step 2: Fetching recently updated doctrines...")
        recent_doctrines = fetch_recent_doctrines(hours_back=1)  # Last 1 hour
        logger.info(f"Found {len(recent_doctrines)} recently updated doctrines")

        # Step 3: Derive items for each doctrine
        logger.info("Step 3: Deriving items of interest...")
        items_deriver = ItemsDeriver()
        total_items_derived = 0
        total_items_saved = 0
        successful_doctrines = 0
        failed_doctrines = 0

        for doctrine in recent_doctrines:
            try:
                logger.info(
                    f"Processing doctrine {doctrine.id}: "
                    f"{doctrine.doctrine_name} (region={doctrine.region_id})"
                )

                # Derive items
                items = items_deriver.derive_items_for_doctrine(doctrine)
                total_items_derived += len(items)

                logger.info(f"  Derived {len(items)} items of interest")

                # Save items to database
                saved_count = save_items_to_database(items)
                total_items_saved += saved_count

                logger.info(f"  Saved {saved_count} items to database")
                successful_doctrines += 1

            except Exception as e:
                logger.error(
                    f"Error processing doctrine {doctrine.id}: {e}",
                    exc_info=True
                )
                failed_doctrines += 1
                # Continue processing other doctrines

        # Step 4: Log summary
        duration = (datetime.now() - start_time).total_seconds()

        logger.info("-" * 80)
        logger.info("Doctrine clustering job complete")
        logger.info(f"Duration: {duration:.1f}s")
        logger.info(f"Doctrines created/updated: {doctrines_created}")
        logger.info(f"Doctrines processed: {successful_doctrines} succeeded, {failed_doctrines} failed")
        logger.info(f"Items derived: {total_items_derived}")
        logger.info(f"Items saved: {total_items_saved}")
        logger.info("=" * 80)

        return 0

    except Exception as e:
        logger.error(f"Fatal error in doctrine clustering job: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Cluster fleet snapshots into doctrine templates"
    )
    parser.add_argument(
        '--hours-back',
        type=int,
        default=168,
        help='How many hours of historical data to cluster (default: 168 = 7 days)'
    )

    args = parser.parse_args()

    # Execute main function and exit with appropriate code
    exit_code = main(hours_back=args.hours_back)
    sys.exit(exit_code)
