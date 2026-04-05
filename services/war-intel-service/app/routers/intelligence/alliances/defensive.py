"""Alliance Defensive Stats — delegates to shared defensive queries."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from app.database import db_cursor
from app.utils.cache import get_cached, set_cached
from eve_shared.utils.error_handling import handle_endpoint_errors
from ..entity_context import EntityContext, EntityType
from ..shared_defensive import get_full_defensive_intel

logger = logging.getLogger(__name__)
router = APIRouter()


def _compute_alliance_defensive(alliance_id: int, days: int) -> dict:
    """Sync DB work — runs in threadpool to avoid blocking event loop."""
    ctx = EntityContext(entity_type=EntityType.ALLIANCE, entity_id=alliance_id)
    with db_cursor(cursor_factory=None) as cur:
        return get_full_defensive_intel(cur, ctx, days)


@router.get("/alliance/{alliance_id}/defensive-stats")
@handle_endpoint_errors()
async def get_defensive_stats(
    alliance_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get comprehensive defensive loss statistics for Alliance."""
    cache_key = f"alliance-defensive:{alliance_id}:{days}"
    cached = get_cached(cache_key, ttl_seconds=300)
    if cached:
        logger.info(f"[Cache HIT] Defensive stats for alliance {alliance_id} ({days}d)")
        return cached

    result = await run_in_threadpool(_compute_alliance_defensive, alliance_id, days)

    set_cached(cache_key, result)
    logger.info(f"[Cache SET] Defensive stats for alliance {alliance_id} ({days}d)")
    return result
