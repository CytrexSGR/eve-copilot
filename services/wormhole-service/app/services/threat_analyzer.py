"""Threat analysis for J-Space residents."""
from eve_shared import get_db


class ThreatAnalyzer:
    """Analyze threats for J-Space residents."""

    def __init__(self, db=None):
        self.db = db or get_db()

    def get_threats(self, wh_class: int = None, limit: int = 20) -> list[dict]:
        """
        Get threat feed for J-Space residents.

        Threat types:
        - CAPITAL: Capital ship sightings
        - HUNTER: Known hunter groups active
        - SPIKE: Unusual activity patterns
        """
        threats = []

        with self.db.cursor() as cur:
            # Capital sightings (last 24h)
            class_filter = "AND wc.\"wormholeClassID\" = %s" if wh_class else ""
            params = (wh_class,) if wh_class else ()

            cur.execute(f"""
                SELECT
                    k.solar_system_id as system_id,
                    ss."solarSystemName" as system_name,
                    wc."wormholeClassID" as wormhole_class,
                    it."typeName" as ship_name,
                    k.killmail_time,
                    'CAPITAL' as threat_type,
                    'critical' as severity
                FROM killmails k
                JOIN "mapSolarSystems" ss ON k.solar_system_id = ss."solarSystemID"
                JOIN "mapLocationWormholeClasses" wc ON k.solar_system_id = wc."locationID"
                JOIN "invTypes" it ON k.ship_type_id = it."typeID"
                WHERE k.solar_system_id >= 31000000 AND k.solar_system_id < 32000000
                  AND k.killmail_time > NOW() - INTERVAL '24 hours'
                  AND k.is_capital = TRUE
                  {class_filter}
                ORDER BY k.killmail_time DESC
                LIMIT 10
            """, params)

            for row in cur.fetchall():
                threats.append({
                    'type': row['threat_type'],
                    'severity': row['severity'],
                    'system_id': row['system_id'],
                    'system_name': row['system_name'],
                    'wormhole_class': row['wormhole_class'],
                    'description': f"{row['ship_name']} in {row['system_name']}",
                    'timestamp': row['killmail_time'].isoformat()
                })

            # Activity spikes (systems with 5+ kills in last 2 hours)
            cur.execute(f"""
                SELECT
                    k.solar_system_id as system_id,
                    ss."solarSystemName" as system_name,
                    wc."wormholeClassID" as wormhole_class,
                    COUNT(*) as kill_count,
                    MAX(k.killmail_time) as last_kill
                FROM killmails k
                JOIN "mapSolarSystems" ss ON k.solar_system_id = ss."solarSystemID"
                JOIN "mapLocationWormholeClasses" wc ON k.solar_system_id = wc."locationID"
                WHERE k.solar_system_id >= 31000000 AND k.solar_system_id < 32000000
                  AND k.killmail_time > NOW() - INTERVAL '2 hours'
                  {class_filter}
                GROUP BY k.solar_system_id, ss."solarSystemName", wc."wormholeClassID"
                HAVING COUNT(*) >= 5
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """, params)

            for row in cur.fetchall():
                severity = 'critical' if row['kill_count'] >= 10 else 'warning'
                threats.append({
                    'type': 'SPIKE',
                    'severity': severity,
                    'system_id': row['system_id'],
                    'system_name': row['system_name'],
                    'wormhole_class': row['wormhole_class'],
                    'description': f"{row['kill_count']} kills in {row['system_name']} (2h)",
                    'timestamp': row['last_kill'].isoformat()
                })

        # Sort by timestamp descending
        threats.sort(key=lambda x: x['timestamp'], reverse=True)
        return threats[:limit]
