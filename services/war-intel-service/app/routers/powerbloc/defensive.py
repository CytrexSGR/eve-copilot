"""Power Bloc Defensive Intelligence — delegates to shared defensive queries."""

import logging
from typing import Dict, Any
from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.utils.cache import get_cached, set_cached
from app.routers.intelligence.entity_context import EntityContext, EntityType
from app.routers.intelligence.shared_defensive import get_full_defensive_intel
from ._shared import _get_coalition_members

logger = logging.getLogger(__name__)
router = APIRouter()

DEFENSIVE_CACHE_TTL = 300  # 5 minutes


def _compute_pb_defensive(member_ids, coalition_name, days):
    """Sync DB work — runs in threadpool to avoid blocking event loop."""
    ctx = EntityContext(entity_type=EntityType.POWERBLOC, member_ids=member_ids)
    with db_cursor(cursor_factory=None) as cur:
        result = get_full_defensive_intel(cur, ctx, days)
        result["coalition_name"] = coalition_name
        result["member_count"] = len(member_ids)
    return result


@router.get("/{leader_id}/defensive")
@handle_endpoint_errors()
async def get_powerbloc_defensive(
    leader_id: int,
    days: int = Query(30, ge=1, le=90)
) -> Dict[str, Any]:
    """Get comprehensive defensive loss statistics for a power bloc.

    Results are cached for 5 minutes.
    """
    cache_key = f"pb-defensive:{leader_id}:{days}"
    cached = get_cached(cache_key, DEFENSIVE_CACHE_TTL)
    if cached:
        logger.debug(f"Defensive cache hit for PowerBloc {leader_id}")
        return cached

    with db_cursor() as dict_cur:
        member_ids, coalition_name, name_map, ticker_map = _get_coalition_members(leader_id, dict_cur)

    result = await run_in_threadpool(_compute_pb_defensive, member_ids, coalition_name, days)

    set_cached(cache_key, result, DEFENSIVE_CACHE_TTL)
    logger.debug(f"Defensive cached for PowerBloc {leader_id}")
    return result
