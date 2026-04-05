"""Power Bloc Geography Endpoint — delegates to shared geography queries."""

import logging
from fastapi import APIRouter, Query
from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.utils.cache import get_cached, set_cached
from app.routers.intelligence.entity_context import EntityContext, EntityType
from app.routers.intelligence.shared_queries import get_full_geography
from app.routers.intelligence.shared_queries_dotlan import get_full_geography_extended
from ._shared import _get_coalition_members

logger = logging.getLogger(__name__)
router = APIRouter()

# Cache TTLs for PowerBloc geography (expensive aggregation)
GEOGRAPHY_CACHE_TTL = 300       # 5 minutes for basic geography
GEOGRAPHY_EXT_CACHE_TTL = 300   # 5 minutes for extended (DOTLAN) data


@router.get("/{leader_id}/geography")
@handle_endpoint_errors()
def get_powerbloc_geography(leader_id: int, minutes: int = Query(43200)):
    """Get power bloc geographic activity distribution."""
    days = minutes // 1440
    cache_key = f"pb-geo:{leader_id}:{days}"

    # Check cache first
    cached = get_cached(cache_key, GEOGRAPHY_CACHE_TTL)
    if cached:
        logger.debug(f"Geography cache hit for PowerBloc {leader_id}")
        return cached

    with db_cursor() as cur:
        member_ids, coalition_name, name_map, ticker_map = _get_coalition_members(leader_id, cur)
        ctx = EntityContext(entity_type=EntityType.POWERBLOC, member_ids=member_ids)
        result = get_full_geography(cur, ctx, days)

    # Cache the result
    set_cached(cache_key, result, GEOGRAPHY_CACHE_TTL)
    logger.debug(f"Geography cached for PowerBloc {leader_id}")
    return result


@router.get("/{leader_id}/geography/extended")
@handle_endpoint_errors()
def get_powerbloc_geography_extended(leader_id: int, minutes: int = Query(43200)):
    """Get extended power bloc geography with DOTLAN integration.

    Returns existing zKillboard data plus:
    - live_activity: Real-time system activity from DOTLAN
    - sov_defense: Active sovereignty campaigns + ADM levels
    - territorial_changes: Recent sovereignty changes
    - alliance_power: Alliance statistics and trends for all coalition members

    Results are cached for 5 minutes to reduce database load.
    """
    days = minutes // 1440
    cache_key = f"pb-geo-ext:{leader_id}:{days}"

    # Check cache first
    cached = get_cached(cache_key, GEOGRAPHY_EXT_CACHE_TTL)
    if cached:
        logger.debug(f"Geography extended cache hit for PowerBloc {leader_id}")
        return cached

    with db_cursor() as cur:
        member_ids, coalition_name, name_map, ticker_map = _get_coalition_members(leader_id, cur)
        ctx = EntityContext(entity_type=EntityType.POWERBLOC, member_ids=member_ids)
        result = get_full_geography_extended(cur, ctx, days)

    # Cache the result
    set_cached(cache_key, result, GEOGRAPHY_EXT_CACHE_TTL)
    logger.debug(f"Geography extended cached for PowerBloc {leader_id}")
    return result
