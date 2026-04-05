"""
zkillboard Live Service Package.

This package provides real-time killmail processing from zKillboard.
It splits the monolithic ZKillboardLiveService into focused modules.

Features:
- RedisQ-based killmail streaming
- Redis hot storage (24h TTL)
- Battle detection and tracking
- Telegram alert integration
- Gate camp detection
- Alliance war tracking

Usage:
    from services.zkillboard.live import ZKillboardLiveService

    service = ZKillboardLiveService()
    await service.listen_zkillboard()
"""

# Re-export constants and models
from .models import (
    LiveKillmail,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_TTL,
    ZKILL_API_URL,
    ZKILL_REDISQ_URL,
    ZKILL_QUEUE_ID,
    ZKILL_WEBSOCKET_URL,
    ZKILL_USER_AGENT,
    ZKILL_REQUEST_TIMEOUT,
    ZKILL_POLL_INTERVAL,
    ZKILL_WS_RECONNECT_DELAY,
    ESI_KILLMAIL_URL,
    ESI_USER_AGENT,
    HOTSPOT_WINDOW_SECONDS,
    HOTSPOT_THRESHOLD_KILLS,
    HOTSPOT_ALERT_COOLDOWN,
)

# Re-export utilities
from .ship_classifier import (
    safe_int_value,
    classify_ship,
    is_capital_ship,
)

# Import mixins
from .killmail_processor import KillmailProcessorMixin
from .battle_tracker import BattleTrackerMixin
from .telegram_alerts import TelegramAlertsMixin
from .redis_cache import RedisCacheMixin
from .statistics import StatisticsMixin
from .listener import ListenerMixin

# Note: ZKillboardLiveService is imported from services.zkillboard.live_service
# to avoid circular imports. The service inherits from the mixins defined here.

__all__ = [
    # Models
    'LiveKillmail',
    # Constants
    'REDIS_HOST',
    'REDIS_PORT',
    'REDIS_DB',
    'REDIS_TTL',
    'ZKILL_API_URL',
    'ZKILL_REDISQ_URL',
    'ZKILL_QUEUE_ID',
    'ZKILL_WEBSOCKET_URL',
    'ZKILL_USER_AGENT',
    'ZKILL_REQUEST_TIMEOUT',
    'ZKILL_POLL_INTERVAL',
    'ZKILL_WS_RECONNECT_DELAY',
    'ESI_KILLMAIL_URL',
    'ESI_USER_AGENT',
    'HOTSPOT_WINDOW_SECONDS',
    'HOTSPOT_THRESHOLD_KILLS',
    'HOTSPOT_ALERT_COOLDOWN',
    # Utilities
    'safe_int_value',
    'classify_ship',
    'is_capital_ship',
    # Mixins
    'KillmailProcessorMixin',
    'BattleTrackerMixin',
    'TelegramAlertsMixin',
    'RedisCacheMixin',
    'StatisticsMixin',
    'ListenerMixin',
]
