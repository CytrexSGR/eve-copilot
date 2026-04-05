"""Process ESI notifications into structure timers."""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.services.notification_sync import (
    is_timer_relevant,
    extract_timer_data,
)

logger = logging.getLogger(__name__)

# Map notification types to timer categories and types
NOTIFICATION_TO_TIMER = {
    "StructureLostShields": {"timer_type": "armor", "category": "citadel"},
    "StructureLostArmor": {"timer_type": "hull", "category": "citadel"},
    "StructureAnchoring": {"timer_type": "anchoring", "category": "citadel"},
    "StructureUnanchoring": {"timer_type": "unanchoring", "category": "citadel"},
    "SovStructureReinforced": {"timer_type": "armor", "category": "ihub"},
    "SovCommandNodeEventStarted": {"timer_type": "hull", "category": "ihub"},
}

# Jitter values by timer type (minutes)
JITTER_BY_TYPE = {
    "armor": 15,
    "hull": 30,
    "anchoring": 0,
    "unanchoring": 0,
    "online": 0,
}


def process_notification_to_timer(
    notification_type: str,
    body: Dict[str, Any],
    timestamp: datetime,
    db,
) -> Optional[int]:
    """Process a single notification into a timer if applicable.

    Returns timer_id if created/updated, None otherwise.
    """
    if not is_timer_relevant(notification_type):
        return None

    timer_data = extract_timer_data(notification_type, body)
    if not timer_data or not timer_data.get("system_id"):
        logger.warning(f"Could not extract timer data from {notification_type}")
        return None

    mapping = NOTIFICATION_TO_TIMER.get(notification_type)
    if not mapping:
        return None

    # Calculate timer end from timeLeft (100-nanosecond intervals)
    timer_end = None
    time_left_s = timer_data.get("time_left_seconds")
    if time_left_s and time_left_s > 0:
        timer_end = timestamp + timedelta(seconds=time_left_s)

    if not timer_end:
        logger.info(f"No timer_end calculable for {notification_type}")
        return None

    structure_name = f"Structure {timer_data.get('structure_id', 'Unknown')}"
    timer_type = mapping["timer_type"]
    jitter = JITTER_BY_TYPE.get(timer_type, 0)
    timer_window_start = timer_end - timedelta(minutes=jitter)
    timer_window_end = timer_end + timedelta(minutes=jitter)

    with db.cursor() as cur:
        # Check for existing active timer on same structure
        if timer_data.get("structure_id"):
            cur.execute("""
                SELECT id FROM structure_timers
                WHERE structure_id = %s AND is_active = TRUE
                ORDER BY timer_end DESC LIMIT 1
            """, (timer_data["structure_id"],))
            existing = cur.fetchone()
        else:
            existing = None

        if existing:
            # Update existing timer
            cur.execute("""
                UPDATE structure_timers
                SET timer_type = %s::structure_timer_type,
                    timer_end = %s,
                    timer_start = %s,
                    jitter_minutes = %s,
                    timer_window_start = %s,
                    timer_window_end = %s,
                    state = 'reinforced',
                    last_state_change = NOW(),
                    notes = COALESCE(notes, '') || E'\nAuto-updated from ' || %s,
                    updated_at = NOW()
                WHERE id = %s
                RETURNING id
            """, (
                timer_type,
                timer_end,
                timer_end - timedelta(minutes=15),
                jitter,
                timer_window_start,
                timer_window_end,
                notification_type,
                existing["id"],
            ))
            row = cur.fetchone()
            logger.info(f"Updated timer {row['id']} from {notification_type}")
            return row["id"]
        else:
            # Resolve system name
            cur.execute("""
                SELECT solar_system_name, region_id, region_name
                FROM system_region_map
                WHERE solar_system_id = %s
            """, (timer_data["system_id"],))
            sys_info = cur.fetchone()

            cur.execute("""
                INSERT INTO structure_timers
                    (structure_name, category, system_id, system_name,
                     region_id, region_name,
                     timer_type, timer_end, timer_start,
                     jitter_minutes, timer_window_start, timer_window_end,
                     structure_id, structure_type_id,
                     owner_alliance_id, owner_corporation_id,
                     reported_by, notes, source, is_active,
                     state, last_state_change)
                VALUES (%s, %s::structure_category, %s, %s,
                        %s, %s,
                        %s::structure_timer_type, %s, %s,
                        %s, %s, %s,
                        %s, %s,
                        %s, %s,
                        %s, %s, %s, TRUE,
                        'reinforced', NOW())
                RETURNING id
            """, (
                structure_name,
                mapping["category"],
                timer_data["system_id"],
                sys_info["solar_system_name"] if sys_info else None,
                sys_info["region_id"] if sys_info else None,
                sys_info["region_name"] if sys_info else None,
                timer_type,
                timer_end,
                timer_end - timedelta(minutes=15),
                jitter,
                timer_window_start,
                timer_window_end,
                timer_data.get("structure_id"),
                timer_data.get("structure_type_id"),
                timer_data.get("owner_alliance_id"),
                timer_data.get("owner_corporation_id"),
                "ESI Notification Auto",
                f"Auto-created from {notification_type}",
                "esi_notification",
            ))
            row = cur.fetchone()
            logger.info(f"Created timer {row['id']} from {notification_type}")
            return row["id"]
