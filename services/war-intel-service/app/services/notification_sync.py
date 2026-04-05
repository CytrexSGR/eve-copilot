"""ESI Notification sync and parsing service."""
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Notification types we care about for automated processing
STRUCTURE_ATTACK_TYPES = {
    "StructureUnderAttack",
    "StructureLostShields",
    "StructureLostArmor",
    "StructureDestroyed",
    "StructureOnline",
    "StructureAnchoring",
    "StructureUnanchoring",
}

SOV_TYPES = {
    "SovStructureReinforced",
    "SovStructureDestroyed",
    "SovCommandNodeEventStarted",
    "SovAllClaimAquiredMsg",
    "SovAllClaimLostMsg",
}

TIMER_RELEVANT_TYPES = STRUCTURE_ATTACK_TYPES | SOV_TYPES


def parse_notification_body(text: str) -> Dict[str, Any]:
    """Parse ESI notification YAML body into dict.

    ESI notification bodies are YAML-formatted text.
    Returns empty dict on parse failure.
    """
    if not text:
        return {}
    try:
        import yaml
        parsed = yaml.safe_load(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception as e:
        logger.warning(f"Failed to parse notification body: {e}")
        return {}


def convert_esi_timestamp(timestamp_str: str) -> Optional[datetime]:
    """Convert ESI timestamp string to datetime.

    ESI uses ISO 8601 format: '2024-01-15T12:30:00Z'
    """
    if not timestamp_str:
        return None
    try:
        if timestamp_str.endswith("Z"):
            timestamp_str = timestamp_str[:-1] + "+00:00"
        return datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError):
        return None


def is_timer_relevant(notification_type: str) -> bool:
    """Check if notification type should create/update a timer."""
    return notification_type in TIMER_RELEVANT_TYPES


def extract_timer_data(notification_type: str, body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract timer-relevant data from parsed notification body.

    Returns dict with keys needed to create a structure_timer, or None if not applicable.
    """
    if not is_timer_relevant(notification_type):
        return None

    owner_corp_link = body.get("ownerCorpLinkData")
    owner_corp_id = None
    if isinstance(owner_corp_link, list) and len(owner_corp_link) >= 3:
        owner_corp_id = owner_corp_link[2]

    result = {
        "notification_type": notification_type,
        "structure_id": body.get("structureID"),
        "structure_type_id": body.get("structureTypeID"),
        "system_id": body.get("solarsystemID") or body.get("solarSystemID"),
        "owner_corporation_id": body.get("corpID") or owner_corp_id,
        "owner_alliance_id": body.get("allianceID"),
    }

    # Timer end from reinforcement — timeLeft is in 100-nanosecond intervals (Windows FILETIME delta)
    if "timeLeft" in body:
        time_left_seconds = body["timeLeft"] / 10_000_000
        result["time_left_seconds"] = time_left_seconds

    if "decloakTime" in body:
        result["vulnerability_time"] = body["decloakTime"]

    return result
