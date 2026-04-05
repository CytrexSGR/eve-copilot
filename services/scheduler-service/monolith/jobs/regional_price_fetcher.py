#!/usr/bin/env python3
"""
EVE Co-Pilot Regional Price Fetcher

Fetches ALL market orders per region from ESI (bulk fetch),
then filters and aggregates for our type IDs.
Much more efficient than per-item fetching.

Runs as cron job every 15-30 minutes.

Usage:
    python3 -m jobs.regional_price_fetcher
    python3 -m jobs.regional_price_fetcher --verbose
    python3 -m jobs.regional_price_fetcher --region the_forge  # Single region
"""

import sys
import os
import time
import argparse
import requests
from datetime import datetime
from typing import List, Dict, Set, Optional
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.database import get_db_connection
from config import REGIONS, ESI_BASE_URL, ESI_USER_AGENT


def get_relevant_type_ids() -> Set[int]:
    """
    Get all type IDs we need prices for:
    - ALL marketable items (has marketGroupID)
    - Excludes: Blueprints, SKINs, Certificates

    This maximizes arbitrage coverage without additional ESI calls
    since we already fetch all orders per region.
    """
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Get ALL marketable items
            cur.execute('''
                SELECT DISTINCT t."typeID"
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                JOIN "invCategories" c ON g."categoryID" = c."categoryID"
                WHERE t."published" = 1
                  AND t."marketGroupID" IS NOT NULL
                  AND c."categoryName" NOT IN (
                      'Blueprint',
                      'Skin',
                      'Certificate',
                      'Reaction'
                  )
            ''')
            return {row[0] for row in cur.fetchall()}


def fetch_region_orders(region_id: int, verbose: bool = False) -> List[Dict]:
    """
    Fetch ALL market orders for a region.
    Uses pagination to get all pages.

    Returns list of order dicts.
    """
    all_orders = []
    page = 1
    max_pages = 400  # Safety limit (The Forge has ~300 pages)

    session = requests.Session()
    session.headers.update({
        "User-Agent": ESI_USER_AGENT,
        "Accept": "application/json"
    })

    while page <= max_pages:
        url = f"{ESI_BASE_URL}/markets/{region_id}/orders/"
        params = {
            "datasource": "tranquility",
            "order_type": "all",
            "page": page
        }

        try:
            response = session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                orders = response.json()
                if not orders:
                    break

                all_orders.extend(orders)

                # Check pagination - ESI returns max 1000 per page
                if len(orders) < 1000:
                    break

                page += 1

                if verbose and page % 50 == 0:
                    print(f"    Page {page}, total orders: {len(all_orders):,}", end='\r')

                # Small delay to be nice to ESI
                time.sleep(0.1)

            elif response.status_code == 404:
                # No more pages
                break
            elif response.status_code == 420:
                print(f"  ERROR: ESI error banned! Stopping.")
                break
            elif response.status_code == 429:
                # Rate limited, wait and retry
                retry_after = int(response.headers.get("Retry-After", 60))
                if verbose:
                    print(f"  Rate limited, waiting {retry_after}s...")
                time.sleep(retry_after)
            else:
                if verbose:
                    print(f"  Warning: HTTP {response.status_code} on page {page}")
                break

        except requests.Timeout:
            if verbose:
                print(f"  Timeout on page {page}, retrying...")
            time.sleep(5)
        except Exception as e:
            if verbose:
                print(f"  Error: {e}")
            break

    return all_orders


def calculate_realistic_price(orders: List[Dict], target_volume: int = 100000) -> Optional[float]:
    """
    Calculate a realistic price to buy target_volume units.
    Returns the average price weighted by volume up to target_volume.
    """
    if not orders:
        return None

    # Sort by price (lowest first for sells)
    sorted_orders = sorted(orders, key=lambda x: x['price'])

    total_cost = 0.0
    units_counted = 0

    for order in sorted_orders:
        volume = order.get('volume_remain', 0)
        price = order['price']

        can_use = min(volume, target_volume - units_counted)
        total_cost += can_use * price
        units_counted += can_use

        if units_counted >= target_volume:
            break

    if units_counted == 0:
        return None

    return total_cost / units_counted


# Main trade hub stations per region
TRADE_HUB_STATIONS = {
    10000002: 60003760,   # Jita IV - Moon 4 - Caldari Navy Assembly Plant
    10000043: 60008494,   # Amarr VIII (Oris) - Emperor Family Academy
    10000030: 60004588,   # Rens VI - Moon 8 - Brutor Tribe Treasury
    10000032: 60011866,   # Dodixie IX - Moon 20 - Federation Navy Assembly Plant
    10000042: 60005686,   # Hek VIII - Moon 12 - Boundless Creation Factory
}


def aggregate_prices(orders: List[Dict], type_ids: Set[int], region_id: int = None) -> Dict[int, Dict]:
    """
    Aggregate orders into lowest_sell/highest_buy per type_id.
    Also calculates realistic price based on order depth.

    For buy orders (what you sell TO), only considers orders that can be filled
    from the main trade hub:
    - Orders at the hub station itself
    - Orders with range="region" (can be filled from anywhere)
    - Orders with range="solarsystem" in the hub's system

    This ensures highest_buy reflects what you can actually sell for at the hub.

    Returns: {type_id: {'lowest_sell': x, 'highest_buy': y, 'sell_volume': z, 'buy_volume': w,
                        'realistic_sell': r, 'top_sells': [...], 'top_buys': [...]}}
    """
    # Get trade hub station and system for this region
    hub_station_id = TRADE_HUB_STATIONS.get(region_id)

    # Group by type_id
    sell_orders = defaultdict(list)
    buy_orders = defaultdict(list)

    # Collect all sell orders, then filter per type_id
    all_sell_orders = defaultdict(list)
    hub_sell_orders = defaultdict(list)

    for order in orders:
        type_id = order.get('type_id')
        if type_id not in type_ids:
            continue

        if order.get('is_buy_order'):
            # Filter buy orders: only those fillable from trade hub
            order_range = order.get('range', '')
            location_id = order.get('location_id')

            # Include if: range is "region", OR at hub station
            if order_range == 'region' or location_id == hub_station_id:
                buy_orders[type_id].append(order)
            # Note: We skip orders with range "station", "solarsystem", or jump ranges
            # at other locations since you can't sell to them from the hub
        else:
            # Track both hub-only and all sell orders
            all_sell_orders[type_id].append(order)
            if hub_station_id and order.get('location_id') == hub_station_id:
                hub_sell_orders[type_id].append(order)

    # Use hub-station sell orders when available, fall back to region-wide
    for type_id in all_sell_orders:
        if hub_sell_orders[type_id]:
            sell_orders[type_id] = hub_sell_orders[type_id]
        else:
            sell_orders[type_id] = all_sell_orders[type_id]

    # Aggregate
    results = {}

    all_type_ids = set(sell_orders.keys()) | set(buy_orders.keys())

    for type_id in all_type_ids:
        sells = sell_orders.get(type_id, [])
        buys = buy_orders.get(type_id, [])

        # Sort for top orders
        sorted_sells = sorted(sells, key=lambda x: x['price'])[:10]  # Top 10 cheapest
        sorted_buys = sorted(buys, key=lambda x: -x['price'])[:10]  # Top 10 highest

        # Calculate realistic price (average for 100K units)
        realistic_sell = calculate_realistic_price(sells, target_volume=100000)

        results[type_id] = {
            'lowest_sell': min((o['price'] for o in sells), default=None),
            'highest_buy': max((o['price'] for o in buys), default=None),
            'sell_volume': sum(o.get('volume_remain', 0) for o in sells),
            'buy_volume': sum(o.get('volume_remain', 0) for o in buys),
            'realistic_sell': realistic_sell,
            'top_sells': [
                {
                    'price': o['price'],
                    'volume': o.get('volume_remain', 0),
                    'location_id': o.get('location_id'),
                    'issued': o.get('issued')
                }
                for o in sorted_sells
            ],
            'top_buys': [
                {
                    'price': o['price'],
                    'volume': o.get('volume_remain', 0),
                    'location_id': o.get('location_id'),
                    'issued': o.get('issued')
                }
                for o in sorted_buys
            ],
        }

    return results


def save_prices_to_db(region_id: int, prices: Dict[int, Dict]) -> int:
    """Save aggregated prices and order snapshots to database."""
    if not prices:
        return 0

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Update market_prices with realistic price
            upsert_sql = """
                INSERT INTO market_prices (type_id, region_id, lowest_sell, highest_buy, sell_volume, buy_volume, realistic_sell, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (type_id, region_id)
                DO UPDATE SET
                    lowest_sell = EXCLUDED.lowest_sell,
                    highest_buy = EXCLUDED.highest_buy,
                    sell_volume = EXCLUDED.sell_volume,
                    buy_volume = EXCLUDED.buy_volume,
                    realistic_sell = EXCLUDED.realistic_sell,
                    updated_at = NOW()
            """

            # Order snapshots upsert
            snapshot_sql = """
                INSERT INTO market_order_snapshots (type_id, region_id, is_buy_order, price, volume_remain, location_id, issued, rank, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (type_id, region_id, is_buy_order, rank)
                DO UPDATE SET
                    price = EXCLUDED.price,
                    volume_remain = EXCLUDED.volume_remain,
                    location_id = EXCLUDED.location_id,
                    issued = EXCLUDED.issued,
                    updated_at = NOW()
            """

            saved = 0
            for type_id, data in prices.items():
                try:
                    # Save main price data
                    cur.execute(upsert_sql, (
                        type_id,
                        region_id,
                        data['lowest_sell'],
                        data['highest_buy'],
                        data['sell_volume'],
                        data['buy_volume'],
                        data.get('realistic_sell')
                    ))

                    # Save top sell orders (rank 1-10)
                    for rank, order in enumerate(data.get('top_sells', [])[:10], start=1):
                        cur.execute(snapshot_sql, (
                            type_id,
                            region_id,
                            False,  # is_buy_order
                            order['price'],
                            order['volume'],
                            order.get('location_id'),
                            order.get('issued'),
                            rank
                        ))

                    # Save top buy orders (rank 1-10)
                    for rank, order in enumerate(data.get('top_buys', [])[:10], start=1):
                        cur.execute(snapshot_sql, (
                            type_id,
                            region_id,
                            True,  # is_buy_order
                            order['price'],
                            order['volume'],
                            order.get('location_id'),
                            order.get('issued'),
                            rank
                        ))

                    saved += 1
                except Exception as e:
                    print(f"  Error saving {type_id}: {e}")

            conn.commit()

    return saved


def fetch_region(region_name: str, region_id: int, type_ids: Set[int], verbose: bool = False) -> Dict:
    """Fetch and save prices for a single region."""
    start = time.time()

    if verbose:
        print(f"  {region_name.upper()} (ID: {region_id})...")

    # Fetch all orders
    orders = fetch_region_orders(region_id, verbose)

    if verbose:
        print(f"    Fetched {len(orders):,} orders")

    # Aggregate (pass region_id for buy order filtering)
    prices = aggregate_prices(orders, type_ids, region_id)

    if verbose:
        print(f"    Found prices for {len(prices):,} items")

    # Save
    saved = save_prices_to_db(region_id, prices)

    elapsed = time.time() - start

    return {
        'region': region_name,
        'orders': len(orders),
        'items_priced': len(prices),
        'saved': saved,
        'elapsed': round(elapsed, 1)
    }


def run_price_fetch(
    verbose: bool = False,
    single_region: Optional[str] = None
) -> Dict:
    """
    Main entry point: fetch all regional prices and save to DB.
    """
    start_time = time.time()

    if verbose:
        print("=" * 60)
        print("EVE Co-Pilot Regional Price Fetcher")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()

    # Step 1: Get relevant type IDs
    if verbose:
        print("Step 1: Loading relevant type IDs...")

    type_ids = get_relevant_type_ids()

    if verbose:
        print(f"  {len(type_ids):,} items to track")
        print()

    # Step 2: Fetch each region
    if verbose:
        print("Step 2: Fetching regional market data...")

    if single_region:
        regions_to_fetch = {single_region: REGIONS[single_region]}
    else:
        regions_to_fetch = REGIONS

    results = []
    for region_name, region_id in regions_to_fetch.items():
        result = fetch_region(region_name, region_id, type_ids, verbose)
        results.append(result)

    # Summary
    total_saved = sum(r['saved'] for r in results)
    total_orders = sum(r['orders'] for r in results)
    elapsed = time.time() - start_time

    if verbose:
        print()
        print("=" * 60)
        print("Summary:")
        for r in results:
            print(f"  {r['region']}: {r['saved']:,} prices ({r['elapsed']}s)")
        print()
        print(f"Total: {total_saved:,} prices from {total_orders:,} orders in {elapsed:.1f}s")
        print("=" * 60)

    return {
        "timestamp": datetime.now().isoformat(),
        "type_ids_tracked": len(type_ids),
        "regions": len(regions_to_fetch),
        "total_orders_fetched": total_orders,
        "prices_saved": total_saved,
        "elapsed_seconds": round(elapsed, 2),
        "per_region": results
    }


def main():
    parser = argparse.ArgumentParser(
        description='Regional Price Fetcher - Bulk fetch market prices'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--region', '-r',
        type=str,
        choices=list(REGIONS.keys()),
        help='Fetch single region only'
    )

    args = parser.parse_args()

    result = run_price_fetch(
        verbose=args.verbose,
        single_region=args.region
    )

    if not args.verbose:
        print(f"Regional prices: {result['prices_saved']} saved from {result['total_orders_fetched']:,} orders in {result['elapsed_seconds']}s")


if __name__ == "__main__":
    main()
