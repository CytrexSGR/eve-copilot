"""Regional price fetcher.

Fetches ALL market orders per region from ESI (bulk),
aggregates lowest_sell / highest_buy / realistic_sell,
and saves to market_prices + market_order_snapshots.
"""

import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

import httpx
from psycopg2.extras import execute_values

from eve_shared.constants import TRADE_HUB_REGIONS, TRADE_HUB_STATIONS

logger = logging.getLogger(__name__)

ESI_BASE_URL = "https://esi.evetech.net/latest"
ESI_USER_AGENT = "EVE-Copilot-MarketService/1.0"


def get_relevant_type_ids(db) -> Set[int]:
    """Get all marketable type IDs from SDE (excluding blueprints, skins, etc.)."""
    with db.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT t."typeID"
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                JOIN "invCategories" c ON g."categoryID" = c."categoryID"
                WHERE t."published" = 1
                  AND t."marketGroupID" IS NOT NULL
                  AND c."categoryName" NOT IN ('Blueprint', 'Skin', 'Certificate', 'Reaction')
            """)
            return {row[0] for row in cur.fetchall()}


def fetch_region_orders(region_id: int) -> List[Dict]:
    """Fetch ALL market orders for a region from ESI with pagination."""
    all_orders: List[Dict] = []
    page = 1
    max_pages = 400

    with httpx.Client(
        headers={"User-Agent": ESI_USER_AGENT, "Accept": "application/json"},
        timeout=30,
    ) as client:
        while page <= max_pages:
            try:
                resp = client.get(
                    f"{ESI_BASE_URL}/markets/{region_id}/orders/",
                    params={"datasource": "tranquility", "order_type": "all", "page": page},
                )
                if resp.status_code == 200:
                    orders = resp.json()
                    if not orders:
                        break
                    all_orders.extend(orders)
                    if len(orders) < 1000:
                        break
                    page += 1
                    time.sleep(0.1)
                elif resp.status_code in (404, 420):
                    break
                elif resp.status_code == 429:
                    retry = int(resp.headers.get("Retry-After", 60))
                    logger.warning(f"ESI rate limited, waiting {retry}s")
                    time.sleep(retry)
                else:
                    logger.warning(f"ESI HTTP {resp.status_code} for region {region_id} page {page}")
                    break
            except httpx.TimeoutException:
                logger.warning(f"ESI timeout for region {region_id} page {page}")
                time.sleep(5)
            except Exception as e:
                logger.error(f"ESI error: {e}")
                break

    return all_orders


def calculate_realistic_price(orders: List[Dict], target_volume: int = 100000) -> Optional[float]:
    """Weighted-average price to fill target_volume units."""
    if not orders:
        return None
    sorted_orders = sorted(orders, key=lambda x: x["price"])
    total_cost = 0.0
    units = 0
    for o in sorted_orders:
        vol = o.get("volume_remain", 0)
        can_use = min(vol, target_volume - units)
        total_cost += can_use * o["price"]
        units += can_use
        if units >= target_volume:
            break
    return total_cost / units if units > 0 else None


def aggregate_prices(orders: List[Dict], type_ids: Set[int], region_id: int) -> Dict[int, Dict]:
    """Aggregate orders into per-type price summaries."""
    hub_station_id = TRADE_HUB_STATIONS.get(region_id)
    sell_orders: Dict[int, list] = defaultdict(list)
    buy_orders: Dict[int, list] = defaultdict(list)
    all_sell: Dict[int, list] = defaultdict(list)
    hub_sell: Dict[int, list] = defaultdict(list)

    for order in orders:
        tid = order.get("type_id")
        if tid not in type_ids:
            continue
        if order.get("is_buy_order"):
            rng = order.get("range", "")
            loc = order.get("location_id")
            if rng == "region" or loc == hub_station_id:
                buy_orders[tid].append(order)
        else:
            all_sell[tid].append(order)
            if hub_station_id and order.get("location_id") == hub_station_id:
                hub_sell[tid].append(order)

    for tid in all_sell:
        sell_orders[tid] = hub_sell[tid] if hub_sell[tid] else all_sell[tid]

    results = {}
    for tid in set(sell_orders) | set(buy_orders):
        sells = sell_orders.get(tid, [])
        buys = buy_orders.get(tid, [])
        sorted_sells = sorted(sells, key=lambda x: x["price"])[:10]
        sorted_buys = sorted(buys, key=lambda x: -x["price"])[:10]
        realistic = calculate_realistic_price(sells)
        results[tid] = {
            "lowest_sell": min((o["price"] for o in sells), default=None),
            "highest_buy": max((o["price"] for o in buys), default=None),
            "sell_volume": sum(o.get("volume_remain", 0) for o in sells),
            "buy_volume": sum(o.get("volume_remain", 0) for o in buys),
            "realistic_sell": realistic,
            "top_sells": [
                {"price": o["price"], "volume": o.get("volume_remain", 0),
                 "location_id": o.get("location_id"), "issued": o.get("issued")}
                for o in sorted_sells
            ],
            "top_buys": [
                {"price": o["price"], "volume": o.get("volume_remain", 0),
                 "location_id": o.get("location_id"), "issued": o.get("issued")}
                for o in sorted_buys
            ],
        }
    return results


def save_prices_to_db(db, region_id: int, prices: Dict[int, Dict]) -> int:
    """Save aggregated prices + order snapshots to DB using batch inserts."""
    if not prices:
        return 0
    with db.connection() as conn:
        with conn.cursor() as cur:
            # Batch upsert market_prices
            price_rows = [
                (tid, region_id, data["lowest_sell"], data["highest_buy"],
                 data["sell_volume"], data["buy_volume"], data.get("realistic_sell"))
                for tid, data in prices.items()
            ]
            execute_values(
                cur,
                """
                INSERT INTO market_prices (type_id, region_id, lowest_sell, highest_buy,
                                           sell_volume, buy_volume, realistic_sell, updated_at)
                VALUES %s
                ON CONFLICT (type_id, region_id) DO UPDATE SET
                    lowest_sell = EXCLUDED.lowest_sell,
                    highest_buy = EXCLUDED.highest_buy,
                    sell_volume = EXCLUDED.sell_volume,
                    buy_volume = EXCLUDED.buy_volume,
                    realistic_sell = EXCLUDED.realistic_sell,
                    updated_at = NOW()
                """,
                [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], datetime.now(timezone.utc))
                 for r in price_rows],
                page_size=1000,
            )

            # Batch upsert market_order_snapshots (sells + buys combined)
            snapshot_rows = []
            for tid, data in prices.items():
                for rank, o in enumerate(data.get("top_sells", [])[:10], 1):
                    snapshot_rows.append(
                        (tid, region_id, False, o["price"], o["volume"],
                         o.get("location_id"), o.get("issued"), rank)
                    )
                for rank, o in enumerate(data.get("top_buys", [])[:10], 1):
                    snapshot_rows.append(
                        (tid, region_id, True, o["price"], o["volume"],
                         o.get("location_id"), o.get("issued"), rank)
                    )
            if snapshot_rows:
                execute_values(
                    cur,
                    """
                    INSERT INTO market_order_snapshots
                        (type_id, region_id, is_buy_order, price, volume_remain,
                         location_id, issued, rank, updated_at)
                    VALUES %s
                    ON CONFLICT (type_id, region_id, is_buy_order, rank) DO UPDATE SET
                        price = EXCLUDED.price, volume_remain = EXCLUDED.volume_remain,
                        location_id = EXCLUDED.location_id, issued = EXCLUDED.issued,
                        updated_at = NOW()
                    """,
                    [(r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7],
                      datetime.now(timezone.utc)) for r in snapshot_rows],
                    page_size=1000,
                )
            conn.commit()
    return len(prices)


def refresh_regional_prices(db) -> dict:
    """Fetch regional prices for all trade hubs and save to DB.

    Args:
        db: eve_shared DatabasePool instance.

    Returns:
        Job result dict.
    """
    start = time.time()
    type_ids = get_relevant_type_ids(db)
    logger.info(f"Tracking {len(type_ids)} marketable items")

    per_region = []
    total_saved = 0
    total_orders = 0

    for region_name, region_id in TRADE_HUB_REGIONS.items():
        t0 = time.time()
        orders = fetch_region_orders(region_id)
        prices = aggregate_prices(orders, type_ids, region_id)
        saved = save_prices_to_db(db, region_id, prices)
        elapsed = round(time.time() - t0, 1)

        per_region.append({
            "region": region_name,
            "orders": len(orders),
            "items_priced": len(prices),
            "saved": saved,
            "elapsed": elapsed,
        })
        total_saved += saved
        total_orders += len(orders)
        logger.info(f"{region_name}: {saved} prices from {len(orders)} orders in {elapsed}s")

    total_elapsed = round(time.time() - start, 2)
    logger.info(f"Regional prices: {total_saved} saved from {total_orders} orders in {total_elapsed}s")

    return {
        "status": "completed",
        "job": "refresh-regional-prices",
        "details": {
            "type_ids_tracked": len(type_ids),
            "regions": len(TRADE_HUB_REGIONS),
            "total_orders_fetched": total_orders,
            "prices_saved": total_saved,
            "elapsed_seconds": total_elapsed,
            "per_region": per_region,
        },
    }
