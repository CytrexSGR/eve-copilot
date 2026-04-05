"""
Corporation Sync Job

Fetches corporation membership for all active alliances from ESI.
This is "Truth #1" (structural membership) for coalition detection.

The job:
1. Gets all active alliances (from alliance_activity_total with kills > 100)
2. For each alliance, fetches corporation IDs from ESI
3. For each corporation, fetches corp details (name, ticker, member_count)
4. Upserts into corporations table

Runs daily.
"""

import sys
sys.path.insert(0, '/home/cytrex/eve_copilot')

import logging
import os
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Any, Optional
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

from src.integrations.esi.shared_rate_state import shared_rate_state

logger = logging.getLogger(__name__)

# Database connection settings
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "eve_sde",
    "user": "eve",
    "password": os.environ.get("DB_PASSWORD", "")
}

# ESI endpoints
ESI_BASE = "https://esi.evetech.net/latest"
ESI_ALLIANCE_CORPS = ESI_BASE + "/alliances/{alliance_id}/corporations/"
ESI_CORPORATION = ESI_BASE + "/corporations/{corporation_id}/"

# Rate limiting
MAX_CONCURRENT_REQUESTS = 20
REQUEST_TIMEOUT = 10


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


async def fetch_alliance_corporations(
    session: aiohttp.ClientSession,
    alliance_id: int
) -> List[int]:
    """Fetch corporation IDs for an alliance from ESI."""
    if shared_rate_state.is_globally_banned() or shared_rate_state.should_hard_stop():
        return []
    url = ESI_ALLIANCE_CORPS.format(alliance_id=alliance_id)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as response:
            shared_rate_state.update_from_headers(dict(response.headers))
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                logger.debug(f"Alliance {alliance_id} not found (404)")
                return []
            elif response.status == 420:
                shared_rate_state.set_global_ban()
                return []
            else:
                logger.warning(f"ESI error for alliance {alliance_id}: {response.status}")
                return []
    except Exception as e:
        logger.error(f"Failed to fetch corps for alliance {alliance_id}: {e}")
        return []


async def fetch_corporation_details(
    session: aiohttp.ClientSession,
    corporation_id: int
) -> Optional[Dict[str, Any]]:
    """Fetch corporation details from ESI."""
    if shared_rate_state.is_globally_banned() or shared_rate_state.should_hard_stop():
        return None
    url = ESI_CORPORATION.format(corporation_id=corporation_id)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as response:
            shared_rate_state.update_from_headers(dict(response.headers))
            if response.status == 200:
                data = await response.json()
                return {
                    "corporation_id": corporation_id,
                    "corporation_name": data.get("name", f"Corporation {corporation_id}"),
                    "ticker": data.get("ticker", "???"),
                    "alliance_id": data.get("alliance_id"),
                    "ceo_id": data.get("ceo_id"),
                    "member_count": data.get("member_count", 0),
                    "home_system_id": data.get("home_station_id")
                }
            elif response.status == 404:
                logger.debug(f"Corporation {corporation_id} not found (404)")
                return None
            elif response.status == 420:
                shared_rate_state.set_global_ban()
                return None
            else:
                logger.warning(f"ESI error for corporation {corporation_id}: {response.status}")
                return None
    except Exception as e:
        logger.error(f"Failed to fetch details for corporation {corporation_id}: {e}")
        return None


async def fetch_corporations_batch(
    session: aiohttp.ClientSession,
    corporation_ids: List[int]
) -> List[Dict[str, Any]]:
    """Fetch corporation details in batches."""
    results = []
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def fetch_with_semaphore(corp_id: int) -> Optional[Dict[str, Any]]:
        async with semaphore:
            return await fetch_corporation_details(session, corp_id)

    tasks = [fetch_with_semaphore(corp_id) for corp_id in corporation_ids]
    fetched = await asyncio.gather(*tasks)

    for result in fetched:
        if result:
            results.append(result)

    return results


def get_active_alliances() -> List[int]:
    """Get alliances with significant activity."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT alliance_id
            FROM alliance_activity_total
            WHERE total_kills > 100
            ORDER BY total_kills DESC
        """)
        return [row["alliance_id"] for row in cur.fetchall()]


def get_recently_updated_corp_ids(hours: int = 24) -> set:
    """Get corporation IDs updated within the last N hours."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT corporation_id FROM corporations
            WHERE updated_at > NOW() - INTERVAL '%s hours'
        """, (hours,))
        return {row["corporation_id"] for row in cur.fetchall()}


def upsert_corporations(corporations: List[Dict[str, Any]]) -> int:
    """Upsert corporation data into database."""
    if not corporations:
        return 0

    with db_cursor() as cur:
        # Use execute_batch for efficiency
        query = """
            INSERT INTO corporations (
                corporation_id, corporation_name, ticker,
                alliance_id, ceo_id, member_count, home_system_id, updated_at
            ) VALUES (
                %(corporation_id)s, %(corporation_name)s, %(ticker)s,
                %(alliance_id)s, %(ceo_id)s, %(member_count)s, %(home_system_id)s, NOW()
            )
            ON CONFLICT (corporation_id) DO UPDATE SET
                corporation_name = EXCLUDED.corporation_name,
                ticker = EXCLUDED.ticker,
                alliance_id = EXCLUDED.alliance_id,
                ceo_id = EXCLUDED.ceo_id,
                member_count = EXCLUDED.member_count,
                home_system_id = EXCLUDED.home_system_id,
                updated_at = NOW()
        """
        psycopg2.extras.execute_batch(cur, query, corporations)

        # Record daily member count snapshot for history tracking
        history_query = """
            INSERT INTO corporation_member_count_history
                (corporation_id, snapshot_date, member_count, alliance_id)
            VALUES (%(corporation_id)s, CURRENT_DATE, %(member_count)s, %(alliance_id)s)
            ON CONFLICT (corporation_id, snapshot_date) DO NOTHING
        """
        psycopg2.extras.execute_batch(cur, history_query, corporations)

        return len(corporations)


async def sync_corporation_data() -> Dict[str, Any]:
    """
    Main sync function. Fetches all corporations for active alliances.

    Returns:
        Dict with stats about the sync operation
    """
    logger.info("Starting corporation sync")
    start_time = datetime.now()

    stats = {
        "alliances_processed": 0,
        "corporations_fetched": 0,
        "corporations_saved": 0,
        "errors": 0
    }

    # Get active alliances
    alliance_ids = get_active_alliances()
    logger.info(f"Found {len(alliance_ids)} active alliances")
    stats["alliances_to_process"] = len(alliance_ids)

    all_corporation_ids = set()

    async with aiohttp.ClientSession() as session:
        # Fetch corporation IDs for each alliance
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def fetch_alliance_corps(alliance_id: int) -> List[int]:
            async with semaphore:
                return await fetch_alliance_corporations(session, alliance_id)

        tasks = [fetch_alliance_corps(aid) for aid in alliance_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            stats["alliances_processed"] += 1
            if isinstance(result, Exception):
                logger.error(f"Error fetching alliance {alliance_ids[i]}: {result}")
                stats["errors"] += 1
            elif isinstance(result, list):
                all_corporation_ids.update(result)

        logger.info(f"Found {len(all_corporation_ids)} unique corporations")
        stats["unique_corporations"] = len(all_corporation_ids)

        # Delta: skip recently updated corps
        fresh_corps = get_recently_updated_corp_ids(hours=24)
        stale_corps = all_corporation_ids - fresh_corps
        stats["total_corporations"] = len(all_corporation_ids)
        stats["skipped_fresh"] = len(fresh_corps & all_corporation_ids)
        stats["stale_to_fetch"] = len(stale_corps)

        logger.info(
            f"Delta sync: {len(stale_corps)} stale, "
            f"{stats['skipped_fresh']} fresh (skipped)"
        )

        if not stale_corps:
            logger.info("All corporations up-to-date, skipping ESI fetch")
            elapsed = (datetime.now() - start_time).total_seconds()
            stats["elapsed_seconds"] = elapsed
            return stats

        # Fetch only stale corporation details in batches
        corp_list = list(stale_corps)
        batch_size = 500
        all_corps = []

        for i in range(0, len(corp_list), batch_size):
            batch = corp_list[i:i+batch_size]
            logger.info(f"Fetching corporation details {i+1}-{min(i+batch_size, len(corp_list))} of {len(corp_list)}")

            corps = await fetch_corporations_batch(session, batch)
            all_corps.extend(corps)
            stats["corporations_fetched"] += len(corps)

    # Save to database
    if all_corps:
        saved = upsert_corporations(all_corps)
        stats["corporations_saved"] = saved
        logger.info(f"Saved {saved} corporations to database")

    elapsed = (datetime.now() - start_time).total_seconds()
    stats["elapsed_seconds"] = elapsed

    logger.info(
        f"Corporation sync complete: "
        f"{stats['corporations_saved']} corporations from {stats['alliances_processed']} alliances "
        f"in {elapsed:.1f}s"
    )

    return stats


def run_sync() -> Dict[str, Any]:
    """Synchronous wrapper for the async sync function."""
    return asyncio.run(sync_corporation_data())


if __name__ == "__main__":
    # Allow running directly for testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )
    result = run_sync()
    print(f"\nResult: {result}")
