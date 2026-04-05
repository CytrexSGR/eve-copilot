"""Alliance Capital Fleet Intelligence — delegates to shared capital queries."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from app.database import db_cursor
from app.utils.cache import get_cached, set_cached
from eve_shared.utils.error_handling import handle_endpoint_errors
from ..entity_context import EntityContext, EntityType
from ..shared_queries import get_full_capital_intel

logger = logging.getLogger(__name__)
router = APIRouter()

CAPITALS_CACHE_TTL = 300  # 5 minutes


def _compute_alliance_capitals(alliance_id: int, days: int) -> dict:
    """Sync DB work — runs in threadpool to avoid blocking event loop."""
    ctx = EntityContext(entity_type=EntityType.ALLIANCE, entity_id=alliance_id)
    with db_cursor(cursor_factory=None) as cur:
        return get_full_capital_intel(cur, ctx, days)


@router.get("/alliance/{alliance_id}/capital-intel")
@handle_endpoint_errors()
async def get_capital_intel(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get comprehensive capital ship intelligence for an alliance."""
    cache_key = f"alliance-capitals:{alliance_id}:{days}"
    cached = get_cached(cache_key, CAPITALS_CACHE_TTL)
    if cached:
        return cached

    result = await run_in_threadpool(_compute_alliance_capitals, alliance_id, days)

    set_cached(cache_key, result, CAPITALS_CACHE_TTL)
    return result
