"""Background job to automatically sync character data."""
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class CharacterAutoSync:
    """
    Background job for automatic character data synchronization.

    Runs every 30 minutes to keep character data fresh in cache.
    """

    def __init__(self, repository, db_pool):
        """
        Initialize auto-sync job.

        Args:
            repository: CharacterRepository instance
            db_pool: Database pool for querying active characters
        """
        self.repo = repository
        self.db = db_pool

    def get_active_characters(self) -> List[int]:
        """
        Get list of active character IDs to sync.

        Returns characters with valid OAuth tokens.
        """
        try:
            with self.db.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT character_id
                        FROM oauth_tokens
                        WHERE expires_at > NOW()
                        OR refresh_token IS NOT NULL
                    """)
                    return [row[0] for row in cur.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get active characters: {e}")
            return []

    def sync(self) -> Dict[str, Any]:
        """
        Sync all active characters.

        Returns:
            Dict with sync statistics
        """
        start = time.time()
        result = {
            "success": True,
            "synced": 0,
            "failed": 0,
            "characters": [],
            "duration_ms": 0,
            "timestamp": datetime.now().isoformat()
        }

        try:
            characters = self.get_active_characters()
            logger.info(f"Syncing {len(characters)} active characters")

            for char_id in characters:
                try:
                    sync_result = self.repo.sync_character(char_id)

                    all_success = all(sync_result.values())
                    if all_success:
                        result["synced"] += 1
                    else:
                        result["failed"] += 1

                    result["characters"].append({
                        "character_id": char_id,
                        "result": sync_result
                    })

                except Exception as e:
                    logger.warning(f"Failed to sync character {char_id}: {e}")
                    result["failed"] += 1
                    result["characters"].append({
                        "character_id": char_id,
                        "error": str(e)
                    })

        except Exception as e:
            logger.error(f"Character auto-sync failed: {e}")
            result["success"] = False
            result["error"] = str(e)

        result["duration_ms"] = int((time.time() - start) * 1000)
        logger.info(f"Character auto-sync complete: {result['synced']} synced, {result['failed']} failed")
        return result


def main():
    """Entry point for cron job."""
    import redis
    from src.core.database import get_database_pool
    from src.services.character.repository import CharacterRepository

    # Initialize dependencies
    redis_client = redis.Redis(host=os.environ.get("REDIS_HOST", "redis"), port=int(os.environ.get("REDIS_PORT", "6379")), db=0)
    db_pool = get_database_pool()

    # Create ESI client for syncing
    from src.integrations.esi.client import ESIClient
    esi_client = ESIClient()

    repo = CharacterRepository(
        redis_client=redis_client,
        db_pool=db_pool,
        esi_client=esi_client
    )

    syncer = CharacterAutoSync(repository=repo, db_pool=db_pool)
    result = syncer.sync()

    if not result["success"]:
        exit(1)

    # Exit with error if more than 50% failed
    if result["failed"] > result["synced"]:
        logger.warning("More failures than successes")
        exit(1)


if __name__ == "__main__":
    main()
