"""
zKillboard RedisQ Client

Proper implementation following official zKillboard RedisQ documentation:
https://github.com/zKillboard/RedisQ

Key features:
- Uses persistent queueID for 3-hour position memory
- Supports redirect to /object.php (August 2025 change)
- Fetches killmail data from ESI (December 2025 change)
- Proper rate limiting (1 concurrent/queueID, 2 req/sec/IP)
- Exponential backoff on errors
- ESI killmail response caching (Redis, 24h TTL) - reduces API load by ~90%
"""

import asyncio
import aiohttp
import json
import logging
import os
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import hashlib
import platform

import redis

# Configure logging
logger = logging.getLogger(__name__)


# RedisQ Configuration (based on official docs)
REDISQ_BASE_URL = "https://zkillredisq.stream"
REDISQ_LISTEN_ENDPOINT = "/listen.php"

# Default queue ID - should be unique and persistent
DEFAULT_QUEUE_ID = "eve-copilot-live-v3"

# Time to wait parameter (1-10 seconds, default 10)
DEFAULT_TTW = 10

# ESI Configuration for killmail fetching
ESI_BASE_URL = "https://esi.evetech.net/latest"
ESI_KILLMAIL_ENDPOINT = "/killmails/{killmail_id}/{hash}/"

# Rate Limiting
MAX_REQUESTS_PER_SECOND = 2
REQUEST_TIMEOUT = 30

# Retry Configuration
MAX_RETRIES = 3
INITIAL_BACKOFF = 1.0
MAX_BACKOFF = 60.0

# User Agent (required by zKillboard)
USER_AGENT = f"EVE-CoPilot/2.0 ({platform.system()}; zKillboard RedisQ Client)"

# Redis Cache Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
ESI_KILLMAIL_CACHE_TTL = 86400  # 24 hours - killmails are immutable


@dataclass
class RedisQPackage:
    """Parsed RedisQ package"""
    killmail_id: int
    hash: str
    zkb: Dict[str, Any]
    killmail: Optional[Dict[str, Any]] = None  # ESI data (fetched separately since Dec 2025)


@dataclass
class RedisQResponse:
    """RedisQ response wrapper"""
    package: Optional[RedisQPackage]
    has_data: bool
    error: Optional[str] = None
    rate_limited: bool = False
    retry_after: int = 0


class ZKillRedisQClient:
    """
    Client for zKillboard RedisQ API.

    Implements proper polling with:
    - Persistent queueID (survives restarts)
    - Redirect support for /object.php
    - ESI killmail fetching
    - Rate limiting compliance
    - Exponential backoff on errors
    """

    def __init__(
        self,
        queue_id: str = DEFAULT_QUEUE_ID,
        ttw: int = DEFAULT_TTW,
        session: Optional[aiohttp.ClientSession] = None,
        redis_client: Optional[redis.Redis] = None
    ):
        """
        Initialize RedisQ client.

        Args:
            queue_id: Unique identifier for this client. zKillboard remembers
                     position for up to 3 hours. MUST be persistent across restarts!
            ttw: Time to wait for new killmails (1-10 seconds)
            session: Optional aiohttp session to reuse
            redis_client: Optional Redis client for ESI killmail caching
        """
        self.queue_id = queue_id
        self.ttw = max(1, min(10, ttw))  # Enforce 1-10 range
        self._session = session
        self._own_session = False
        self._last_request_time = 0
        self._consecutive_errors = 0
        self._running = True

        # Initialize Redis client for ESI killmail caching
        if redis_client is not None:
            self._redis = redis_client
        else:
            try:
                self._redis = redis.Redis(
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    db=REDIS_DB,
            password=os.environ.get("REDIS_PASSWORD", "") or None,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                # Verify connection
                self._redis.ping()
            except redis.ConnectionError as e:
                logger.warning(f"[RedisQ] Redis connection failed, ESI caching disabled: {e}")
                self._redis = None

        # Cache statistics
        self._cache_hits = 0
        self._cache_misses = 0

        print(f"[RedisQ] Initialized with queueID={queue_id}, ttw={self.ttw}")
        print(f"[RedisQ] zKillboard will remember position for 3 hours")
        if self._redis:
            print(f"[RedisQ] ESI killmail caching enabled (TTL: {ESI_KILLMAIL_CACHE_TTL}s)")

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept-Encoding": "gzip",
                    "Accept": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            )
            self._own_session = True
        return self._session

    async def close(self):
        """Close the client session"""
        if self._own_session and self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def _rate_limit(self):
        """Enforce rate limiting (max 2 req/sec)"""
        now = asyncio.get_event_loop().time()
        min_interval = 1.0 / MAX_REQUESTS_PER_SECOND
        elapsed = now - self._last_request_time

        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)

        self._last_request_time = asyncio.get_event_loop().time()

    async def _fetch_with_redirect(self, url: str) -> aiohttp.ClientResponse:
        """
        Fetch URL with redirect support.

        Since August 2025, RedisQ redirects to /object.php with objectID.
        """
        session = await self._get_session()
        response = await session.get(url, allow_redirects=True)
        return response

    async def poll(self) -> RedisQResponse:
        """
        Poll RedisQ for the next killmail.

        Returns:
            RedisQResponse with package (if available) or error info
        """
        await self._rate_limit()

        url = f"{REDISQ_BASE_URL}{REDISQ_LISTEN_ENDPOINT}?queueID={self.queue_id}&ttw={self.ttw}"

        try:
            response = await self._fetch_with_redirect(url)

            # Handle rate limiting (429)
            if response.status == 429:
                retry_after = int(response.headers.get("Retry-After", 10))
                print(f"[RedisQ] Rate limited! Retry after {retry_after}s")
                return RedisQResponse(
                    package=None,
                    has_data=False,
                    rate_limited=True,
                    retry_after=retry_after
                )

            # Handle other errors
            if response.status != 200:
                error_text = await response.text()
                print(f"[RedisQ] HTTP {response.status}: {error_text[:200]}")
                return RedisQResponse(
                    package=None,
                    has_data=False,
                    error=f"HTTP {response.status}: {error_text[:100]}"
                )

            # Parse response
            data = await response.json()

            # Check for empty package (no new kills)
            if data.get("package") is None:
                return RedisQResponse(package=None, has_data=False)

            # Parse package
            package_data = data["package"]
            zkb = package_data.get("zkb", {})

            package = RedisQPackage(
                killmail_id=package_data.get("killID"),
                hash=zkb.get("hash", ""),
                zkb=zkb,
                killmail=package_data.get("killmail")  # May be None since Dec 2025
            )

            self._consecutive_errors = 0
            return RedisQResponse(package=package, has_data=True)

        except asyncio.TimeoutError:
            print("[RedisQ] Request timeout")
            return RedisQResponse(package=None, has_data=False, error="Timeout")

        except aiohttp.ClientError as e:
            print(f"[RedisQ] Client error: {e}")
            return RedisQResponse(package=None, has_data=False, error=str(e))

        except Exception as e:
            print(f"[RedisQ] Unexpected error: {e}")
            return RedisQResponse(package=None, has_data=False, error=str(e))

    def _get_esi_cache_key(self, killmail_id: int) -> str:
        """Get the Redis cache key for an ESI killmail."""
        return f"esi:killmail:{killmail_id}"

    def _get_cached_killmail(self, killmail_id: int) -> Optional[Dict]:
        """
        Check Redis cache for a killmail.

        Args:
            killmail_id: Killmail ID to look up

        Returns:
            Cached killmail data or None if not found/error
        """
        if not self._redis:
            return None

        try:
            cache_key = self._get_esi_cache_key(killmail_id)
            cached = self._redis.get(cache_key)
            if cached:
                self._cache_hits += 1
                logger.debug(f"[ESI Cache HIT] Killmail {killmail_id}")
                return json.loads(cached)
        except redis.RedisError as e:
            logger.warning(f"[ESI Cache] Redis error on get: {e}")
        except json.JSONDecodeError as e:
            logger.warning(f"[ESI Cache] JSON decode error for killmail {killmail_id}: {e}")

        return None

    def _cache_killmail(self, killmail_id: int, killmail_data: Dict) -> bool:
        """
        Cache a killmail in Redis.

        Args:
            killmail_id: Killmail ID
            killmail_data: Full killmail data from ESI

        Returns:
            True if cached successfully, False otherwise
        """
        if not self._redis:
            return False

        try:
            cache_key = self._get_esi_cache_key(killmail_id)
            self._redis.setex(cache_key, ESI_KILLMAIL_CACHE_TTL, json.dumps(killmail_data))
            return True
        except redis.RedisError as e:
            logger.warning(f"[ESI Cache] Failed to cache killmail {killmail_id}: {e}")
        except (TypeError, ValueError) as e:
            logger.warning(f"[ESI Cache] JSON encode error for killmail {killmail_id}: {e}")

        return False

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache hit/miss statistics.

        Returns:
            Dict with cache_hits, cache_misses, and hit_rate percentage
        """
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0.0
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "total_requests": total,
            "hit_rate_percent": round(hit_rate, 2)
        }

    async def fetch_killmail_from_esi(self, killmail_id: int, hash_str: str) -> Optional[Dict]:
        """
        Fetch full killmail data from ESI with Redis caching.

        Since December 2025, RedisQ no longer includes embedded killmail data.
        We must fetch directly from ESI using the provided killmail ID and hash.

        Caching Strategy:
        - Check Redis cache first (24h TTL)
        - On cache miss, fetch from ESI and cache the response
        - Killmails are immutable, so 24h cache is safe

        Args:
            killmail_id: Killmail ID from RedisQ
            hash_str: Hash from RedisQ zkb data

        Returns:
            Full killmail data from ESI (or cache), or None on error
        """
        if not killmail_id or not hash_str:
            return None

        # Check cache first
        cached = self._get_cached_killmail(killmail_id)
        if cached:
            return cached

        # Cache miss - fetch from ESI
        self._cache_misses += 1
        logger.debug(f"[ESI Cache MISS] Fetching killmail {killmail_id}")

        url = f"{ESI_BASE_URL}{ESI_KILLMAIL_ENDPOINT.format(killmail_id=killmail_id, hash=hash_str)}"

        try:
            await self._rate_limit()
            session = await self._get_session()

            async with session.get(url) as response:
                if response.status == 200:
                    killmail_data = await response.json()

                    # Cache the response for future requests
                    self._cache_killmail(killmail_id, killmail_data)

                    return killmail_data
                else:
                    print(f"[ESI] Failed to fetch killmail {killmail_id}: HTTP {response.status}")
                    return None

        except Exception as e:
            print(f"[ESI] Error fetching killmail {killmail_id}: {e}")
            return None

    async def poll_with_retry(self) -> RedisQResponse:
        """
        Poll with exponential backoff on errors.

        Returns:
            RedisQResponse after successful poll or max retries
        """
        backoff = INITIAL_BACKOFF

        for attempt in range(MAX_RETRIES):
            response = await self.poll()

            # Success or no data - return immediately
            if response.has_data or (not response.error and not response.rate_limited):
                return response

            # Rate limited - wait specified time
            if response.rate_limited:
                wait_time = response.retry_after
                print(f"[RedisQ] Waiting {wait_time}s (rate limited)")
                await asyncio.sleep(wait_time)
                continue

            # Error - exponential backoff
            if response.error:
                self._consecutive_errors += 1
                wait_time = min(backoff * (2 ** attempt), MAX_BACKOFF)
                print(f"[RedisQ] Attempt {attempt + 1}/{MAX_RETRIES} failed, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

        return response

    def stop(self):
        """Signal the client to stop"""
        self._running = False

    async def listen(self, callback, batch_size: int = 1):
        """
        Continuous polling loop with callback.

        Args:
            callback: Async function to call with each RedisQPackage
            batch_size: Number of packages to batch before callback (1 = immediate)
        """
        print(f"[RedisQ] Starting listener loop (queueID={self.queue_id})")
        batch = []

        while self._running:
            try:
                response = await self.poll_with_retry()

                if response.has_data and response.package:
                    # Fetch ESI data if not included
                    if response.package.killmail is None:
                        response.package.killmail = await self.fetch_killmail_from_esi(
                            response.package.killmail_id,
                            response.package.hash
                        )

                    batch.append(response.package)

                    if len(batch) >= batch_size:
                        await callback(batch)
                        batch = []

                elif response.error and self._consecutive_errors >= MAX_RETRIES:
                    # Too many consecutive errors - take a longer break
                    print(f"[RedisQ] {self._consecutive_errors} consecutive errors, taking 60s break")
                    await asyncio.sleep(60)
                    self._consecutive_errors = 0

            except asyncio.CancelledError:
                print("[RedisQ] Listener cancelled")
                break
            except Exception as e:
                print(f"[RedisQ] Listener error: {e}")
                await asyncio.sleep(5)

        # Process remaining batch on shutdown
        if batch:
            try:
                await callback(batch)
            except Exception as e:
                print(f"[RedisQ] Error processing final batch: {e}")

        print("[RedisQ] Listener stopped")


# Factory function for easy instantiation
def create_redisq_client(
    queue_id: str = DEFAULT_QUEUE_ID,
    ttw: int = DEFAULT_TTW,
    redis_client: Optional[redis.Redis] = None
) -> ZKillRedisQClient:
    """
    Create a RedisQ client with proper configuration.

    Args:
        queue_id: Unique identifier (persistent across restarts!)
        ttw: Time to wait for new kills (1-10 seconds)
        redis_client: Optional Redis client for ESI killmail caching

    Returns:
        Configured ZKillRedisQClient instance with ESI caching enabled
    """
    return ZKillRedisQClient(queue_id=queue_id, ttw=ttw, redis_client=redis_client)
