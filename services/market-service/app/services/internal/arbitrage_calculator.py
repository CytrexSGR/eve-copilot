"""Arbitrage route calculator.

Pre-calculates profitable arbitrage routes between trade hubs
and stores them in the database for fast API responses.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Optional

from psycopg2.extras import RealDictCursor, execute_values

from eve_shared.constants import JITA_REGION_ID, REGION_NAMES

logger = logging.getLogger(__name__)

# Trade hub configuration: region_id -> (region_name, hub_city_name)
TRADE_HUBS = {
    10000002: ("The Forge", "Jita"),
    10000043: ("Domain", "Amarr"),
    10000030: ("Heimatar", "Rens"),
    10000032: ("Sinq Laison", "Dodixie"),
    10000042: ("Metropolis", "Hek"),
}

# Approximate high-sec jump distances between hubs
HUB_DISTANCES = {
    (10000002, 10000043): 9,
    (10000002, 10000030): 11,
    (10000002, 10000032): 12,
    (10000002, 10000042): 14,
    (10000043, 10000030): 18,
    (10000043, 10000032): 8,
    (10000043, 10000042): 15,
    (10000030, 10000032): 15,
    (10000030, 10000042): 7,
    (10000032, 10000042): 10,
}

CARGO_CAPACITY = 60000
BROKER_FEE_PCT = 1.5
SALES_TAX_PCT = 3.6


def calculate_turnover(days_to_sell: Optional[float]) -> str:
    """Classify turnover speed."""
    if days_to_sell is None:
        return "unknown"
    if days_to_sell < 1:
        return "instant"
    if days_to_sell < 3:
        return "fast"
    if days_to_sell < 7:
        return "moderate"
    return "slow"


def get_tradeable_items(conn) -> list:
    """Get tradeable items from SDE."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT t."typeID" as type_id, t."typeName" as type_name,
                   COALESCE(t."volume", 0.01) as volume
            FROM "invTypes" t
            JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE g."categoryID" IN (4, 5, 6, 7, 8, 9, 16, 17, 18, 20, 22, 23, 25, 32, 35, 39, 43, 46, 87)
              AND t."published" = 1
              AND t."marketGroupID" IS NOT NULL
            ORDER BY t."typeID"
            LIMIT 2000
        """)
        return list(cur.fetchall())


def get_all_cached_prices(conn, region_ids: list) -> dict:
    """Load cached prices for regions: {(region_id, type_id): {lowest_sell, highest_buy}}."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT region_id, type_id, lowest_sell, highest_buy
            FROM market_prices
            WHERE region_id = ANY(%s)
              AND (lowest_sell > 0 OR highest_buy > 0)
              AND updated_at > NOW() - INTERVAL '7 days'
        """, (region_ids,))
        return {
            (row["region_id"], row["type_id"]): {
                "lowest_sell": float(row["lowest_sell"]) if row["lowest_sell"] else None,
                "highest_buy": float(row["highest_buy"]) if row["highest_buy"] else None,
            }
            for row in cur.fetchall()
        }


def get_destination_volumes(conn, region_id: int, type_ids: list) -> dict:
    """Get avg daily volumes from market_prices for destination."""
    if not type_ids:
        return {}
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT type_id, COALESCE(avg_daily_volume, 0)::bigint as avg_volume
            FROM market_prices
            WHERE region_id = %s AND type_id = ANY(%s) AND avg_daily_volume > 0
        """, (region_id, type_ids))
        return {row["type_id"]: row["avg_volume"] for row in cur.fetchall()}


def calculate_route(from_region, to_region, items, prices_cache, volumes, cargo=CARGO_CAPACITY):
    """Calculate arbitrage route between two regions."""
    _, from_hub = TRADE_HUBS[from_region]
    _, to_hub = TRADE_HUBS[to_region]
    key = tuple(sorted([from_region, to_region]))
    jumps = HUB_DISTANCES.get(key, 15)

    bf_rate = BROKER_FEE_PCT / 100.0
    st_rate = SALES_TAX_PCT / 100.0
    route_items = []

    for item in items:
        tid = item["type_id"]
        iv = float(item["volume"])
        ss = prices_cache.get((from_region, tid))
        ds = prices_cache.get((to_region, tid))
        if not ss or not ds:
            continue
        source_sell = ss.get("lowest_sell") or 0
        dest_buy = ds.get("highest_buy") or 0
        if source_sell <= 0 or dest_buy <= 0:
            continue
        ppu = dest_buy - source_sell
        if ppu <= 0:
            continue
        fees = (source_sell * bf_rate) + (dest_buy * bf_rate) + (dest_buy * st_rate)
        net_ppu = ppu - fees
        if net_ppu <= 0:
            continue
        gross_margin = (ppu / source_sell * 100) if source_sell else 0
        net_margin = (net_ppu / source_sell * 100) if source_sell else 0
        cargo_qty = int(cargo / iv) if iv > 0 else 0
        dv = volumes.get(tid, 0)
        if dv > 0:
            qty = min(cargo_qty, dv, 1000)
            dts = qty / dv if dv else None
        else:
            qty = min(cargo_qty, 50)
            dts = None
        if qty <= 0:
            continue
        net_total = net_ppu * qty
        if net_total < 100000:
            continue
        route_items.append({
            "type_id": tid,
            "type_name": item["type_name"],
            "buy_price_source": source_sell,
            "sell_price_dest": dest_buy,
            "quantity": qty,
            "volume": round(iv * qty, 2),
            "profit_per_unit": round(ppu, 2),
            "total_profit": round(ppu * qty, 2),
            "gross_margin_pct": round(gross_margin, 2),
            "net_profit_per_unit": round(net_ppu, 2),
            "net_margin_pct": round(net_margin, 2),
            "total_fees_per_unit": round(fees, 2),
            "net_total_profit": round(net_total, 2),
            "avg_daily_volume": dv if dv > 0 else None,
            "days_to_sell": round(dts, 1) if dts else None,
            "turnover": calculate_turnover(dts),
            "competition": "medium",
        })

    if not route_items:
        return None

    route_items.sort(key=lambda x: x["total_profit"], reverse=True)
    selected = []
    used_vol = 0
    for it in route_items:
        if used_vol + it["volume"] <= cargo:
            selected.append(it)
            used_vol += it["volume"]
        if used_vol >= cargo * 0.95:
            break
    if not selected:
        return None

    total_buy = sum(i["buy_price_source"] * i["quantity"] for i in selected)
    total_sell = sum(i["sell_price_dest"] * i["quantity"] for i in selected)
    total_profit = total_sell - total_buy
    net_profit = sum(i["net_total_profit"] for i in selected)
    if net_profit < 2000000:
        return None

    roi = (total_profit / total_buy * 100) if total_buy else 0
    net_roi = (net_profit / total_buy * 100) if total_buy else 0
    ppj = total_profit / jumps if jumps else 0
    nppj = net_profit / jumps if jumps else 0
    rt_min = jumps * 2 * 2
    pph = (total_profit / rt_min * 60) if rt_min else 0
    npph = (net_profit / rt_min * 60) if rt_min else 0

    return {
        "from_region_id": from_region,
        "to_region_id": to_region,
        "from_hub_name": from_hub,
        "to_hub_name": to_hub,
        "jumps": jumps,
        "items": selected,
        "total_items": len(selected),
        "total_volume": used_vol,
        "total_buy_cost": round(total_buy, 2),
        "total_sell_value": round(total_sell, 2),
        "total_profit": round(total_profit, 2),
        "profit_per_jump": round(ppj, 2),
        "profit_per_hour": round(pph, 2),
        "roi_percent": round(roi, 2),
        "net_total_profit": round(net_profit, 2),
        "net_roi_percent": round(net_roi, 2),
        "net_profit_per_hour": round(npph, 2),
        "net_profit_per_jump": round(nppj, 2),
        "broker_fee_pct": BROKER_FEE_PCT,
        "sales_tax_pct": SALES_TAX_PCT,
    }


def save_routes(conn, routes: list):
    """Save calculated routes to DB (clear + insert)."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM arbitrage_route_items")
        cur.execute("DELETE FROM arbitrage_routes")

        for route in routes:
            cur.execute("""
                INSERT INTO arbitrage_routes
                (from_region_id, to_region_id, from_hub_name, to_hub_name, jumps,
                 total_items, total_volume, total_buy_cost, total_sell_value,
                 total_profit, profit_per_jump, profit_per_hour, roi_percent,
                 net_total_profit, net_roi_percent, net_profit_per_hour,
                 net_profit_per_jump, broker_fee_pct, sales_tax_pct, calculated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
                RETURNING id
            """, (
                route["from_region_id"], route["to_region_id"],
                route["from_hub_name"], route["to_hub_name"], route["jumps"],
                route["total_items"], route["total_volume"],
                route["total_buy_cost"], route["total_sell_value"],
                route["total_profit"], route["profit_per_jump"],
                route["profit_per_hour"], route["roi_percent"],
                route["net_total_profit"], route["net_roi_percent"],
                route["net_profit_per_hour"], route["net_profit_per_jump"],
                route["broker_fee_pct"], route["sales_tax_pct"],
            ))
            route_id = cur.fetchone()[0]

            if route["items"]:
                items_data = [
                    (route_id, i["type_id"], i["type_name"], i["buy_price_source"],
                     i["sell_price_dest"], i["quantity"], i["volume"],
                     i["profit_per_unit"], i["total_profit"],
                     i.get("avg_daily_volume"), i.get("days_to_sell"),
                     i.get("turnover", "unknown"), i.get("competition", "medium"),
                     i.get("gross_margin_pct"), i.get("net_profit_per_unit"),
                     i.get("net_margin_pct"), i.get("total_fees_per_unit"),
                     i.get("net_total_profit"))
                    for i in route["items"]
                ]
                execute_values(cur, """
                    INSERT INTO arbitrage_route_items
                    (route_id, type_id, type_name, buy_price_source, sell_price_dest,
                     quantity, volume, profit_per_unit, total_profit,
                     avg_daily_volume, days_to_sell, turnover, competition,
                     gross_margin_pct, net_profit_per_unit, net_margin_pct,
                     total_fees_per_unit, net_total_profit)
                    VALUES %s
                """, items_data)
        conn.commit()


def calculate_arbitrage(db) -> dict:
    """Calculate all arbitrage routes and save to DB.

    Args:
        db: eve_shared DatabasePool instance.

    Returns:
        Job result dict.
    """
    start = time.time()

    with db.connection() as conn:
        items = get_tradeable_items(conn)
        logger.info(f"Found {len(items)} tradeable items")

        region_ids = list(TRADE_HUBS.keys())
        prices_cache = get_all_cached_prices(conn, region_ids)
        if not prices_cache:
            logger.error("No cached prices found - run refresh-regional-prices first")
            return {
                "status": "completed",
                "job": "calculate-arbitrage",
                "details": {"routes_found": 0, "error": "no_cached_prices"},
            }

        all_type_ids = [i["type_id"] for i in items]
        jita_volumes = get_destination_volumes(conn, JITA_REGION_ID, all_type_ids)
        dest_volumes = {r: jita_volumes for r in TRADE_HUBS}

        all_routes = []
        for fr in TRADE_HUBS:
            for tr in TRADE_HUBS:
                if fr == tr:
                    continue
                route = calculate_route(fr, tr, items, prices_cache, dest_volumes.get(tr, {}))
                if route:
                    all_routes.append(route)
                    logger.info(f"{TRADE_HUBS[fr][1]}->{TRADE_HUBS[tr][1]}: {route['net_total_profit']:,.0f} ISK net")

        save_routes(conn, all_routes)

    elapsed = round(time.time() - start, 2)
    logger.info(f"Arbitrage calc: {len(all_routes)} routes in {elapsed}s")

    return {
        "status": "completed",
        "job": "calculate-arbitrage",
        "details": {
            "tradeable_items": len(items),
            "cached_prices": len(prices_cache),
            "routes_found": len(all_routes),
            "elapsed_seconds": elapsed,
        },
    }
