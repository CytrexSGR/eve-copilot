"""
Trading Opportunities V2 - Enhanced with MER categories and risk metrics.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from eve_shared.utils.error_handling import handle_endpoint_errors
from eve_shared.constants import JITA_REGION_ID, REGION_NAMES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trading", tags=["Trading V2"])


# === Models ===

class Competition(BaseModel):
    buy_orders: int
    sell_orders: int
    update_frequency: str  # 'low', 'medium', 'high'


class TradingStrategy(BaseModel):
    style: str  # 'active', 'semi-active', 'passive'
    turnover: str  # 'instant', 'fast', 'moderate', 'slow'
    competition: str  # 'low', 'medium', 'high', 'extreme'
    update_frequency: str  # "Every 15-30 min", "2-3x per day", "Once daily"
    order_duration: str  # "1 day", "3 days", "1 week"
    tips: List[str]


class TradingOpportunityV2(BaseModel):
    type_id: int
    type_name: str
    best_buy: float
    best_sell: float
    spread: float
    margin_percent: float
    profit_per_unit: float
    daily_potential: float
    capital_required: float
    roi_daily: float

    # Categories
    primary_index: Optional[str] = None
    sub_index: Optional[str] = None

    # Liquidity
    avg_daily_volume: Optional[int] = None
    days_to_sell_100: Optional[float] = None
    volume_vs_capital_ratio: float

    # Stability
    price_volatility: float
    trend_7d: float

    # Risk
    risk_score: int
    risk_factors: List[str]

    # Existing
    competition: Competition
    recommendation: str
    reason: str

    # Trading strategy
    strategy: TradingStrategy


class TradingOpportunitiesV2Response(BaseModel):
    region_id: int
    region_name: str
    filters_applied: dict
    opportunities: List[TradingOpportunityV2]
    available_categories: dict
    generated_at: str


class SimulationResult(BaseModel):
    type_id: int
    type_name: str
    investment: int
    units: int
    unit_price: float
    expected_profit: float
    days_to_sell: Optional[float]
    roi_percent: float
    risk_score: int
    breakdown: dict


class AllocationRequest(BaseModel):
    budget: int
    strategy: str = "balanced"  # max_profit, balanced, min_risk
    max_per_item: Optional[int] = None
    max_days_to_sell: Optional[float] = None
    primary_index: Optional[str] = None
    sub_indices: Optional[List[str]] = None


class ItemAllocation(BaseModel):
    type_id: int
    type_name: str
    investment: int
    units: int
    expected_profit_per_day: float
    days_to_sell: Optional[float]
    risk_score: int
    allocation_percent: float


class AllocationResult(BaseModel):
    allocations: List[ItemAllocation]
    total_invested: int
    expected_daily_profit: float
    average_days_to_sell: float
    average_risk_score: float
    reserve: int


# === Helpers ===

def calculate_risk_factors(opp: dict) -> List[str]:
    """Generate human-readable risk factors."""
    factors = []

    if opp.get('price_volatility', 0) > 10:
        factors.append("high volatility")
    elif opp.get('price_volatility', 0) > 5:
        factors.append("moderate volatility")

    vol = opp.get('avg_daily_volume')
    if vol is None:
        factors.append("no volume data")
    elif vol < 50:
        factors.append("very low volume")
    elif vol < 200:
        factors.append("low volume")

    trend = opp.get('trend_7d', 0)
    if trend < -10:
        factors.append("price dropping")
    elif trend > 20:
        factors.append("price spiking")

    days = opp.get('days_to_sell_100')
    if days and days > 30:
        factors.append("slow turnover")

    if not factors:
        factors.append("stable market")

    return factors


def calculate_recommendation(margin: float, volume: Optional[int], risk_score: int) -> tuple:
    """Calculate recommendation and reason."""
    score = 0
    reasons = []

    # Margin scoring
    if margin >= 15:
        score += 3
        reasons.append("High margin")
    elif margin >= 10:
        score += 2
        reasons.append("Good margin")
    elif margin >= 5:
        score += 1
        reasons.append("Moderate margin")

    # Volume scoring
    if volume is None:
        reasons.append("no volume data")
    elif volume >= 1000:
        score += 3
        reasons.append("high volume")
    elif volume >= 500:
        score += 2
        reasons.append("decent volume")
    elif volume >= 100:
        score += 1
        reasons.append("low volume")

    # Risk scoring (inverse)
    if risk_score <= 20:
        score += 2
        reasons.append("low risk")
    elif risk_score <= 40:
        score += 1
        reasons.append("moderate risk")
    else:
        reasons.append("high risk")

    if score >= 7:
        return 'excellent', ', '.join(reasons)
    elif score >= 5:
        return 'good', ', '.join(reasons)
    elif score >= 3:
        return 'moderate', ', '.join(reasons)
    else:
        return 'risky', ', '.join(reasons)


def calculate_strategy(days_to_sell: Optional[float], total_orders: int, volume: Optional[int]) -> TradingStrategy:
    """Calculate trading strategy based on turnover and competition."""

    # Turnover speed
    if days_to_sell is None or volume is None:
        turnover = 'unknown'
    elif days_to_sell <= 0.1:
        turnover = 'instant'
    elif days_to_sell <= 1:
        turnover = 'fast'
    elif days_to_sell <= 7:
        turnover = 'moderate'
    else:
        turnover = 'slow'

    # Competition level
    if total_orders >= 2000:
        competition = 'extreme'
    elif total_orders >= 500:
        competition = 'high'
    elif total_orders >= 100:
        competition = 'medium'
    else:
        competition = 'low'

    # Strategy based on competition + turnover
    tips = []

    if competition in ('extreme', 'high'):
        style = 'active'
        update_frequency = 'Every 15-30 min'
        order_duration = '1 day'
        tips.append('High competition - update prices frequently')
        tips.append('Expect to be outbid every 5-30 minutes')
        if turnover == 'instant':
            tips.append('Fast turnover - orders fill quickly when at top')
    elif competition == 'medium':
        style = 'semi-active'
        update_frequency = '2-3x per day'
        order_duration = '3 days'
        tips.append('Moderate competition - check a few times daily')
        if turnover in ('instant', 'fast'):
            tips.append('Good turnover - should sell same day')
    else:
        style = 'passive'
        update_frequency = 'Once daily'
        order_duration = '1 week'
        tips.append('Low competition - can set and forget')
        if turnover in ('slow', 'moderate'):
            tips.append('Slower turnover - be patient')

    # Volume-based tips
    if volume and volume >= 10000:
        tips.append(f'Very high volume ({volume:,}/day) - room for larger orders')
    elif volume and volume < 100:
        tips.append(f'Low volume ({volume}/day) - keep orders small')

    return TradingStrategy(
        style=style,
        turnover=turnover,
        competition=competition,
        update_frequency=update_frequency,
        order_duration=order_duration,
        tips=tips
    )


# === Endpoints ===

@router.get("/opportunities/v2", response_model=TradingOpportunitiesV2Response)
@handle_endpoint_errors()
def get_trading_opportunities_v2(
    request: Request,
    region_id: int = Query(JITA_REGION_ID, description="Region ID"),
    primary_index: Optional[str] = Query(None, description="Filter by primary index"),
    sub_indices: Optional[str] = Query(None, description="Comma-separated sub indices"),
    min_capital: int = Query(0, ge=0, description="Minimum capital"),
    max_capital: Optional[int] = Query(None, ge=0, description="Maximum capital"),
    min_volume: int = Query(10, ge=0, description="Minimum daily volume (0 to include all)"),
    max_days_to_sell: Optional[float] = Query(None, ge=0, description="Max days to sell 100 units"),
    min_margin: float = Query(5.0, ge=0, le=100, description="Minimum margin %"),
    max_competition: Optional[str] = Query(None, description="Max competition level: low, medium, high, extreme"),
    turnover: Optional[str] = Query(None, description="Turnover speed: instant, fast, moderate, slow"),
    sort_by: str = Query("daily_potential", description="Sort field"),
    limit: int = Query(100, ge=1, le=500, description="Max results")
):
    """Get trading opportunities with MER categories and risk metrics."""
    db = request.app.state.db

    # Parse sub_indices
    sub_index_list = [s.strip() for s in sub_indices.split(',')] if sub_indices else None

    # Build query
    query = """
        SELECT
            mp.type_id,
            t."typeName" as type_name,
            mp.lowest_sell,
            mp.highest_buy,
            COALESCE(mp.buy_volume, 0) as buy_volume,
            COALESCE(mp.sell_volume, 0) as sell_volume,
            COALESCE(mp.avg_daily_volume, 0) as avg_daily_volume,
            COALESCE(mp.price_volatility, 0) as price_volatility,
            COALESCE(mp.trend_7d, 0) as trend_7d,
            mp.days_to_sell_100,
            COALESCE(mp.risk_score, 50) as risk_score,
            mc.primary_index,
            mc.sub_index
        FROM market_prices mp
        JOIN "invTypes" t ON mp.type_id = t."typeID"
        LEFT JOIN mer_item_categories mc ON mp.type_id = mc.type_id
        WHERE mp.region_id = %s
        AND mp.lowest_sell > 0
        AND mp.highest_buy >= 1000
        AND mp.lowest_sell > mp.highest_buy
        AND ((mp.lowest_sell - mp.highest_buy) / mp.highest_buy * 100) >= %s
        AND ((mp.lowest_sell - mp.highest_buy) / mp.highest_buy * 100) <= 200
    """
    params = [region_id, min_margin]

    # Category filters
    if primary_index:
        query += " AND mc.primary_index = %s"
        params.append(primary_index)

    if sub_index_list:
        query += " AND mc.sub_index = ANY(%s)"
        params.append(sub_index_list)

    # Days to sell filter
    if max_days_to_sell:
        query += " AND (mp.days_to_sell_100 IS NULL OR mp.days_to_sell_100 <= %s)"
        params.append(max_days_to_sell)

    # Capital filters (must be in SQL, not just Python, to get correct results)
    if min_capital and min_capital > 0:
        query += " AND mp.highest_buy * 100 >= %s"
        params.append(min_capital)

    if max_capital:
        query += " AND mp.highest_buy * 100 <= %s"
        params.append(max_capital)

    # Volume filter - excludes items with no trading data
    if min_volume > 0:
        query += " AND COALESCE(mp.avg_daily_volume, 0) >= %s"
        params.append(min_volume)

    query += " ORDER BY (mp.lowest_sell - mp.highest_buy) DESC LIMIT 1000"

    with db.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    opportunities = []

    for row in rows:
        best_buy = float(row['highest_buy'])
        best_sell = float(row['lowest_sell'])
        spread = best_sell - best_buy
        margin_percent = (spread / best_buy) * 100

        # Capital required for 100 units
        capital_required = best_buy * 100

        # Capital filters
        if capital_required < min_capital:
            continue
        if max_capital and capital_required > max_capital:
            continue

        # Calculate profit (7% fees)
        profit_per_unit = spread * 0.93

        # Use actual volume, don't fake it with defaults
        avg_volume = row['avg_daily_volume'] if row['avg_daily_volume'] else None
        daily_potential = profit_per_unit * (avg_volume or 1) * 0.1

        roi_daily = (profit_per_unit * min(avg_volume or 1, 100) / capital_required) * 100 if capital_required > 0 else 0

        # Volume vs capital ratio
        vol_cap_ratio = ((avg_volume or 0) * best_buy) / capital_required if capital_required > 0 else 0

        # Competition
        total_orders = (row['buy_volume'] or 0) // 100 + (row['sell_volume'] or 0) // 100
        if total_orders > 50:
            comp_freq = 'high'
        elif total_orders > 20:
            comp_freq = 'medium'
        else:
            comp_freq = 'low'

        risk_score = row['risk_score']
        recommendation, reason = calculate_recommendation(margin_percent, avg_volume, risk_score)

        risk_factors = calculate_risk_factors({
            'price_volatility': row['price_volatility'],
            'avg_daily_volume': avg_volume,
            'trend_7d': row['trend_7d'],
            'days_to_sell_100': row['days_to_sell_100']
        })

        # Calculate trading strategy
        days_to_sell = float(row['days_to_sell_100']) if row['days_to_sell_100'] is not None else None
        strategy = calculate_strategy(days_to_sell, total_orders, avg_volume)

        opportunities.append(TradingOpportunityV2(
            type_id=row['type_id'],
            type_name=row['type_name'],
            best_buy=best_buy,
            best_sell=best_sell,
            spread=round(spread, 2),
            margin_percent=round(margin_percent, 2),
            profit_per_unit=round(profit_per_unit, 2),
            daily_potential=round(daily_potential, 2),
            capital_required=round(capital_required, 2),
            roi_daily=round(roi_daily, 2),
            primary_index=row['primary_index'],
            sub_index=row['sub_index'],
            avg_daily_volume=avg_volume,
            days_to_sell_100=days_to_sell,
            volume_vs_capital_ratio=round(vol_cap_ratio, 2),
            price_volatility=float(row['price_volatility']),
            trend_7d=float(row['trend_7d']),
            risk_score=risk_score,
            risk_factors=risk_factors,
            competition=Competition(
                buy_orders=(row['buy_volume'] or 0) // 100,
                sell_orders=(row['sell_volume'] or 0) // 100,
                update_frequency=comp_freq
            ),
            recommendation=recommendation,
            reason=reason,
            strategy=strategy
        ))

    # Filter by turnover speed
    if turnover:
        turnover_levels = ['instant', 'fast', 'moderate', 'slow']
        if turnover in turnover_levels:
            opportunities = [o for o in opportunities if o.strategy.turnover == turnover]

    # Filter by max competition level
    if max_competition:
        competition_order = ['low', 'medium', 'high', 'extreme']
        if max_competition in competition_order:
            max_idx = competition_order.index(max_competition)
            opportunities = [o for o in opportunities
                            if o.strategy.competition in competition_order[:max_idx + 1]]

    # Sort
    sort_key = {
        'daily_potential': lambda x: x.daily_potential,
        'margin': lambda x: x.margin_percent,
        'profit_per_unit': lambda x: x.profit_per_unit,
        'days_to_sell': lambda x: x.days_to_sell_100 or 999,
        'risk_score': lambda x: x.risk_score,
        'volume': lambda x: x.avg_daily_volume or 0
    }.get(sort_by, lambda x: x.daily_potential)

    reverse = sort_by not in ('days_to_sell', 'risk_score')
    opportunities.sort(key=sort_key, reverse=reverse)

    # Get available categories
    with db.cursor() as cur:
        cur.execute("""
            SELECT DISTINCT primary_index, sub_index, COUNT(*) as cnt
            FROM mer_item_categories
            GROUP BY primary_index, sub_index
            ORDER BY primary_index, cnt DESC
        """)
        cat_rows = cur.fetchall()

    categories = {}
    for row in cat_rows:
        pi = row['primary_index']
        if pi not in categories:
            categories[pi] = []
        categories[pi].append({'name': row['sub_index'], 'count': row['cnt']})

    return TradingOpportunitiesV2Response(
        region_id=region_id,
        region_name=REGION_NAMES.get(region_id, f"Region {region_id}"),
        filters_applied={
            'primary_index': primary_index,
            'sub_indices': sub_index_list,
            'min_capital': min_capital,
            'max_capital': max_capital,
            'max_days_to_sell': max_days_to_sell,
            'min_margin': min_margin
        },
        opportunities=opportunities[:limit],
        available_categories=categories,
        generated_at=datetime.now(timezone.utc).isoformat()
    )


@router.get("/simulate", response_model=SimulationResult)
@handle_endpoint_errors()
def simulate_investment(
    request: Request,
    type_id: int = Query(..., description="Item type ID"),
    region_id: int = Query(JITA_REGION_ID, description="Region ID"),
    investment: int = Query(..., ge=1000000, description="Investment in ISK")
):
    """Simulate investment in a specific item."""
    db = request.app.state.db

    with db.cursor() as cur:
        cur.execute("""
            SELECT
                mp.type_id,
                t."typeName" as type_name,
                mp.lowest_sell,
                mp.highest_buy,
                COALESCE(mp.avg_daily_volume, 100) as avg_daily_volume,
                mp.days_to_sell_100,
                COALESCE(mp.risk_score, 50) as risk_score
            FROM market_prices mp
            JOIN "invTypes" t ON mp.type_id = t."typeID"
            WHERE mp.type_id = %s AND mp.region_id = %s
        """, (type_id, region_id))
        row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Item not found")

    buy_price = float(row['highest_buy'])
    sell_price = float(row['lowest_sell'])

    if buy_price <= 0:
        raise HTTPException(status_code=400, detail="No buy orders for item")

    # Calculate
    units = int(investment / buy_price)
    actual_investment = units * buy_price

    spread = sell_price - buy_price
    profit_per_unit = spread * 0.93  # After fees
    expected_profit = profit_per_unit * units

    roi = (expected_profit / actual_investment) * 100 if actual_investment > 0 else 0

    # Days to sell
    avg_volume = row['avg_daily_volume']
    days_to_sell = (units / avg_volume) if avg_volume > 0 else None

    return SimulationResult(
        type_id=type_id,
        type_name=row['type_name'],
        investment=int(actual_investment),
        units=units,
        unit_price=buy_price,
        expected_profit=round(expected_profit, 2),
        days_to_sell=round(days_to_sell, 2) if days_to_sell else None,
        roi_percent=round(roi, 2),
        risk_score=row['risk_score'],
        breakdown={
            'buy_price': buy_price,
            'sell_price': sell_price,
            'spread': round(spread, 2),
            'broker_fee': round(actual_investment * 0.03, 2),
            'sales_tax': round(units * sell_price * 0.04, 2),
            'gross_profit': round(spread * units, 2),
            'net_profit': round(expected_profit, 2)
        }
    )


@router.post("/allocate", response_model=AllocationResult)
@handle_endpoint_errors()
def allocate_capital(
    request: Request,
    body: AllocationRequest
):
    """Allocate capital across multiple items optimally."""
    db = request.app.state.db

    # Get opportunities
    query = """
        SELECT
            mp.type_id,
            t."typeName" as type_name,
            mp.lowest_sell,
            mp.highest_buy,
            COALESCE(mp.avg_daily_volume, 100) as avg_daily_volume,
            mp.days_to_sell_100,
            COALESCE(mp.risk_score, 50) as risk_score,
            mc.primary_index,
            mc.sub_index
        FROM market_prices mp
        JOIN "invTypes" t ON mp.type_id = t."typeID"
        LEFT JOIN mer_item_categories mc ON mp.type_id = mc.type_id
        WHERE mp.region_id = %s
        AND mp.lowest_sell > 0
        AND mp.highest_buy >= 1000
        AND mp.lowest_sell > mp.highest_buy
        AND ((mp.lowest_sell - mp.highest_buy) / mp.highest_buy * 100) >= 5
    """
    params = [JITA_REGION_ID]

    if body.primary_index:
        query += " AND mc.primary_index = %s"
        params.append(body.primary_index)

    if body.sub_indices:
        query += " AND mc.sub_index = ANY(%s)"
        params.append(body.sub_indices)

    if body.max_days_to_sell:
        query += " AND (mp.days_to_sell_100 IS NULL OR mp.days_to_sell_100 <= %s)"
        params.append(body.max_days_to_sell)

    query += " ORDER BY (mp.lowest_sell - mp.highest_buy) * COALESCE(mp.avg_daily_volume, 100) DESC LIMIT 200"

    with db.cursor() as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    # Score and allocate
    weights = {
        'max_profit': {'margin': 0.5, 'volume': 0.3, 'risk': 0.1, 'trend': 0.1},
        'balanced': {'margin': 0.3, 'volume': 0.3, 'risk': 0.2, 'trend': 0.2},
        'min_risk': {'margin': 0.1, 'volume': 0.3, 'risk': 0.5, 'trend': 0.1}
    }
    w = weights.get(body.strategy, weights['balanced'])

    scored_items = []
    for row in rows:
        buy_price = float(row['highest_buy'])
        sell_price = float(row['lowest_sell'])
        spread = sell_price - buy_price
        margin = (spread / buy_price) * 100
        volume = row['avg_daily_volume']
        risk = row['risk_score']

        # Normalize scores (0-1)
        margin_score = min(margin / 30, 1)  # 30% margin = max score
        volume_score = min(volume / 1000, 1)  # 1000/day = max score
        risk_score = 1 - (risk / 100)  # Lower risk = higher score

        total_score = (
            margin_score * w['margin'] +
            volume_score * w['volume'] +
            risk_score * w['risk']
        )

        scored_items.append({
            'type_id': row['type_id'],
            'type_name': row['type_name'],
            'buy_price': buy_price,
            'sell_price': sell_price,
            'margin': margin,
            'volume': volume,
            'risk_score': risk,
            'days_to_sell': float(row['days_to_sell_100']) if row['days_to_sell_100'] else None,
            'score': total_score
        })

    # Sort by score
    scored_items.sort(key=lambda x: x['score'], reverse=True)

    # Allocate
    allocations = []
    remaining = body.budget
    max_per = body.max_per_item or (body.budget // 5)  # Default: max 20% per item

    for item in scored_items:
        if remaining <= 0:
            break

        # Skip if days to sell exceeds limit
        if body.max_days_to_sell and item['days_to_sell'] and item['days_to_sell'] > body.max_days_to_sell:
            continue

        # Calculate allocation
        capital_for_100 = item['buy_price'] * 100
        alloc = min(remaining, max_per, capital_for_100 * 10)

        if alloc < item['buy_price']:  # Can't even buy 1
            continue

        units = int(alloc / item['buy_price'])
        actual_alloc = units * item['buy_price']

        profit_per_unit = (item['sell_price'] - item['buy_price']) * 0.93
        profit_per_day = profit_per_unit * min(units, item['volume'])

        days_to_sell = (units / item['volume']) if item['volume'] > 0 else None

        allocations.append(ItemAllocation(
            type_id=item['type_id'],
            type_name=item['type_name'],
            investment=int(actual_alloc),
            units=units,
            expected_profit_per_day=round(profit_per_day, 2),
            days_to_sell=round(days_to_sell, 2) if days_to_sell else None,
            risk_score=item['risk_score'],
            allocation_percent=round((actual_alloc / body.budget) * 100, 1)
        ))

        remaining -= actual_alloc

        # Diversification: at least 5 items if budget allows
        if len(allocations) >= 20:
            break

    total_invested = sum(a.investment for a in allocations)
    total_profit = sum(a.expected_profit_per_day for a in allocations)

    valid_days = [a.days_to_sell for a in allocations if a.days_to_sell]
    avg_days = sum(valid_days) / len(valid_days) if valid_days else 0

    avg_risk = sum(a.risk_score for a in allocations) / len(allocations) if allocations else 50

    return AllocationResult(
        allocations=allocations,
        total_invested=total_invested,
        expected_daily_profit=round(total_profit, 2),
        average_days_to_sell=round(avg_days, 2),
        average_risk_score=round(avg_risk, 1),
        reserve=remaining
    )
