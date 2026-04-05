"""Corp Wallet Journal sync with gap-filling algorithm.

Implements the backward-pagination gap-filling strategy from Spec Section 2.1.2:
1. Read high water mark (Local_Max_ID) from wallet_sync_state
2. Fetch latest page from ESI
3. Compare API_Min_ID with Local_Max_ID
4. If gap: backward pagination loop with from_id cursor
5. Circuit breaker: MAX_PAGES configurable (default 50)
"""

import logging
from typing import Optional

import httpx
from eve_shared import get_db
from eve_shared.esi import EsiClient, esi_circuit_breaker

from app.config import settings

logger = logging.getLogger(__name__)

ESI_JOURNAL_ENDPOINT = "/corporations/{corp_id}/wallets/{division}/journal/"


class WalletSyncService:
    """Syncs corporation wallet journal from ESI to local database."""

    def __init__(self):
        self.esi = EsiClient()
        self.db = get_db()
        self.max_pages = settings.wallet_sync_max_pages

    async def _get_corp_token(self, character_id: int) -> Optional[str]:
        """Get valid ESI token for a character via auth-service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.auth_service_url}/api/auth/token/{character_id}"
                )
                resp.raise_for_status()
                return resp.json()["access_token"]
        except Exception as e:
            logger.error("Failed to get token for character %s: %s", character_id, e)
            return None

    def _get_high_water_mark(self, corp_id: int, division: int) -> int:
        """Get the highest known transaction_id for this corp+division."""
        with self.db.cursor() as cur:
            cur.execute(
                "SELECT high_water_mark FROM wallet_sync_state "
                "WHERE corporation_id = %s AND division_id = %s",
                (corp_id, division),
            )
            row = cur.fetchone()
            return row["high_water_mark"] if row else 0

    def _update_sync_state(
        self, corp_id: int, division: int, hwm: int, pages: int, entries: int
    ):
        """Update the sync state after a successful sync."""
        with self.db.cursor() as cur:
            cur.execute(
                """INSERT INTO wallet_sync_state
                   (corporation_id, division_id, high_water_mark, last_sync_at,
                    pages_fetched, entries_added)
                   VALUES (%s, %s, %s, NOW(), %s, %s)
                   ON CONFLICT (corporation_id, division_id) DO UPDATE SET
                       high_water_mark = GREATEST(
                           wallet_sync_state.high_water_mark, EXCLUDED.high_water_mark
                       ),
                       last_sync_at = NOW(),
                       pages_fetched = EXCLUDED.pages_fetched,
                       entries_added = EXCLUDED.entries_added""",
                (corp_id, division, hwm, pages, entries),
            )

    def _upsert_journal_entries(self, entries: list[dict]) -> int:
        """UPSERT journal entries into corp_wallet_journal. Returns count inserted."""
        if not entries:
            return 0

        inserted = 0
        with self.db.cursor() as cur:
            for e in entries:
                # Build extra_info from optional ESI fields
                extra_info: dict = {}
                if e.get("tax"):
                    extra_info["tax"] = float(e["tax"])
                if e.get("tax_receiver_id"):
                    extra_info["tax_receiver_id"] = e["tax_receiver_id"]
                if e.get("context_id"):
                    extra_info["context_id"] = e["context_id"]
                if e.get("context_id_type"):
                    extra_info["context_id_type"] = e["context_id_type"]

                cur.execute(
                    """INSERT INTO corp_wallet_journal
                       (transaction_id, corporation_id, division_id, date,
                        ref_type, first_party_id, second_party_id,
                        amount, balance, reason, extra_info)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                       ON CONFLICT (transaction_id) DO NOTHING""",
                    (
                        e["id"],
                        e.get("corporation_id"),
                        e.get("division"),
                        e["date"],
                        e.get("ref_type", "unknown"),
                        e.get("first_party_id"),
                        e.get("second_party_id"),
                        e.get("amount", 0),
                        e.get("balance", 0),
                        e.get("reason"),
                        __import__("json").dumps(extra_info) if extra_info else "{}",
                    ),
                )
                # rowcount=1 means inserted, 0 means conflict (already existed)
                inserted += cur.rowcount

        return inserted

    def _fetch_journal_page(
        self, corp_id: int, division: int, token: str, from_id: Optional[int] = None
    ) -> list[dict]:
        """Fetch one page of wallet journal from ESI.

        ESI returns entries sorted by ID descending (newest first).
        Uses from_id cursor for backward pagination.
        """
        endpoint = ESI_JOURNAL_ENDPOINT.format(corp_id=corp_id, division=division)
        params = {}
        if from_id is not None:
            params["from_id"] = from_id

        result = self.esi.get(endpoint, token=token, params=params or None)
        if result is None:
            return []
        if not isinstance(result, list):
            return []
        return result

    async def sync_journal(
        self, corp_id: int, division: int, character_id: int
    ) -> dict:
        """Sync wallet journal for a corporation+division.

        Implements gap-filling algorithm:
        1. Get high water mark (Local_Max_ID)
        2. Fetch latest page
        3. If gap detected, paginate backward with from_id cursor
        4. Circuit breaker after max_pages

        Returns sync result dict.
        """
        result = {
            "corporation_id": corp_id,
            "division_id": division,
            "new_entries": 0,
            "gaps_filled": 0,
            "pages_fetched": 0,
        }

        # Check circuit breaker
        if esi_circuit_breaker.is_open():
            logger.warning("ESI circuit breaker open, skipping wallet sync")
            result["error"] = "circuit_breaker_open"
            return result

        # Get token
        token = await self._get_corp_token(character_id)
        if not token:
            result["error"] = "token_unavailable"
            return result

        local_max_id = self._get_high_water_mark(corp_id, division)
        total_inserted = 0
        pages_fetched = 0
        new_max_id = local_max_id
        gap_filling = False

        # Step 1: Fetch latest page (head request)
        entries = self._fetch_journal_page(corp_id, division, token)
        pages_fetched += 1

        if not entries:
            logger.info(
                "No journal entries for corp %s division %s", corp_id, division
            )
            self._update_sync_state(corp_id, division, local_max_id, 1, 0)
            result["pages_fetched"] = 1
            return result

        # Tag entries with corp_id and division (ESI doesn't include these)
        for e in entries:
            e["corporation_id"] = corp_id
            e["division"] = division

        # Track highest ID seen
        batch_max_id = max(e["id"] for e in entries)
        batch_min_id = min(e["id"] for e in entries)
        new_max_id = max(new_max_id, batch_max_id)

        # Insert first batch
        inserted = self._upsert_journal_entries(entries)
        total_inserted += inserted

        # Step 2: Check for gap
        # Scenario A: batch_min_id <= local_max_id → overlap found, no gap
        # Scenario B: batch_min_id > local_max_id → gap exists
        if local_max_id > 0 and batch_min_id > local_max_id:
            gap_filling = True
            logger.info(
                "Gap detected for corp %s div %s: local_max=%s, api_min=%s",
                corp_id,
                division,
                local_max_id,
                batch_min_id,
            )

            # Step 3: Backward pagination loop
            cursor = batch_min_id

            while pages_fetched < self.max_pages:
                entries = self._fetch_journal_page(corp_id, division, token, from_id=cursor)
                pages_fetched += 1

                if not entries:
                    # No more data from ESI (reached 30-day limit or empty)
                    logger.info(
                        "No more entries from ESI at cursor %s (page %s)",
                        cursor,
                        pages_fetched,
                    )
                    break

                for e in entries:
                    e["corporation_id"] = corp_id
                    e["division"] = division

                page_min_id = min(e["id"] for e in entries)
                inserted = self._upsert_journal_entries(entries)
                total_inserted += inserted

                # Check if gap is closed
                if page_min_id <= local_max_id:
                    logger.info(
                        "Gap closed at page %s (page_min=%s <= local_max=%s)",
                        pages_fetched,
                        page_min_id,
                        local_max_id,
                    )
                    break

                # Move cursor backward
                cursor = page_min_id

            else:
                # Circuit breaker: max pages reached
                logger.warning(
                    "Gap-filling circuit breaker: %s pages fetched for corp %s div %s "
                    "(gap too large, manual intervention may be required)",
                    self.max_pages,
                    corp_id,
                    division,
                )
                result["warning"] = "max_pages_reached"

        elif local_max_id == 0:
            # First sync ever — try to get as much history as possible
            cursor = batch_min_id
            while pages_fetched < self.max_pages:
                entries = self._fetch_journal_page(corp_id, division, token, from_id=cursor)
                pages_fetched += 1

                if not entries:
                    break

                for e in entries:
                    e["corporation_id"] = corp_id
                    e["division"] = division

                page_min_id = min(e["id"] for e in entries)
                inserted = self._upsert_journal_entries(entries)
                total_inserted += inserted

                if page_min_id == cursor:
                    # No progress, stop
                    break
                cursor = page_min_id

        # Update sync state
        self._update_sync_state(corp_id, division, new_max_id, pages_fetched, total_inserted)

        result["new_entries"] = total_inserted
        result["pages_fetched"] = pages_fetched
        if gap_filling:
            result["gaps_filled"] = total_inserted

        logger.info(
            "Wallet sync complete for corp %s div %s: %s new entries, %s pages",
            corp_id,
            division,
            total_inserted,
            pages_fetched,
        )

        return result

    async def sync_all_divisions(self, corp_id: int, character_id: int) -> list[dict]:
        """Sync all 7 wallet divisions for a corporation."""
        results = []
        for div in range(1, 8):
            res = await self.sync_journal(corp_id, div, character_id)
            results.append(res)
            # Check if circuit breaker tripped during sync
            if esi_circuit_breaker.is_open():
                logger.warning("Circuit breaker opened during sync, stopping")
                break
        return results
