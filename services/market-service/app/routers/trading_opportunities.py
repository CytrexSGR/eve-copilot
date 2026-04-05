"""
Trading Opportunities router - Find profitable station trading opportunities.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from eve_shared.utils.error_handling import handle_endpoint_errors
from eve_shared.constants import JITA_REGION_ID, REGION_NAMES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/trading", tags=["Trading Opportunities"])


# Pydantic Models

class Competition(BaseModel):
    """Competition metrics for a trading opportunity."""
    buy_orders: int
    sell_orders: int
    update_frequency: str  # 'low', 'medium', 'high'


class TradingOpportunity(BaseModel):
    """A profitable station trading opportunity."""
    type_id: int
    type_name: str
    best_buy: float
    best_sell: float
    spread: float
    margin_percent: float
    daily_volume: int
    weekly_volume: int
    profit_per_unit: float
    daily_potential: float
    capital_required: float
    roi_daily: float
    competition: Competition
    recommendation: str  # 'excellent', 'good', 'moderate', 'risky'
    reason: str


class TradingOpportunitiesResponse(BaseModel):
    """Response for trading opportunities endpoint."""
    region_id: int
    region_name: str
    opportunities: List[TradingOpportunity]
    generated_at: str


class TradingOpportunitiesService:
    """Service for finding station trading opportunities."""

    def __init__(self, db, redis):
        self.db = db
        self.redis = redis
        self._esi_client = None

    @property
    def esi_client(self):
        """Lazy-load ESI client."""
        if self._esi_client is None:
            from app.services.esi_client import ESIClient
            self._esi_client = ESIClient()
        return self._esi_client

    def get_region_name(self, region_id: int) -> str:
        """Get region name from database."""
        if region_id in REGION_NAMES:
            return REGION_NAMES[region_id]
        try:
            with self.db.cursor() as cur:
                cur.execute(
                    'SELECT "regionName" FROM "mapRegions" WHERE "regionID" = %s',
                    (region_id,)
                )
                row = cur.fetchone()
                return row["regionName"] if row else f"Region {region_id}"
        except Exception as e:
            logger.debug(f"Could not get region name for {region_id}: {e}")
        return f"Region {region_id}"

    def get_tradeable_items(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Get commonly traded items from database."""
        try:
            # Get items from tradeable categories (modules, charges, drones, implants)
            with self.db.cursor() as cur:
                cur.execute(
                    '''
                    SELECT t."typeID", t."typeName", t."volume"
                    FROM "invTypes" t
                    JOIN "invGroups" g ON t."groupID" = g."groupID"
                    WHERE g."categoryID" IN (7, 8, 18, 25)
                    AND t."published" = 1
                    AND t."marketGroupID" IS NOT NULL
                    ORDER BY t."typeID"
                    LIMIT %s
                    ''',
                    (limit,)
                )
                rows = cur.fetchall()
            return [{"typeID": r["typeID"], "typeName": r["typeName"]} for r in rows]
        except Exception as e:
            logger.warning(f"Failed to get tradeable items: {e}")
            return []

    def calculate_recommendation(self, margin: float, volume: int, competition: str) -> tuple:
        """Calculate recommendation and reason based on metrics."""
        score = 0
        reasons = []

        if margin >= 15:
            score += 3
            reasons.append("High margin")
        elif margin >= 10:
            score += 2
            reasons.append("Good margin")
        elif margin >= 5:
            score += 1
            reasons.append("Moderate margin")

        if volume >= 1000:
            score += 3
            reasons.append("high volume")
        elif volume >= 500:
            score += 2
            reasons.append("decent volume")
        elif volume >= 100:
            score += 1
            reasons.append("low volume")

        if competition == 'low':
            score += 2
            reasons.append("low competition")
        elif competition == 'medium':
            score += 1
            reasons.append("moderate competition")
        else:
            reasons.append("high competition")

        if score >= 7:
            return 'excellent', ', '.join(reasons)
        elif score >= 5:
            return 'good', ', '.join(reasons)
        elif score >= 3:
            return 'moderate', ', '.join(reasons)
        else:
            return 'risky', ', '.join(reasons)


@router.get("/opportunities", response_model=TradingOpportunitiesResponse)
@handle_endpoint_errors()
def get_trading_opportunities(
    request: Request,
    region_id: int = Query(JITA_REGION_ID, description="Region ID (default: The Forge)"),
    min_margin_percent: float = Query(5.0, ge=0, le=100),
    min_daily_volume: int = Query(100, ge=0),
    min_profit_per_trade: int = Query(1000000, ge=0),
    max_capital_required: Optional[int] = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    """
    Find profitable station trading opportunities in a region.

    Scans market for items with good spread, volume, and competition metrics.

    Args:
        region_id: Region to scan (default: The Forge / Jita)
        min_margin_percent: Minimum profit margin percentage
        min_daily_volume: Minimum estimated daily trading volume
        min_profit_per_trade: Minimum profit per unit in ISK
        max_capital_required: Maximum capital required (optional)
        limit: Maximum number of opportunities to return

    Returns:
        TradingOpportunitiesResponse with ranked opportunities
    """
    db = request.app.state.db
    service = TradingOpportunitiesService(db, None)

    opportunities = []

    # Query market_prices cache for opportunities with spread
    # Filter out manipulated data (0.01 ISK buy orders, extreme margins)
    with db.cursor() as cur:
        cur.execute(
            '''
            SELECT
                mp.type_id,
                t."typeName" as type_name,
                mp.lowest_sell,
                mp.highest_buy,
                COALESCE(mp.buy_volume, 0) as buy_volume,
                COALESCE(mp.sell_volume, 0) as sell_volume,
                GREATEST(COALESCE(mp.buy_volume, 0) + COALESCE(mp.sell_volume, 0), 100) as daily_volume
            FROM market_prices mp
            JOIN "invTypes" t ON mp.type_id = t."typeID"
            WHERE mp.region_id = %s
            AND mp.lowest_sell > 0
            AND mp.highest_buy >= 1000  -- Filter fake 0.01 ISK buy orders
            AND mp.lowest_sell > mp.highest_buy
            AND ((mp.lowest_sell - mp.highest_buy) / mp.highest_buy * 100) >= %s
            AND ((mp.lowest_sell - mp.highest_buy) / mp.highest_buy * 100) <= 200  -- Max 200%% margin (filter manipulation)
            AND COALESCE(mp.buy_volume, 0) < 1000000000  -- Filter corrupted volume data (INT_MAX)
            AND COALESCE(mp.sell_volume, 0) < 1000000000
            ORDER BY (mp.lowest_sell - mp.highest_buy) DESC  -- Sort by absolute profit potential
            LIMIT 500
            ''',
            (region_id, min_margin_percent)
        )
        rows = cur.fetchall()

    for row in rows:
        type_id = row['type_id']
        type_name = row['type_name']
        best_buy = float(row['highest_buy'])
        best_sell = float(row['lowest_sell'])
        buy_orders = int(row['buy_volume'] / 100) if row['buy_volume'] else 10  # Estimate order count
        sell_orders = int(row['sell_volume'] / 100) if row['sell_volume'] else 10
        daily_volume = int(row['daily_volume'] or 100)

        spread = best_sell - best_buy
        margin_percent = (spread / best_buy) * 100

        if daily_volume < min_daily_volume:
            continue

        # Calculate profit (after ~7% fees: 3% broker + 4% tax)
        fee_percent = 7
        profit_per_unit = spread * (1 - fee_percent / 100)

        if profit_per_unit < min_profit_per_trade:
            continue

        # Capital for 100 units
        capital_required = best_buy * 100

        if max_capital_required and capital_required > max_capital_required:
            continue

        # Daily potential (10% market share estimate)
        daily_potential = profit_per_unit * daily_volume * 0.1

        # ROI per day
        roi_daily = (profit_per_unit * min(daily_volume, 100) / capital_required) * 100 if capital_required > 0 else 0

        total_orders = buy_orders + sell_orders
        # Competition assessment
        if total_orders > 50:
            comp_freq = 'high'
        elif total_orders > 20:
            comp_freq = 'medium'
        else:
            comp_freq = 'low'

        recommendation, reason = service.calculate_recommendation(margin_percent, daily_volume, comp_freq)

        opportunities.append(TradingOpportunity(
            type_id=type_id,
            type_name=type_name,
            best_buy=best_buy,
            best_sell=best_sell,
            spread=round(spread, 2),
            margin_percent=round(margin_percent, 2),
            daily_volume=daily_volume,
            weekly_volume=daily_volume * 7,
            profit_per_unit=round(profit_per_unit, 2),
            daily_potential=round(daily_potential, 2),
            capital_required=round(capital_required, 2),
            roi_daily=round(roi_daily, 2),
            competition=Competition(
                buy_orders=buy_orders,
                sell_orders=sell_orders,
                update_frequency=comp_freq
            ),
            recommendation=recommendation,
            reason=reason
        ))

    # Sort by daily potential
    opportunities.sort(key=lambda x: x.daily_potential, reverse=True)

    region_name = service.get_region_name(region_id)

    return TradingOpportunitiesResponse(
        region_id=region_id,
        region_name=region_name,
        opportunities=opportunities[:limit],
        generated_at=datetime.now(timezone.utc).isoformat()
    )
