"""ESI Notification endpoints."""
import logging
from typing import Optional
from fastapi import APIRouter, Request, Query
from app.database import db_cursor, _db
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.services.notification_sync import (
    convert_esi_timestamp,
    TIMER_RELEVANT_TYPES,
    parse_notification_body,
    is_timer_relevant,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/recent")
@handle_endpoint_errors()
def get_recent_notifications(
    request: Request,
    character_id: Optional[int] = None,
    notification_type: Optional[str] = None,
    unprocessed_only: bool = False,
    limit: int = Query(default=50, le=200),
):
    """Get recent ESI notifications, optionally filtered."""
    conditions = []
    params = {}

    if character_id:
        conditions.append("character_id = %(character_id)s")
        params["character_id"] = character_id
    if notification_type:
        conditions.append("type = %(type)s")
        params["type"] = notification_type
    if unprocessed_only:
        conditions.append("processed = FALSE")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    with db_cursor() as cur:
        cur.execute(f"""
            SELECT notification_id, character_id, sender_id, sender_type,
                   type, timestamp, is_read, processed, processed_at
            FROM esi_notifications
            {where}
            ORDER BY timestamp DESC
            LIMIT %(limit)s
        """, {**params, "limit": limit})
        rows = cur.fetchall()

    return {
        "notifications": [dict(r) for r in rows],
        "count": len(rows),
    }


@router.get("/types")
@handle_endpoint_errors()
def get_notification_type_counts(request: Request):
    """Get count of notifications by type."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT type, COUNT(*) as count,
                   MAX(timestamp) as latest
            FROM esi_notifications
            GROUP BY type
            ORDER BY count DESC
        """)
        rows = cur.fetchall()

    return {"types": [dict(r) for r in rows]}


@router.post("/mark-processed/{notification_id}")
@handle_endpoint_errors()
def mark_notification_processed(
    request: Request,
    notification_id: int,
):
    """Mark a notification as processed."""
    with db_cursor() as cur:
        cur.execute("""
            UPDATE esi_notifications
            SET processed = TRUE, processed_at = NOW()
            WHERE notification_id = %s
            RETURNING notification_id
        """, (notification_id,))
        row = cur.fetchone()

    if not row:
        return {"error": "Notification not found"}
    return {"marked_processed": notification_id}


@router.post("/sync")
@handle_endpoint_errors()
async def store_notifications(request: Request):
    """Store notifications from ESI (called by scheduler).

    Expects JSON body: {"character_id": int, "notifications": [...]}
    After storing, processes timer-relevant notifications into structure_timers.
    """
    body = await request.json()
    character_id = body.get("character_id")
    notifications = body.get("notifications", [])

    stored = 0
    with db_cursor() as cur:
        for notif in notifications:
            cur.execute("""
                INSERT INTO esi_notifications
                    (notification_id, character_id, sender_id, sender_type,
                     type, timestamp, text, is_read)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (notification_id) DO UPDATE SET
                    is_read = EXCLUDED.is_read
            """, (
                notif["notification_id"],
                character_id,
                notif.get("sender_id"),
                notif.get("sender_type"),
                notif["type"],
                convert_esi_timestamp(notif["timestamp"]),
                notif.get("text"),
                notif.get("is_read", False),
            ))
            stored += 1

    # Process unprocessed timer-relevant notifications
    timer_count = 0
    try:
        from app.services.timer_processor import process_notification_to_timer

        with db_cursor() as cur:
            cur.execute("""
                SELECT notification_id, type, text, timestamp
                FROM esi_notifications
                WHERE processed = FALSE AND type = ANY(%s)
            """, (list(TIMER_RELEVANT_TYPES),))
            unprocessed = cur.fetchall()

        for notif in unprocessed:
            notif_body = parse_notification_body(notif["text"])
            timer_id = process_notification_to_timer(
                notif["type"], notif_body, notif["timestamp"], _db
            )
            if timer_id:
                timer_count += 1
            with db_cursor() as cur:
                cur.execute("""
                    UPDATE esi_notifications SET processed = TRUE, processed_at = NOW()
                    WHERE notification_id = %s
                """, (notif["notification_id"],))
    except ImportError:
        logger.debug("timer_processor not available yet, skipping auto-processing")
    except Exception as e:
        logger.warning(f"Timer processing failed: {e}")

    return {
        "stored": stored,
        "character_id": character_id,
        "timers_created": timer_count,
    }
