"""
Batch Pilot Skill Estimates - Parallel Processing

One-time batch job to calculate skill estimates for all pilots.
Uses multiprocessing for parallel execution.

Usage:
    python -m app.jobs.batch_pilot_skill_estimates [--workers 10] [--days 90] [--limit 0]

Example:
    # Process all pilots with 10 workers
    python -m app.jobs.batch_pilot_skill_estimates --workers 10

    # Process first 1000 pilots for testing
    python -m app.jobs.batch_pilot_skill_estimates --workers 4 --limit 1000
"""

import argparse
import logging
import time
from datetime import datetime
from multiprocessing import Pool, cpu_count
from typing import Dict, Any, List, Tuple

import psycopg2
import psycopg2.extras
from psycopg2.extras import Json

from app.jobs.pilot_skill_estimates import (
    DB_CONFIG,
    calculate_pilot_skills,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(processName)s] %(message)s'
)
logger = logging.getLogger(__name__)


def process_pilot_batch(args: Tuple[List[Dict], int]) -> Dict[str, int]:
    """
    Process a batch of pilots in a worker process.

    Args:
        args: Tuple of (pilots list, days)

    Returns:
        Dict with processing stats
    """
    pilots, days = args

    stats = {
        "processed": 0,
        "with_skills": 0,
        "total_sp": 0,
        "errors": 0
    }

    # Each worker gets its own DB connection
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        for pilot in pilots:
            character_id = pilot['character_id']
            alliance_id = pilot['alliance_id']

            try:
                result = calculate_pilot_skills(cur, character_id, alliance_id, days)

                # Upsert into cache table
                cur.execute("""
                    INSERT INTO pilot_skill_estimates
                        (character_id, alliance_id, min_sp, skill_breakdown,
                         ships_analyzed, modules_analyzed, fitted_modules_analyzed, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (character_id) DO UPDATE SET
                        alliance_id = EXCLUDED.alliance_id,
                        min_sp = EXCLUDED.min_sp,
                        skill_breakdown = EXCLUDED.skill_breakdown,
                        ships_analyzed = EXCLUDED.ships_analyzed,
                        modules_analyzed = EXCLUDED.modules_analyzed,
                        fitted_modules_analyzed = EXCLUDED.fitted_modules_analyzed,
                        updated_at = NOW()
                """, (
                    character_id,
                    alliance_id,
                    result['min_sp'],
                    Json(result['categories']),
                    result['ships_analyzed'],
                    result['modules_analyzed'],
                    result['fitted_modules_analyzed']
                ))

                stats["processed"] += 1
                if result['min_sp'] > 0:
                    stats["with_skills"] += 1
                    stats["total_sp"] += result['min_sp']

            except Exception as e:
                logger.warning(f"Error processing pilot {character_id}: {e}")
                stats["errors"] += 1

    finally:
        cur.close()
        conn.close()

    return stats


def get_all_pilots(days: int, limit: int = 0) -> List[Dict]:
    """Get all pilots to process."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Get all unique character/alliance combinations from recent kills
        query = """
            SELECT DISTINCT ka.character_id, ka.alliance_id
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            WHERE k.killmail_time > NOW() - INTERVAL '%s days'
              AND ka.character_id IS NOT NULL
              AND ka.alliance_id IS NOT NULL
            ORDER BY ka.character_id
        """

        if limit > 0:
            query += f" LIMIT {limit}"

        cur.execute(query, (days,))
        pilots = cur.fetchall()

        return [dict(p) for p in pilots]

    finally:
        cur.close()
        conn.close()


def chunk_list(lst: List, n: int) -> List[List]:
    """Split list into n roughly equal chunks."""
    k, m = divmod(len(lst), n)
    return [lst[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n)]


def run_batch(workers: int = 10, days: int = 90, limit: int = 0) -> Dict[str, Any]:
    """
    Run batch processing with multiple workers.

    Args:
        workers: Number of parallel workers
        days: Number of days to analyze
        limit: Max pilots to process (0 = all)

    Returns:
        Dict with overall stats
    """
    start_time = datetime.now()
    logger.info(f"Starting batch pilot skill estimates with {workers} workers")

    # Get all pilots
    logger.info("Fetching pilot list...")
    pilots = get_all_pilots(days, limit)
    total_pilots = len(pilots)
    logger.info(f"Found {total_pilots:,} pilots to process")

    if total_pilots == 0:
        return {"success": True, "pilots": 0, "duration_seconds": 0}

    # Split into chunks for workers
    chunks = chunk_list(pilots, workers)
    logger.info(f"Split into {len(chunks)} chunks of ~{len(chunks[0]) if chunks else 0} pilots each")

    # Process in parallel
    with Pool(processes=workers) as pool:
        # Pass (chunk, days) tuple to each worker
        args = [(chunk, days) for chunk in chunks]
        results = pool.map(process_pilot_batch, args)

    # Aggregate results
    total_stats = {
        "processed": sum(r["processed"] for r in results),
        "with_skills": sum(r["with_skills"] for r in results),
        "total_sp": sum(r["total_sp"] for r in results),
        "errors": sum(r["errors"] for r in results)
    }

    duration = (datetime.now() - start_time).total_seconds()

    logger.info(
        f"Batch complete: {total_stats['processed']:,} pilots processed, "
        f"{total_stats['with_skills']:,} with skills, "
        f"{total_stats['total_sp']:,} total SP, "
        f"{total_stats['errors']} errors, "
        f"in {duration:.1f}s ({total_stats['processed']/duration:.1f} pilots/sec)"
    )

    return {
        "success": True,
        "total_pilots": total_pilots,
        "stats": total_stats,
        "duration_seconds": duration,
        "pilots_per_second": total_stats['processed'] / duration if duration > 0 else 0
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch process pilot skill estimates")
    parser.add_argument("--workers", type=int, default=10, help="Number of parallel workers")
    parser.add_argument("--days", type=int, default=90, help="Days to analyze")
    parser.add_argument("--limit", type=int, default=0, help="Max pilots (0 = all)")

    args = parser.parse_args()

    result = run_batch(workers=args.workers, days=args.days, limit=args.limit)

    print("\n" + "="*60)
    print("BATCH COMPLETE")
    print("="*60)
    print(f"Total pilots:    {result['total_pilots']:,}")
    print(f"Processed:       {result['stats']['processed']:,}")
    print(f"With skills:     {result['stats']['with_skills']:,}")
    print(f"Total SP:        {result['stats']['total_sp']:,}")
    print(f"Errors:          {result['stats']['errors']}")
    print(f"Duration:        {result['duration_seconds']:.1f}s")
    print(f"Rate:            {result['pilots_per_second']:.1f} pilots/sec")
    print("="*60)
