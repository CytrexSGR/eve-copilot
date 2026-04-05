"""Discord webhook dispatch service.

Sends formatted embeds to Discord webhooks based on relay configurations.
"""
import logging
import httpx
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


async def dispatch_event(
    event_type: str,
    event_data: Dict[str, Any],
    db,
) -> int:
    """Dispatch an event to all matching Discord relay configs.

    Args:
        event_type: One of timer_created, timer_expiring, battle_started,
                    structure_attack, high_value_kill
        event_data: Event-specific data dict
        db: Database connection pool

    Returns:
        Number of webhooks successfully notified
    """
    with db.cursor() as cur:
        cur.execute("""
            SELECT id, name, webhook_url, filter_regions, filter_alliances,
                   notify_types, ping_role_id, min_isk_threshold
            FROM discord_relay_configs
            WHERE is_active = TRUE
              AND %s = ANY(notify_types)
        """, (event_type,))
        relays = cur.fetchall()

    sent = 0
    for relay in relays:
        if not _matches_filters(relay, event_data):
            continue

        embed = _build_embed(event_type, event_data)
        if await _send_webhook(relay["webhook_url"], embed, relay.get("ping_role_id")):
            sent += 1

    return sent


def _matches_filters(relay: Dict, event_data: Dict) -> bool:
    """Check if event matches relay's region/alliance/ISK filters."""
    if relay.get("filter_regions"):
        event_region = event_data.get("region_id")
        if event_region and event_region not in relay["filter_regions"]:
            return False

    if relay.get("filter_alliances"):
        event_alliance = event_data.get("alliance_id")
        if event_alliance and event_alliance not in relay["filter_alliances"]:
            return False

    min_isk = relay.get("min_isk_threshold", 0)
    if min_isk and min_isk > 0:
        event_isk = event_data.get("isk_value", 0)
        if event_isk < min_isk:
            return False

    return True


def _build_embed(event_type: str, data: Dict) -> Dict:
    """Build Discord embed for event type."""
    colors = {
        "timer_created": 0xFF8800,
        "timer_expiring": 0xFF4444,
        "battle_started": 0x00D4FF,
        "structure_attack": 0xFF0000,
        "high_value_kill": 0x3FB950,
    }

    embed = {
        "color": colors.get(event_type, 0x888888),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "footer": {"text": "EVE Co-Pilot Intel"},
    }

    if event_type == "timer_created":
        embed["title"] = f"New Timer: {data.get('structure_name', 'Unknown')}"
        embed["description"] = (
            f"**System:** {data.get('system_name', 'Unknown')}\n"
            f"**Type:** {data.get('timer_type', 'Unknown')}\n"
            f"**Ends:** {data.get('timer_end', 'Unknown')}"
        )
    elif event_type == "timer_expiring":
        embed["title"] = f"Timer Expiring: {data.get('structure_name', 'Unknown')}"
        embed["description"] = (
            f"**System:** {data.get('system_name', 'Unknown')}\n"
            f"**Expires in:** {data.get('hours_until', '?')} hours"
        )
    elif event_type == "high_value_kill":
        embed["title"] = f"High Value Kill: {data.get('ship_name', 'Unknown')}"
        embed["description"] = (
            f"**Value:** {data.get('isk_value', 0):,.0f} ISK\n"
            f"**System:** {data.get('system_name', 'Unknown')}\n"
            f"**Victim:** {data.get('victim_name', 'Unknown')}"
        )
    elif event_type == "battle_started":
        embed["title"] = f"Battle Detected: {data.get('system_name', 'Unknown')}"
        embed["description"] = (
            f"**Kills:** {data.get('kill_count', 0)}\n"
            f"**ISK Destroyed:** {data.get('isk_destroyed', 0):,.0f}"
        )
    elif event_type == "structure_attack":
        embed["title"] = f"Structure Under Attack: {data.get('structure_name', 'Unknown')}"
        embed["description"] = (
            f"**System:** {data.get('system_name', 'Unknown')}\n"
            f"**Attacker:** {data.get('attacker_name', 'Unknown')}"
        )

    return embed


async def _send_webhook(
    webhook_url: str,
    embed: Dict,
    ping_role_id: Optional[str] = None,
) -> bool:
    """Send embed to Discord webhook."""
    payload: Dict[str, Any] = {"embeds": [embed]}
    if ping_role_id:
        payload["content"] = f"<@&{ping_role_id}>"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(webhook_url, json=payload, timeout=10)
            if resp.status_code == 204:
                return True
            logger.warning(f"Discord webhook returned {resp.status_code}")
            return False
    except Exception as e:
        logger.error(f"Discord webhook failed: {e}")
        return False
