#!/usr/bin/env python3
"""
Sovereignty Structures Updater

Fetches sovereignty structures (TCU, IHUB) from ESI and updates database.
Run via scheduler-service every 5 minutes.

Usage:
    python jobs/sov_structures_updater.py
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

import httpx
import psycopg2
from psycopg2.extras import execute_values

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ESI endpoint
ESI_SOV_STRUCTURES = "https://esi.evetech.net/latest/sovereignty/structures/"


def fetch_sov_structures() -> list:
    """Fetch sovereignty structures from ESI."""
    logger.info("Fetching sovereignty structures from ESI...")

    response = httpx.get(
        ESI_SOV_STRUCTURES,
        headers={"User-Agent": "EVE-Copilot-SovUpdater/1.0"},
        timeout=30.0
    )
    response.raise_for_status()

    data = response.json()
    logger.info(f"Fetched {len(data)} structures from ESI")
    return data


def update_database(structures: list) -> int:
    """Update sovereignty structures in database."""
    settings = get_settings()

    conn = psycopg2.connect(
        host=settings.db_host,
        port=settings.db_port,
        dbname=settings.db_name,
        user=settings.db_user,
        password=settings.db_password
    )

    try:
        with conn.cursor() as cur:
            # Prepare data for bulk upsert
            values = []
            for item in structures:
                values.append((
                    item.get("alliance_id", 0),
                    item["solar_system_id"],
                    item["structure_type_id"],
                    item.get("vulnerability_occupancy_level"),
                    item.get("vulnerable_start_time"),
                    item.get("vulnerable_end_time"),
                ))

            # Bulk upsert using execute_values
            execute_values(
                cur,
                """
                INSERT INTO sovereignty_structures
                    (alliance_id, solar_system_id, structure_type_id,
                     vulnerability_occupancy_level, vulnerable_start_time,
                     vulnerable_end_time, last_updated)
                VALUES %s
                ON CONFLICT (solar_system_id, structure_type_id)
                DO UPDATE SET
                    alliance_id = EXCLUDED.alliance_id,
                    vulnerability_occupancy_level = EXCLUDED.vulnerability_occupancy_level,
                    vulnerable_start_time = EXCLUDED.vulnerable_start_time,
                    vulnerable_end_time = EXCLUDED.vulnerable_end_time,
                    last_updated = NOW()
                """,
                values,
                template="(%s, %s, %s, %s, %s, %s, NOW())"
            )

            conn.commit()
            logger.info(f"Updated {len(values)} sovereignty structures in database")
            return len(values)

    finally:
        conn.close()


def main():
    """Main entry point."""
    start_time = datetime.now()
    logger.info("Starting sovereignty structures update job")

    try:
        structures = fetch_sov_structures()
        count = update_database(structures)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"Job completed: {count} structures updated in {duration:.2f}s")

    except httpx.HTTPError as e:
        logger.error(f"ESI request failed: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Job failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
