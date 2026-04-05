"""Corporation Geography Endpoint — delegates to shared geography queries."""

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

GEOGRAPHY_CACHE_TTL = 60  # 1 minute (matches corp-offensive)


def _get_corp_context(cur, corp_id: int) -> EntityContext:
    """Create EntityContext for a corporation with alliance lookup."""
    cur.execute("SELECT alliance_id FROM corporations WHERE corporation_id = %s", (corp_id,))
    row = cur.fetchone()
    corp_alliance_id = row['alliance_id'] if row else None

    return EntityContext(
        entity_type=EntityType.CORPORATION,
        entity_id=corp_id,
        alliance_id_for_sov=corp_alliance_id
    )


@router.get("/corporation/{corp_id}/geography")
@handle_endpoint_errors()
def get_corporation_geography(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
):
    """Get corporation geographic activity distribution."""
    cache_key = f"corp-geo:{corp_id}:{days}"
    cached = get_cached(cache_key, GEOGRAPHY_CACHE_TTL)
    if cached:
        return cached

    with db_cursor() as cur:
        ctx = _get_corp_context(cur, corp_id)
        result = get_full_geography(cur, ctx, days)

    set_cached(cache_key, result, GEOGRAPHY_CACHE_TTL)
    return result


@router.get("/corporation/{corp_id}/geography/extended")
@handle_endpoint_errors()
def get_corporation_geography_extended(
    corp_id: int,
    days: int = Query(30, ge=1, le=90)
):
    """Get extended corporation geography with DOTLAN integration."""
    cache_key = f"corp-geo-ext:{corp_id}:{days}"
    cached = get_cached(cache_key, GEOGRAPHY_CACHE_TTL)
    if cached:
        return cached

    with db_cursor() as cur:
        ctx = _get_corp_context(cur, corp_id)
        result = get_full_geography_extended(cur, ctx, days)

    set_cached(cache_key, result, GEOGRAPHY_CACHE_TTL)
    return result
