"""
zKillboard R2Z2 Client

Replacement for RedisQ using Cloudflare R2 sequence-based polling.
R2Z2 delivers complete killmail data (ESI + zkb) in each response,
eliminating the need for separate ESI fetches.

API Documentation: https://github.com/zKillboard/zKillboard/wiki/API-(R2Z2)

Key differences from RedisQ:
- Client tracks sequence number (not server-side queue)
- 404 = no data yet (wait 6s), 200 = data (increment sequence)
- Complete killmail included (no ESI fetch needed)
- Rate limit: 20 req/s/IP (we use 15 to be safe)
"""

import asyncio
import logging
import platform
from typing import Optional, Dict, Any
from dataclasses import dataclass

import aiohttp

from services.zkillboard.live.models import (
    R2Z2_BASE_URL,
    R2Z2_SEQUENCE_ENDPOINT,
    R2Z2_KILLMAIL_ENDPOINT,
    R2Z2_POLL_INTERVAL_DATA,
    R2Z2_POLL_INTERVAL_EMPTY,
    R2Z2_MAX_REQUESTS_PER_SECOND,
    R2Z2_REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)

USER_AGENT = f"EVE-CoPilot/3.0 ({platform.system()}; R2Z2 Client)"

# Retry configuration
MAX_RETRIES = 5
INITIAL_BACKOFF = 2.0
MAX_BACKOFF = 120.0


@dataclass
class R2Z2Package:
    """Parsed R2Z2 killmail package."""
    killmail_id: int
    hash: str
    zkb: Dict[str, Any]
    killmail: Dict[str, Any]  # Always present in R2Z2 (unlike RedisQ)
    sequence_id: int
    uploaded_at: int


class R2Z2Client:
    """
    Client for zKillboard R2Z2 API.

    Polling loop:
    1. Fetch sequence.json to get starting point (or resume from Redis)
    2. Fetch {sequence}.json
    3. On 200: process, sleep 100ms, sequence++
    4. On 404: sleep 6s, retry same sequence
    5. On 429: exponential backoff
    """

    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self._session = session
        self._own_session = False
        self._running = True
        self._last_request_time = 0.0
        self._consecutive_errors = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Encoding": "gzip",
                    "Accept": "application/json",
                },
                timeout=aiohttp.ClientTimeout(total=R2Z2_REQUEST_TIMEOUT),
            )
            self._own_session = True
        return self._session

    async def close(self):
        """Close the client session."""
        if self._own_session and self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def stop(self):
        """Signal the client to stop."""
        self._running = False

    async def _rate_limit(self):
        """Enforce rate limiting."""
        now = asyncio.get_event_loop().time()
        min_interval = 1.0 / R2Z2_MAX_REQUESTS_PER_SECOND
        elapsed = now - self._last_request_time
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    async def fetch_current_sequence(self) -> Optional[int]:
        """
        Fetch the current sequence number from R2Z2.

        Returns:
            Current sequence number, or None on error
        """
        await self._rate_limit()
        session = await self._get_session()

        try:
            async with session.get(R2Z2_SEQUENCE_ENDPOINT) as response:
                if response.status == 200:
                    data = await response.json()
                    seq = data.get("sequence")
                    if seq is not None:
                        return int(seq)
                    logger.error("[R2Z2] sequence.json missing 'sequence' field")
                    return None
                else:
                    logger.error(f"[R2Z2] Failed to fetch sequence.json: HTTP {response.status}")
                    return None
        except Exception as e:
            logger.error(f"[R2Z2] Error fetching sequence.json: {e}")
            return None

    async def fetch_killmail(self, sequence_id: int) -> Optional[R2Z2Package]:
        """
        Fetch a killmail by sequence number.

        Args:
            sequence_id: The sequence number to fetch

        Returns:
            R2Z2Package on success, None on 404 (no data) or error.
            Raises R2Z2RateLimited on 429.
        """
        await self._rate_limit()
        session = await self._get_session()
        url = R2Z2_KILLMAIL_ENDPOINT.format(sequence_id=sequence_id)

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    self._consecutive_errors = 0

                    killmail_id = data.get("killmail_id")
                    zkb = data.get("zkb", {})
                    # R2Z2 uses "esi" key for killmail data (not "killmail")
                    killmail = data.get("esi") or data.get("killmail")
                    hash_str = zkb.get("hash", data.get("hash", ""))

                    if not killmail_id or not killmail:
                        logger.warning(f"[R2Z2] Sequence {sequence_id}: missing killmail_id or killmail data")
                        return None

                    return R2Z2Package(
                        killmail_id=killmail_id,
                        hash=hash_str,
                        zkb=zkb,
                        killmail=killmail,
                        sequence_id=data.get("sequence_id", sequence_id),
                        uploaded_at=data.get("uploaded_at", 0),
                    )

                elif response.status == 404:
                    # No data at this sequence yet — caller should wait
                    return None

                elif response.status == 429:
                    retry_after = int(response.headers.get("Retry-After", 10))
                    logger.warning(f"[R2Z2] Rate limited (429), retry after {retry_after}s")
                    raise R2Z2RateLimited(retry_after)

                elif response.status == 403:
                    logger.error("[R2Z2] Blocked (403) — polling too aggressively!")
                    raise R2Z2Blocked()

                else:
                    logger.warning(f"[R2Z2] Unexpected HTTP {response.status} for sequence {sequence_id}")
                    self._consecutive_errors += 1
                    return None

        except (R2Z2RateLimited, R2Z2Blocked):
            raise
        except asyncio.TimeoutError:
            logger.warning(f"[R2Z2] Timeout fetching sequence {sequence_id}")
            self._consecutive_errors += 1
            return None
        except aiohttp.ClientError as e:
            logger.warning(f"[R2Z2] Client error for sequence {sequence_id}: {e}")
            self._consecutive_errors += 1
            return None

    def to_process_format(self, package: R2Z2Package) -> Dict[str, Any]:
        """
        Convert R2Z2Package to the dict format expected by process_live_kill().

        process_live_kill() expects:
        - killmail_id: int
        - zkb: dict with hash, totalValue, npc, awox, points, etc.
        - killmail: dict (full ESI killmail) — optional, fetched from ESI if missing

        R2Z2 provides the killmail inline, so we always include it.

        IMPORTANT: process_live_kill() reads hash from zkb.get("hash").
        R2Z2 may place hash at top level only. We defensively inject it
        into zkb to prevent silent kill drops.
        """
        zkb = package.zkb
        # Ensure hash is in zkb dict — process_live_kill() reads it from there
        if "hash" not in zkb and package.hash:
            zkb["hash"] = package.hash
        return {
            "killmail_id": package.killmail_id,
            "zkb": zkb,
            "killmail": package.killmail,
        }


class R2Z2RateLimited(Exception):
    """Raised when R2Z2 returns 429."""
    def __init__(self, retry_after: int = 10):
        self.retry_after = retry_after
        super().__init__(f"Rate limited, retry after {retry_after}s")


class R2Z2Blocked(Exception):
    """Raised when R2Z2 returns 403 (IP blocked for aggressive polling)."""
    pass
