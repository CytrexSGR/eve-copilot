"""Tier and module configuration loading for SaaS feature gating.

Loads tier_map.yaml and module_map.yaml, provides constants for
tier hierarchy, entity module groups, and environment-based config.
"""
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml

logger = logging.getLogger(__name__)

# Tier hierarchy: higher rank = more access
TIER_HIERARCHY = {
    "public": -1,
    "free": 0,
    "pilot": 1,
    "corporation": 2,
    "alliance": 3,
    "coalition": 4,
}

DEFAULT_TIER = "pilot"  # Unlisted endpoints require pilot

# Entity module groups: any variant grants the base module access
ENTITY_MODULE_GROUPS = {
    "corp_intel": ["corp_intel_1", "corp_intel_5", "corp_intel_unlimited"],
    "alliance_intel": ["alliance_intel_1", "alliance_intel_5", "alliance_intel_unlimited"],
    "powerbloc_intel": ["powerbloc_intel_1", "powerbloc_intel_5", "powerbloc_intel_unlimited"],
}

# Config from env
JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_ALGORITHM = "HS256"
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
TIER_CACHE_TTL = 300  # 5 min
AUTH_SERVICE_URL = os.environ.get("AUTH_SERVICE_URL", "http://auth-service:8000")


@dataclass
class TierMap:
    """Parsed tier-map.yaml with route patterns per tier."""
    public: List[str] = field(default_factory=list)
    free: List[str] = field(default_factory=list)
    pilot: List[str] = field(default_factory=list)
    corporation: List[str] = field(default_factory=list)
    alliance: List[str] = field(default_factory=list)
    coalition: List[str] = field(default_factory=list)


def load_tier_map() -> TierMap:
    """Load tier_map.yaml from config directory."""
    config_path = Path(__file__).parent.parent / "config" / "tier_map.yaml"
    if not config_path.exists():
        logger.warning(f"tier_map.yaml not found at {config_path}")
        return TierMap()

    with open(config_path) as f:
        data = yaml.safe_load(f)

    return TierMap(
        public=data.get("public", []),
        free=data.get("free", []),
        pilot=data.get("pilot", []),
        corporation=data.get("corporation", []),
        alliance=data.get("alliance", []),
        coalition=data.get("coalition", []),
    )


def load_module_map() -> dict[str, list[str]]:
    """Load module_map.yaml from config directory.

    Returns dict mapping module_name -> list of endpoint patterns.
    """
    config_path = Path(__file__).parent.parent / "config" / "module_map.yaml"
    if not config_path.exists():
        logger.warning(f"module_map.yaml not found at {config_path}")
        return {}

    with open(config_path) as f:
        data = yaml.safe_load(f)

    return data or {}
