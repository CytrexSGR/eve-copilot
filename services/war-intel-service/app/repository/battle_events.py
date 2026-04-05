"""Battle Events Repository - Database operations for events."""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from app.database import db_cursor
from app.services.events.models import BattleEvent, BattleEventType, BattleEventSeverity

logger = logging.getLogger(__name__)


class BattleEventsRepository:
    """Repository for battle events database operations."""

    def _generate_event_hash(self, event: BattleEvent) -> str:
        """Generate a unique hash for event deduplication."""
        # Hash based on: type, system_id, alliance_id, event_time, title
        hash_data = {
            'type': event.event_type,
            'system_id': event.system_id,
            'alliance_id': event.alliance_id,
            'event_time': event.event_time.isoformat() if event.event_time else None,
            'title': event.title,
        }
        hash_str = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(hash_str.encode()).hexdigest()

    def save_event(self, event: BattleEvent) -> Optional[int]:
        """Save event to database. Returns event ID if saved, None if duplicate."""
        event_hash = self._generate_event_hash(event)

        with db_cursor() as cur:
            try:
                cur.execute("""
                    INSERT INTO battle_events (
                        event_type, severity, title, description,
                        system_id, system_name, region_id, region_name,
                        alliance_id, alliance_name, event_data,
                        detected_at, event_time, event_hash
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (event_hash) DO NOTHING
                    RETURNING id
                """, (
                    event.event_type, event.severity, event.title, event.description,
                    event.system_id, event.system_name, event.region_id, event.region_name,
                    event.alliance_id, event.alliance_name, json.dumps(event.event_data),
                    event.detected_at, event.event_time, event_hash
                ))

                result = cur.fetchone()
                if result:
                    logger.info(f"Saved event: {event.title} (ID: {result['id']})")
                    return result['id']
                else:
                    logger.debug(f"Duplicate event skipped: {event.title}")
                    return None
            except Exception as e:
                logger.error(f"Failed to save event: {e}")
                raise

    def save_events(self, events: List[BattleEvent]) -> int:
        """Save multiple events. Returns count of new events saved."""
        saved = 0
        for event in events:
            if self.save_event(event):
                saved += 1
        return saved

    def get_recent_events(
        self,
        since: Optional[datetime] = None,
        limit: int = 50,
        severity: Optional[BattleEventSeverity] = None,
        event_types: Optional[List[BattleEventType]] = None
    ) -> List[BattleEvent]:
        """Get recent events with optional filters."""
        with db_cursor() as cur:
            conditions = []
            params = []

            if since:
                conditions.append("detected_at > %s")
                params.append(since)

            if severity:
                conditions.append("severity = %s")
                params.append(severity.value if hasattr(severity, 'value') else severity)

            if event_types:
                conditions.append("event_type = ANY(%s)")
                params.append([t.value if hasattr(t, 'value') else t for t in event_types])

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            cur.execute(f"""
                SELECT id, event_type, severity, title, description,
                       system_id, system_name, region_id, region_name,
                       alliance_id, alliance_name, event_data,
                       detected_at, event_time, event_hash
                FROM battle_events
                WHERE {where_clause}
                ORDER BY detected_at DESC
                LIMIT %s
            """, params + [limit])

            events = []
            for row in cur.fetchall():
                events.append(BattleEvent(
                    id=row['id'],
                    event_type=row['event_type'],
                    severity=row['severity'],
                    title=row['title'],
                    description=row['description'],
                    system_id=row['system_id'],
                    system_name=row['system_name'],
                    region_id=row['region_id'],
                    region_name=row['region_name'],
                    alliance_id=row['alliance_id'],
                    alliance_name=row['alliance_name'],
                    event_data=row['event_data'] or {},
                    detected_at=row['detected_at'],
                    event_time=row['event_time'],
                    event_hash=row['event_hash']
                ))

            return events

    def save_snapshot(self, snapshot_type: str, data: Dict[str, Any]) -> Optional[int]:
        """Save a state snapshot for change detection. Returns snapshot ID or None."""
        try:
            with db_cursor() as cur:
                cur.execute("""
                    INSERT INTO battle_state_snapshots (snapshot_type, snapshot_data)
                    VALUES (%s, %s)
                    RETURNING id
                """, (snapshot_type, json.dumps(data)))
                result = cur.fetchone()
                if result:
                    logger.debug(f"Saved snapshot: {snapshot_type}")
                    return result['id']
                logger.error(f"Failed to save snapshot {snapshot_type}")
                return None
        except Exception as e:
            logger.error(f"Snapshot save error: {e}")
            raise

    def get_latest_snapshot(self, snapshot_type: str) -> Optional[Dict[str, Any]]:
        """Get the most recent snapshot of a given type."""
        with db_cursor() as cur:
            cur.execute("""
                SELECT snapshot_data, created_at
                FROM battle_state_snapshots
                WHERE snapshot_type = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (snapshot_type,))

            row = cur.fetchone()
            if row:
                return row['snapshot_data']
            return None

    def cleanup_old_events(self, hours: int = 24) -> int:
        """Delete events older than specified hours."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        with db_cursor() as cur:
            cur.execute("""
                DELETE FROM battle_events
                WHERE detected_at < %s
                RETURNING id
            """, (cutoff,))
            deleted = len(cur.fetchall())
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old events")
            return deleted


# Global repository instance
battle_events_repo = BattleEventsRepository()
