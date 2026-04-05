import os
"""
zKillboard Live Service - Real-time Killmail Processing

Integrates with zKillboard RedisQ for live killmail streaming.
Provides real-time combat intelligence and hotspot detection.

Features:
- RedisQ real-time killmail streaming (primary)
- WebSocket connection (fallback, currently disabled by zkillboard)
- API polling (legacy fallback)
- Redis hot storage (24h TTL)
- Battle detection and tracking
- Telegram alert integration
- Gate camp detection
- Alliance war tracking

Architecture:
The service is composed of focused mixins:
- KillmailProcessorMixin: Fetching and parsing killmails
- BattleTrackerMixin: Battle detection and tracking
- TelegramAlertsMixin: Telegram alert integration
- RedisCacheMixin: Redis hot storage operations
- StatisticsMixin: Statistics and danger calculations
- ListenerMixin: RedisQ/WebSocket listeners
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Optional

import aiohttp
import redis

from src.database import get_db_connection
from services.zkillboard.state_manager import RedisStateManager

# Import mixins from modular package
from services.zkillboard.live.killmail_processor import KillmailProcessorMixin
from services.zkillboard.live.battle_tracker import BattleTrackerMixin
from services.zkillboard.live.telegram_alerts import TelegramAlertsMixin
from services.zkillboard.live.redis_cache import RedisCacheMixin
from services.zkillboard.live.statistics import StatisticsMixin
from services.zkillboard.live.listener import ListenerMixin

# Import constants and models
from services.zkillboard.live.models import (
    LiveKillmail,
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    ZKILL_USER_AGENT,
    HOTSPOT_WINDOW_SECONDS,
    HOTSPOT_THRESHOLD_KILLS,
)
from services.zkillboard.live.ship_classifier import classify_ship


class ZKillboardLiveService(
    KillmailProcessorMixin,
    BattleTrackerMixin,
    TelegramAlertsMixin,
    RedisCacheMixin,
    StatisticsMixin,
    ListenerMixin
):
    """
    Service for processing live killmail data from zKillboard RedisQ.

    This service uses composition via mixins to separate concerns:
    - KillmailProcessorMixin: Fetching and parsing killmails
    - BattleTrackerMixin: Battle detection and tracking
    - TelegramAlertsMixin: Telegram alert integration
    - RedisCacheMixin: Redis hot storage operations
    - StatisticsMixin: Statistics and danger calculations
    - ListenerMixin: RedisQ/WebSocket/API listeners

    Usage:
        service = ZKillboardLiveService()
        await service.listen_redisq(verbose=True)
    """

    def __init__(self):
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=os.environ.get("REDIS_PASSWORD", "") or None,
            decode_responses=True
        )
        self.session: Optional[aiohttp.ClientSession] = None
        self.running = False

        # Redis-based state management (survives restarts!)
        self.state_manager = RedisStateManager()

        # System -> Region mapping cache
        self.system_region_map: Dict[int, int] = {}
        try:
            self._load_system_region_map()
        except Exception:
            pass  # DB unavailable (e.g. test environment), map loaded on first use

    def _load_system_region_map(self):
        """Load solar_system_id -> region_id mapping from DB"""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT solar_system_id, region_id FROM system_region_map")
                self.system_region_map = {row[0]: row[1] for row in cur.fetchall()}

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"User-Agent": ZKILL_USER_AGENT}
            )
        return self.session

    async def process_live_kill(self, zkb_entry: Dict):
        """
        Process a single killmail from zkillboard API.

        Pipeline (REDESIGNED for atomicity):
        1. Check Redis if already processed (fast, survives restarts)
        2. Mark as processed in Redis (atomic SADD)
        3. Fetch full data from ESI
        4. Parse killmail
        5. Store in PostgreSQL with atomic battle assignment
        6. If hotspot detected, create new battle (battles stats from computed view)
        7. Update battle participants
        8. Track alliance wars
        9. Update intelligence stats
        10. Send alerts if needed
        11. Check for Panoptikum tracked targets

        Args:
            zkb_entry: zkillboard entry with killmail_id and zkb metadata
        """
        killmail_id = zkb_entry.get("killmail_id")
        hash_str = zkb_entry.get("zkb", {}).get("hash")

        if not killmail_id or not hash_str:
            return

        # STEP 1: Check if already processed using Redis (survives restarts!)
        if self.state_manager.is_kill_processed(killmail_id):
            return

        # STEP 2: Atomically mark as processed in Redis
        # SADD returns False if already exists (race condition protection)
        if not self.state_manager.mark_kill_processed(killmail_id, source="redisq"):
            return  # Another process already claimed this kill

        # STEP 3: Use pre-fetched killmail from ZKillRedisQClient if available,
        # otherwise fetch from ESI. This avoids double-fetching when using
        # the ZKillRedisQClient which already fetches killmails.
        # See: services/zkillboard/redisq_client.py:ZKillRedisQClient.fetch_killmail_from_esi()
        killmail = zkb_entry.get("killmail")
        if not killmail:
            killmail = await self.fetch_killmail_from_esi(killmail_id, hash_str)
        if not killmail:
            return

        # STEP 4: Parse killmail
        kill = self.parse_killmail(killmail, zkb_entry.get("zkb", {}))
        if not kill:
            return

        # STEP 5: Detect hotspot (for alerts)
        # This uses Redis-based timestamps that survive restarts
        hotspot = self.detect_hotspot(kill)

        # STEP 6: Ensure a battle exists for this system (ALWAYS, not just for hotspots)
        # Every kill belongs to a battle - even single kills
        # The battle must exist BEFORE store_live_kill so the kill gets associated
        self.ensure_battle_exists(kill)

        # STEP 7: Store in PostgreSQL with atomic battle assignment
        # This returns:
        # - battle_id (>0) if associated with battle
        # - 0 if stored but no battle
        # - None if duplicate (shouldn't happen due to Redis check)
        battle_id = self.store_live_kill(
            kill,
            zkb_data=zkb_entry.get("zkb", {}),
            esi_killmail=killmail
        )

        if battle_id is None:
            # Kill was duplicate (DB constraint) - shouldn't happen with Redis check
            print(f"[SKIP] Killmail {killmail_id} not stored - duplicate in DB")
            return

        # STEP 8: Update battle participants (if kill is part of a battle)
        if battle_id and battle_id > 0:
            self.update_battle_participants(battle_id, kill)

            # Check for battle milestones and send alerts
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT total_kills FROM battles WHERE battle_id = %s", (battle_id,))
                    row = cur.fetchone()
                    if row:
                        asyncio.create_task(self.send_initial_battle_alert(battle_id, kill.solar_system_id))
                        asyncio.create_task(self.check_and_send_milestone_alert(battle_id, row[0], kill.solar_system_id))

        # STEP 9: Track alliance wars
        self.track_alliance_war(kill)

        # STEP 10: HIGH-VALUE KILL ALERTS: Alert on expensive kills (>=2B ISK)
        asyncio.create_task(self.send_high_value_kill_alert(kill))

        # STEP 11: Store hotspot data for live map visualization
        if hotspot:
            self._store_live_hotspot(kill, hotspot)

    def _store_live_hotspot(self, kill: LiveKillmail, hotspot: Dict):
        """
        Store hotspot data for analytics and live map visualization.

        Args:
            kill: Parsed killmail data
            hotspot: Hotspot detection data
        """
        system_id = kill.solar_system_id
        now = time.time()

        # Store hotspot data for analytics (1h TTL)
        key = f"hotspot:{system_id}:{int(now)}"
        self.redis_client.setex(key, 3600, json.dumps(hotspot))

        # Calculate simplified danger score for live visualization
        # Based on kill count: 5-7 = LOW, 8-10 = MEDIUM, 11+ = HIGH
        kill_count = hotspot.get("kill_count", 0)
        if kill_count >= 11:
            simple_danger = "HIGH"
        elif kill_count >= 8:
            simple_danger = "MEDIUM"
        else:
            simple_danger = "LOW"

        # Store live hotspot for real-time map visualization (5-minute TTL)
        live_hotspot_data = {
            "system_id": system_id,
            "region_id": hotspot.get("region_id"),
            "kill_count": kill_count,
            "timestamp": hotspot.get("timestamp"),
            "latest_ship": hotspot.get("latest_ship"),
            "latest_value": hotspot.get("latest_value"),
            "system_name": self._get_system_name(system_id),
            "danger_level": simple_danger,
            "age_seconds": 0  # Age will be calculated by API endpoint
        }
        live_key = f"live_hotspot:{system_id}"
        self.redis_client.setex(live_key, 300, json.dumps(live_hotspot_data))  # 5-minute TTL
        print(f"Stored live hotspot for system {system_id} (TTL: 300s, danger: {simple_danger})")
