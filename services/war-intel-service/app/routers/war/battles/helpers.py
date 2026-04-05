"""Shared helpers for battle endpoints."""

import logging
from typing import List

import httpx

from app.database import db_cursor

logger = logging.getLogger(__name__)


async def fetch_and_cache_alliance_names(alliance_ids: List[int]):
    """Fetch alliance names from ESI and cache them."""
    if not alliance_ids:
        return

    async with httpx.AsyncClient(timeout=10.0) as client:
        for alliance_id in alliance_ids[:10]:  # Limit to 10 per request
            try:
                resp = await client.get(f"https://esi.evetech.net/latest/alliances/{alliance_id}/")
                if resp.status_code == 200:
                    data = resp.json()
                    alliance_name = data.get("name")
                    ticker = data.get("ticker")
                    if alliance_name:
                        with db_cursor() as cur:
                            cur.execute("""
                                INSERT INTO alliance_name_cache (alliance_id, alliance_name, ticker)
                                VALUES (%s, %s, %s)
                                ON CONFLICT (alliance_id) DO UPDATE SET
                                    alliance_name = EXCLUDED.alliance_name,
                                    ticker = EXCLUDED.ticker,
                                    updated_at = NOW()
                            """, (alliance_id, alliance_name, ticker))
                        logger.debug(f"Cached alliance {alliance_id}: {alliance_name}")
            except Exception as e:
                logger.debug(f"Failed to fetch alliance {alliance_id}: {e}")
