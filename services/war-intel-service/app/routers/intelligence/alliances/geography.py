"""Alliance Geography Endpoint — delegates to shared geography queries."""

import logging
from fastapi import APIRouter, Query

from app.database import db_cursor
from app.utils.cache import get_cached, set_cached
from eve_shared.utils.error_handling import handle_endpoint_errors
from ..entity_context import EntityContext, EntityType
from ..shared_queries import get_full_geography
from ..shared_queries_dotlan import get_full_geography_extended

logger = logging.getLogger(__name__)
router = APIRouter()

GEOGRAPHY_CACHE_TTL = 300  # 5 minutes


@router.get("/alliance/{alliance_id}/geography")
@handle_endpoint_errors()
def get_alliance_geography(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90)
):
    """Get alliance geographic activity distribution."""
    cache_key = f"alliance-geo:{alliance_id}:{days}"
    cached = get_cached(cache_key, GEOGRAPHY_CACHE_TTL)
    if cached:
        return cached

    ctx = EntityContext(entity_type=EntityType.ALLIANCE, entity_id=alliance_id)
    with db_cursor() as cur:
        result = get_full_geography(cur, ctx, days)

    set_cached(cache_key, result, GEOGRAPHY_CACHE_TTL)
    return result


@router.get("/alliance/{alliance_id}/geography/extended")
@handle_endpoint_errors()
def get_alliance_geography_extended(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90)
):
    """Get extended alliance geography with DOTLAN integration."""
    cache_key = f"alliance-geo-ext:{alliance_id}:{days}"
    cached = get_cached(cache_key, GEOGRAPHY_CACHE_TTL)
    if cached:
        return cached

    ctx = EntityContext(entity_type=EntityType.ALLIANCE, entity_id=alliance_id)
    with db_cursor() as cur:
        result = get_full_geography_extended(cur, ctx, days)

    set_cached(cache_key, result, GEOGRAPHY_CACHE_TTL)
    return result
