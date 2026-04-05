"""Distributed token refresh locking using Redis.

Prevents multiple services from simultaneously refreshing the same
character's OAuth token. Uses Redis SET NX PX (Redlock-like) pattern.

Usage:
    from eve_shared.esi import TokenLock

    lock = TokenLock()

    acquired = lock.acquire(character_id=12345)
    if acquired:
        try:
            # Re-read token (double-check locking)
            token = get_token_from_db(12345)
            if token_needs_refresh(token):
                new_token = refresh_via_esi(token)
                save_token(new_token)
        finally:
            lock.release(character_id=12345)
"""

import logging
import secrets
import time
from typing import Optional

logger = logging.getLogger(__name__)

LOCK_KEY_PREFIX = "lock:token_refresh:"
LOCK_TTL_MS = 20_000        # 20 seconds (slightly > ESI timeout)
TOKEN_EXPIRY_BUFFER = 60     # Treat tokens as expired 60s before actual expiry


class TokenLock:
    """Distributed lock for ESI token refresh operations.

    Uses Redis SET NX PX for atomic lock acquisition with automatic
    expiry. Each lock has a unique owner value to prevent accidental
    release by other processes.
    """

    def __init__(self, ttl_ms: int = LOCK_TTL_MS):
        self._redis = None
        self._ttl_ms = ttl_ms
        self._locks: dict[int, str] = {}  # character_id -> owner_token

    @property
    def redis(self):
        if self._redis is None:
            try:
                from eve_shared import get_redis
                self._redis = get_redis().client
            except Exception:
                logger.debug("Redis unavailable for token lock")
        return self._redis

    def _lock_key(self, character_id: int) -> str:
        return f"{LOCK_KEY_PREFIX}{character_id}"

    def acquire(self, character_id: int) -> bool:
        """Acquire a distributed lock for token refresh.

        Args:
            character_id: EVE character ID

        Returns:
            True if lock was acquired, False if already held by another process
        """
        if not self.redis:
            # Fallback: no Redis = no distributed locking, allow refresh
            logger.debug("No Redis, skipping distributed lock")
            return True

        owner = secrets.token_hex(16)
        key = self._lock_key(character_id)

        try:
            acquired = self.redis.set(key, owner, nx=True, px=self._ttl_ms)
            if acquired:
                self._locks[character_id] = owner
                logger.debug(f"Lock acquired for character {character_id}")
                return True
            else:
                logger.debug(f"Lock already held for character {character_id}")
                return False
        except Exception as e:
            logger.warning(f"Failed to acquire lock for {character_id}: {e}")
            return True  # On Redis failure, allow refresh (availability > consistency)

    def release(self, character_id: int) -> bool:
        """Release a distributed lock.

        Only releases if this process owns the lock (prevents
        accidental release of another process's lock).

        Args:
            character_id: EVE character ID

        Returns:
            True if lock was released, False if not owned by this process
        """
        if not self.redis:
            return True

        owner = self._locks.pop(character_id, None)
        if not owner:
            return False

        key = self._lock_key(character_id)

        # Atomic compare-and-delete via Lua script
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        try:
            result = self.redis.eval(lua_script, 1, key, owner)
            released = result == 1
            if released:
                logger.debug(f"Lock released for character {character_id}")
            else:
                logger.debug(f"Lock expired or stolen for character {character_id}")
            return released
        except Exception as e:
            logger.warning(f"Failed to release lock for {character_id}: {e}")
            return False

    def is_locked(self, character_id: int) -> bool:
        """Check if a lock is currently held for a character."""
        if not self.redis:
            return False
        try:
            return self.redis.exists(self._lock_key(character_id)) > 0
        except Exception:
            return False

    @staticmethod
    def needs_refresh(expires_at_timestamp: float, buffer_seconds: int = TOKEN_EXPIRY_BUFFER) -> bool:
        """Check if a token needs refresh based on expiry time.

        Args:
            expires_at_timestamp: Token expiry as Unix timestamp
            buffer_seconds: Seconds before actual expiry to trigger refresh

        Returns:
            True if token should be refreshed
        """
        return time.time() >= (expires_at_timestamp - buffer_seconds)
