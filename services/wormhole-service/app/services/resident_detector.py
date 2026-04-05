"""Detect WH residents from killmail data."""
from eve_shared import get_db


class ResidentDetector:
    """Detect and track J-Space residents from killmail activity."""

    def __init__(self, db=None):
        self.db = db or get_db()

    def refresh_residents(self, days: int = 30) -> int:
        """
        Refresh resident data from killmails.

        Logic:
        - Corps with 3+ total activity (kills + losses) in same system = potential resident
        - Activity score = (kills + losses) / days_active
        - Higher score + longer presence = more likely resident
        """
        with self.db.cursor() as cur:
            # Clear and rebuild
            cur.execute("TRUNCATE wormhole_residents RESTART IDENTITY")

            # Insert from killmail analysis
            # Separate kills (attacker activity) and losses (victim activity) then combine
            cur.execute("""
                INSERT INTO wormhole_residents (
                    system_id, corporation_id, alliance_id,
                    kill_count, loss_count, last_activity, first_seen,
                    activity_score
                )
                SELECT
                    system_id,
                    corporation_id,
                    MAX(alliance_id) as alliance_id,
                    SUM(kills) as kill_count,
                    SUM(losses) as loss_count,
                    MAX(last_activity) as last_activity,
                    MIN(first_seen) as first_seen,
                    -- Activity score: weighted combination
                    (SUM(kills) + SUM(losses))::DECIMAL /
                        GREATEST(1, EXTRACT(DAY FROM MAX(last_activity) - MIN(first_seen))) as score
                FROM (
                    -- Kills: corp was attacker
                    SELECT
                        k.solar_system_id as system_id,
                        ka.corporation_id,
                        ka.alliance_id,
                        COUNT(DISTINCT k.killmail_id) as kills,
                        0 as losses,
                        MAX(k.killmail_time) as last_activity,
                        MIN(k.killmail_time) as first_seen
                    FROM killmails k
                    JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                    WHERE k.solar_system_id >= 31000000
                      AND k.solar_system_id < 32000000
                      AND k.killmail_time > NOW() - INTERVAL '%s days'
                      AND ka.corporation_id IS NOT NULL
                    GROUP BY k.solar_system_id, ka.corporation_id, ka.alliance_id

                    UNION ALL

                    -- Losses: corp was victim
                    SELECT
                        k.solar_system_id as system_id,
                        k.victim_corporation_id as corporation_id,
                        k.victim_alliance_id as alliance_id,
                        0 as kills,
                        COUNT(*) as losses,
                        MAX(k.killmail_time) as last_activity,
                        MIN(k.killmail_time) as first_seen
                    FROM killmails k
                    WHERE k.solar_system_id >= 31000000
                      AND k.solar_system_id < 32000000
                      AND k.killmail_time > NOW() - INTERVAL '%s days'
                      AND k.victim_corporation_id IS NOT NULL
                    GROUP BY k.solar_system_id, k.victim_corporation_id, k.victim_alliance_id
                ) combined
                GROUP BY system_id, corporation_id
                HAVING SUM(kills) + SUM(losses) >= 3  -- Minimum activity threshold
            """, (days, days))

            count = cur.rowcount
            return count

    def get_system_residents(self, system_id: int) -> list[dict]:
        """Get residents for a specific system."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    wr.*,
                    c.corporation_name,
                    a.alliance_name
                FROM wormhole_residents wr
                LEFT JOIN (
                    SELECT corporation_id, MAX(corporation_name) as corporation_name
                    FROM (
                        SELECT DISTINCT victim_corporation_id as corporation_id,
                               'Corp ' || victim_corporation_id as corporation_name
                        FROM killmails WHERE victim_corporation_id IS NOT NULL
                    ) x GROUP BY corporation_id
                ) c ON wr.corporation_id = c.corporation_id
                LEFT JOIN (
                    SELECT alliance_id, alliance_name
                    FROM alliance_name_cache
                ) a ON wr.alliance_id = a.alliance_id
                WHERE wr.system_id = %s
                ORDER BY wr.activity_score DESC
            """, (system_id,))
            return cur.fetchall()

    def get_top_residents(self, limit: int = 50) -> list[dict]:
        """Get most active J-Space residents across all systems."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    wr.corporation_id,
                    wr.alliance_id,
                    COUNT(DISTINCT wr.system_id) as systems_active,
                    SUM(wr.kill_count) as total_kills,
                    SUM(wr.loss_count) as total_losses,
                    MAX(wr.last_activity) as last_activity
                FROM wormhole_residents wr
                GROUP BY wr.corporation_id, wr.alliance_id
                ORDER BY SUM(wr.kill_count) + SUM(wr.loss_count) DESC
                LIMIT %s
            """, (limit,))
            return cur.fetchall()

    def get_alliance_systems(self, alliance_id: int) -> list[dict]:
        """Get all systems where an alliance has presence."""
        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    wr.system_id,
                    ss."solarSystemName" as system_name,
                    ws.wormhole_class,
                    ws.class_name,
                    SUM(wr.kill_count) as kills,
                    SUM(wr.loss_count) as losses,
                    MAX(wr.last_activity) as last_activity
                FROM wormhole_residents wr
                JOIN "mapSolarSystems" ss ON wr.system_id = ss."solarSystemID"
                LEFT JOIN v_wormhole_systems ws ON wr.system_id = ws.system_id
                WHERE wr.alliance_id = %s
                GROUP BY wr.system_id, ss."solarSystemName", ws.wormhole_class, ws.class_name
                ORDER BY SUM(wr.kill_count) + SUM(wr.loss_count) DESC
            """, (alliance_id,))
            return cur.fetchall()
