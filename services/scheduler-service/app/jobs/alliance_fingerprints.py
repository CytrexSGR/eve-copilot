"""
Alliance Doctrine Fingerprints Job

Analyzes killmail_attackers to build ship usage fingerprints per alliance.

NOTE: Coalition membership (coalition_id) is NO LONGER calculated here.
The coalition endpoint now uses dynamic calculation at runtime via
war-intel-service/app/routers/war/utils.py::get_coalition_memberships()
which uses alliance_fight_together/against tables with proper friend/enemy ratio.

Runs daily or on-demand.
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Any
from contextlib import contextmanager

import json
import psycopg2
import psycopg2.extras
from psycopg2.extras import Json

logger = logging.getLogger(__name__)

# Database connection settings (use Docker internal hostname)
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "eve_db"),
    "port": int(os.environ.get("DB_PORT", 5432)),
    "dbname": os.environ.get("DB_NAME", "eve_sde"),
    "user": os.environ.get("DB_USER", "eve"),
    "password": os.environ.get("DB_PASSWORD", ""),
}


@contextmanager
def db_cursor():
    """Database cursor context manager."""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur
    finally:
        conn.close()


def detect_primary_doctrine(ships: List[Dict[str, Any]]) -> str:
    """Detect primary doctrine type from ship fingerprint."""
    if not ships:
        return "Unknown"

    # Count by ship class
    class_counts = {}
    for ship in ships:
        ship_class = ship.get("ship_class", "unknown")
        class_counts[ship_class] = class_counts.get(ship_class, 0) + ship["uses"]

    # Find dominant class
    total = sum(class_counts.values())
    if total == 0:
        return "Unknown"

    sorted_classes = sorted(class_counts.items(), key=lambda x: x[1], reverse=True)
    top_class, top_count = sorted_classes[0]
    top_pct = (top_count / total) * 100

    # Map to doctrine type
    doctrine_map = {
        "heavy assault cruiser": "HAC Fleet",
        "command ship": "Command Fleet",
        "battleship": "Battleship Fleet",
        "strategic cruiser": "T3C Fleet",
        "cruiser": "Cruiser Fleet",
        "destroyer": "Destroyer Fleet",
        "frigate": "Frigate Fleet",
        "stealth bomber": "Bomber Fleet",
        "interdictor": "Dictor Gang",
        "logistics": "Support Fleet",
        "carrier": "Capital Fleet",
        "dreadnought": "Capital Fleet",
        "supercarrier": "Super Fleet",
        "titan": "Titan Fleet",
    }

    if top_pct >= 30:
        return doctrine_map.get(top_class.lower(), f"{top_class} Fleet")
    else:
        return "Mixed Fleet"


def refresh_alliance_fingerprints(days: int = 30) -> Dict[str, Any]:
    """
    Refresh alliance doctrine fingerprints from killmail data.

    Args:
        days: Number of days to analyze (default 30)

    Returns:
        Dict with stats about the refresh operation
    """
    logger.info(f"Starting alliance fingerprint refresh for last {days} days")
    start_time = datetime.now()

    stats = {
        "alliances_processed": 0,
        "alliances_updated": 0,
        "alliances_created": 0,
        "errors": 0
    }

    try:
        with db_cursor() as cur:
            # Get ship usage per alliance
            # Exclude Capsules (groupID 29) and Shuttles (groupID 31) from doctrine detection
            cur.execute("""
                WITH ship_usage AS (
                    SELECT
                        ka.alliance_id,
                        ka.ship_type_id,
                        t."typeName" as ship_name,
                        g."groupName" as ship_class,
                        COUNT(*) as uses
                    FROM killmail_attackers ka
                    JOIN killmails k ON ka.killmail_id = k.killmail_id
                    JOIN "invTypes" t ON ka.ship_type_id = t."typeID"
                    JOIN "invGroups" g ON t."groupID" = g."groupID"
                    WHERE ka.alliance_id IS NOT NULL
                      AND ka.ship_type_id IS NOT NULL
                      AND ka.ship_type_id > 0
                      AND g."groupID" NOT IN (29, 31)  -- Exclude Capsule (29) and Shuttle (31)
                      AND k.killmail_time > NOW() - INTERVAL '%s days'
                    GROUP BY ka.alliance_id, ka.ship_type_id, t."typeName", g."groupName"
                ),
                alliance_totals AS (
                    SELECT
                        alliance_id,
                        SUM(uses) as total_uses,
                        COUNT(DISTINCT ship_type_id) as unique_ships
                    FROM ship_usage
                    GROUP BY alliance_id
                    HAVING SUM(uses) >= 10  -- Minimum activity threshold
                ),
                ranked_ships AS (
                    SELECT
                        su.alliance_id,
                        su.ship_type_id,
                        su.ship_name,
                        su.ship_class,
                        su.uses,
                        at.total_uses,
                        at.unique_ships,
                        ROUND((su.uses::numeric / at.total_uses * 100), 2) as percentage,
                        ROW_NUMBER() OVER (PARTITION BY su.alliance_id ORDER BY su.uses DESC) as rank
                    FROM ship_usage su
                    JOIN alliance_totals at ON su.alliance_id = at.alliance_id
                )
                SELECT
                    alliance_id,
                    total_uses,
                    unique_ships,
                    JSONB_AGG(
                        JSONB_BUILD_OBJECT(
                            'type_id', ship_type_id,
                            'type_name', ship_name,
                            'ship_class', ship_class,
                            'uses', uses,
                            'percentage', percentage
                        ) ORDER BY uses DESC
                    ) as ship_fingerprint
                FROM ranked_ships
                WHERE rank <= 10
                GROUP BY alliance_id, total_uses, unique_ships
                ORDER BY total_uses DESC
            """, (days,))

            alliances = cur.fetchall()
            logger.info(f"Found {len(alliances)} alliances with activity")

            # Get alliance names
            alliance_ids = [row["alliance_id"] for row in alliances]
            if alliance_ids:
                placeholders = ','.join(['%s'] * len(alliance_ids))
                cur.execute(f"""
                    SELECT alliance_id, alliance_name
                    FROM alliance_name_cache
                    WHERE alliance_id IN ({placeholders})
                """, alliance_ids)
                name_map = {r["alliance_id"]: r["alliance_name"] for r in cur.fetchall()}
            else:
                name_map = {}

            # Process each alliance
            for row in alliances:
                stats["alliances_processed"] += 1
                alliance_id = row["alliance_id"]

                try:
                    ships = row["ship_fingerprint"]
                    primary_doctrine = detect_primary_doctrine(ships)
                    alliance_name = name_map.get(alliance_id, f"Alliance {alliance_id}")

                    # Upsert (coalition_id is now calculated dynamically by the API)
                    cur.execute("""
                        INSERT INTO alliance_doctrine_fingerprints
                            (alliance_id, alliance_name, total_uses, unique_ships,
                             ship_fingerprint, primary_doctrine,
                             data_period_days, last_updated)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (alliance_id) DO UPDATE SET
                            alliance_name = EXCLUDED.alliance_name,
                            total_uses = EXCLUDED.total_uses,
                            unique_ships = EXCLUDED.unique_ships,
                            ship_fingerprint = EXCLUDED.ship_fingerprint,
                            primary_doctrine = EXCLUDED.primary_doctrine,
                            data_period_days = EXCLUDED.data_period_days,
                            last_updated = NOW()
                    """, (
                        alliance_id,
                        alliance_name,
                        row["total_uses"],
                        row["unique_ships"],
                        Json(ships),  # Convert list of dicts to JSONB
                        primary_doctrine,
                        days
                    ))

                    stats["alliances_updated"] += 1

                except Exception as e:
                    logger.error(f"Error processing alliance {alliance_id}: {e}")
                    stats["errors"] += 1

    except Exception as e:
        logger.exception(f"Failed to refresh alliance fingerprints: {e}")
        raise

    elapsed = (datetime.now() - start_time).total_seconds()
    stats["elapsed_seconds"] = elapsed

    logger.info(
        f"Alliance fingerprint refresh complete: "
        f"{stats['alliances_updated']} updated, {stats['errors']} errors in {elapsed:.1f}s"
    )

    return stats


if __name__ == "__main__":
    # Allow running directly for testing
    logging.basicConfig(level=logging.INFO)
    result = refresh_alliance_fingerprints(30)
    print(result)
