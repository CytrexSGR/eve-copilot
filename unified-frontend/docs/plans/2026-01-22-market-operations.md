# Market Operations Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement Multi-Account Order Dashboard, Station Trading Opportunities, and Regional Arbitrage UI for EVE Co-Pilot.

**Architecture:** This plan requires BOTH backend AND frontend work. The backend endpoints must be created first, then the frontend pages.

**Tech Stack:**
- **Backend:** FastAPI, PostgreSQL, ESI API
- **Frontend:** React 19, TypeScript, TanStack Query, Recharts, Tailwind CSS

---

## Pre-Implementation Analysis

### Existing Backend Endpoints (DO NOT REBUILD)

**market.py:**
- `GET /api/market/stats/{region_id}/{type_id}` - Market stats for one item
- `GET /api/market/compare/{type_id}` - Multi-region price comparison
- `GET /api/arbitrage/enhanced/{type_id}` - Enhanced arbitrage with route/cargo for ONE item

**trading.py:**
- `GET /api/trading/{character_id}/pnl` - P&L report
- `GET /api/trading/{character_id}/competition` - Competition report (single character)
- `GET /api/trading/{character_id}/velocity` - Velocity report
- `GET /api/trading/{character_id}/summary` - Trading summary

**character.py (existing):**
- `GET /api/character/{id}/orders` - Character orders (ESI)

### Backend Endpoints TO CREATE

1. **`GET /api/orders/aggregated`** - Multi-account order aggregation
2. **`GET /api/trading/opportunities`** - Station trading opportunity finder
3. **`GET /api/arbitrage/routes`** - Multi-destination arbitrage route planner

### Existing Frontend (DO NOT REBUILD)

- `src/pages/market/MarketOrders.tsx` - Single-character orders
- `src/pages/market/CompetitionTracker.tsx` - Competition analysis
- `src/api/market.ts` - API client with 25+ functions
- `src/types/market.ts` - Complete type definitions

---

## Task 1: Backend - Multi-Account Order Aggregation Endpoint

**Files:**
- Create: `routers/orders.py`
- Modify: `main.py` (register router)

**Step 1: Create orders router**

Create `/home/cytrex/eve_copilot/routers/orders.py`:

```python
"""
Orders router - Multi-account order aggregation and management.
"""

from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Optional
from pydantic import BaseModel

from src.services.character.service import CharacterService
from src.services.auth.service import AuthService
from src.services.auth.repository import AuthRepository
from src.integrations.esi.client import ESIClient
from src.core.config import get_settings
from src.core.database import DatabasePool

router = APIRouter(prefix="/api/orders", tags=["Orders"])


# Pydantic Models

class MarketStatus(BaseModel):
    current_best_buy: float
    current_best_sell: float
    is_outbid: bool
    outbid_by: float
    spread_percent: float


class AggregatedOrder(BaseModel):
    order_id: int
    character_id: int
    character_name: str
    type_id: int
    type_name: str
    is_buy_order: bool
    price: float
    volume_remain: int
    volume_total: int
    location_name: str
    region_name: str
    issued: str
    duration: int
    market_status: MarketStatus


class CharacterOrderSummary(BaseModel):
    character_id: int
    character_name: str
    buy_orders: int
    sell_orders: int
    order_slots_used: int
    order_slots_max: int
    isk_in_escrow: float
    isk_in_sell_orders: float


class AggregatedOrdersSummary(BaseModel):
    total_characters: int
    total_buy_orders: int
    total_sell_orders: int
    total_isk_in_buy_orders: float
    total_isk_in_sell_orders: float
    outbid_count: int
    undercut_count: int


class AggregatedOrdersResponse(BaseModel):
    summary: AggregatedOrdersSummary
    by_character: List[CharacterOrderSummary]
    orders: List[AggregatedOrder]
    generated_at: str


def get_character_service() -> CharacterService:
    """Dependency injection for CharacterService."""
    settings = get_settings()
    db = DatabasePool(settings)
    esi = ESIClient()
    auth_repo = AuthRepository()
    auth_svc = AuthService(auth_repo, esi, settings)
    return CharacterService(esi, auth_svc, db)


@router.get("/aggregated", response_model=AggregatedOrdersResponse)
async def get_aggregated_orders(
    character_ids: Optional[List[int]] = Query(None, description="Filter to specific character IDs"),
    order_type: Optional[str] = Query(None, description="Filter: 'buy' or 'sell'"),
    service: CharacterService = Depends(get_character_service)
):
    """
    Get aggregated orders across all authenticated characters.

    Returns orders enriched with market status (outbid/undercut detection).
    """
    from datetime import datetime

    try:
        # Get all authenticated characters if no filter
        auth_repo = AuthRepository()
        all_chars = auth_repo.get_all_characters()

        if character_ids:
            all_chars = [c for c in all_chars if c['character_id'] in character_ids]

        if not all_chars:
            return AggregatedOrdersResponse(
                summary=AggregatedOrdersSummary(
                    total_characters=0, total_buy_orders=0, total_sell_orders=0,
                    total_isk_in_buy_orders=0, total_isk_in_sell_orders=0,
                    outbid_count=0, undercut_count=0
                ),
                by_character=[],
                orders=[],
                generated_at=datetime.utcnow().isoformat()
            )

        all_orders = []
        by_character = []

        for char in all_chars:
            char_id = char['character_id']
            char_name = char.get('character_name', f'Character {char_id}')

            # Get orders for this character
            try:
                orders = await service.get_character_orders(char_id)
            except Exception:
                continue

            # Calculate character summary
            buy_orders = [o for o in orders if o.get('is_buy_order')]
            sell_orders = [o for o in orders if not o.get('is_buy_order')]

            # Get skill-based order slots (default estimate if unavailable)
            try:
                skills = await service.get_character_skills(char_id)
                trade_skill = next((s for s in skills.get('skills', []) if s['skill_id'] == 3443), None)
                retail_skill = next((s for s in skills.get('skills', []) if s['skill_id'] == 3444), None)
                wholesale_skill = next((s for s in skills.get('skills', []) if s['skill_id'] == 16596), None)
                tycoon_skill = next((s for s in skills.get('skills', []) if s['skill_id'] == 18580), None)

                base_slots = 5
                trade_slots = (trade_skill.get('active_skill_level', 0) if trade_skill else 0) * 4
                retail_slots = (retail_skill.get('active_skill_level', 0) if retail_skill else 0) * 8
                wholesale_slots = (wholesale_skill.get('active_skill_level', 0) if wholesale_skill else 0) * 16
                tycoon_slots = (tycoon_skill.get('active_skill_level', 0) if tycoon_skill else 0) * 32

                order_slots_max = base_slots + trade_slots + retail_slots + wholesale_slots + tycoon_slots
            except Exception:
                order_slots_max = 100  # Default estimate

            isk_in_escrow = sum(o.get('escrow', 0) for o in buy_orders)
            isk_in_sell = sum(o.get('price', 0) * o.get('volume_remain', 0) for o in sell_orders)

            by_character.append(CharacterOrderSummary(
                character_id=char_id,
                character_name=char_name,
                buy_orders=len(buy_orders),
                sell_orders=len(sell_orders),
                order_slots_used=len(orders),
                order_slots_max=order_slots_max,
                isk_in_escrow=isk_in_escrow,
                isk_in_sell_orders=isk_in_sell
            ))

            # Enrich orders with market status
            for order in orders:
                if order_type == 'buy' and not order.get('is_buy_order'):
                    continue
                if order_type == 'sell' and order.get('is_buy_order'):
                    continue

                # Get market data for this item
                type_id = order.get('type_id')
                region_id = order.get('region_id', 10000002)

                try:
                    from src.esi_client import esi_client
                    market_stats = esi_client.get_market_stats(region_id, type_id)
                    best_buy = market_stats.get('highest_buy', 0)
                    best_sell = market_stats.get('lowest_sell', float('inf'))
                except Exception:
                    best_buy = 0
                    best_sell = float('inf')

                order_price = order.get('price', 0)
                is_buy = order.get('is_buy_order', False)

                if is_buy:
                    is_outbid = order_price < best_buy
                    outbid_by = best_buy - order_price if is_outbid else 0
                else:
                    is_outbid = order_price > best_sell
                    outbid_by = order_price - best_sell if is_outbid else 0

                spread = ((best_sell - best_buy) / best_buy * 100) if best_buy > 0 and best_sell < float('inf') else 0

                # Get item name
                from src.database import get_item_info
                item_info = get_item_info(type_id)
                type_name = item_info.get('typeName', f'Type {type_id}') if item_info else f'Type {type_id}'

                all_orders.append(AggregatedOrder(
                    order_id=order.get('order_id'),
                    character_id=char_id,
                    character_name=char_name,
                    type_id=type_id,
                    type_name=type_name,
                    is_buy_order=is_buy,
                    price=order_price,
                    volume_remain=order.get('volume_remain', 0),
                    volume_total=order.get('volume_total', 0),
                    location_name=order.get('location_name', 'Unknown'),
                    region_name=order.get('region_name', 'Unknown'),
                    issued=order.get('issued', ''),
                    duration=order.get('duration', 0),
                    market_status=MarketStatus(
                        current_best_buy=best_buy,
                        current_best_sell=best_sell if best_sell < float('inf') else 0,
                        is_outbid=is_outbid,
                        outbid_by=outbid_by,
                        spread_percent=spread
                    )
                ))

        # Calculate summary
        buy_orders_list = [o for o in all_orders if o.is_buy_order]
        sell_orders_list = [o for o in all_orders if not o.is_buy_order]

        summary = AggregatedOrdersSummary(
            total_characters=len(by_character),
            total_buy_orders=len(buy_orders_list),
            total_sell_orders=len(sell_orders_list),
            total_isk_in_buy_orders=sum(c.isk_in_escrow for c in by_character),
            total_isk_in_sell_orders=sum(c.isk_in_sell_orders for c in by_character),
            outbid_count=len([o for o in buy_orders_list if o.market_status.is_outbid]),
            undercut_count=len([o for o in sell_orders_list if o.market_status.is_outbid])
        )

        return AggregatedOrdersResponse(
            summary=summary,
            by_character=by_character,
            orders=all_orders,
            generated_at=datetime.utcnow().isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to aggregate orders: {str(e)}")
```

**Step 2: Register router in main.py**

Add to imports in `main.py`:
```python
from routers.orders import router as orders_router
```

Add to router registration:
```python
app.include_router(orders_router)
```

**Step 3: Verify endpoint**

Run: `curl http://localhost:8000/api/orders/aggregated 2>/dev/null | head -c 500`
Expected: JSON response with aggregated orders

**Step 4: Commit**

```bash
git add routers/orders.py main.py
git commit -m "feat(backend): add multi-account order aggregation endpoint

- GET /api/orders/aggregated returns orders from all characters
- Includes market status (outbid/undercut detection)
- Character breakdown with order slot usage
- Filter by character_ids and order_type

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Backend - Station Trading Opportunities Endpoint

**Files:**
- Create: `routers/trading_opportunities.py`
- Modify: `main.py`

**Step 1: Create trading opportunities router**

Create `/home/cytrex/eve_copilot/routers/trading_opportunities.py`:

```python
"""
Trading Opportunities router - Find profitable station trading opportunities.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from src.esi_client import esi_client
from src.database import get_items_by_category
from config import REGIONS

router = APIRouter(prefix="/api/trading", tags=["Trading Opportunities"])


class Competition(BaseModel):
    buy_orders: int
    sell_orders: int
    update_frequency: str  # 'low', 'medium', 'high'


class TradingOpportunity(BaseModel):
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
    region_id: int
    region_name: str
    opportunities: List[TradingOpportunity]
    generated_at: str


def calculate_recommendation(margin: float, volume: int, competition: str) -> tuple:
    """Calculate recommendation and reason."""
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
async def get_trading_opportunities(
    region_id: int = Query(10000002, description="Region ID (default: The Forge)"),
    min_margin_percent: float = Query(5.0, ge=0, le=100),
    min_daily_volume: int = Query(100, ge=0),
    min_profit_per_trade: int = Query(1000000, ge=0),
    max_capital_required: Optional[int] = Query(None, ge=0),
    limit: int = Query(50, ge=1, le=200)
):
    """
    Find profitable station trading opportunities in a region.

    Scans market for items with good spread, volume, and competition metrics.
    """
    region_names = {
        10000002: "The Forge",
        10000043: "Domain",
        10000030: "Heimatar",
        10000032: "Sinq Laison",
        10000042: "Metropolis"
    }

    try:
        opportunities = []

        # Get tradeable items from common categories
        # Category IDs: 6=Ship, 7=Module, 8=Charge, 18=Drone, 25=Implant, 32=SKill
        category_ids = [7, 8, 18, 25]  # Modules, charges, drones, implants

        items_to_check = []
        for cat_id in category_ids:
            items = get_items_by_category(cat_id, limit=500)
            items_to_check.extend(items)

        # Limit total items to check
        items_to_check = items_to_check[:1000]

        for item in items_to_check:
            type_id = item['typeID']
            type_name = item['typeName']

            try:
                # Get market stats
                stats = esi_client.get_market_stats(region_id, type_id)

                if not stats.get('total_orders'):
                    continue

                best_buy = stats.get('highest_buy', 0)
                best_sell = stats.get('lowest_sell', 0)

                if best_buy <= 0 or best_sell <= 0 or best_sell <= best_buy:
                    continue

                spread = best_sell - best_buy
                margin_percent = (spread / best_buy) * 100

                if margin_percent < min_margin_percent:
                    continue

                # Estimate volume from order count (rough approximation)
                buy_orders = stats.get('buy_orders', 0)
                sell_orders = stats.get('sell_orders', 0)
                total_orders = stats.get('total_orders', 0)

                # Estimate daily volume (very rough - better would be ESI history)
                daily_volume = int(total_orders * 2)  # Rough estimate
                weekly_volume = daily_volume * 7

                if daily_volume < min_daily_volume:
                    continue

                # Calculate profit metrics (after 3% broker + 4% tax = ~7% fees)
                fee_percent = 7
                profit_per_unit = spread * (1 - fee_percent/100)

                if profit_per_unit * 1 < min_profit_per_trade:
                    continue

                # Capital required for 100 units
                capital_required = best_buy * 100

                if max_capital_required and capital_required > max_capital_required:
                    continue

                # Daily potential (assume 10% market share)
                daily_potential = profit_per_unit * daily_volume * 0.1

                # ROI per day (based on 100 unit position)
                roi_daily = (profit_per_unit * min(daily_volume, 100) / capital_required) * 100 if capital_required > 0 else 0

                # Competition assessment
                if total_orders > 50:
                    comp_freq = 'high'
                elif total_orders > 20:
                    comp_freq = 'medium'
                else:
                    comp_freq = 'low'

                recommendation, reason = calculate_recommendation(margin_percent, daily_volume, comp_freq)

                opportunities.append(TradingOpportunity(
                    type_id=type_id,
                    type_name=type_name,
                    best_buy=best_buy,
                    best_sell=best_sell,
                    spread=spread,
                    margin_percent=round(margin_percent, 2),
                    daily_volume=daily_volume,
                    weekly_volume=weekly_volume,
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

            except Exception:
                continue  # Skip items that fail

        # Sort by daily potential descending
        opportunities.sort(key=lambda x: x.daily_potential, reverse=True)

        return TradingOpportunitiesResponse(
            region_id=region_id,
            region_name=region_names.get(region_id, f"Region {region_id}"),
            opportunities=opportunities[:limit],
            generated_at=datetime.utcnow().isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to find opportunities: {str(e)}")
```

**Step 2: Register router**

Add to `main.py`:
```python
from routers.trading_opportunities import router as trading_opportunities_router
app.include_router(trading_opportunities_router)
```

**Step 3: Verify**

Run: `curl "http://localhost:8000/api/trading/opportunities?limit=5" 2>/dev/null | head -c 1000`

**Step 4: Commit**

```bash
git add routers/trading_opportunities.py main.py
git commit -m "feat(backend): add station trading opportunities endpoint

- GET /api/trading/opportunities scans market for profitable trades
- Filters by margin, volume, capital required
- Competition assessment and recommendations
- Sorted by daily profit potential

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Backend - Arbitrage Routes Endpoint

**Files:**
- Modify: `routers/market.py`

**Step 1: Add arbitrage routes endpoint**

Add to `/home/cytrex/eve_copilot/routers/market.py`:

```python
from typing import List
from pydantic import BaseModel

# Add these models after existing imports

class ArbitrageItem(BaseModel):
    type_id: int
    type_name: str
    buy_price_source: float
    sell_price_dest: float
    quantity: int
    volume: float
    profit_per_unit: float
    total_profit: float


class ArbitrageRouteSummary(BaseModel):
    total_items: int
    total_volume: float
    total_buy_cost: float
    total_sell_value: float
    total_profit: float
    profit_per_jump: float
    roi_percent: float


class ArbitrageLogistics(BaseModel):
    recommended_ship: str
    round_trip_time: str
    profit_per_hour: float


class ArbitrageRoute(BaseModel):
    destination_region: str
    destination_hub: str
    jumps: int
    safety: str  # 'safe', 'caution', 'dangerous'
    items: List[ArbitrageItem]
    summary: ArbitrageRouteSummary
    logistics: ArbitrageLogistics


class ArbitrageRoutesResponse(BaseModel):
    start_region: str
    cargo_capacity: int
    routes: List[ArbitrageRoute]
    generated_at: str


# Add this endpoint

@router.get("/api/arbitrage/routes", response_model=ArbitrageRoutesResponse)
async def get_arbitrage_routes(
    start_region: int = Query(10000002, description="Starting region ID"),
    max_jumps: int = Query(15, ge=1, le=50),
    min_profit_per_trip: int = Query(10000000, ge=0),
    cargo_capacity: int = Query(60000, ge=1000),
    collateral_limit: Optional[int] = Query(None)
):
    """
    Find profitable arbitrage routes from a starting region to all other trade hubs.

    Calculates which items to haul for maximum profit per trip.
    """
    from datetime import datetime

    region_names = {
        10000002: ("The Forge", "Jita"),
        10000043: ("Domain", "Amarr"),
        10000030: ("Heimatar", "Rens"),
        10000032: ("Sinq Laison", "Dodixie"),
        10000042: ("Metropolis", "Hek")
    }

    # Jumps between hubs (approximate)
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

    try:
        routes = []
        start_name, start_hub = region_names.get(start_region, (f"Region {start_region}", "Unknown"))

        # Get common tradeable items
        from src.database import get_items_by_category
        items_to_check = []
        for cat_id in [7, 8, 18]:  # Modules, charges, drones
            items = get_items_by_category(cat_id, limit=200)
            items_to_check.extend(items)

        for dest_region, (dest_name, dest_hub_name) in region_names.items():
            if dest_region == start_region:
                continue

            # Get distance
            key = tuple(sorted([start_region, dest_region]))
            jumps = hub_distances.get(key, 15)

            if jumps > max_jumps:
                continue

            route_items = []

            for item in items_to_check[:300]:  # Limit checks
                type_id = item['typeID']
                type_name = item['typeName']

                try:
                    # Get prices in both regions
                    source_stats = esi_client.get_market_stats(start_region, type_id)
                    dest_stats = esi_client.get_market_stats(dest_region, type_id)

                    source_sell = source_stats.get('lowest_sell', 0)
                    dest_buy = dest_stats.get('highest_buy', 0)

                    if source_sell <= 0 or dest_buy <= 0:
                        continue

                    profit_per_unit = dest_buy - source_sell

                    if profit_per_unit <= 0:
                        continue

                    # Get item volume
                    item_volume = cargo_service.get_item_volume(type_id) or 0.01

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

            # Estimate time
            round_trip_minutes = jumps * 2 * 2  # 2 min per jump, round trip
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
                logistics=ArbitrageLogistics(
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
            generated_at=datetime.utcnow().isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate routes: {str(e)}")
```

**Step 2: Verify**

Run: `curl "http://localhost:8000/api/arbitrage/routes?limit=3" 2>/dev/null | head -c 1000`

**Step 3: Commit**

```bash
git add routers/market.py
git commit -m "feat(backend): add arbitrage routes endpoint

- GET /api/arbitrage/routes finds profitable hauling routes
- Calculates items to haul for each destination hub
- Includes profit per jump and per hour metrics
- Recommends ship type based on cargo capacity

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Frontend - Types & API Functions

**Files:**
- Modify: `unified-frontend/src/types/market.ts`
- Modify: `unified-frontend/src/api/market.ts`

**Step 1: Add types to market.ts**

Add at the end of `src/types/market.ts`:

```typescript
// Multi-Account Order Types

export interface CharacterOrderSummary {
  character_id: number
  character_name: string
  buy_orders: number
  sell_orders: number
  order_slots_used: number
  order_slots_max: number
  isk_in_escrow: number
  isk_in_sell_orders: number
}

export interface AggregatedOrderMarketStatus {
  current_best_buy: number
  current_best_sell: number
  is_outbid: boolean
  outbid_by: number
  spread_percent: number
}

export interface AggregatedOrder {
  order_id: number
  character_id: number
  character_name: string
  type_id: number
  type_name: string
  is_buy_order: boolean
  price: number
  volume_remain: number
  volume_total: number
  location_name: string
  region_name: string
  issued: string
  duration: number
  market_status: AggregatedOrderMarketStatus
}

export interface AggregatedOrdersSummary {
  total_characters: number
  total_buy_orders: number
  total_sell_orders: number
  total_isk_in_buy_orders: number
  total_isk_in_sell_orders: number
  outbid_count: number
  undercut_count: number
}

export interface AggregatedOrdersResponse {
  summary: AggregatedOrdersSummary
  by_character: CharacterOrderSummary[]
  orders: AggregatedOrder[]
  generated_at: string
}

// Station Trading Types

export interface TradingOpportunityCompetition {
  buy_orders: number
  sell_orders: number
  update_frequency: 'low' | 'medium' | 'high'
}

export interface TradingOpportunity {
  type_id: number
  type_name: string
  best_buy: number
  best_sell: number
  spread: number
  margin_percent: number
  daily_volume: number
  weekly_volume: number
  profit_per_unit: number
  daily_potential: number
  capital_required: number
  roi_daily: number
  competition: TradingOpportunityCompetition
  recommendation: 'excellent' | 'good' | 'moderate' | 'risky'
  reason: string
}

export interface TradingOpportunitiesResponse {
  region_id: number
  region_name: string
  opportunities: TradingOpportunity[]
  generated_at: string
}

// Arbitrage Route Types

export interface ArbitrageItem {
  type_id: number
  type_name: string
  buy_price_source: number
  sell_price_dest: number
  quantity: number
  volume: number
  profit_per_unit: number
  total_profit: number
}

export interface ArbitrageRouteSummary {
  total_items: number
  total_volume: number
  total_buy_cost: number
  total_sell_value: number
  total_profit: number
  profit_per_jump: number
  roi_percent: number
}

export interface ArbitrageRouteLogistics {
  recommended_ship: string
  round_trip_time: string
  profit_per_hour: number
}

export interface ArbitrageRoute {
  destination_region: string
  destination_hub: string
  jumps: number
  safety: 'safe' | 'caution' | 'dangerous'
  items: ArbitrageItem[]
  summary: ArbitrageRouteSummary
  logistics: ArbitrageRouteLogistics
}

export interface ArbitrageRoutesResponse {
  start_region: string
  cargo_capacity: number
  routes: ArbitrageRoute[]
  generated_at: string
}
```

**Step 2: Add API functions to market.ts**

Add to `src/api/market.ts` (inside the `marketApi` object):

```typescript
  // Multi-Account Orders

  /**
   * Get aggregated orders across all characters
   */
  getAggregatedOrders: async (
    characterIds?: number[],
    orderType?: 'buy' | 'sell'
  ): Promise<AggregatedOrdersResponse> => {
    const params = new URLSearchParams()
    if (characterIds?.length) {
      characterIds.forEach(id => params.append('character_ids', id.toString()))
    }
    if (orderType) {
      params.set('order_type', orderType)
    }
    const response = await apiClient.get<AggregatedOrdersResponse>(
      `/orders/aggregated?${params.toString()}`
    )
    return response.data
  },

  // Station Trading

  /**
   * Get station trading opportunities in a region
   */
  getTradingOpportunities: async (
    regionId: number = 10000002,
    options?: {
      minMarginPercent?: number
      minDailyVolume?: number
      minProfitPerTrade?: number
      maxCapitalRequired?: number
      limit?: number
    }
  ): Promise<TradingOpportunitiesResponse> => {
    const response = await apiClient.get<TradingOpportunitiesResponse>(
      '/trading/opportunities',
      {
        params: {
          region_id: regionId,
          min_margin_percent: options?.minMarginPercent ?? 5.0,
          min_daily_volume: options?.minDailyVolume ?? 100,
          min_profit_per_trade: options?.minProfitPerTrade ?? 1000000,
          max_capital_required: options?.maxCapitalRequired,
          limit: options?.limit ?? 50,
        },
      }
    )
    return response.data
  },

  // Arbitrage Routes

  /**
   * Get profitable arbitrage routes from a starting region
   */
  getArbitrageRoutes: async (
    startRegion: number = 10000002,
    options?: {
      maxJumps?: number
      minProfitPerTrip?: number
      cargoCapacity?: number
      collateralLimit?: number
    }
  ): Promise<ArbitrageRoutesResponse> => {
    const response = await apiClient.get<ArbitrageRoutesResponse>(
      '/arbitrage/routes',
      {
        params: {
          start_region: startRegion,
          max_jumps: options?.maxJumps ?? 15,
          min_profit_per_trip: options?.minProfitPerTrip ?? 10000000,
          cargo_capacity: options?.cargoCapacity ?? 60000,
          collateral_limit: options?.collateralLimit,
        },
      }
    )
    return response.data
  },
```

**Step 3: Add imports**

Add to imports in `src/api/market.ts`:

```typescript
import type {
  // ... existing imports ...
  AggregatedOrdersResponse,
  TradingOpportunitiesResponse,
  ArbitrageRoutesResponse,
} from '@/types/market'
```

**Step 4: TypeScript check**

Run: `cd /home/cytrex/eve_copilot/unified-frontend && npx tsc --noEmit`

**Step 5: Commit**

```bash
cd /home/cytrex/eve_copilot/unified-frontend
git add src/types/market.ts src/api/market.ts
git commit -m "feat(frontend): add types and API functions for market operations

- AggregatedOrdersResponse types for multi-account orders
- TradingOpportunity types for station trading
- ArbitrageRoute types for hauling routes
- getAggregatedOrders, getTradingOpportunities, getArbitrageRoutes API functions

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Frontend - Multi-Account Orders Page

**Files:**
- Create: `unified-frontend/src/pages/market/MultiAccountOrders.tsx`
- Modify: `unified-frontend/src/App.tsx`

This creates the Multi-Account Order Dashboard page as specified in the original plan (see original Task 2 content).

**Step 1:** Create the page component (full code in original Task 2)

**Step 2:** Add route in App.tsx:
```typescript
const MultiAccountOrders = lazy(() => import('./pages/market/MultiAccountOrders'))
// ...
<Route path="/market/multi-account" element={<MultiAccountOrders />} />
```

**Step 3:** TypeScript check and commit

---

## Task 6: Frontend - Station Trading Page

**Files:**
- Create: `unified-frontend/src/pages/market/StationTrading.tsx`
- Modify: `unified-frontend/src/App.tsx`

This creates the Station Trading Opportunities page as specified in the original plan (see original Task 3 content).

---

## Task 7: Frontend - Arbitrage Planner Page

**Files:**
- Create: `unified-frontend/src/pages/market/ArbitragePlanner.tsx`
- Modify: `unified-frontend/src/App.tsx`

This creates the Regional Arbitrage Planner page as specified in the original plan (see original Task 4 content).

---

## Task 8: Frontend - Navigation Updates

**Files:**
- Modify: `unified-frontend/src/pages/market/MarketDashboard.tsx`
- Modify: `unified-frontend/src/components/layout/Sidebar.tsx`

Add navigation links to the new pages (see original Tasks 5-6).

---

## Task 9: Verification & Final Commit

**Step 1:** Start backend and verify endpoints:
```bash
curl http://localhost:8000/api/orders/aggregated
curl http://localhost:8000/api/trading/opportunities?limit=3
curl http://localhost:8000/api/arbitrage/routes
```

**Step 2:** Start frontend and verify pages:
- http://localhost:3003/market/multi-account
- http://localhost:3003/market/station-trading
- http://localhost:3003/market/arbitrage

**Step 3:** Push to GitHub:
```bash
git push origin main
```

---

## Summary

This plan creates:

**Backend (3 new endpoints):**
1. `GET /api/orders/aggregated` - Multi-account order aggregation
2. `GET /api/trading/opportunities` - Station trading opportunities
3. `GET /api/arbitrage/routes` - Regional arbitrage routes

**Frontend (3 new pages):**
1. `/market/multi-account` - Multi-Account Order Dashboard
2. `/market/station-trading` - Station Trading Opportunities
3. `/market/arbitrage` - Regional Arbitrage Planner

**Total Tasks:** 9
**Estimated Time:** Backend 15-20h, Frontend 20-25h
