"""EVE Co-Pilot Shared Library - Common utilities for all services."""

from eve_shared.config import ServiceConfig, get_config
from eve_shared.logging import setup_logging, get_logger
from eve_shared.database import DatabasePool, get_db
from eve_shared.redis_client import RedisClient, get_redis
from eve_shared.health import HealthStatus, health_router

__version__ = "1.0.0"

__all__ = [
    "ServiceConfig",
    "get_config",
    "setup_logging",
    "get_logger",
    "DatabasePool",
    "get_db",
    "RedisClient",
    "get_redis",
    "HealthStatus",
    "health_router",
]

# Monitoring utilities available via submodule imports:
# from eve_shared.monitoring import track_query, tracked_cursor, monitor_connection_pool
# from eve_shared.monitoring.business_metrics import track_kill_processed, update_active_battles_count
