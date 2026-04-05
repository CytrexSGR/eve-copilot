"""Alliance router - rankings and historical stats."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from eve_shared.utils.error_handling import handle_endpoint_errors

from app.database import db_cursor
from app.models.alliance import AllianceStats, AllianceStatsHistory

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/rankings", response_model=list[AllianceStats])
@handle_endpoint_errors()
def get_alliance_rankings(
    sort: str = Query("systems", description="Sort by: systems, members, corps"),
    limit: int = Query(50, ge=1, le=200),
):
    """Get alliance rankings from latest snapshot."""
    sort_columns = {
        "systems": "systems_count",
        "members": "member_count",
        "corps": "corp_count",
    }
    sort_col = sort_columns.get(sort, "systems_count")

    with db_cursor() as cur:
        cur.execute(f"""
            SELECT DISTINCT ON (alliance_slug)
                   alliance_name, alliance_slug, alliance_id,
                   systems_count, member_count, corp_count,
                   rank_by_systems, snapshot_date
            FROM dotlan_alliance_stats
            ORDER BY alliance_slug, snapshot_date DESC
        """)
        results = cur.fetchall()

    # Sort by requested metric
    results.sort(key=lambda r: r.get(sort_col, 0) or 0, reverse=True)
    return results[:limit]


@router.get("/{alliance_id}/history", response_model=list[AllianceStats])
@handle_endpoint_errors()
def get_alliance_history(
    alliance_id: int,
    days: int = Query(30, ge=1, le=180),
):
    """Get historical stats for an alliance."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT alliance_name, alliance_slug, alliance_id,
                   systems_count, member_count, corp_count,
                   rank_by_systems, snapshot_date
            FROM dotlan_alliance_stats
            WHERE alliance_id = %s
              AND snapshot_date > CURRENT_DATE - %s
            ORDER BY snapshot_date ASC
        """, (alliance_id, days))
        results = cur.fetchall()

    if not results:
        raise HTTPException(status_code=404, detail=f"No stats for alliance {alliance_id}")
    return results


@router.get("/movements", response_model=list[dict])
@handle_endpoint_errors()
def get_alliance_movements(
    days: int = Query(7, ge=1, le=30),
):
    """Get alliances with biggest member count changes."""
    with db_cursor() as cur:
        cur.execute("""
            WITH latest AS (
                SELECT DISTINCT ON (alliance_slug)
                       alliance_slug, alliance_name, alliance_id,
                       member_count, systems_count, snapshot_date
                FROM dotlan_alliance_stats
                ORDER BY alliance_slug, snapshot_date DESC
            ),
            earlier AS (
                SELECT DISTINCT ON (alliance_slug)
                       alliance_slug, member_count as old_member_count,
                       systems_count as old_systems_count
                FROM dotlan_alliance_stats
                WHERE snapshot_date <= CURRENT_DATE - %s
                ORDER BY alliance_slug, snapshot_date DESC
            )
            SELECT l.alliance_name, l.alliance_id,
                   l.member_count, e.old_member_count,
                   l.member_count - COALESCE(e.old_member_count, l.member_count) as member_delta,
                   l.systems_count, e.old_systems_count,
                   l.systems_count - COALESCE(e.old_systems_count, l.systems_count) as systems_delta
            FROM latest l
            LEFT JOIN earlier e ON e.alliance_slug = l.alliance_slug
            WHERE ABS(l.member_count - COALESCE(e.old_member_count, l.member_count)) > 10
            ORDER BY ABS(l.member_count - COALESCE(e.old_member_count, l.member_count)) DESC
            LIMIT 50
        """, (days,))
        return cur.fetchall()
