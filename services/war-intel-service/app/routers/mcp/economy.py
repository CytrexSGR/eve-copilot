"""Economy Intelligence MCP Tools."""

from typing import Optional, Literal, Dict, Any
import logging

from fastapi import APIRouter, Query, HTTPException

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from ..intelligence.economics import get_economics, get_expensive_losses, get_production_needs
from ..moon_mining import get_mining_summary, get_corporation_observers, get_value_report

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/market-intel")
@handle_endpoint_errors()
async def mcp_get_market_intel(
    alliance_id: int,
    days: int = Query(7, ge=1, le=90),
    include_losses: bool = True,
    include_production_needs: bool = True,
    loss_limit: int = Query(10, ge=1, le=50)
) -> Dict[str, Any]:
    """
    MCP Tool: War economy analysis for an alliance.

    Combines ISK balance, expensive losses, and production replacement
    needs into a single economic intelligence view.

    Args:
        alliance_id: Alliance to analyze
        days: Historical data period (1-90 days)
        include_losses: Include expensive loss details
        include_production_needs: Include ship replacement analysis
        loss_limit: Maximum expensive losses to return

    Returns:
        Economic analysis with ISK flow, losses, and replacement needs
    """
    # Core economics (ISK balance, cost per kill)
    # economics endpoint caps at 30 days
    econ_days = min(days, 30)
    economics = await get_economics(alliance_id, econ_days)

    result = {
        "alliance_id": alliance_id,
        "period_days": days,
        "economics": economics,
    }

    if include_losses:
        losses = await get_expensive_losses(alliance_id, econ_days, min(loss_limit, 20))
        result["expensive_losses"] = losses
        result["total_loss_value"] = sum(l.get("isk_lost", 0) for l in losses)

    if include_production_needs:
        needs = await get_production_needs(alliance_id, econ_days, 10)
        result["production_needs"] = needs
        result["weekly_replacement_cost"] = sum(n.get("estimated_cost", 0) for n in needs)
        critical = [n for n in needs if n.get("priority") in ("critical", "high")]
        result["critical_shortages"] = len(critical)

    return result


@router.get("/mining-ops")
@handle_endpoint_errors()
async def mcp_analyze_mining_ops(
    corporation_id: int,
    days: int = Query(30, ge=7, le=90),
    include_observers: bool = False
) -> Dict[str, Any]:
    """
    MCP Tool: Moon mining operations analysis.

    Analyzes moon mining activity, ore extraction values, and observer status
    for a corporation.

    Args:
        corporation_id: Corporation to analyze
        days: Historical data period (7-90 days)
        include_observers: Include individual observer details

    Returns:
        Mining statistics with value breakdown and observer status
    """
    # Mining summary (top miners, observer count, estimated value)
    summary = await get_mining_summary(corporation_id, days)

    # Value report (ore type breakdown, R64/R32 values)
    value = await get_value_report(corporation_id, days)

    result = {
        "corporation_id": corporation_id,
        "period_days": days,
        "mining_summary": {
            "observer_count": summary.get("observer_count", 0),
            "total_estimated_value": summary.get("total_estimated_value", 0),
            "by_rarity": summary.get("by_rarity", {}),
            "top_miners": summary.get("top_miners", [])[:10],
        },
        "value_breakdown": {
            "total_estimated_value": value.get("total_estimated_value", 0),
            "r64_value": value.get("r64_value", 0),
            "r32_value": value.get("r32_value", 0),
            "high_value_percentage": value.get("high_value_percentage", 0),
            "by_ore_type": value.get("by_ore_type", [])[:15],
        },
    }

    if include_observers:
        observers = await get_corporation_observers(corporation_id)
        result["observers"] = observers.get("observers", [])

    return result
