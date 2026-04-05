"""
Supercap Timer Manager
Tracks supercapital construction timers.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
import logging

from psycopg2.extras import RealDictCursor

from src.database import get_db_connection
from services.war_economy.models import SupercapTimer


logger = logging.getLogger(__name__)


class SupercapTimerManager:
    """Manager for supercapital construction timers."""

    def __init__(self, db_pool):
        self.db_pool = db_pool

    def add_timer(
        self,
        solar_system_id: int,
        ship_type_id: int,
        build_start_date: date,
        estimated_completion_date: date,
        alliance_id: Optional[int] = None,
        confidence_level: str = 'unconfirmed',
        intel_source: Optional[str] = None,
        notes: Optional[str] = None,
        reported_by: Optional[str] = None
    ) -> int:
        """Add new supercap timer."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO war_economy_supercap_timers (
                        solar_system_id, ship_type_id,
                        build_start_date, estimated_completion_date,
                        alliance_id, confidence_level, intel_source,
                        notes, reported_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    solar_system_id, ship_type_id,
                    build_start_date, estimated_completion_date,
                    alliance_id, confidence_level, intel_source,
                    notes, reported_by
                ))
                timer_id = cur.fetchone()[0]
                conn.commit()
                logger.info(f"Added supercap timer {timer_id}")
                return timer_id

    def get_active_timers(self, region_id: Optional[int] = None) -> List[SupercapTimer]:
        """Get all active timers."""
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                query = '''
                    SELECT
                        t.id, t.ship_type_id, i."typeName" as ship_name,
                        t.solar_system_id, s."solarSystemName" as system_name,
                        r."regionName" as region_name,
                        t.alliance_name,
                        t.build_start_date, t.estimated_completion_date,
                        t.status, t.confidence_level, t.notes
                    FROM war_economy_supercap_timers t
                    LEFT JOIN "invTypes" i ON t.ship_type_id = i."typeID"
                    LEFT JOIN "mapSolarSystems" s ON t.solar_system_id = s."solarSystemID"
                    LEFT JOIN "mapRegions" r ON s."regionID" = r."regionID"
                    WHERE t.status = 'active'
                '''
                params = []

                if region_id:
                    query += ' AND s."regionID" = %s'
                    params.append(region_id)

                query += ' ORDER BY t.estimated_completion_date'

                cur.execute(query, params)
                rows = cur.fetchall()

                timers = []
                for row in rows:
                    days_remaining, hours_remaining = self._calculate_time_remaining(
                        row['estimated_completion_date']
                    )

                    timer = SupercapTimer(
                        id=row['id'],
                        ship_type_id=row['ship_type_id'],
                        ship_name=row['ship_name'] or f"Ship {row['ship_type_id']}",
                        solar_system_id=row['solar_system_id'],
                        system_name=row['system_name'] or f"System {row['solar_system_id']}",
                        region_name=row['region_name'] or "Unknown",
                        alliance_name=row['alliance_name'],
                        build_start_date=row['build_start_date'],
                        estimated_completion=row['estimated_completion_date'],
                        days_remaining=days_remaining,
                        hours_remaining=hours_remaining,
                        status=row['status'],
                        confidence_level=row['confidence_level'],
                        notes=row['notes']
                    )
                    timers.append(timer)

                return timers

    def update_status(self, timer_id: int, status: str):
        """Update timer status."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    UPDATE war_economy_supercap_timers
                    SET status = %s, status_updated_at = NOW()
                    WHERE id = %s
                ''', (status, timer_id))
                conn.commit()
                logger.info(f"Updated timer {timer_id} to status {status}")

    def update_timer(
        self,
        timer_id: int,
        estimated_completion_date: Optional[date] = None,
        confidence_level: Optional[str] = None,
        notes: Optional[str] = None
    ):
        """Update timer details."""
        updates = []
        params = []

        if estimated_completion_date:
            updates.append('estimated_completion_date = %s')
            params.append(estimated_completion_date)

        if confidence_level:
            updates.append('confidence_level = %s')
            params.append(confidence_level)

        if notes:
            updates.append('notes = %s')
            params.append(notes)

        if not updates:
            return

        updates.append('updated_at = NOW()')
        params.append(timer_id)

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                query = f"UPDATE war_economy_supercap_timers SET {', '.join(updates)} WHERE id = %s"
                cur.execute(query, params)
                conn.commit()
                logger.info(f"Updated timer {timer_id}")

    def _calculate_time_remaining(self, completion_date: date) -> Tuple[int, int]:
        """Calculate days and hours remaining."""
        now = datetime.utcnow().date()
        delta = completion_date - now

        days_remaining = max(0, delta.days)
        hours_remaining = days_remaining * 24

        return days_remaining, hours_remaining
