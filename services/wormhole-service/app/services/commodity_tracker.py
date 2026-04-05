"""Wormhole commodity price tracking and analysis."""
from typing import List, Dict, Any
from datetime import datetime
from eve_shared import get_db


# Wormhole commodity type IDs (volume in m3 per unit from SDE)
FULLERITE_GAS = {
    30378: {'name': 'Fullerite-C540', 'tier': 'high', 'class': 'C5/C6', 'volume': 10},
    30377: {'name': 'Fullerite-C320', 'tier': 'high', 'class': 'C5/C6', 'volume': 5},
    30374: {'name': 'Fullerite-C84', 'tier': 'mid', 'class': 'C3/C4', 'volume': 2},
    30373: {'name': 'Fullerite-C72', 'tier': 'mid', 'class': 'C3/C4', 'volume': 2},
    30372: {'name': 'Fullerite-C70', 'tier': 'mid', 'class': 'C3/C4', 'volume': 1},
    30371: {'name': 'Fullerite-C60', 'tier': 'low', 'class': 'C1/C2', 'volume': 1},
    30370: {'name': 'Fullerite-C50', 'tier': 'low', 'class': 'C1/C2', 'volume': 1},
    30376: {'name': 'Fullerite-C32', 'tier': 'low', 'class': 'C1/C2', 'volume': 5},
    30375: {'name': 'Fullerite-C28', 'tier': 'low', 'class': 'C1/C2', 'volume': 2},
}

BLUE_LOOT = {
    30259: {'name': 'Melted Nanoribbons', 'tier': 'high', 'npc_buy': 662000},
    30022: {'name': 'Heuristic Selfassemblers', 'tier': 'high', 'npc_buy': 1346000},
    30270: {'name': 'Central System Controller', 'tier': 'mid', 'npc_buy': 212500},
    30018: {'name': 'Fused Nanomechanical Engines', 'tier': 'mid', 'npc_buy': 170000},
    30024: {'name': 'Cartesian Temporal Coordinator', 'tier': 'mid', 'npc_buy': 127500},
    30019: {'name': 'Powdered C-540 Graphite', 'tier': 'low', 'npc_buy': 42500},
}

HYBRID_POLYMERS = {
    30309: {'name': 'Graphene Nanoribbons', 'tier': 'high'},
    30310: {'name': 'C3-FTM Acid', 'tier': 'high'},
    30311: {'name': 'PPD Fullerene Fibers', 'tier': 'high'},
    30312: {'name': 'Nanotori Polymers', 'tier': 'mid'},
    30313: {'name': 'Lanthanum Metallofullerene', 'tier': 'mid'},
    30314: {'name': 'Scandium Metallofullerene', 'tier': 'mid'},
    30305: {'name': 'Fullerene Intercalated Sheets', 'tier': 'low'},
    30306: {'name': 'Carbon-86 Epoxy Resin', 'tier': 'low'},
}

JITA_REGION_ID = 10000002


class CommodityTracker:
    """Track wormhole commodity prices and trends."""

    def __init__(self, db=None):
        self.db = db or get_db()

    def get_commodity_prices(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get current prices for all WH commodities.

        Returns categorized prices for gas, blue loot, and polymers.
        """
        all_type_ids = list(FULLERITE_GAS.keys()) + list(BLUE_LOOT.keys()) + list(HYBRID_POLYMERS.keys())

        with self.db.cursor() as cur:
            cur.execute("""
                SELECT
                    mp.type_id,
                    it."typeName" as name,
                    mp.lowest_sell,
                    mp.highest_buy,
                    mp.trend_7d,
                    mp.avg_daily_volume,
                    mp.updated_at
                FROM market_prices mp
                JOIN "invTypes" it ON mp.type_id = it."typeID"
                WHERE mp.region_id = %s AND mp.type_id = ANY(%s)
            """, (JITA_REGION_ID, all_type_ids))

            prices_by_id = {row['type_id']: row for row in cur.fetchall()}

        def format_commodity(type_id: int, meta: dict, prices: dict) -> dict:
            price_data = prices.get(type_id, {})
            sell = float(price_data.get('lowest_sell') or 0)
            buy = float(price_data.get('highest_buy') or 0)
            trend = float(price_data.get('trend_7d') or 0)
            daily_vol = int(price_data.get('avg_daily_volume') or 0)

            # trend_7d is already stored as percentage in market_prices
            trend_pct = trend

            # Volume in m3 per unit (for gas ISK/m3 calculation)
            unit_volume = meta.get('volume', 1)
            isk_per_m3 = round(sell / unit_volume, 0) if sell > 0 and unit_volume > 0 else 0

            return {
                'type_id': type_id,
                'name': meta['name'],
                'tier': meta['tier'],
                'sell_price': sell,
                'buy_price': buy,
                'spread': round((sell - buy) / sell * 100, 1) if sell > 0 else 0,
                'trend_7d': round(trend_pct, 1),
                'trend_direction': 'up' if trend_pct > 2 else 'down' if trend_pct < -2 else 'stable',
                'daily_volume': daily_vol,
                'npc_buy': meta.get('npc_buy'),
                'class': meta.get('class'),
                'unit_volume': unit_volume,
                'isk_per_m3': isk_per_m3,
            }

        return {
            'gas': [format_commodity(tid, meta, prices_by_id) for tid, meta in FULLERITE_GAS.items()],
            'blue_loot': [format_commodity(tid, meta, prices_by_id) for tid, meta in BLUE_LOOT.items()],
            'polymers': [format_commodity(tid, meta, prices_by_id) for tid, meta in HYBRID_POLYMERS.items()],
            'updated_at': datetime.now().isoformat(),
        }

    def get_eviction_intel(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get detailed eviction intelligence.

        Returns evictions with:
        - Who was evicted (corps/alliances involved)
        - What was lost (structure types, ships)
        - Estimated loot value
        - Time since eviction
        """
        with self.db.cursor() as cur:
            # Get major battles (evictions) in J-space
            cur.execute("""
                SELECT
                    b.battle_id,
                    b.solar_system_id,
                    ms."solarSystemName" as system_name,
                    mlw."wormholeClassID" as wh_class,
                    b.started_at,
                    b.ended_at,
                    b.total_kills,
                    b.total_isk_destroyed,
                    b.capital_kills
                FROM battles b
                JOIN "mapSolarSystems" ms ON b.solar_system_id = ms."solarSystemID"
                LEFT JOIN "mapLocationWormholeClasses" mlw ON ms."regionID" = mlw."locationID"
                WHERE b.solar_system_id >= 31000000 AND b.solar_system_id < 32000000
                  AND b.started_at > NOW() - INTERVAL '%s days'
                  AND b.total_kills >= 15
                ORDER BY b.total_isk_destroyed DESC
                LIMIT 10
            """, (days,))

            evictions = []
            for battle in cur.fetchall():
                # Get top defenders (evicted parties)
                cur.execute("""
                    SELECT
                        COALESCE(anc.alliance_name, c.corporation_name, 'Unknown') as entity_name,
                        k.victim_alliance_id as alliance_id,
                        k.victim_corporation_id as corporation_id,
                        COUNT(*) as losses,
                        SUM(k.ship_value) as isk_lost
                    FROM killmails k
                    LEFT JOIN alliance_name_cache anc ON k.victim_alliance_id = anc.alliance_id
                    LEFT JOIN corporations c ON k.victim_corporation_id = c.corporation_id
                    WHERE k.solar_system_id = %s
                      AND k.killmail_time BETWEEN %s AND %s
                    GROUP BY k.victim_alliance_id, k.victim_corporation_id, anc.alliance_name, c.corporation_name
                    ORDER BY SUM(k.ship_value) DESC
                    LIMIT 5
                """, (battle['solar_system_id'], battle['started_at'],
                      battle['ended_at'] or datetime.now()))

                victims = cur.fetchall()

                # Get structure losses
                cur.execute("""
                    SELECT
                        it."typeName" as structure_type,
                        COUNT(*) as count,
                        SUM(k.ship_value) as value
                    FROM killmails k
                    JOIN "invTypes" it ON k.ship_type_id = it."typeID"
                    JOIN "invGroups" ig ON it."groupID" = ig."groupID"
                    WHERE k.solar_system_id = %s
                      AND k.killmail_time BETWEEN %s AND %s
                      AND ig."categoryID" = 65  -- Structures
                    GROUP BY it."typeName"
                    ORDER BY SUM(k.ship_value) DESC
                """, (battle['solar_system_id'], battle['started_at'],
                      battle['ended_at'] or datetime.now()))

                structures = cur.fetchall()

                # Calculate loot timing
                hours_since = (datetime.now() - battle['started_at']).total_seconds() / 3600

                if hours_since < 24:
                    loot_status = 'imminent'
                    loot_eta = '0-24h'
                elif hours_since < 72:
                    loot_status = 'expected'
                    loot_eta = '24-48h'
                else:
                    loot_status = 'dumped'
                    loot_eta = 'already sold'

                evictions.append({
                    'battle_id': battle['battle_id'],
                    'system_id': battle['solar_system_id'],
                    'system_name': battle['system_name'],
                    'wh_class': battle['wh_class'],
                    'timestamp': battle['started_at'].isoformat(),
                    'hours_ago': round(hours_since, 1),
                    'total_kills': battle['total_kills'],
                    'isk_destroyed': float(battle['total_isk_destroyed'] or 0),
                    'estimated_loot': float(battle['total_isk_destroyed'] or 0) * 0.5,  # ~50% drops
                    'loot_status': loot_status,
                    'loot_eta': loot_eta,
                    'victims': [
                        {
                            'name': v['entity_name'],
                            'alliance_id': v['alliance_id'],
                            'corporation_id': v['corporation_id'],
                            'losses': v['losses'],
                            'isk_lost': float(v['isk_lost'] or 0)
                        }
                        for v in victims
                    ],
                    'structures_lost': [
                        {
                            'type': s['structure_type'],
                            'count': s['count'],
                            'value': float(s['value'] or 0)
                        }
                        for s in structures
                    ]
                })

            return evictions

    def get_supply_disruptions(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Detect supply chain disruptions from evictions.

        Identifies when major producers were evicted and predicts
        market impact.
        """
        with self.db.cursor() as cur:
            # Find corps with high activity that were evicted
            cur.execute("""
                WITH evicted_corps AS (
                    SELECT DISTINCT k.victim_corporation_id as corporation_id, k.victim_alliance_id as alliance_id
                    FROM killmails k
                    JOIN battles b ON k.solar_system_id = b.solar_system_id
                        AND k.killmail_time BETWEEN b.started_at AND COALESCE(b.ended_at, NOW())
                    WHERE b.solar_system_id >= 31000000 AND b.solar_system_id < 32000000
                      AND b.started_at > NOW() - INTERVAL '%s days'
                      AND b.total_kills >= 20
                ),
                corp_activity AS (
                    SELECT
                        wr.corporation_id,
                        wr.alliance_id,
                        COUNT(DISTINCT wr.system_id) as systems_lived,
                        MAX(wr.last_activity) as last_seen
                    FROM wormhole_residents wr
                    WHERE wr.corporation_id IN (SELECT corporation_id FROM evicted_corps)
                    GROUP BY wr.corporation_id, wr.alliance_id
                )
                SELECT
                    ca.corporation_id,
                    ca.alliance_id,
                    COALESCE(c.corporation_name, 'Unknown Corp') as corp_name,
                    COALESCE(anc.alliance_name, 'No Alliance') as alliance_name,
                    ca.systems_lived,
                    ca.last_seen
                FROM corp_activity ca
                LEFT JOIN corporations c ON ca.corporation_id = c.corporation_id
                LEFT JOIN alliance_name_cache anc ON ca.alliance_id = anc.alliance_id
                WHERE ca.systems_lived >= 2
                ORDER BY ca.systems_lived DESC
                LIMIT 10
            """, (days,))

            disruptions = []
            for row in cur.fetchall():
                # Estimate impact based on systems they controlled
                impact = 'high' if row['systems_lived'] >= 5 else 'medium' if row['systems_lived'] >= 3 else 'low'

                disruptions.append({
                    'corporation_id': row['corporation_id'],
                    'corporation_name': row['corp_name'],
                    'alliance_id': row['alliance_id'],
                    'alliance_name': row['alliance_name'],
                    'systems_affected': row['systems_lived'],
                    'impact_level': impact,
                    'last_seen': row['last_seen'].isoformat() if row['last_seen'] else None,
                    'predicted_effects': self._predict_effects(row['systems_lived'])
                })

            return disruptions

    def _predict_effects(self, systems: int) -> List[str]:
        """Predict market effects based on operation size."""
        effects = []
        if systems >= 5:
            effects.append("Major gas supply disruption expected")
            effects.append("T3 component prices may spike 10-20%")
        if systems >= 3:
            effects.append("Blue loot flood in 48-72h")
            effects.append("Regional polymer shortage possible")
        if systems >= 2:
            effects.append("Local market oversupply temporary")
        return effects

    def get_market_index(self) -> Dict[str, Any]:
        """
        Calculate J-Space Market Index - aggregate health indicator.
        """
        commodities = self.get_commodity_prices()

        # Calculate weighted index from high-value commodities
        gas_index = 0
        gas_count = 0
        for gas in commodities['gas']:
            if gas['tier'] == 'high' and gas['sell_price'] > 0:
                gas_index += gas['trend_7d']
                gas_count += 1

        loot_index = 0
        loot_count = 0
        for loot in commodities['blue_loot']:
            if loot['sell_price'] > 0:
                loot_index += loot['trend_7d']
                loot_count += 1

        avg_gas_trend = gas_index / gas_count if gas_count > 0 else 0
        avg_loot_trend = loot_index / loot_count if loot_count > 0 else 0

        overall_trend = (avg_gas_trend + avg_loot_trend) / 2

        if overall_trend > 5:
            market_status = 'bullish'
            recommendation = 'SELL - Prices elevated'
        elif overall_trend < -5:
            market_status = 'bearish'
            recommendation = 'BUY - Prices depressed'
        else:
            market_status = 'stable'
            recommendation = 'HOLD - Normal market conditions'

        return {
            'gas_trend': round(avg_gas_trend, 1),
            'loot_trend': round(avg_loot_trend, 1),
            'overall_trend': round(overall_trend, 1),
            'market_status': market_status,
            'recommendation': recommendation,
            'updated_at': datetime.now().isoformat()
        }

    def get_price_history(self, days: int = 7) -> Dict[int, Dict[str, Any]]:
        """
        Get price history for sparklines.

        Returns dict keyed by type_id with:
        - prices: list of daily prices (oldest first)
        - dates: list of dates
        - min_price: minimum price in period
        - max_price: maximum price in period
        - avg_price: average price in period
        - pct_vs_avg: current price vs average (percentage)
        """
        all_type_ids = list(FULLERITE_GAS.keys()) + list(BLUE_LOOT.keys()) + list(HYBRID_POLYMERS.keys())

        with self.db.cursor() as cur:
            # Get historical prices
            cur.execute("""
                SELECT
                    type_id,
                    array_agg(sell_price ORDER BY snapshot_date ASC) as prices,
                    array_agg(snapshot_date::text ORDER BY snapshot_date ASC) as dates,
                    MIN(sell_price) as min_price,
                    MAX(sell_price) as max_price,
                    AVG(sell_price) as avg_price
                FROM wh_commodity_price_history
                WHERE type_id = ANY(%s)
                  AND snapshot_date >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY type_id
            """, (all_type_ids, days))

            history = {}
            for row in cur.fetchall():
                prices = row['prices'] or []
                avg = float(row['avg_price'] or 0)
                current = float(prices[-1]) if prices else 0

                pct_vs_avg = 0
                if avg > 0 and current > 0:
                    pct_vs_avg = round((current - avg) / avg * 100, 1)

                history[row['type_id']] = {
                    'prices': [float(p) if p else 0 for p in prices],
                    'dates': row['dates'] or [],
                    'min_price': float(row['min_price'] or 0),
                    'max_price': float(row['max_price'] or 0),
                    'avg_price': round(avg, 2),
                    'pct_vs_avg': pct_vs_avg,
                    'data_points': len(prices)
                }

            return history

    def get_price_context(self) -> Dict[int, Dict[str, Any]]:
        """
        Get 30-day price context for historical comparison.

        Returns dict keyed by type_id with:
        - avg_30d: 30-day average price
        - pct_vs_30d: current price vs 30-day average
        - data_points: number of data points available
        """
        all_type_ids = list(FULLERITE_GAS.keys()) + list(BLUE_LOOT.keys()) + list(HYBRID_POLYMERS.keys())

        with self.db.cursor() as cur:
            # Get 30-day averages
            cur.execute("""
                SELECT
                    type_id,
                    AVG(sell_price) as avg_30d,
                    COUNT(*) as data_points
                FROM wh_commodity_price_history
                WHERE type_id = ANY(%s)
                  AND snapshot_date >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY type_id
            """, (all_type_ids,))

            averages = {row['type_id']: row for row in cur.fetchall()}

            # Get current prices
            cur.execute("""
                SELECT type_id, lowest_sell
                FROM market_prices
                WHERE region_id = %s AND type_id = ANY(%s)
            """, (JITA_REGION_ID, all_type_ids))

            context = {}
            for row in cur.fetchall():
                type_id = row['type_id']
                current = float(row['lowest_sell'] or 0)
                avg_data = averages.get(type_id, {})
                avg_30d = float(avg_data.get('avg_30d') or 0)
                data_points = avg_data.get('data_points', 0)

                pct_vs_30d = 0
                if avg_30d > 0 and current > 0:
                    pct_vs_30d = round((current - avg_30d) / avg_30d * 100, 1)

                context[type_id] = {
                    'avg_30d': round(avg_30d, 2),
                    'pct_vs_30d': pct_vs_30d,
                    'data_points': data_points
                }

            return context
