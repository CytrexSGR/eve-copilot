"""Market arbitrage router."""
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel

from app.models import ArbitrageOpportunity, RegionalComparison
from app.services import ESIClient
from eve_shared.utils.error_handling import handle_endpoint_errors
from eve_shared.constants import JITA_REGION_ID, REGION_NAMES

logger = logging.getLogger(__name__)
router = APIRouter()


def _group_items_by_route(rows: list) -> dict:
    """Group flat query results by route_id."""
    grouped = defaultdict(list)
    for row in rows:
        grouped[row['route_id']].append(row)
    return dict(grouped)


def get_item_name(type_id: int, db) -> Optional[str]:
    """Get item name from database."""
    with db.cursor() as cur:
        cur.execute('''
            SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s
        ''', (type_id,))
        row = cur.fetchone()
        return row['typeName'] if row else None


@router.get("/compare/{type_id}")
@handle_endpoint_errors()
def compare_prices(
    request: Request,
    type_id: int
) -> RegionalComparison:
    """
    Compare prices for an item across all trade hub regions.

    Returns best buy and sell regions with price differentials.
    """
    esi = ESIClient()
    prices = esi.get_all_region_prices(type_id)

    if not prices:
        raise HTTPException(
            status_code=404,
            detail=f"No market data found for type_id {type_id}"
        )

    # Get item name from database
    db = request.app.state.db
    item_name = get_item_name(type_id, db) or f"Type {type_id}"

    best_buy = {"region": None, "price": float('inf')}
    best_sell = {"region": None, "price": 0}

    for region, data in prices.items():
        if data.get("lowest_sell") and data["lowest_sell"] < best_buy["price"]:
            best_buy = {"region": region, "price": data["lowest_sell"]}
        if data.get("highest_buy") and data["highest_buy"] > best_sell["price"]:
            best_sell = {"region": region, "price": data["highest_buy"]}

    return RegionalComparison(
        type_id=type_id,
        type_name=item_name,
        prices_by_region=prices,
        best_buy_region=best_buy["region"],
        best_buy_price=best_buy["price"] if best_buy["price"] != float('inf') else None,
        best_sell_region=best_sell["region"],
        best_sell_price=best_sell["price"] if best_sell["price"] > 0 else None,
    )


@router.get("/arbitrage/{type_id}")
@handle_endpoint_errors()
def find_arbitrage(
    request: Request,
    type_id: int,
    min_profit: float = Query(default=5.0, description="Minimum profit percentage")
) -> dict:
    """
    Find arbitrage opportunities for an item between trade hubs.

    Returns list of profitable buy/sell region pairs.
    """
    esi = ESIClient()
    opportunities = esi.find_arbitrage_opportunities(type_id, min_profit)

    # Get item name from database
    db = request.app.state.db
    item_name = get_item_name(type_id, db) or f"Type {type_id}"

    return {
        "type_id": type_id,
        "item_name": item_name,
        "min_profit_percent": min_profit,
        "opportunities": opportunities,
        "opportunity_count": len(opportunities),
    }


@router.get("/arbitrage/{type_id}/enhanced")
@handle_endpoint_errors()
def find_enhanced_arbitrage(
    request: Request,
    type_id: int,
    min_profit: float = Query(default=5.0, description="Minimum profit percentage"),
    broker_fee_percent: float = Query(default=3.0, description="Broker fee percentage"),
    sales_tax_percent: float = Query(default=8.0, description="Sales tax percentage")
) -> dict:
    """
    Enhanced arbitrage with fee and tax calculations.

    Includes net profit after broker fees and sales tax.
    """
    esi = ESIClient()
    opportunities = esi.find_arbitrage_opportunities(type_id, min_profit)

    # Get item name from database
    db = request.app.state.db
    item_name = get_item_name(type_id, db) or f"Type {type_id}"

    # Enhance with fee calculations
    enhanced = []
    for opp in opportunities:
        buy_price = opp["buy_price"]
        sell_price = opp["sell_price"]

        # Calculate fees
        broker_fee_buy = buy_price * (broker_fee_percent / 100)
        broker_fee_sell = sell_price * (broker_fee_percent / 100)
        sales_tax = sell_price * (sales_tax_percent / 100)

        total_fees = broker_fee_buy + broker_fee_sell + sales_tax
        gross_profit = opp["profit_per_unit"]
        net_profit = gross_profit - total_fees

        net_profit_percent = (
            (net_profit / buy_price * 100) if buy_price > 0 else 0
        )

        enhanced_opp = {
            **opp,
            "broker_fee_buy": round(broker_fee_buy, 2),
            "broker_fee_sell": round(broker_fee_sell, 2),
            "sales_tax": round(sales_tax, 2),
            "total_fees": round(total_fees, 2),
            "net_profit_per_unit": round(net_profit, 2),
            "net_profit_percent": round(net_profit_percent, 2),
            "is_profitable_after_fees": net_profit > 0,
        }
        enhanced.append(enhanced_opp)

    # Filter to only profitable after fees
    profitable = [o for o in enhanced if o["is_profitable_after_fees"]]

    return {
        "type_id": type_id,
        "item_name": item_name,
        "min_profit_percent": min_profit,
        "broker_fee_percent": broker_fee_percent,
        "sales_tax_percent": sales_tax_percent,
        "opportunities": profitable,
        "opportunity_count": len(profitable),
        "filtered_count": len(enhanced) - len(profitable),
    }


# Models for arbitrage routes
class ArbitrageItem(BaseModel):
    """An item in an arbitrage route cargo."""
    type_id: int
    type_name: str
    buy_price_source: float
    sell_price_dest: float
    quantity: int
    volume: float
    profit_per_unit: float
    total_profit: float
    # Fee-adjusted fields
    gross_margin_pct: Optional[float] = None
    net_profit_per_unit: Optional[float] = None
    net_margin_pct: Optional[float] = None
    total_fees_per_unit: Optional[float] = None
    net_total_profit: Optional[float] = None
    # V2 fields
    avg_daily_volume: Optional[int] = None
    days_to_sell: Optional[float] = None
    turnover: str = 'unknown'
    competition: str = 'medium'


class ArbitrageRouteSummary(BaseModel):
    """Summary metrics for an arbitrage route."""
    total_items: int
    total_volume: float
    total_buy_cost: float
    total_sell_value: float
    total_profit: float
    profit_per_jump: float
    roi_percent: float
    # Fee-adjusted
    net_total_profit: Optional[float] = None
    net_roi_percent: Optional[float] = None
    net_profit_per_jump: Optional[float] = None


class ArbitrageRouteLogistics(BaseModel):
    """Logistics info for an arbitrage route."""
    recommended_ship: str
    round_trip_time: str
    profit_per_hour: float
    net_profit_per_hour: Optional[float] = None


class ArbitrageRoute(BaseModel):
    """A complete arbitrage route to a destination."""
    destination_region: str
    destination_hub: str
    jumps: int
    safety: str  # 'safe', 'caution', 'dangerous'
    items: List[ArbitrageItem]
    summary: ArbitrageRouteSummary
    logistics: ArbitrageRouteLogistics
    # V2 fields
    avg_days_to_sell: Optional[float] = None
    route_risk: str = 'medium'


class ArbitrageRoutesResponse(BaseModel):
    """Response for arbitrage routes endpoint."""
    start_region: str
    cargo_capacity: int
    routes: List[ArbitrageRoute]
    generated_at: str
    fee_assumptions: Optional[dict] = None


@router.get("/routes")
def get_cached_arbitrage_routes(
    request: Request,
    start_region: int = Query(JITA_REGION_ID, description="Starting region ID"),
    max_jumps: int = Query(15, ge=1, le=50),
    min_profit_per_trip: int = Query(10000000, ge=0),
    cargo_capacity: int = Query(60000, ge=1000),
    collateral_limit: Optional[int] = Query(None),
    # V2 filters
    turnover: Optional[str] = Query(None, description="Filter: instant, fast, moderate, slow"),
    max_competition: Optional[str] = Query(None, description="Max: low, medium, high, extreme"),
    max_days_to_sell: Optional[float] = Query(None, ge=0),
    min_volume: Optional[int] = Query(None, ge=0),
) -> ArbitrageRoutesResponse:
    """
    Get pre-calculated arbitrage routes from cache (fast, <100ms).

    Routes are calculated every 30 minutes by the scheduler-service.
    Falls back to live calculation if cache is empty.

    Args:
        start_region: Starting region ID (default: The Forge/Jita)
        max_jumps: Maximum jumps to destination
        min_profit_per_trip: Minimum total profit required
        cargo_capacity: Ship cargo capacity in m3 (for filtering)
        collateral_limit: Optional max collateral/value

    Returns:
        ArbitrageRoutesResponse with profitable routes sorted by ISK/hour
    """
    db = request.app.state.db

    try:
        with db.cursor() as cur:
            # Get cached routes from starting region
            cur.execute('''
                SELECT r.id, r.from_region_id, r.to_region_id, r.from_hub_name,
                       r.to_hub_name, r.jumps, r.total_items, r.total_volume,
                       r.total_buy_cost, r.total_sell_value, r.total_profit,
                       r.profit_per_jump, r.profit_per_hour, r.roi_percent,
                       r.net_total_profit, r.net_roi_percent,
                       r.net_profit_per_hour, r.net_profit_per_jump,
                       r.broker_fee_pct, r.sales_tax_pct,
                       r.calculated_at
                FROM arbitrage_routes r
                WHERE r.from_region_id = %s
                  AND r.jumps <= %s
                  AND COALESCE(r.net_total_profit, r.total_profit) >= %s
                ORDER BY COALESCE(r.net_profit_per_hour, r.profit_per_hour) DESC
            ''', (start_region, max_jumps, min_profit_per_trip))

            routes_data = cur.fetchall()

            if not routes_data:
                # No cached data, return empty (scheduler will populate)
                return ArbitrageRoutesResponse(
                    start_region=REGION_NAMES.get(start_region, "Unknown"),
                    cargo_capacity=cargo_capacity,
                    routes=[],
                    generated_at=datetime.now(timezone.utc).isoformat()
                )

            # Fetch ALL items for ALL routes in one query (was N+1)
            route_ids = [r['id'] for r in routes_data]
            cur.execute('''
                SELECT route_id, type_id, type_name, buy_price_source, sell_price_dest,
                       quantity, volume, profit_per_unit, total_profit,
                       gross_margin_pct, net_profit_per_unit, net_margin_pct,
                       total_fees_per_unit, net_total_profit,
                       avg_daily_volume, days_to_sell, turnover, competition
                FROM arbitrage_route_items
                WHERE route_id = ANY(%s)
                ORDER BY route_id, COALESCE(net_total_profit, total_profit) DESC
            ''', (route_ids,))
            all_items_raw = cur.fetchall()
            items_by_route = _group_items_by_route(all_items_raw)

            routes = []
            for route_row in routes_data:
                route_id = route_row['id']
                raw_items = items_by_route.get(route_id, [])

                items = [
                    ArbitrageItem(
                        type_id=item['type_id'],
                        type_name=item['type_name'],
                        buy_price_source=float(item['buy_price_source']),
                        sell_price_dest=float(item['sell_price_dest']),
                        quantity=item['quantity'],
                        volume=float(item['volume']),
                        profit_per_unit=float(item['profit_per_unit']),
                        total_profit=float(item['total_profit']),
                        gross_margin_pct=float(item['gross_margin_pct']) if item.get('gross_margin_pct') else None,
                        net_profit_per_unit=float(item['net_profit_per_unit']) if item.get('net_profit_per_unit') else None,
                        net_margin_pct=float(item['net_margin_pct']) if item.get('net_margin_pct') else None,
                        total_fees_per_unit=float(item['total_fees_per_unit']) if item.get('total_fees_per_unit') else None,
                        net_total_profit=float(item['net_total_profit']) if item.get('net_total_profit') else None,
                        avg_daily_volume=item['avg_daily_volume'],
                        days_to_sell=float(item['days_to_sell']) if item['days_to_sell'] else None,
                        turnover=item['turnover'] or 'unknown',
                        competition=item['competition'] or 'medium',
                    )
                    for item in raw_items
                ]

                # Apply V2 filters
                if turnover:
                    items = [i for i in items if i.turnover == turnover]
                if max_competition:
                    comp_order = ['low', 'medium', 'high', 'extreme']
                    max_idx = comp_order.index(max_competition) if max_competition in comp_order else 3
                    items = [i for i in items if i.competition in comp_order[:max_idx+1]]
                if min_volume:
                    items = [i for i in items if i.avg_daily_volume and i.avg_daily_volume >= min_volume]
                if max_days_to_sell:
                    items = [i for i in items if i.days_to_sell is None or i.days_to_sell <= max_days_to_sell]

                if not items:
                    continue

                # Route-level metrics
                valid_days = [i.days_to_sell for i in items if i.days_to_sell is not None]
                avg_days = sum(valid_days) / len(valid_days) if valid_days else None
                max_days = max(valid_days) if valid_days else None
                route_risk = 'low' if max_days and max_days < 3 else 'medium' if max_days and max_days < 7 else 'high'

                routes.append(ArbitrageRoute(
                    destination_region=route_row['to_hub_name'],
                    destination_hub=route_row['to_hub_name'],
                    jumps=route_row['jumps'],
                    safety="safe",
                    items=items,
                    summary=ArbitrageRouteSummary(
                        total_items=len(items),  # Update to filtered count
                        total_volume=sum(i.volume for i in items),
                        total_buy_cost=sum(i.buy_price_source * i.quantity for i in items),
                        total_sell_value=sum(i.sell_price_dest * i.quantity for i in items),
                        total_profit=sum(i.total_profit for i in items),
                        profit_per_jump=sum(i.total_profit for i in items) / route_row['jumps'] if route_row['jumps'] > 0 else 0,
                        roi_percent=float(route_row['roi_percent']),
                        net_total_profit=float(route_row['net_total_profit']) if route_row.get('net_total_profit') else None,
                        net_roi_percent=float(route_row['net_roi_percent']) if route_row.get('net_roi_percent') else None,
                        net_profit_per_jump=float(route_row['net_profit_per_jump']) if route_row.get('net_profit_per_jump') else None,
                    ),
                    logistics=ArbitrageRouteLogistics(
                        recommended_ship="Deep Space Transport",
                        round_trip_time=f"{route_row['jumps'] * 4} minutes",
                        profit_per_hour=float(route_row['profit_per_hour']),
                        net_profit_per_hour=float(route_row['net_profit_per_hour']) if route_row.get('net_profit_per_hour') else None,
                    ),
                    avg_days_to_sell=avg_days,
                    route_risk=route_risk,
                ))

            calculated_at = routes_data[0]['calculated_at'] if routes_data else datetime.now(timezone.utc)

            fee_assumptions = None
            if routes_data:
                fee_assumptions = {
                    'broker_fee_pct': float(routes_data[0].get('broker_fee_pct') or 1.5),
                    'sales_tax_pct': float(routes_data[0].get('sales_tax_pct') or 3.6),
                    'skill_assumption': 'Broker Relations V + Accounting V',
                }

            return ArbitrageRoutesResponse(
                start_region=REGION_NAMES.get(start_region, "Unknown"),
                cargo_capacity=cargo_capacity,
                routes=routes,
                generated_at=calculated_at.isoformat() if calculated_at else datetime.now(timezone.utc).isoformat(),
                fee_assumptions=fee_assumptions,
            )

    except Exception as e:
        logger.warning(f"Error fetching cached routes: {e}")
        # Return empty on error
        return ArbitrageRoutesResponse(
            start_region=REGION_NAMES.get(start_region, "Unknown"),
            cargo_capacity=cargo_capacity,
            routes=[],
            generated_at=datetime.now(timezone.utc).isoformat()
        )


@router.get("/routes/live")
@handle_endpoint_errors()
def get_arbitrage_routes_live(
    request: Request,
    start_region: int = Query(JITA_REGION_ID, description="Starting region ID"),
    max_jumps: int = Query(15, ge=1, le=50),
    min_profit_per_trip: int = Query(10000000, ge=0),
    cargo_capacity: int = Query(60000, ge=1000),
    collateral_limit: Optional[int] = Query(None)
) -> ArbitrageRoutesResponse:
    """
    Calculate arbitrage routes in real-time (slow, ~4-5 minutes).

    Use /routes for cached results instead. This endpoint is for manual refresh.

    Args:
        start_region: Starting region ID (default: The Forge/Jita)
        max_jumps: Maximum jumps to destination
        min_profit_per_trip: Minimum total profit required
        cargo_capacity: Ship cargo capacity in m3
        collateral_limit: Optional max collateral/value

    Returns:
        ArbitrageRoutesResponse with profitable routes sorted by ISK/hour
    """
    region_names = {
        10000002: ("The Forge", "Jita"),
        10000043: ("Domain", "Amarr"),
        10000030: ("Heimatar", "Rens"),
        10000032: ("Sinq Laison", "Dodixie"),
        10000042: ("Metropolis", "Hek")
    }

    # Jump distances between hubs (approximate high-sec)
    hub_distances = {
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

    db = request.app.state.db
    esi = ESIClient()

    routes = []
    start_name, start_hub = region_names.get(start_region, (f"Region {start_region}", "Unknown"))

    # Get tradeable items from database (modules, charges, drones)
    items_to_check = []
    try:
        with db.cursor() as cur:
            cur.execute('''
                SELECT t."typeID", t."typeName", t."volume"
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE g."categoryID" IN (7, 8, 18)
                AND t."published" = 1
                AND t."marketGroupID" IS NOT NULL
                ORDER BY t."typeID"
                LIMIT 600
            ''')
            items_to_check = [
                {"typeID": r["typeID"], "typeName": r["typeName"], "volume": r["volume"] or 0.01}
                for r in cur.fetchall()
            ]
    except Exception as e:
        logger.warning(f"Failed to get tradeable items: {e}")
        items_to_check = []

    for dest_region, (dest_name, dest_hub_name) in region_names.items():
        if dest_region == start_region:
            continue

        # Get distance
        key = tuple(sorted([start_region, dest_region]))
        jumps = hub_distances.get(key, 15)

        if jumps > max_jumps:
            continue

        route_items = []

        for item in items_to_check[:300]:  # Limit checks per destination
            type_id = item['typeID']
            type_name = item['typeName']
            item_volume = item['volume']

            try:
                # Get prices in both regions
                source_stats = esi.get_market_stats(start_region, type_id)
                dest_stats = esi.get_market_stats(dest_region, type_id)

                source_sell = source_stats.get('lowest_sell', 0) or 0
                dest_buy = dest_stats.get('highest_buy', 0) or 0

                if source_sell <= 0 or dest_buy <= 0:
                    continue

                profit_per_unit = dest_buy - source_sell

                if profit_per_unit <= 0:
                    continue

                # How many can we carry?
                quantity = int(cargo_capacity / item_volume) if item_volume > 0 else 0
                quantity = min(quantity, 1000)  # Cap at 1000 units

                if quantity <= 0:
                    continue

                total_profit = profit_per_unit * quantity

                if total_profit < 100000:  # Skip tiny profits
                    continue

                route_items.append(ArbitrageItem(
                    type_id=type_id,
                    type_name=type_name,
                    buy_price_source=source_sell,
                    sell_price_dest=dest_buy,
                    quantity=quantity,
                    volume=round(item_volume * quantity, 2),
                    profit_per_unit=round(profit_per_unit, 2),
                    total_profit=round(total_profit, 2)
                ))

            except Exception:
                continue

        if not route_items:
            continue

        # Sort by profit and select top items that fit cargo
        route_items.sort(key=lambda x: x.total_profit, reverse=True)

        selected_items = []
        used_volume = 0

        for item in route_items:
            if used_volume + item.volume <= cargo_capacity:
                selected_items.append(item)
                used_volume += item.volume

        if not selected_items:
            continue

        # Calculate summary
        total_buy = sum(i.buy_price_source * i.quantity for i in selected_items)
        total_sell = sum(i.sell_price_dest * i.quantity for i in selected_items)
        total_profit = sum(i.total_profit for i in selected_items)

        if total_profit < min_profit_per_trip:
            continue

        if collateral_limit and total_buy > collateral_limit:
            continue

        roi = (total_profit / total_buy * 100) if total_buy > 0 else 0
        profit_per_jump = total_profit / jumps if jumps > 0 else 0

        # Estimate time (2 min per jump, round trip)
        round_trip_minutes = jumps * 2 * 2
        profit_per_hour = (total_profit / round_trip_minutes * 60) if round_trip_minutes > 0 else 0

        # Recommend ship
        if cargo_capacity >= 500000:
            ship = "Freighter"
        elif cargo_capacity >= 30000:
            ship = "Deep Space Transport"
        elif cargo_capacity >= 10000:
            ship = "Blockade Runner"
        else:
            ship = "Industrial"

        routes.append(ArbitrageRoute(
            destination_region=dest_name,
            destination_hub=dest_hub_name,
            jumps=jumps,
            safety="safe",  # Simplified - all high-sec routes
            items=selected_items,
            summary=ArbitrageRouteSummary(
                total_items=len(selected_items),
                total_volume=round(used_volume, 2),
                total_buy_cost=round(total_buy, 2),
                total_sell_value=round(total_sell, 2),
                total_profit=round(total_profit, 2),
                profit_per_jump=round(profit_per_jump, 2),
                roi_percent=round(roi, 2)
            ),
            logistics=ArbitrageRouteLogistics(
                recommended_ship=ship,
                round_trip_time=f"{round_trip_minutes} minutes",
                profit_per_hour=round(profit_per_hour, 2)
            )
        ))

    # Sort by profit per hour
    routes.sort(key=lambda x: x.logistics.profit_per_hour, reverse=True)

    return ArbitrageRoutesResponse(
        start_region=start_hub,
        cargo_capacity=cargo_capacity,
        routes=routes,
        generated_at=datetime.now(timezone.utc).isoformat()
    )
