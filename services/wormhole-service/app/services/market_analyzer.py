"""Market signal analysis from J-Space activity."""
from eve_shared import get_db


class MarketAnalyzer:
    """Analyze market signals from J-Space activity."""

    def __init__(self, db=None):
        self.db = db or get_db()

    def get_market_signals(self, days: int = 7) -> dict:
        """
        Get market demand signals from J-Space activity.

        Analyzes:
        - Eviction impact (loot dumps expected)
        - Capital losses (replacement demand)
        - Ship losses (fit demand)
        """
        with self.db.cursor() as cur:
            # Eviction stats
            cur.execute("""
                SELECT
                    COUNT(*) as eviction_count,
                    COALESCE(SUM(total_isk_destroyed), 0) as total_isk_destroyed
                FROM battles b
                WHERE b.solar_system_id >= 31000000 AND b.solar_system_id < 32000000
                  AND b.started_at > NOW() - INTERVAL '%s days'
                  AND b.total_kills >= 20
            """, (days,))
            evictions = cur.fetchone()

            # Capital losses
            cur.execute("""
                SELECT
                    CASE
                        WHEN ig."groupName" ILIKE '%%dreadnought%%' THEN 'Dreadnought'
                        WHEN ig."groupName" ILIKE '%%carrier%%' THEN 'Carrier'
                        WHEN ig."groupName" ILIKE '%%force auxiliary%%' THEN 'FAX'
                        ELSE 'Other Capital'
                    END as capital_type,
                    COUNT(*) as losses,
                    COALESCE(SUM(k.ship_value), 0) as isk_value
                FROM killmails k
                JOIN "invTypes" it ON k.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE k.solar_system_id >= 31000000 AND k.solar_system_id < 32000000
                  AND k.killmail_time > NOW() - INTERVAL '%s days'
                  AND k.is_capital = TRUE
                GROUP BY 1
                ORDER BY isk_value DESC
            """, (days,))
            capitals = cur.fetchall()

            # Top ship losses (for fit demand)
            cur.execute("""
                SELECT
                    it."typeName" as ship_name,
                    ig."groupName" as ship_class,
                    COUNT(*) as losses,
                    COALESCE(SUM(k.ship_value), 0) as isk_value
                FROM killmails k
                JOIN "invTypes" it ON k.ship_type_id = it."typeID"
                JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                WHERE k.solar_system_id >= 31000000 AND k.solar_system_id < 32000000
                  AND k.killmail_time > NOW() - INTERVAL '%s days'
                  AND k.ship_value > 50000000  -- 50M+ ISK ships
                GROUP BY it."typeName", ig."groupName"
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """, (days,))
            top_ships = cur.fetchall()

            # Active resident groups
            cur.execute("""
                SELECT COUNT(DISTINCT alliance_id) FILTER (WHERE alliance_id IS NOT NULL) as active_alliances,
                       COUNT(DISTINCT corporation_id) as active_corps
                FROM wormhole_residents
                WHERE last_activity > NOW() - INTERVAL '%s days'
            """, (days,))
            groups = cur.fetchone()

        total_cap_isk = sum(float(c['isk_value'] or 0) for c in capitals)

        return {
            'timeframe_days': days,
            'evictions': {
                'count': evictions['eviction_count'] or 0,
                'total_isk_destroyed': float(evictions['total_isk_destroyed'] or 0),
                'loot_dump_expected': evictions['eviction_count'] > 0
            },
            'capital_losses': {
                'total_count': sum(c['losses'] for c in capitals),
                'total_isk': total_cap_isk,
                'by_type': [
                    {
                        'type': c['capital_type'],
                        'losses': c['losses'],
                        'isk_value': float(c['isk_value'] or 0)
                    }
                    for c in capitals
                ],
                'replacement_demand_estimate': total_cap_isk * 0.8  # 80% will rebuild
            },
            'ship_demand': [
                {
                    'ship_name': s['ship_name'],
                    'ship_class': s['ship_class'],
                    'losses': s['losses'],
                    'isk_value': float(s['isk_value'] or 0)
                }
                for s in top_ships
            ],
            'active_groups': {
                'alliances': groups['active_alliances'] or 0,
                'corporations': groups['active_corps'] or 0
            }
        }
