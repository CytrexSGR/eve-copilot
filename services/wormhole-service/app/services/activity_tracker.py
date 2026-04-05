"""Track J-Space activity and detect evictions."""
from eve_shared import get_db


class ActivityTracker:
    """Track activity in J-Space systems."""

    def __init__(self, db=None):
        self.db = db or get_db()

    def refresh_activity_stats(self) -> int:
        """Refresh system activity aggregates."""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO wormhole_system_activity (
                    system_id, wormhole_class,
                    kills_24h, kills_7d, kills_30d,
                    isk_destroyed_24h, isk_destroyed_7d, isk_destroyed_30d,
                    capital_kills_30d, unique_corps_30d, unique_alliances_30d,
                    last_kill_time
                )
                SELECT
                    k.solar_system_id,
                    wc."wormholeClassID",
                    COUNT(*) FILTER (WHERE k.killmail_time > NOW() - INTERVAL '24 hours'),
                    COUNT(*) FILTER (WHERE k.killmail_time > NOW() - INTERVAL '7 days'),
                    COUNT(*),
                    COALESCE(SUM(k.ship_value) FILTER (WHERE k.killmail_time > NOW() - INTERVAL '24 hours'), 0),
                    COALESCE(SUM(k.ship_value) FILTER (WHERE k.killmail_time > NOW() - INTERVAL '7 days'), 0),
                    COALESCE(SUM(k.ship_value), 0),
                    COUNT(*) FILTER (WHERE k.is_capital = TRUE),
                    COUNT(DISTINCT k.victim_corporation_id),
                    COUNT(DISTINCT k.victim_alliance_id) FILTER (WHERE k.victim_alliance_id IS NOT NULL),
                    MAX(k.killmail_time)
                FROM killmails k
                JOIN "mapLocationWormholeClasses" wc ON k.solar_system_id = wc."locationID"
                WHERE k.solar_system_id >= 31000000
                  AND k.solar_system_id < 32000000
                  AND k.killmail_time > NOW() - INTERVAL '30 days'
                GROUP BY k.solar_system_id, wc."wormholeClassID"
                ON CONFLICT (system_id) DO UPDATE SET
                    kills_24h = EXCLUDED.kills_24h,
                    kills_7d = EXCLUDED.kills_7d,
                    kills_30d = EXCLUDED.kills_30d,
                    isk_destroyed_24h = EXCLUDED.isk_destroyed_24h,
                    isk_destroyed_7d = EXCLUDED.isk_destroyed_7d,
                    isk_destroyed_30d = EXCLUDED.isk_destroyed_30d,
                    capital_kills_30d = EXCLUDED.capital_kills_30d,
                    unique_corps_30d = EXCLUDED.unique_corps_30d,
                    unique_alliances_30d = EXCLUDED.unique_alliances_30d,
                    last_kill_time = EXCLUDED.last_kill_time,
                    updated_at = NOW()
            """)
            count = cur.rowcount
            return count

    def get_activity_heatmap(self, wh_class: int = None, limit: int = 100) -> list[dict]:
        """Get most active J-Space systems."""
        with self.db.cursor() as cur:
            if wh_class:
                cur.execute("""
                    SELECT wa.*, ss."solarSystemName" as system_name
                    FROM wormhole_system_activity wa
                    JOIN "mapSolarSystems" ss ON wa.system_id = ss."solarSystemID"
                    WHERE wa.wormhole_class = %s
                    ORDER BY wa.kills_7d DESC
                    LIMIT %s
                """, (wh_class, limit))
            else:
                cur.execute("""
                    SELECT wa.*, ss."solarSystemName" as system_name
                    FROM wormhole_system_activity wa
                    JOIN "mapSolarSystems" ss ON wa.system_id = ss."solarSystemID"
                    ORDER BY wa.kills_7d DESC
                    LIMIT %s
                """, (limit,))
            return cur.fetchall()

    def get_recent_evictions(self, days: int = 30) -> list[dict]:
        """Get potential evictions (large fights in J-Space)."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    b.battle_id,
                    b.solar_system_id as system_id,
                    ss."solarSystemName" as system_name,
                    wc."wormholeClassID" as wormhole_class,
                    b.total_kills,
                    b.total_isk_destroyed,
                    b.started_at,
                    b.ended_at,
                    b.status,
                    b.status_level
                FROM battles b
                JOIN "mapSolarSystems" ss ON b.solar_system_id = ss."solarSystemID"
                JOIN "mapLocationWormholeClasses" wc ON b.solar_system_id = wc."locationID"
                WHERE b.solar_system_id >= 31000000
                  AND b.solar_system_id < 32000000
                  AND b.started_at > NOW() - INTERVAL '%s days'
                  AND b.total_kills >= 20  -- Significant fight
                ORDER BY b.total_kills DESC
                LIMIT 50
            """, (days,))
            return cur.fetchall()

    def get_system_activity(self, system_id: int) -> dict:
        """Get activity stats for a specific system."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT wa.*, ss."solarSystemName" as system_name
                FROM wormhole_system_activity wa
                JOIN "mapSolarSystems" ss ON wa.system_id = ss."solarSystemID"
                WHERE wa.system_id = %s
            """, (system_id,))
            return cur.fetchone()

    def get_summary_stats(self) -> dict:
        """Get aggregated J-Space stats for hero section."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(DISTINCT wa.system_id) FILTER (WHERE wa.kills_30d > 0) as active_systems,
                    COALESCE(SUM(wa.kills_24h), 0) as kills_24h,
                    COALESCE(SUM(wa.kills_7d), 0) as kills_7d,
                    COALESCE(SUM(wa.isk_destroyed_24h), 0) as isk_destroyed_24h,
                    COALESCE(SUM(wa.isk_destroyed_7d), 0) as isk_destroyed_7d,
                    MAX(wa.last_kill_time) as last_activity
                FROM wormhole_system_activity wa
            """)
            activity = cur.fetchone()

        with self.db.cursor() as cur:
            cur.execute("""
                SELECT COUNT(DISTINCT corporation_id) as resident_count
                FROM wormhole_residents
            """)
            residents = cur.fetchone()

        with self.db.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as eviction_count
                FROM battles b
                WHERE b.solar_system_id >= 31000000 AND b.solar_system_id < 32000000
                  AND b.started_at > NOW() - INTERVAL '7 days'
                  AND b.total_kills >= 20
            """)
            evictions = cur.fetchone()

        kills_7d = activity['kills_7d'] or 0
        activity_level = 'HIGH' if kills_7d > 500 else 'MODERATE' if kills_7d > 200 else 'LOW'

        return {
            'active_systems_30d': activity['active_systems'] or 0,
            'known_residents': residents['resident_count'] or 0,
            'kills_24h': activity['kills_24h'] or 0,
            'isk_destroyed_24h': float(activity['isk_destroyed_24h'] or 0),
            'evictions_7d': evictions['eviction_count'] or 0,
            'activity_level': activity_level,
            'last_activity': activity['last_activity'].isoformat() if activity['last_activity'] else None
        }
