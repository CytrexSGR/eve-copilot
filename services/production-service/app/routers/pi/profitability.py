"""PI profitability and make-or-buy endpoints."""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request, Query

from app.services.pi.models import (
    PIProfitability,
    MakeOrBuyResult,
    PISchematicInput,
    MakeOrBuyRecommendation,
)
from eve_shared.constants import JITA_REGION_ID
from ._helpers import (
    get_pi_repository,
    PISchematicService,
    MarketPriceAdapter,
    PIProfitabilityService,
)

router = APIRouter()


# ==================== Profitability Endpoints ====================

@router.get("/profitability/{type_id}")
def get_profitability(
    request: Request,
    type_id: int,
    region_id: int = Query(JITA_REGION_ID, description="Market region (default: Jita)")
) -> PIProfitability:
    """Calculate profitability for a PI product."""
    repo = get_pi_repository(request)
    market = MarketPriceAdapter(request.app.state.db)
    service = PIProfitabilityService(repo, market)

    profit = service.calculate_profitability(type_id, region_id)
    if not profit:
        raise HTTPException(
            status_code=404,
            detail="Not a PI product or missing market prices"
        )
    return profit


@router.get("/opportunities")
def get_opportunities(
    request: Request,
    tier: Optional[int] = Query(None, ge=1, le=4),
    limit: int = Query(50, ge=1, le=200),
    min_roi: float = Query(0, ge=0),
    region_id: int = Query(JITA_REGION_ID)
) -> List[PIProfitability]:
    """Get top profitable PI opportunities."""
    repo = get_pi_repository(request)
    market = MarketPriceAdapter(request.app.state.db)
    service = PIProfitabilityService(repo, market)

    return service.get_opportunities(
        tier=tier,
        limit=limit,
        min_roi=min_roi,
        region_id=region_id
    )


# ==================== Make-or-Buy Endpoints ====================

@router.get("/make-or-buy/{type_id}")
def analyze_make_or_buy(
    request: Request,
    type_id: int,
    quantity: int = Query(1, ge=1),
    region_id: int = Query(JITA_REGION_ID),
    include_p0_cost: bool = Query(False)
) -> MakeOrBuyResult:
    """Analyze make-or-buy decision for a PI product."""
    repo = get_pi_repository(request)
    market = MarketPriceAdapter(request.app.state.db)
    schematic_service = PISchematicService(repo)

    schematic = repo.get_schematic_for_output(type_id)
    if not schematic:
        raise HTTPException(status_code=404, detail="Not a PI product")

    runs_needed = quantity / schematic.output_quantity

    unit_price = market.get_price(type_id, region_id)
    if not unit_price or unit_price <= 0:
        raise HTTPException(status_code=400, detail="Market price not available")

    market_price = unit_price * quantity

    make_cost = 0.0
    inputs = []

    for inp in schematic.inputs:
        inp_qty = inp.quantity * runs_needed
        inp_price = market.get_price(inp.type_id, region_id)
        if not inp_price or inp_price <= 0:
            raise HTTPException(status_code=400, detail=f"Price unavailable for input {inp.type_id}")
        make_cost += inp_price * inp_qty
        inputs.append(PISchematicInput(
            type_id=inp.type_id,
            type_name=inp.type_name,
            quantity=round(inp_qty),
        ))

    p0_cost = None
    if include_p0_cost:
        p0_inputs = schematic_service.get_flat_inputs(type_id, quantity)
        if p0_inputs:
            p0_total = 0.0
            for p0 in p0_inputs:
                price = market.get_price(p0["type_id"], region_id)
                if price and price > 0:
                    p0_total += price * p0["quantity"]
            p0_cost = p0_total if p0_total > 0 else None

    if make_cost < market_price:
        recommendation = MakeOrBuyRecommendation.MAKE
        savings_isk = market_price - make_cost
    else:
        recommendation = MakeOrBuyRecommendation.BUY
        savings_isk = make_cost - market_price

    savings_percent = (savings_isk / market_price * 100) if market_price > 0 else 0

    return MakeOrBuyResult(
        type_id=type_id,
        type_name=schematic.output_name,
        tier=schematic.tier,
        quantity=quantity,
        market_price=round(market_price, 2),
        make_cost=round(make_cost, 2),
        recommendation=recommendation,
        savings_isk=round(savings_isk, 2),
        savings_percent=round(savings_percent, 1),
        inputs=inputs,
        p0_cost=round(p0_cost, 2) if p0_cost else None,
    )


@router.post("/make-or-buy/batch")
async def analyze_make_or_buy_batch(
    request: Request,
    items: List[dict]
) -> List[MakeOrBuyResult]:
    """Analyze multiple PI products for make-or-buy decision."""
    results = []
    for item in items:
        try:
            result = await analyze_make_or_buy(
                request,
                type_id=item["type_id"],
                quantity=item.get("quantity", 1),
                region_id=item.get("region_id", JITA_REGION_ID),
                include_p0_cost=item.get("include_p0_cost", False)
            )
            results.append(result)
        except HTTPException:
            continue
    return results
