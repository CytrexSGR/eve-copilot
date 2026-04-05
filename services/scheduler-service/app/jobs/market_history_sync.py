# services/scheduler-service/app/jobs/market_history_sync.py
"""
Market History Sync Job

Fetches ESI market history for top items and calculates trading metrics:
- avg_daily_volume (30-day average)
- price_volatility (std dev as %)
- trend_7d (7-day price change %)
- days_to_sell_100
- risk_score
"""

import logging
import asyncio
import os
import statistics
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

import httpx
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)

ESI_BASE = "https://esi.evetech.net/latest"
REGION_ID = 10000002  # The Forge (Jita)
BATCH_SIZE = 50
MAX_ITEMS = 5000

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
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur, conn
    finally:
        conn.close()


async def fetch_market_history(
    client: httpx.AsyncClient,
    region_id: int,
    type_id: int
) -> Optional[List[Dict[str, Any]]]:
    """Fetch market history from ESI."""
    url = f"{ESI_BASE}/markets/{region_id}/history/"
    params = {"type_id": type_id, "datasource": "tranquility"}

    try:
        response = await client.get(url, params=params, timeout=30)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return None
        else:
            logger.debug(f"ESI {response.status_code} for type {type_id}")
            return None
    except Exception as e:
        logger.debug(f"Error fetching {type_id}: {e}")
        return None


def calculate_metrics(history: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Calculate trading metrics from history data."""
    if not history or len(history) < 7:
        return None

    # Sort by date
    history = sorted(history, key=lambda x: x['date'])

    # Last 30 days
    recent = history[-30:] if len(history) >= 30 else history

    volumes = [h.get('volume', 0) for h in recent]
    prices = [h.get('average', 0) for h in recent if h.get('average', 0) > 0]

    if not volumes or not prices:
        return None

    avg_volume = sum(volumes) / len(volumes)
    avg_price = sum(prices) / len(prices)

    # Volatility (std dev as % of mean)
    if len(prices) >= 2 and avg_price > 0:
        try:
            std_dev = statistics.stdev(prices)
            volatility = (std_dev / avg_price) * 100
        except Exception:
            volatility = 0
    else:
        volatility = 0

    # 7-day trend
    if len(history) >= 7:
        price_7d_ago = history[-7].get('average', 0)
        price_now = history[-1].get('average', 0)
        if price_7d_ago > 0:
            trend_7d = ((price_now - price_7d_ago) / price_7d_ago) * 100
        else:
            trend_7d = 0
    else:
        trend_7d = 0

    # Days to sell 100 units
    days_to_sell = (100 / avg_volume) if avg_volume > 0 else None

    # Risk score (0-100, lower = safer)
    # Based on: volatility (40%), volume (30%), trend stability (30%)
    vol_score = min(volatility * 2, 40)  # High volatility = high risk

    if avg_volume >= 1000:
        volume_score = 0
    elif avg_volume >= 100:
        volume_score = 15
    else:
        volume_score = 30  # Low volume = higher risk

    trend_score = min(abs(trend_7d), 30)  # Big swings = risk

    risk_score = int(vol_score + volume_score + trend_score)
    risk_score = min(max(risk_score, 0), 100)

    # Cap extreme values to fit in NUMERIC(12,4)
    volatility = min(volatility, 9999999.9999)
    trend_7d = min(max(trend_7d, -9999999.9999), 9999999.9999)

    return {
        'avg_daily_volume': int(avg_volume),
        'price_volatility': round(volatility, 4),
        'trend_7d': round(trend_7d, 4),
        'days_to_sell_100': round(days_to_sell, 2) if days_to_sell else None,
        'risk_score': risk_score
    }


async def sync_market_history():
    """Main sync function."""
    logger.info("Starting market history sync...")

    # Get top items by volume
    with db_cursor() as (cur, conn):
        cur.execute("""
            SELECT type_id
            FROM market_prices
            WHERE region_id = %s
            AND COALESCE(buy_volume, 0) + COALESCE(sell_volume, 0) > 0
            ORDER BY COALESCE(buy_volume, 0) + COALESCE(sell_volume, 0) DESC
            LIMIT %s
        """, (REGION_ID, MAX_ITEMS))
        type_ids = [row['type_id'] for row in cur.fetchall()]

    logger.info(f"Processing {len(type_ids)} items...")

    updated = 0
    errors = 0

    async with httpx.AsyncClient() as client:
        # Process in batches
        for i in range(0, len(type_ids), BATCH_SIZE):
            batch = type_ids[i:i + BATCH_SIZE]

            # Fetch all in parallel
            tasks = [
                fetch_market_history(client, REGION_ID, type_id)
                for type_id in batch
            ]
            results = await asyncio.gather(*tasks)

            # Process results
            updates = []
            for type_id, history in zip(batch, results):
                if history:
                    metrics = calculate_metrics(history)
                    if metrics:
                        updates.append((type_id, metrics))

            # Batch update database
            if updates:
                with db_cursor() as (cur, conn):
                    for type_id, metrics in updates:
                        cur.execute("""
                            UPDATE market_prices SET
                                avg_daily_volume = %s,
                                price_volatility = %s,
                                trend_7d = %s,
                                days_to_sell_100 = %s,
                                risk_score = %s,
                                metrics_updated_at = %s
                            WHERE type_id = %s AND region_id = %s
                        """, (
                            metrics['avg_daily_volume'],
                            metrics['price_volatility'],
                            metrics['trend_7d'],
                            metrics['days_to_sell_100'],
                            metrics['risk_score'],
                            datetime.now(timezone.utc),
                            type_id,
                            REGION_ID
                        ))
                    conn.commit()

                updated += len(updates)

            errors += len(batch) - len(updates)

            # Rate limit: ~100 req/sec allowed, be conservative
            await asyncio.sleep(0.5)

            if (i + BATCH_SIZE) % 500 == 0:
                logger.info(f"Progress: {i + BATCH_SIZE}/{len(type_ids)} items")

    logger.info(f"Market history sync complete: {updated} updated, {errors} skipped")
    return updated


def run_market_history_sync():
    """Synchronous wrapper for scheduler."""
    return asyncio.run(sync_market_history())


if __name__ == "__main__":
    # Allow running directly for testing
    logging.basicConfig(level=logging.INFO)
    result = run_market_history_sync()
    print(f"Updated {result} items")
