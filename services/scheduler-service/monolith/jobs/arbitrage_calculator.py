#!/usr/bin/env python3
"""Arbitrage route calculator job.

Pre-calculates profitable arbitrage routes between trade hubs
and stores them in the database for fast API responses.

Runs every 30 minutes via scheduler-service.
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
import httpx

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection
_pg_host = os.environ.get('POSTGRES_HOST', 'eve_db')
_pg_port = os.environ.get('POSTGRES_PORT', '5432')
_pg_user = os.environ.get('POSTGRES_USER', 'eve')
_pg_pass = os.environ.get('POSTGRES_PASSWORD', '')
_pg_db = os.environ.get('POSTGRES_DB', 'eve_sde')
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    f'postgresql://{_pg_user}:{_pg_pass}@{_pg_host}:{_pg_port}/{_pg_db}'
)

# Trade hub configuration
TRADE_HUBS = {
    10000002: ("The Forge", "Jita"),
    10000043: ("Domain", "Amarr"),
    10000030: ("Heimatar", "Rens"),
    10000032: ("Sinq Laison", "Dodixie"),
    10000042: ("Metropolis", "Hek"),
}

# Jump distances between hubs (approximate high-sec)
HUB_DISTANCES = {
    (10000002, 10000043): 9,   # Jita -> Amarr
    (10000002, 10000030): 11,  # Jita -> Rens
    (10000002, 10000032): 12,  # Jita -> Dodixie
    (10000002, 10000042): 14,  # Jita -> Hek
    (10000043, 10000030): 18,
    (10000043, 10000032): 8,
    (10000043, 10000042): 15,
    (10000030, 10000032): 15,
    (10000030, 10000042): 7,
    (10000032, 10000042): 10,
}

# Default cargo capacity (DST)
CARGO_CAPACITY = 60000

# Fee calculation — exact EVE formulas
# Broker Relations V: 1.5% per side, Accounting V: 3.6% sales tax
BROKER_FEE_PCT = 1.5   # Broker Relations V
SALES_TAX_PCT = 3.6     # Accounting V


def get_destination_volumes(conn, region_id: int, type_ids: list[int]) -> dict[int, int]:
    """Get average daily volumes at destination from market_prices."""
    if not type_ids:
        return {}

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('''
            SELECT type_id, COALESCE(avg_daily_volume, 0)::bigint as avg_volume
            FROM market_prices
            WHERE region_id = %s
              AND type_id = ANY(%s)
              AND avg_daily_volume > 0
        ''', (region_id, type_ids))
        return {row['type_id']: row['avg_volume'] for row in cur.fetchall()}


def calculate_turnover(days_to_sell: float | None) -> str:
    """Classify turnover speed based on days to sell."""
    if days_to_sell is None:
        return 'unknown'
    if days_to_sell < 1:
        return 'instant'
    if days_to_sell < 3:
        return 'fast'
    if days_to_sell < 7:
        return 'moderate'
    return 'slow'


def calculate_competition(sell_orders: int) -> str:
    """Classify competition based on number of sell orders."""
    if sell_orders <= 5:
        return 'low'
    if sell_orders <= 15:
        return 'medium'
    if sell_orders <= 30:
        return 'high'
    return 'extreme'


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL)


def get_tradeable_items(conn) -> list[dict]:
    """Get list of tradeable items from database."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('''
            SELECT t."typeID" as type_id, t."typeName" as type_name,
                   COALESCE(t."volume", 0.01) as volume
            FROM "invTypes" t
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE g."categoryID" IN (4, 5, 6, 7, 8, 9, 16, 17, 18, 20, 22, 23, 25, 32, 35, 39, 43, 46, 87)
            AND t."published" = 1
            AND t."marketGroupID" IS NOT NULL
            ORDER BY t."typeID"
            LIMIT 2000
        ''')
        return list(cur.fetchall())


def get_all_cached_prices(conn, region_ids: list[int]) -> dict:
    """Get all cached prices from database for given regions.

    Returns dict: {(region_id, type_id): {'lowest_sell': X, 'highest_buy': Y}}
    """
    prices = {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('''
            SELECT region_id, type_id, lowest_sell, highest_buy
            FROM market_prices
            WHERE region_id = ANY(%s)
              AND (lowest_sell > 0 OR highest_buy > 0)
              AND updated_at > NOW() - INTERVAL '7 days'
        ''', (region_ids,))

        for row in cur.fetchall():
            key = (row['region_id'], row['type_id'])
            prices[key] = {
                'lowest_sell': float(row['lowest_sell']) if row['lowest_sell'] else None,
                'highest_buy': float(row['highest_buy']) if row['highest_buy'] else None
            }

    logger.info(f"Loaded {len(prices)} cached prices from database")
    return prices


def get_market_stats_cached(prices_cache: dict, region_id: int, type_id: int) -> Optional[dict]:
    """Get market stats from cache."""
    return prices_cache.get((region_id, type_id))


def calculate_route(
    from_region: int,
    to_region: int,
    items: list[dict],
    prices_cache: dict,
    volumes: dict[int, int],
    cargo_capacity: int = CARGO_CAPACITY
) -> Optional[dict]:
    """Calculate arbitrage route between two regions using cached prices."""
    _, from_hub = TRADE_HUBS[from_region]
    _, to_hub = TRADE_HUBS[to_region]

    # Get jump distance
    key = tuple(sorted([from_region, to_region]))
    jumps = HUB_DISTANCES.get(key, 15)

    route_items = []

    for item in items:  # Check all items - fast with cache
        type_id = item['type_id']
        type_name = item['type_name']
        item_volume = float(item['volume'])

        # Get prices from cache
        source_stats = get_market_stats_cached(prices_cache, from_region, type_id)
        dest_stats = get_market_stats_cached(prices_cache, to_region, type_id)

        if not source_stats or not dest_stats:
            continue

        source_sell = source_stats.get('lowest_sell') or 0
        dest_buy = dest_stats.get('highest_buy') or 0

        if source_sell <= 0 or dest_buy <= 0:
            continue

        profit_per_unit = dest_buy - source_sell

        if profit_per_unit <= 0:
            continue

        # Fee calculation (skilled trader defaults)
        bf_rate = BROKER_FEE_PCT / 100.0
        st_rate = SALES_TAX_PCT / 100.0
        fees_per_unit = (source_sell * bf_rate) + (dest_buy * bf_rate) + (dest_buy * st_rate)
        net_ppu = profit_per_unit - fees_per_unit

        if net_ppu <= 0:
            continue  # Skip items that lose money after fees

        gross_margin = (profit_per_unit / source_sell * 100) if source_sell > 0 else 0
        net_margin = (net_ppu / source_sell * 100) if source_sell > 0 else 0

        # How many can we carry?
        cargo_quantity = int(cargo_capacity / item_volume) if item_volume > 0 else 0
        dest_volume = volumes.get(type_id, 0)

        if dest_volume > 0:
            volume_quantity = dest_volume  # 1 day of stock
            quantity = min(cargo_quantity, volume_quantity, 1000)
            days_to_sell = quantity / dest_volume if dest_volume > 0 else None
        else:
            quantity = min(cargo_quantity, 50)  # Conservative if no volume data
            days_to_sell = None

        if quantity <= 0:
            continue

        net_total = net_ppu * quantity

        if net_total < 100000:  # Skip tiny profits
            continue

        route_items.append({
            'type_id': type_id,
            'type_name': type_name,
            'buy_price_source': source_sell,
            'sell_price_dest': dest_buy,
            'quantity': quantity,
            'volume': round(item_volume * quantity, 2),
            'profit_per_unit': round(profit_per_unit, 2),
            'total_profit': round(profit_per_unit * quantity, 2),
            # Fee-adjusted fields
            'gross_margin_pct': round(gross_margin, 2),
            'net_profit_per_unit': round(net_ppu, 2),
            'net_margin_pct': round(net_margin, 2),
            'total_fees_per_unit': round(fees_per_unit, 2),
            'net_total_profit': round(net_total, 2),
            # Volume fields
            'avg_daily_volume': dest_volume if dest_volume > 0 else None,
            'days_to_sell': round(days_to_sell, 1) if days_to_sell else None,
            'turnover': calculate_turnover(days_to_sell),
            'competition': 'medium',  # Default for now
        })

    if not route_items:
        return None

    # Sort by profit and select best items
    route_items.sort(key=lambda x: x['total_profit'], reverse=True)

    selected_items = []
    used_volume = 0

    for item in route_items:
        if used_volume + item['volume'] <= cargo_capacity:
            selected_items.append(item)
            used_volume += item['volume']

        if used_volume >= cargo_capacity * 0.95:
            break

    if not selected_items:
        return None

    # Calculate summary
    total_buy_cost = sum(i['buy_price_source'] * i['quantity'] for i in selected_items)
    total_sell_value = sum(i['sell_price_dest'] * i['quantity'] for i in selected_items)
    total_profit = total_sell_value - total_buy_cost
    net_profit = sum(i['net_total_profit'] for i in selected_items)

    if net_profit < 2000000:  # Min 2M net profit
        return None

    roi_percent = (total_profit / total_buy_cost * 100) if total_buy_cost > 0 else 0
    net_roi_percent = (net_profit / total_buy_cost * 100) if total_buy_cost > 0 else 0
    profit_per_jump = total_profit / jumps if jumps > 0 else 0
    net_profit_per_jump = net_profit / jumps if jumps > 0 else 0

    # Estimate round trip time (2 min per jump)
    round_trip_minutes = jumps * 2 * 2  # round trip
    profit_per_hour = (total_profit / round_trip_minutes * 60) if round_trip_minutes > 0 else 0
    net_profit_per_hour = (net_profit / round_trip_minutes * 60) if round_trip_minutes > 0 else 0

    return {
        'from_region_id': from_region,
        'to_region_id': to_region,
        'from_hub_name': from_hub,
        'to_hub_name': to_hub,
        'jumps': jumps,
        'items': selected_items,
        'total_items': len(selected_items),
        'total_volume': used_volume,
        'total_buy_cost': round(total_buy_cost, 2),
        'total_sell_value': round(total_sell_value, 2),
        'total_profit': round(total_profit, 2),
        'profit_per_jump': round(profit_per_jump, 2),
        'profit_per_hour': round(profit_per_hour, 2),
        'roi_percent': round(roi_percent, 2),
        # Net (fee-adjusted) fields
        'net_total_profit': round(net_profit, 2),
        'net_roi_percent': round(net_roi_percent, 2),
        'net_profit_per_hour': round(net_profit_per_hour, 2),
        'net_profit_per_jump': round(net_profit_per_jump, 2),
        'broker_fee_pct': BROKER_FEE_PCT,
        'sales_tax_pct': SALES_TAX_PCT,
    }


def save_routes(conn, routes: list[dict]):
    """Save calculated routes to database."""
    with conn.cursor() as cur:
        # Clear old data
        cur.execute("DELETE FROM arbitrage_route_items")
        cur.execute("DELETE FROM arbitrage_routes")

        for route in routes:
            # Insert route
            cur.execute('''
                INSERT INTO arbitrage_routes
                (from_region_id, to_region_id, from_hub_name, to_hub_name, jumps,
                 total_items, total_volume, total_buy_cost, total_sell_value,
                 total_profit, profit_per_jump, profit_per_hour, roi_percent,
                 net_total_profit, net_roi_percent, net_profit_per_hour,
                 net_profit_per_jump, broker_fee_pct, sales_tax_pct, calculated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            ''', (
                route['from_region_id'], route['to_region_id'],
                route['from_hub_name'], route['to_hub_name'], route['jumps'],
                route['total_items'], route['total_volume'],
                route['total_buy_cost'], route['total_sell_value'],
                route['total_profit'], route['profit_per_jump'],
                route['profit_per_hour'], route['roi_percent'],
                route['net_total_profit'], route['net_roi_percent'],
                route['net_profit_per_hour'], route['net_profit_per_jump'],
                route['broker_fee_pct'], route['sales_tax_pct']
            ))
            route_id = cur.fetchone()[0]

            # Insert items
            if route['items']:
                items_data = [
                    (route_id, i['type_id'], i['type_name'], i['buy_price_source'],
                     i['sell_price_dest'], i['quantity'], i['volume'],
                     i['profit_per_unit'], i['total_profit'],
                     i.get('avg_daily_volume'), i.get('days_to_sell'),
                     i.get('turnover', 'unknown'), i.get('competition', 'medium'),
                     i.get('gross_margin_pct'), i.get('net_profit_per_unit'),
                     i.get('net_margin_pct'), i.get('total_fees_per_unit'),
                     i.get('net_total_profit'))
                    for i in route['items']
                ]
                execute_values(cur, '''
                    INSERT INTO arbitrage_route_items
                    (route_id, type_id, type_name, buy_price_source, sell_price_dest,
                     quantity, volume, profit_per_unit, total_profit,
                     avg_daily_volume, days_to_sell, turnover, competition,
                     gross_margin_pct, net_profit_per_unit, net_margin_pct,
                     total_fees_per_unit, net_total_profit)
                    VALUES %s
                ''', items_data)

        conn.commit()
        logger.info(f"Saved {len(routes)} arbitrage routes to database")


def main():
    """Main job execution."""
    logger.info("Starting arbitrage calculator job")
    start_time = datetime.now(timezone.utc)

    try:
        conn = get_db_connection()

        # Get tradeable items
        items = get_tradeable_items(conn)
        logger.info(f"Found {len(items)} tradeable items")

        # Load all cached prices at once (fast!)
        region_ids = list(TRADE_HUBS.keys())
        prices_cache = get_all_cached_prices(conn, region_ids)

        if not prices_cache:
            logger.error("No cached prices found! Run regional_price_fetcher first.")
            return False

        # Load destination volumes for all items
        # Note: Volume data currently only available for Jita (10000002)
        # Using Jita volumes as proxy for all regions (better than nothing)
        all_type_ids = [item['type_id'] for item in items]
        jita_volumes = get_destination_volumes(conn, 10000002, all_type_ids)
        logger.info(f"Loaded {len(jita_volumes)} items with volume data from Jita")

        dest_volumes = {}
        for to_region in TRADE_HUBS.keys():
            # Use Jita volumes as fallback for all regions
            dest_volumes[to_region] = jita_volumes

        # Calculate routes from each hub to all others
        all_routes = []

        for from_region in TRADE_HUBS.keys():
            for to_region in TRADE_HUBS.keys():
                if from_region == to_region:
                    continue

                logger.info(f"Calculating {TRADE_HUBS[from_region][1]} -> {TRADE_HUBS[to_region][1]}")

                route = calculate_route(
                    from_region, to_region, items, prices_cache,
                    dest_volumes.get(to_region, {})
                )
                if route:
                    all_routes.append(route)
                    logger.info(f"  Found route: {route['total_profit']:,.0f} ISK profit")

        # Save to database
        save_routes(conn, all_routes)

        conn.close()

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"Arbitrage calculator completed in {elapsed:.1f}s, found {len(all_routes)} routes")

        return True

    except Exception as e:
        logger.exception(f"Arbitrage calculator failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
