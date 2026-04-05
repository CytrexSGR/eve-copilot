"""Alliance Offensive Stats - Kill Analysis.

Thin orchestrator calling shared_offensive.py section helpers.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from app.database import db_cursor
from app.utils.cache import get_cached, set_cached
from eve_shared.utils.error_handling import handle_endpoint_errors
from ..entity_context import EntityContext, EntityType
from ..shared_offensive import (
    fetch_hourly_stats_batch, fetch_killmail_attacker_batch,
    build_summary, build_engagement_profile, build_fleet_profile,
    build_solo_killers, build_doctrine_profile, build_ship_losses_inflicted,
    build_victim_analysis, build_kill_heatmap, build_hunting_regions,
    build_kill_timeline, build_capital_threat, build_top_victims,
    build_high_value_kills, build_hunting_hours, build_damage_dealt,
    build_ewar_usage, build_hot_systems, build_effective_doctrines,
    build_kill_velocity,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def validate_efficiency_consistency(
    alliance_id: int,
    offensive_eff: float,
    offensive_kills: int,
    offensive_deaths: int,
    days: int
) -> None:
    """Log warning if efficiency data appears inconsistent."""
    if offensive_kills + offensive_deaths > 0:
        expected_eff = 100.0 * offensive_kills / (offensive_kills + offensive_deaths)
        diff = abs(offensive_eff - expected_eff)
        if diff > 0.5:
            logger.warning(
                f"[Alliance {alliance_id}] Efficiency calculation mismatch: "
                f"reported={offensive_eff}%, expected={expected_eff:.1f}% "
                f"(kills={offensive_kills}, deaths={offensive_deaths}, diff={diff:.1f}%)"
            )
    logger.info(
        f"[Alliance {alliance_id}] Offensive stats calculated: "
        f"efficiency={offensive_eff}%, K/D={offensive_kills}/{offensive_deaths}, "
        f"period={days}d"
    )


def _compute_alliance_offensive(alliance_id: int, ctx: EntityContext, days: int) -> dict:
    """Sync function doing all DB work — runs in threadpool to avoid blocking event loop."""
    with db_cursor(cursor_factory=None) as cur:
        # Batch 1: Hourly stats + SDE lookups (3 queries instead of 8)
        hs_batch = fetch_hourly_stats_batch(cur, ctx, days)

        summary, deaths = build_summary(cur, ctx, days, hs_batch=hs_batch)

        validate_efficiency_consistency(
            alliance_id=alliance_id,
            offensive_eff=summary["efficiency"],
            offensive_kills=summary["total_kills"],
            offensive_deaths=deaths,
            days=days,
        )

        # Batch 2: Killmail temp table (single scan for all killmail-based functions)
        fetch_killmail_attacker_batch(cur, ctx, days)

        engagement_profile = build_engagement_profile(cur, ctx, days, km_batch=True)

        # Sync total_kills with engagement_profile (killmail-based) for consistency
        ep_total = sum(ep["kills"] for ep in engagement_profile.values())
        if ep_total > 0:
            summary["total_kills"] = ep_total
            solo_kills = engagement_profile["solo"]["kills"]
            summary["solo_kill_pct"] = round(100.0 * solo_kills / ep_total, 1)

        fleet_profile = build_fleet_profile(cur, ctx, days, km_batch=True)
        solo_killers = build_solo_killers(cur, ctx, days, km_batch=True)
        doctrine_profile = build_doctrine_profile(cur, ctx, days, km_batch=True)
        ship_losses_inflicted = build_ship_losses_inflicted(cur, ctx, days, hs_batch=hs_batch)
        victim_analysis = build_victim_analysis(cur, ctx, days, km_batch=True)
        kill_heatmap = build_kill_heatmap(cur, ctx, days, hs_batch=hs_batch)
        hunting_regions = build_hunting_regions(cur, ctx, days, hs_batch=hs_batch)
        kill_timeline = build_kill_timeline(cur, ctx, days)

        # Capital threat uses victim_analysis capital_kills for Alliance
        capital_threat = build_capital_threat(cur, ctx, days, summary["total_kills"])
        if capital_threat:
            summary["capital_kills"] = capital_threat["capital_kills"]

        top_victims = build_top_victims(cur, ctx, days, km_batch=True)
        high_value_kills = build_high_value_kills(cur, ctx, days, km_batch=True)

        # Update max_kill_value from actual kills (summary used placeholder)
        if high_value_kills:
            summary["max_kill_value"] = high_value_kills[0]["isk_value"]

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
        "high_value_kills": high_value_kills,
        "hunting_hours": hunting_hours,
        "damage_dealt": damage_dealt,
        "ewar_usage": ewar_usage,
        "hot_systems": hot_systems,
        "effective_doctrines": effective_doctrines,
        "kill_velocity": kill_velocity,
        "fleet_profile": fleet_profile,
    }


@router.get("/alliance/{alliance_id}/offensive-stats")
@handle_endpoint_errors()
async def get_offensive_stats(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get comprehensive offensive kill intelligence for Alliance."""
    cache_key = f"alliance-offensive:{alliance_id}:{days}"
    cached = get_cached(cache_key, ttl_seconds=300)
    if cached:
        logger.info(f"[Cache HIT] Offensive stats for alliance {alliance_id} ({days}d)")
        return cached

    ctx = EntityContext(EntityType.ALLIANCE, entity_id=alliance_id)
    result = await run_in_threadpool(_compute_alliance_offensive, alliance_id, ctx, days)

    set_cached(cache_key, result)
    logger.info(f"[Cache SET] Offensive stats for alliance {alliance_id} ({days}d)")
    return result
