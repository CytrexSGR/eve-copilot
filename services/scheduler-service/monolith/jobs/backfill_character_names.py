#!/usr/bin/env python3
"""
Backfill character names for existing killmails.

Runs in batches to avoid ESI rate limits:
- Fetches 1000 unique character IDs without names
- Resolves via ESI /universe/names/
- Updates character_name_cache + killmails/attackers
- Sleeps between batches

Usage:
    python jobs/backfill_character_names.py [--batch-size 1000] [--delay 2]
"""

import argparse
import time
import requests
import psycopg2
from psycopg2.extras import execute_values

# Database config
import os
DB_CONFIG = {
    "host": os.environ.get("POSTGRES_HOST", "eve_db"),
    "port": int(os.environ.get("POSTGRES_PORT", "5432")),
    "dbname": os.environ.get("POSTGRES_DB", "eve_sde"),
    "user": os.environ.get("POSTGRES_USER", "eve"),
    "password": os.environ.get("POSTGRES_PASSWORD", "")
}

ESI_NAMES_URL = "https://esi.evetech.net/latest/universe/names/"


def get_unresolved_character_ids(conn, limit: int) -> list:
    """Get character IDs that don't have names yet."""
    with conn.cursor() as cur:
        cur.execute("""
            WITH all_chars AS (
                SELECT DISTINCT victim_character_id as char_id FROM killmails
                WHERE victim_character_id IS NOT NULL AND victim_character_name IS NULL
                UNION
                SELECT DISTINCT character_id FROM killmail_attackers
                WHERE character_id IS NOT NULL AND character_name IS NULL
            )
            SELECT char_id FROM all_chars
            WHERE char_id NOT IN (SELECT character_id FROM character_name_cache)
            LIMIT %s
        """, (limit,))
        return [row[0] for row in cur.fetchall()]


def resolve_names_via_esi(character_ids: list) -> dict:
    """Resolve character names via ESI batch endpoint."""
    if not character_ids:
        return {}

    try:
        resp = requests.post(
            ESI_NAMES_URL,
            json=character_ids,
            timeout=30,
            headers={"User-Agent": "EVE-Copilot/1.0 backfill"}
        )
        if resp.status_code == 200:
            return {item["id"]: item["name"] for item in resp.json()}
        elif resp.status_code == 404:
            # Some IDs might be invalid/deleted characters
            print(f"  Warning: Some IDs not found (404)")
            return {}
        else:
            print(f"  ESI error: {resp.status_code}")
            return {}
    except Exception as e:
        print(f"  ESI request failed: {e}")
        return {}


def update_database(conn, names: dict):
    """Update character_name_cache and killmail tables."""
    if not names:
        return

    with conn.cursor() as cur:
        # 1. Insert into character_name_cache
        values = [(char_id, name) for char_id, name in names.items()]
        execute_values(cur, """
            INSERT INTO character_name_cache (character_id, character_name)
            VALUES %s
            ON CONFLICT (character_id) DO UPDATE SET
                character_name = EXCLUDED.character_name,
                updated_at = NOW()
        """, values)

        # 2. Update killmails victim names
        cur.execute("""
            UPDATE killmails k
            SET victim_character_name = c.character_name
            FROM character_name_cache c
            WHERE k.victim_character_id = c.character_id
            AND k.victim_character_name IS NULL
            AND k.victim_character_id = ANY(%s)
        """, (list(names.keys()),))
        victim_updated = cur.rowcount

        # 3. Update killmails final_blow names
        cur.execute("""
            UPDATE killmails k
            SET final_blow_character_name = c.character_name
            FROM character_name_cache c
            WHERE k.final_blow_character_id = c.character_id
            AND k.final_blow_character_name IS NULL
            AND k.final_blow_character_id = ANY(%s)
        """, (list(names.keys()),))
        final_updated = cur.rowcount

        # 4. Update attacker names
        cur.execute("""
            UPDATE killmail_attackers ka
            SET character_name = c.character_name
            FROM character_name_cache c
            WHERE ka.character_id = c.character_id
            AND ka.character_name IS NULL
            AND ka.character_id = ANY(%s)
        """, (list(names.keys()),))
        attacker_updated = cur.rowcount

        conn.commit()
        print(f"  Updated: {victim_updated} victims, {final_updated} final blows, {attacker_updated} attackers")


def main():
    parser = argparse.ArgumentParser(description="Backfill character names")
    parser.add_argument("--batch-size", type=int, default=1000, help="IDs per batch")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between batches")
    parser.add_argument("--max-batches", type=int, default=0, help="Max batches (0=unlimited)")
    args = parser.parse_args()

    conn = psycopg2.connect(**DB_CONFIG)

    batch_num = 0
    total_resolved = 0

    print(f"Starting backfill (batch_size={args.batch_size}, delay={args.delay}s)")

    while True:
        batch_num += 1

        if args.max_batches > 0 and batch_num > args.max_batches:
            print(f"Reached max batches ({args.max_batches})")
            break

        # Get unresolved IDs
        char_ids = get_unresolved_character_ids(conn, args.batch_size)

        if not char_ids:
            print("No more characters to resolve!")
            break

        print(f"Batch {batch_num}: Resolving {len(char_ids)} characters...")

        # Resolve via ESI
        names = resolve_names_via_esi(char_ids)

        if names:
            update_database(conn, names)
            total_resolved += len(names)
            print(f"  Resolved {len(names)} names (total: {total_resolved})")
        else:
            # If ESI fails, mark these as processed to avoid infinite loop
            print(f"  No names resolved, skipping batch")

        # Rate limit
        if char_ids:
            time.sleep(args.delay)

    conn.close()
    print(f"\nDone! Total resolved: {total_resolved}")


if __name__ == "__main__":
    main()
