#!/usr/bin/env python3
"""
Doctrine Extraction from Battles

Extracts fleet doctrines from completed battles.
More accurate than live snapshots because it sees the complete fleet composition.

Run daily via cron:
0 7 * * * cd /home/cytrex/eve_copilot && python3 jobs/doctrine_from_battles.py >> logs/doctrine_battles.log 2>&1
"""

import psycopg2
import json
import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Minimum kills for a battle to be considered for doctrine extraction
MIN_BATTLE_KILLS = 30

# Top N ships to include in doctrine composition
TOP_SHIPS = 15

# Ship types to exclude (pods, structures, etc)
EXCLUDED_SHIPS = [670, 33328]  # Capsule, Capsule - Genolution


def get_db_connection():
    import os
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "eve_db"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        database=os.environ.get("POSTGRES_DB", "eve_sde"),
        user=os.environ.get("POSTGRES_USER", "eve"),
        password=os.environ.get("POSTGRES_PASSWORD", ""),
        options="-c client_min_messages=ERROR"
    )


def get_recent_battles(cur, hours_back=24):
    """Get battles that ended in the last N hours"""
    cur.execute("""
        SELECT battle_id, solar_system_id, region_id, started_at, ended_at, total_kills
        FROM battles
        WHERE status = 'ended'
          AND total_kills >= %s
          AND ended_at > NOW() - INTERVAL '%s hours'
        ORDER BY total_kills DESC
    """, (MIN_BATTLE_KILLS, hours_back))
    return cur.fetchall()


def get_battle_composition(cur, battle_id):
    """Get ship composition for a battle"""
    excluded = tuple(EXCLUDED_SHIPS)
    cur.execute("""
        SELECT a.ship_type_id, COUNT(*) as cnt
        FROM killmail_attackers a
        JOIN killmails k ON a.killmail_id = k.killmail_id
        WHERE k.battle_id = %s
          AND a.ship_type_id IS NOT NULL
          AND a.ship_type_id NOT IN %s
        GROUP BY a.ship_type_id
        ORDER BY cnt DESC
        LIMIT %s
    """, (battle_id, excluded, TOP_SHIPS))
    return cur.fetchall()


def get_ship_name(cur, type_id):
    """Get ship name from SDE"""
    cur.execute('SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s', (type_id,))
    row = cur.fetchone()
    return row[0] if row else f"Ship {type_id}"


def doctrine_exists(cur, doctrine_name):
    """Check if doctrine already exists"""
    cur.execute("SELECT id FROM doctrine_templates WHERE doctrine_name = %s", (doctrine_name,))
    return cur.fetchone() is not None


def create_doctrine(cur, battle, composition):
    """Create a doctrine template from battle composition"""
    battle_id, system_id, region_id, started_at, ended_at, total_kills = battle

    if not composition:
        return None

    total = sum(s[1] for s in composition)

    # Create normalized composition
    comp_dict = {}
    for type_id, count in composition:
        ratio = round(count / total, 4)
        comp_dict[str(type_id)] = ratio

    # Get top ship name for doctrine name
    top_ship = get_ship_name(cur, composition[0][0])
    doctrine_name = f"{top_ship} Fleet (Battle {battle_id})"

    # Check if already exists
    if doctrine_exists(cur, doctrine_name):
        logger.info(f"  Skipping existing: {doctrine_name}")
        return None

    # Determine doctrine type based on ships
    doctrine_type = "subcap"
    capital_ships = [23757, 23911, 23913, 24483, 24685, 24688]  # Archon, Thanatos, etc
    for type_id, _ in composition:
        if type_id in capital_ships:
            doctrine_type = "capital"
            break

    # Insert doctrine
    cur.execute("""
        INSERT INTO doctrine_templates
        (doctrine_name, region_id, composition, confidence_score,
         observation_count, first_seen, last_seen, total_pilots_avg,
         primary_doctrine_type, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        RETURNING id
    """, (
        doctrine_name,
        region_id or 10000002,
        json.dumps(comp_dict),
        0.95,
        total_kills,
        started_at,
        ended_at or started_at,
        max(10, total_kills // 20),  # Rough fleet size estimate
        doctrine_type
    ))

    return cur.fetchone()[0]


def main():
    logger.info("=" * 60)
    logger.info("Starting doctrine extraction from battles")

    conn = get_db_connection()
    cur = conn.cursor()

    # Get recent ended battles
    battles = get_recent_battles(cur, hours_back=48)
    logger.info(f"Found {len(battles)} battles with {MIN_BATTLE_KILLS}+ kills")

    created = 0
    for battle in battles:
        battle_id = battle[0]
        total_kills = battle[5]

        composition = get_battle_composition(cur, battle_id)

        if composition:
            doctrine_id = create_doctrine(cur, battle, composition)
            if doctrine_id:
                logger.info(f"  ✓ Created doctrine {doctrine_id}: Battle {battle_id} ({total_kills} kills)")
                created += 1

    conn.commit()
    conn.close()

    logger.info("-" * 60)
    logger.info(f"Done! Created {created} new doctrines")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
