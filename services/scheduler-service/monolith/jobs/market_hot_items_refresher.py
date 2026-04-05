# jobs/market_hot_items_refresher.py
"""Background job to proactively refresh hot item prices."""
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict

from src.services.market.hot_items import get_hot_items, HotItemsConfig

logger = logging.getLogger(__name__)


class HotItemsRefresher:
    """
    Background job for proactive hot item caching.

    Runs every 4 minutes (before 5 min Redis TTL expires).
    Ensures hot items are always fresh in cache.
    """

    def __init__(self, repository):
        """
        Initialize refresher with market repository.

        Args:
            repository: UnifiedMarketRepository instance
        """
        self.repo = repository
        self.config = HotItemsConfig()
        self.hot_items = list(get_hot_items())

    def refresh(self) -> Dict[str, Any]:
        """
        Refresh all hot items in cache.

        Returns:
            Dict with refresh statistics
        """
        start = time.time()
        result = {
            "success": True,
            "refreshed": 0,
            "errors": 0,
            "duration_ms": 0,
            "timestamp": datetime.now().isoformat()
        }

        try:
            # Delegate to repository's refresh method
            stats = self.repo.refresh_hot_items()
            result.update(stats)

        except Exception as e:
            logger.error(f"Hot items refresh failed: {e}")
            result["success"] = False
            result["error"] = str(e)

        result["duration_ms"] = int((time.time() - start) * 1000)
        logger.info(f"Hot items refresh: {result}")
        return result


def main():
    """Entry point for cron job."""
    import redis
    from src.core.database import get_db_pool
    from src.integrations.esi.client import ESIClient
    from src.services.market.repository import UnifiedMarketRepository

    # Initialize dependencies
    redis_client = redis.Redis(host=os.environ.get("REDIS_HOST", "redis"), port=int(os.environ.get("REDIS_PORT", "6379")), db=0)
    db_pool = get_db_pool()
    esi_client = ESIClient()

    repo = UnifiedMarketRepository(
        redis_client=redis_client,
        db_pool=db_pool,
        esi_client=esi_client
    )

    refresher = HotItemsRefresher(repository=repo)
    result = refresher.refresh()

    if not result["success"]:
        exit(1)


if __name__ == "__main__":
    main()
