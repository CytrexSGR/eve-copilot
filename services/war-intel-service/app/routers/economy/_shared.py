"""
Shared constants and helper functions for economy endpoints.
"""

from typing import List, Dict

from app.database import db_cursor


# ============================================================
# TRADE HUBS & CONSTANTS
# ============================================================

TRADE_HUBS = {
    "jita": 10000002,
    "amarr": 10000043,
    "rens": 10000030,
    "dodixie": 10000032,
    "hek": 10000042
}

# Estimated jump distances from Jita to major nullsec regions
JITA_DISTANCES = {
    # Core nullsec regions
    10000060: 35,  # Delve
    10000014: 28,  # Catch
    10000023: 18,  # Pure Blind
    10000015: 20,  # Venal
    10000010: 30,  # Tribute
    10000045: 32,  # Tenal
    10000046: 28,  # Fade
    10000058: 40,  # Fountain
    10000050: 38,  # Querious
    10000051: 42,  # Cloud Ring
    10000039: 25,  # Esoteria
    10000041: 30,  # Syndicate
    10000040: 35,  # Impass
    10000062: 28,  # Omist
    10000063: 32,  # Period Basis
    10000064: 30,  # Outer Passage
    10000065: 26,  # Outer Ring
    10000066: 34,  # Perrigen Falls
    10000067: 28,  # Geminate
    10000068: 30,  # Paragon Soul
    10000069: 36,  # Feythabolis
    10000070: 38,  # Tenerifis
    10000011: 24,  # Vale of the Silent
    10000003: 22,  # Branch
    10000006: 20,  # Wicked Creek
    10000013: 26,  # Malpais
    10000057: 24,  # Great Wildlands
    10000059: 35,  # Immensea
    10000047: 25,  # Providence
    10000007: 22,  # Cache
    10000008: 24,  # Scalding Pass
    10000012: 22,  # Curse
    10000018: 30,  # The Spire
    10000025: 28,  # Insmother
    10000027: 32,  # Etherium Reach
    10000029: 34,  # Cobalt Edge
    10000031: 36,  # Oasa
    10000035: 30,  # Deklein
    10000054: 28,  # Kalevala Expanse
    # Lowsec regions (closer)
    10000016: 8,   # Lonetrek
    10000020: 6,   # Tash-Murkon
    10000033: 10,  # The Citadel
    10000036: 12,  # Devoid
    10000038: 14,  # The Bleak Lands
    10000048: 16,  # Placid
    10000052: 18,  # Khanid
    10000055: 20,  # Black Rise
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_destruction_zones_batch(type_ids: List[int], days: int = 1) -> Dict[int, List[Dict]]:
    """Get top regions where items are destroyed - batched for multiple type_ids."""
    if not type_ids:
        return {}

    with db_cursor() as cur:
        cur.execute("""
            WITH totals AS (
                SELECT
                    ki.item_type_id,
                    SUM(ki.quantity) as total_qty
                FROM killmail_items ki
                JOIN killmails k ON ki.killmail_id = k.killmail_id
                WHERE ki.item_type_id = ANY(%s)
                AND ki.was_destroyed = true
                AND k.killmail_time >= NOW() - INTERVAL '%s days'
                GROUP BY ki.item_type_id
            ),
            ranked AS (
                SELECT
                    ki.item_type_id,
                    k.region_id,
                    r."regionName" as region_name,
                    SUM(ki.quantity) as quantity,
                    ROUND(100.0 * SUM(ki.quantity) / NULLIF(t.total_qty, 0), 1) as percentage,
                    ROW_NUMBER() OVER (PARTITION BY ki.item_type_id ORDER BY SUM(ki.quantity) DESC) as rn
                FROM killmail_items ki
                JOIN killmails k ON ki.killmail_id = k.killmail_id
                LEFT JOIN "mapRegions" r ON k.region_id = r."regionID"
                JOIN totals t ON ki.item_type_id = t.item_type_id
                WHERE ki.item_type_id = ANY(%s)
                AND ki.was_destroyed = true
                AND k.killmail_time >= NOW() - INTERVAL '%s days'
                GROUP BY ki.item_type_id, k.region_id, r."regionName", t.total_qty
            )
            SELECT item_type_id, region_id, region_name, quantity, percentage
            FROM ranked
            WHERE rn <= 3
            ORDER BY item_type_id, quantity DESC
        """, (type_ids, days, type_ids, days))

        result: Dict[int, List[Dict]] = {tid: [] for tid in type_ids}
        for row in cur.fetchall():
            result[row['item_type_id']].append({
                'region_id': row['region_id'],
                'region_name': row['region_name'],
                'quantity': row['quantity'],
                'percentage': row['percentage']
            })
        return result


def get_destruction_trends_batch(type_ids: List[int]) -> Dict[int, float]:
    """Calculate 7-day trends for multiple type_ids - batched query."""
    if not type_ids:
        return {}

    with db_cursor() as cur:
        cur.execute("""
            SELECT
                ki.item_type_id,
                COALESCE(SUM(CASE WHEN k.killmail_time >= NOW() - INTERVAL '7 days'
                             THEN ki.quantity ELSE 0 END), 0) as this_week,
                COALESCE(SUM(CASE WHEN k.killmail_time >= NOW() - INTERVAL '14 days'
                                  AND k.killmail_time < NOW() - INTERVAL '7 days'
                             THEN ki.quantity ELSE 0 END), 0) as last_week
            FROM killmail_items ki
            JOIN killmails k ON ki.killmail_id = k.killmail_id
            WHERE ki.item_type_id = ANY(%s)
            AND ki.was_destroyed = true
            AND k.killmail_time >= NOW() - INTERVAL '14 days'
            GROUP BY ki.item_type_id
        """, (type_ids,))

        result: Dict[int, float] = {}
        for row in cur.fetchall():
            this_week = row['this_week'] or 0
            last_week = row['last_week'] or 0
            if last_week == 0:
                result[row['item_type_id']] = 100.0 if this_week > 0 else 0.0
            else:
                result[row['item_type_id']] = round(((this_week - last_week) / last_week) * 100, 1)
        # Fill in zeros for type_ids not found
        for tid in type_ids:
            if tid not in result:
                result[tid] = 0.0
        return result


def get_regional_prices_batch(type_ids: List[int]) -> Dict[int, Dict[str, float]]:
    """Fetch prices from all trade hubs via database - batched query."""
    if not type_ids:
        return {}

    # Map region_id to hub name
    region_to_hub = {v: k for k, v in TRADE_HUBS.items()}
    trade_hub_regions = list(TRADE_HUBS.values())

    with db_cursor() as cur:
        cur.execute("""
            SELECT type_id, region_id, lowest_sell
            FROM market_prices
            WHERE type_id = ANY(%s)
            AND region_id = ANY(%s)
        """, (type_ids, trade_hub_regions))

        result: Dict[int, Dict[str, float]] = {tid: {} for tid in type_ids}
        for row in cur.fetchall():
            type_id = row['type_id']
            region_id = row['region_id']
            hub_name = region_to_hub.get(region_id)
            if hub_name:
                result[type_id][hub_name] = float(row['lowest_sell'] or 0)

        return result


def estimate_jumps_from_jita(region_id: int) -> int:
    """Return estimated jump count from Jita to a region."""
    return JITA_DISTANCES.get(region_id, 20)


def get_active_warzones(min_kills: int = 50) -> List[Dict]:
    """
    Get regions with high combat activity in last 24h.
    Excludes trade hub regions. Returns top 10 by kill count.
    """
    trade_hub_regions = list(TRADE_HUBS.values())

    with db_cursor() as cur:
        cur.execute("""
            WITH region_activity AS (
                SELECT
                    k.region_id,
                    r."regionName" as region_name,
                    COUNT(*) as kills_24h,
                    COUNT(DISTINCT k.battle_id) as active_battles,
                    MAX(b.status_level) as max_status_level
                FROM killmails k
                JOIN "mapRegions" r ON k.region_id = r."regionID"
                LEFT JOIN battles b ON k.battle_id = b.battle_id
                WHERE k.killmail_time >= NOW() - INTERVAL '24 hours'
                AND k.region_id != ALL(%s)
                GROUP BY k.region_id, r."regionName"
                HAVING COUNT(*) >= %s
            )
            SELECT
                region_id,
                region_name,
                kills_24h,
                active_battles,
                max_status_level
            FROM region_activity
            ORDER BY kills_24h DESC
            LIMIT 10
        """, (trade_hub_regions, min_kills))

        return [dict(row) for row in cur.fetchall()]


def get_warzone_demand(region_id: int, limit: int = 10) -> List[Dict]:
    """
    Get top destroyed items in a specific warzone region.
    Filters to items with Jita price >= 1M ISK.
    """
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                ki.item_type_id as type_id,
                t."typeName" as name,
                SUM(ki.quantity) as quantity_destroyed,
                COALESCE(mp.lowest_sell, 0) as jita_price
            FROM killmail_items ki
            JOIN killmails k ON ki.killmail_id = k.killmail_id
            JOIN "invTypes" t ON ki.item_type_id = t."typeID"
            LEFT JOIN market_prices mp ON ki.item_type_id = mp.type_id AND mp.region_id = 10000002
            WHERE k.killmail_time >= NOW() - INTERVAL '24 hours'
            AND k.region_id = %s
            AND ki.was_destroyed = true
            AND COALESCE(mp.lowest_sell, 0) >= 1000000
            GROUP BY ki.item_type_id, t."typeName", mp.lowest_sell
            ORDER BY SUM(ki.quantity) * COALESCE(mp.lowest_sell, 0) DESC
            LIMIT %s
        """, (region_id, limit))

        return [dict(row) for row in cur.fetchall()]


def get_warzone_demand_batch(region_ids: List[int], limit: int = 10) -> Dict[int, List[Dict]]:
    """
    Get top destroyed items for multiple warzone regions in a single query.
    Uses ROW_NUMBER() OVER (PARTITION BY ...) to get top N items per region.
    Filters to items with Jita price >= 1M ISK.
    """
    if not region_ids:
        return {}

    with db_cursor() as cur:
        cur.execute("""
            WITH ranked AS (
                SELECT
                    k.region_id,
                    ki.item_type_id as type_id,
                    t."typeName" as name,
                    SUM(ki.quantity) as quantity_destroyed,
                    COALESCE(mp.lowest_sell, 0) as jita_price,
                    ROW_NUMBER() OVER (
                        PARTITION BY k.region_id
                        ORDER BY SUM(ki.quantity) * COALESCE(mp.lowest_sell, 0) DESC
                    ) as rn
                FROM killmail_items ki
                JOIN killmails k ON ki.killmail_id = k.killmail_id
                JOIN "invTypes" t ON ki.item_type_id = t."typeID"
                LEFT JOIN market_prices mp ON ki.item_type_id = mp.type_id AND mp.region_id = 10000002
                WHERE k.killmail_time >= NOW() - INTERVAL '24 hours'
                AND k.region_id = ANY(%s)
                AND ki.was_destroyed = true
                AND COALESCE(mp.lowest_sell, 0) >= 1000000
                GROUP BY k.region_id, ki.item_type_id, t."typeName", mp.lowest_sell
            )
            SELECT region_id, type_id, name, quantity_destroyed, jita_price
            FROM ranked
            WHERE rn <= %s
            ORDER BY region_id, rn
        """, (region_ids, limit))

        result: Dict[int, List[Dict]] = {rid: [] for rid in region_ids}
        for row in cur.fetchall():
            result[row['region_id']].append({
                'type_id': row['type_id'],
                'name': row['name'],
                'quantity_destroyed': row['quantity_destroyed'],
                'jita_price': row['jita_price']
            })
        return result


def get_base_hot_items(limit: int) -> List[Dict]:
    """Fetch base hot items from database (sync helper for asyncio.to_thread)."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                ki.item_type_id,
                t."typeName" as item_name,
                g."groupName" as group_name,
                SUM(ki.quantity) as quantity_destroyed,
                COALESCE(mp.lowest_sell, 0) as jita_price
            FROM killmail_items ki
            JOIN killmails k ON ki.killmail_id = k.killmail_id
            JOIN "invTypes" t ON ki.item_type_id = t."typeID"
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            LEFT JOIN market_prices mp ON ki.item_type_id = mp.type_id AND mp.region_id = 10000002
            WHERE k.killmail_time >= NOW() - INTERVAL '24 hours'
            AND ki.was_destroyed = true
            AND g."categoryID" NOT IN (4, 25, 43)  -- Exclude materials, asteroids, PI
            AND COALESCE(mp.lowest_sell, 0) > 0
            GROUP BY ki.item_type_id, t."typeName", g."groupName", mp.lowest_sell
            ORDER BY SUM(ki.quantity) * COALESCE(mp.lowest_sell, 0) DESC
            LIMIT %s
        """, (limit,))
        return [dict(row) for row in cur.fetchall()]
