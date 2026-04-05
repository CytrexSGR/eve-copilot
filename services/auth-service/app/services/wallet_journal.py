"""
ESI Wallet Journal fetcher for payment processing.

Fetches wallet journal entries for the holding character via ESI,
filtering for incoming player donations after a given ref ID.
"""
import logging
from typing import List, Dict, Any

import httpx

from app.services.payment_poller import is_player_donation

logger = logging.getLogger(__name__)

ESI_BASE = "https://esi.evetech.net/latest"


def build_journal_url(character_id: int, page: int = 1) -> str:
    """Build ESI wallet journal URL."""
    url = f"{ESI_BASE}/characters/{character_id}/wallet/journal/"
    if page > 1:
        url += f"?page={page}"
    return url


def filter_donations_since(
    entries: List[Dict[str, Any]],
    last_ref_id: int,
) -> List[Dict[str, Any]]:
    """Filter journal entries to player donations after last_ref_id."""
    result = []
    for entry in entries:
        if entry.get("id", 0) <= last_ref_id:
            continue
        if not is_player_donation(entry):
            continue
        result.append(entry)
    return result


async def fetch_wallet_journal(
    character_id: int,
    access_token: str,
    last_ref_id: int = 0,
) -> List[Dict[str, Any]]:
    """
    Fetch wallet journal from ESI and filter to new donations.

    Returns list of donation entries with id > last_ref_id.
    """
    url = build_journal_url(character_id)
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                entries = resp.json()
                return filter_donations_since(entries, last_ref_id)
            elif resp.status_code == 403:
                logger.error("ESI 403 for wallet journal — token may lack esi-wallet.read_character_wallet.v1 scope")
                return []
            else:
                logger.warning(f"ESI wallet journal returned {resp.status_code}")
                return []
    except Exception as e:
        logger.error(f"ESI wallet journal fetch failed: {e}")
        return []
