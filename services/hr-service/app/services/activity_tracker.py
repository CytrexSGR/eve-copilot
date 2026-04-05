"""Activity Tracking - Fleet sessions, login monitoring, activity summaries.

Tracks member activity for HR oversight:
- Fleet participation (from ESI fleet endpoints)
- Login/logout detection (online status changes)
- Kill/death events (from killmail feed)
- 30-day activity summaries for inactivity monitoring
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from eve_shared import get_db

logger = logging.getLogger(__name__)


class ActivityTracker:
    """Member activity tracking and reporting."""

    def __init__(self):
        self.db = get_db()

    def get_summary(self, character_id: int) -> Dict[str, Any]:
        """Get 30-day activity summary for a character."""
        with self.db.cursor() as cur:
            # Fleet count (30d)
            cur.execute(
                """
                SELECT COUNT(*) as fleet_count
                FROM fleet_sessions
                WHERE character_id = %(character_id)s
                AND start_time > NOW() - INTERVAL '30 days'
                """,
                {"character_id": character_id},
            )
            fleet_row = cur.fetchone()
            fleet_count = fleet_row["fleet_count"] if fleet_row else 0

            # Kill count (30d) from activity log
            cur.execute(
                """
                SELECT COUNT(*) as kill_count
                FROM character_activity_log
                WHERE character_id = %(character_id)s
                AND event_type = 'kill'
                AND recorded_at > NOW() - INTERVAL '30 days'
                """,
                {"character_id": character_id},
            )
            kill_row = cur.fetchone()
            kill_count = kill_row["kill_count"] if kill_row else 0

            # Last timestamps
            cur.execute(
                """
                SELECT
                    (SELECT MAX(recorded_at) FROM character_activity_log
                     WHERE character_id = %(cid)s AND event_type = 'kill') as last_kill,
                    (SELECT MAX(start_time) FROM fleet_sessions
                     WHERE character_id = %(cid)s) as last_fleet,
                    (SELECT MAX(recorded_at) FROM character_activity_log
                     WHERE character_id = %(cid)s AND event_type = 'login') as last_login
                """,
                {"cid": character_id},
            )
            ts_row = cur.fetchone()

        return {
            "character_id": character_id,
            "fleet_count_30d": fleet_count,
            "kill_count_30d": kill_count,
            "last_kill_at": ts_row["last_kill"] if ts_row else None,
            "last_fleet_at": ts_row["last_fleet"] if ts_row else None,
            "last_login_at": ts_row["last_login"] if ts_row else None,
        }

    def get_fleet_sessions(
        self,
        character_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List fleet sessions with optional character filter."""
        params: dict = {"limit": limit}
        where = ""

        if character_id:
            where = "WHERE character_id = %(character_id)s"
            params["character_id"] = character_id

        with self.db.cursor() as cur:
            cur.execute(
                f"""
                SELECT id, fleet_id, fleet_name, character_id, character_name,
                       ship_type_id, ship_name, start_time, end_time, solar_system_id
                FROM fleet_sessions
                {where}
                ORDER BY start_time DESC
                LIMIT %(limit)s
                """,
                params,
            )
            return [dict(r) for r in cur.fetchall()]

    def record_fleet_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Record a fleet participation session."""
        # Ensure optional keys have defaults
        session.setdefault("character_name", None)
        session.setdefault("ship_name", None)
        session.setdefault("fleet_id", None)
        session.setdefault("fleet_name", None)
        session.setdefault("ship_type_id", None)
        session.setdefault("end_time", None)
        session.setdefault("solar_system_id", None)

        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO fleet_sessions
                    (fleet_id, fleet_name, character_id, character_name,
                     ship_type_id, ship_name, start_time, end_time, solar_system_id)
                VALUES
                    (%(fleet_id)s, %(fleet_name)s, %(character_id)s, %(character_name)s,
                     %(ship_type_id)s, %(ship_name)s, %(start_time)s, %(end_time)s,
                     %(solar_system_id)s)
                RETURNING id, fleet_id, fleet_name, character_id, character_name,
                          ship_type_id, ship_name, start_time, end_time, solar_system_id
                """,
                session,
            )
            row = cur.fetchone()
            
        # Also log fleet_join event
        self.record_event(
            character_id=session["character_id"],
            event_type="fleet_join",
            details={"fleet_id": session.get("fleet_id"), "ship_type_id": session.get("ship_type_id")},
        )

        return dict(row)

    def record_event(
        self,
        character_id: int,
        event_type: str,
        details: Optional[Dict] = None,
    ):
        """Record an activity event (login, fleet, kill, death)."""
        import json

        with self.db.cursor() as cur:
            cur.execute(
                """
                INSERT INTO character_activity_log
                    (character_id, event_type, details)
                VALUES
                    (%(character_id)s, %(event_type)s, %(details)s::jsonb)
                """,
                {
                    "character_id": character_id,
                    "event_type": event_type,
                    "details": json.dumps(details or {}),
                },
            )
            
    def get_inactive_members(self, days: int = 30) -> List[Dict[str, Any]]:
        """List members with no activity in the last N days.

        Checks both fleet sessions and activity log.
        """
        with self.db.cursor() as cur:
            cur.execute(
                """
                WITH last_activity AS (
                    SELECT character_id,
                           MAX(recorded_at) as last_seen
                    FROM character_activity_log
                    GROUP BY character_id
                ),
                last_fleet AS (
                    SELECT character_id,
                           MAX(start_time) as last_fleet
                    FROM fleet_sessions
                    GROUP BY character_id
                ),
                combined AS (
                    SELECT
                        COALESCE(a.character_id, f.character_id) as character_id,
                        GREATEST(a.last_seen, f.last_fleet) as last_active
                    FROM last_activity a
                    FULL OUTER JOIN last_fleet f ON a.character_id = f.character_id
                )
                SELECT character_id, last_active
                FROM combined
                WHERE last_active < NOW() - INTERVAL '1 day' * %(days)s
                ORDER BY last_active ASC
                """,
                {"days": days},
            )
            return [dict(r) for r in cur.fetchall()]
