"""
Live Service Models and Constants.

Provides data structures and configuration for real-time killmail processing.
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional


# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_TTL = 86400  # 24 hours

# zKillboard Configuration
ZKILL_API_URL = "https://zkillboard.com/api/kills/"
ZKILL_REDISQ_URL = "https://zkillredisq.stream/listen.php"
ZKILL_QUEUE_ID = "eve-copilot-production"
ZKILL_WEBSOCKET_URL = "wss://zkillboard.com/websocket/"  # Currently disabled by zkillboard
ZKILL_USER_AGENT = "EVE-CoPilot/1.0 (Live Combat Intelligence)"
ZKILL_REQUEST_TIMEOUT = 15  # seconds (RedisQ is long-poll)
ZKILL_POLL_INTERVAL = 10  # Poll every 10 seconds (fallback)
ZKILL_WS_RECONNECT_DELAY = 5  # seconds between reconnection attempts

# R2Z2 Configuration (replaces RedisQ — sunset May 31, 2026)
R2Z2_BASE_URL = "https://r2z2.zkillboard.com/ephemeral"
R2Z2_SEQUENCE_ENDPOINT = f"{R2Z2_BASE_URL}/sequence.json"
R2Z2_KILLMAIL_ENDPOINT = f"{R2Z2_BASE_URL}/{{sequence_id}}.json"
R2Z2_POLL_INTERVAL_DATA = 0.1      # 100ms between successful fetches
R2Z2_POLL_INTERVAL_EMPTY = 6.0     # 6s when no new data (404)
R2Z2_MAX_REQUESTS_PER_SECOND = 15  # Conservative (limit is 20/s/IP)
R2Z2_REQUEST_TIMEOUT = 10          # seconds

# ESI Configuration
ESI_KILLMAIL_URL = "https://esi.evetech.net/latest/killmails/{killmail_id}/{hash}/"
ESI_USER_AGENT = "EVE-CoPilot/1.0"

# Hotspot Detection Configuration
HOTSPOT_WINDOW_SECONDS = 300  # 5 minutes
HOTSPOT_THRESHOLD_KILLS = 5   # 5+ kills in 5min = hotspot
HOTSPOT_ALERT_COOLDOWN = 600  # 10 minutes between alerts for same system


@dataclass
class LiveKillmail:
    """Structured killmail data"""
    killmail_id: int
    killmail_time: str
    solar_system_id: int
    region_id: int
    ship_type_id: int
    ship_value: float
    victim_character_id: Optional[int]
    victim_corporation_id: Optional[int]
    victim_alliance_id: Optional[int]
    attacker_count: int
    is_solo: bool
    is_npc: bool
    destroyed_items: List[Dict]  # Items that were destroyed (market demand)
    dropped_items: List[Dict]    # Items that dropped (no market demand)
    attacker_corporations: List[int]  # Corp IDs of attackers
    attacker_alliances: List[int]     # Alliance IDs of attackers
