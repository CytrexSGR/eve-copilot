"""Power Bloc offensive intelligence endpoint.

Thin orchestrator calling shared_offensive.py section helpers.
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from app.database import db_cursor
from app.utils.cache import get_cached, set_cached
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.routers.intelligence.entity_context import EntityContext, EntityType
from app.routers.intelligence.shared_offensive import (
    fetch_hourly_stats_batch, fetch_killmail_attacker_batch,
    build_summary, build_powerbloc_isk_dedup, build_powerbloc_max_kill_value,
    build_engagement_profile, build_solo_killers, build_doctrine_profile,
    build_ship_losses_inflicted, build_victim_analysis, build_kill_heatmap,
    build_hunting_regions, build_kill_timeline, build_capital_threat,
    build_top_victims, build_hunting_hours, build_damage_dealt,
    build_ewar_usage, build_hot_systems, build_effective_doctrines,
    build_kill_velocity,
)
from ._shared import _get_coalition_members

logger = logging.getLogger(__name__)
router = APIRouter()

OFFENSIVE_CACHE_TTL = 300  # 5 minutes


def _compute_powerbloc_offensive(member_ids: List[int], days: int) -> dict:
    """Sync function doing all DB work — runs in threadpool to avoid blocking event loop."""
    ctx = EntityContext(EntityType.POWERBLOC, member_ids=member_ids)

    # Run all section queries using tuple cursor
    with db_cursor(cursor_factory=None) as cur:
        # Batch 1: Hourly stats + SDE lookups (3 queries instead of 8)
        hs_batch = fetch_hourly_stats_batch(cur, ctx, days)

        summary, deaths = build_summary(cur, ctx, days, hs_batch=hs_batch)

        # Batch 2: Killmail temp table (single scan for all killmail-based functions)
        fetch_killmail_attacker_batch(cur, ctx, days)

        engagement_profile = build_engagement_profile(cur, ctx, days, km_batch=True)

        # Sync total_kills with engagement_profile (killmail-based) for consistency
        # intelligence_hourly_stats may undercount by ~11%
        ep_total = sum(ep["kills"] for ep in engagement_profile.values())
        if ep_total > 0:
            summary["total_kills"] = ep_total
            solo_kills = engagement_profile["solo"]["kills"]
            summary["solo_kill_pct"] = round(100.0 * solo_kills / ep_total, 1)

        victim_analysis = build_victim_analysis(cur, ctx, days, km_batch=True)

        # PowerBloc-specific: fix coalition overlap inflation on ISK
        build_powerbloc_isk_dedup(cur, ctx, days, summary, km_batch=True)
        build_powerbloc_max_kill_value(cur, ctx, days, summary, km_batch=True)

        # Sync capital_kills with victim_analysis (deduplicated)
        summary["capital_kills"] = victim_analysis["capital_kills"]

        solo_killers = build_solo_killers(cur, ctx, days, km_batch=True)
        doctrine_profile = build_doctrine_profile(cur, ctx, days, km_batch=True)
        ship_losses_inflicted = build_ship_losses_inflicted(cur, ctx, days, hs_batch=hs_batch)
        kill_heatmap = build_kill_heatmap(cur, ctx, days, hs_batch=hs_batch)
        hunting_regions = build_hunting_regions(cur, ctx, days, hs_batch=hs_batch)
        kill_timeline = build_kill_timeline(cur, ctx, days)
        capital_threat = build_capital_threat(cur, ctx, days, ep_total)
        top_victims = build_top_victims(cur, ctx, days, km_batch=True)
        hunting_hours = build_hunting_hours(cur, ctx, days, hs_batch=hs_batch)
        damage_dealt = build_damage_dealt(cur, ctx, days, km_batch=True)
        ewar_usage = build_ewar_usage(cur, ctx, days, km_batch=True)
        hot_systems = build_hot_systems(cur, ctx, days, hs_batch=hs_batch)
        effective_doctrines = build_effective_doctrines(cur, ctx, days, hs_batch=hs_batch)
        kill_velocity = build_kill_velocity(cur, ctx, days, hs_batch=hs_batch)

    return {
        "summary": summary,
        "engagement_profile": engagement_profile,
        "solo_killers": solo_killers,
        "doctrine_profile": doctrine_profile,
        "ship_losses_inflicted": ship_losses_inflicted,
        "victim_analysis": victim_analysis,
        "kill_heatmap": kill_heatmap,
        "hunting_regions": hunting_regions,
        "kill_timeline": kill_timeline,
        "capital_threat": capital_threat,
        "top_victims": top_victims,
        "hunting_hours": hunting_hours,
        "damage_dealt": damage_dealt,
        "ewar_usage": ewar_usage,
        "hot_systems": hot_systems,
        "effective_doctrines": effective_doctrines,
        "kill_velocity": kill_velocity,
    }


@router.get("/{leader_id}/offensive")
@handle_endpoint_errors()
async def get_powerbloc_offensive(
    leader_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get comprehensive offensive kill intelligence for PowerBloc (aggregated across coalition)."""
    cache_key = f"pb-offensive:{leader_id}:{days}"
    cached = get_cached(cache_key, OFFENSIVE_CACHE_TTL)
    if cached:
        logger.debug(f"Offensive cache hit for PowerBloc {leader_id}")
        return cached

    # Resolve coalition members using RealDictCursor (required by _get_coalition_members)
    with db_cursor() as cur:
        member_ids, coalition_name, name_map, ticker_map = _get_coalition_members(leader_id, cur)

    result = await run_in_threadpool(_compute_powerbloc_offensive, member_ids, days)

    set_cached(cache_key, result, OFFENSIVE_CACHE_TTL)
    logger.debug(f"Offensive cached for PowerBloc {leader_id}")
    return result
