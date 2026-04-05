"""
Alliances API Router
Serves alliance-related data including corporations.
"""

import logging
from typing import Dict, List
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{alliance_id}/corporations")
@handle_endpoint_errors()
def get_alliance_corporations(
    alliance_id: int,
    limit: int = Query(default=20, ge=1, le=100)
) -> Dict:
    """
    Get corporations belonging to an alliance.

    Returns corporations sorted by member count descending.
    """
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                corporation_id,
                corporation_name as name,
                ticker,
                member_count
            FROM corporations
            WHERE alliance_id = %s
            ORDER BY member_count DESC NULLS LAST
            LIMIT %s
        """, (alliance_id, limit))

        corps = cur.fetchall()

        return {
            "alliance_id": alliance_id,
            "corporation_count": len(corps),
            "corporations": [
                {
                    "corporation_id": c['corporation_id'],
                    "name": c['name'],
                    "ticker": c['ticker'] or '???',
                    "member_count": c['member_count'] or 0
                }
                for c in corps
            ]
        }


@router.get("/{alliance_id}/corporations/{corporation_id}")
@handle_endpoint_errors()
def get_corporation_detail(
    alliance_id: int,
    corporation_id: int
) -> Dict:
    """
    Get detailed corporation information including kill stats.
    """
    with db_cursor() as cur:
        # Get basic corp info
        cur.execute("""
            SELECT
                corporation_id,
                corporation_name as name,
                ticker,
                member_count,
                ceo_id
            FROM corporations
            WHERE corporation_id = %s
        """, (corporation_id,))

        corp = cur.fetchone()
        if not corp:
            raise HTTPException(status_code=404, detail="Corporation not found")

        # Get CEO name if available
        ceo_name = None
        if corp['ceo_id']:
            cur.execute("""
                SELECT character_name
                FROM character_name_cache
                WHERE character_id = %s
            """, (corp['ceo_id'],))
            ceo_row = cur.fetchone()
            if ceo_row:
                ceo_name = ceo_row['character_name']

        # Get kill stats (last 30 days) - kills where corp members participated
        cur.execute("""
            SELECT
                COUNT(DISTINCT k.killmail_id) as total_kills,
                COALESCE(SUM(DISTINCT k.ship_value), 0) as isk_destroyed,
                COUNT(DISTINCT k.solar_system_id) as systems_active
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            WHERE ka.corporation_id = %s
            AND k.killmail_time > NOW() - INTERVAL '30 days'
        """, (corporation_id,))
        kill_stats = cur.fetchone()

        # Get loss stats (last 30 days) - kills where corp was victim
        cur.execute("""
            SELECT
                COUNT(*) as total_losses,
                COALESCE(SUM(ship_value), 0) as isk_lost
            FROM killmails
            WHERE victim_corporation_id = %s
            AND killmail_time > NOW() - INTERVAL '30 days'
        """, (corporation_id,))
        loss_stats = cur.fetchone()

        # Get top ships used (last 30 days)
        cur.execute("""
            SELECT
                it."typeName" as ship_name,
                ig."groupName" as ship_class,
                COUNT(*) as uses
            FROM killmail_attackers ka
            JOIN killmails k ON k.killmail_id = ka.killmail_id
            JOIN "invTypes" it ON it."typeID" = ka.ship_type_id
            JOIN "invGroups" ig ON ig."groupID" = it."groupID"
            WHERE ka.corporation_id = %s
            AND k.killmail_time > NOW() - INTERVAL '30 days'
            AND ka.ship_type_id IS NOT NULL
            AND ka.ship_type_id > 0
            GROUP BY it."typeName", ig."groupName"
            ORDER BY uses DESC
            LIMIT 5
        """, (corporation_id,))
        top_ships = cur.fetchall()

        # Calculate efficiency
        isk_destroyed = kill_stats['isk_destroyed'] or 0
        isk_lost = loss_stats['isk_lost'] or 0
        efficiency = 0
        if isk_destroyed + isk_lost > 0:
            efficiency = round((isk_destroyed / (isk_destroyed + isk_lost)) * 100)

        return {
            "corporation_id": corp['corporation_id'],
            "name": corp['name'],
            "ticker": corp['ticker'] or '???',
            "member_count": corp['member_count'] or 0,
            "ceo_name": ceo_name,
            "stats_30d": {
                "kills": kill_stats['total_kills'] or 0,
                "losses": loss_stats['total_losses'] or 0,
                "isk_destroyed": isk_destroyed,
                "isk_lost": isk_lost,
                "efficiency": efficiency,
                "systems_active": kill_stats['systems_active'] or 0
            },
            "top_ships": [
                {
                    "ship_name": s['ship_name'],
                    "ship_class": s['ship_class'],
                    "uses": s['uses']
                }
                for s in top_ships
            ]
        }


@router.get("/{alliance_id}")
@handle_endpoint_errors()
def get_alliance_info(alliance_id: int) -> Dict:
    """
    Get basic alliance information.
    """
    with db_cursor() as cur:
        # Get alliance name from cache
        cur.execute("""
            SELECT alliance_name, ticker
            FROM alliance_name_cache
            WHERE alliance_id = %s
        """, (alliance_id,))

        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Alliance not found")

        # Get corp count and total members
        cur.execute("""
            SELECT
                COUNT(*) as corp_count,
                COALESCE(SUM(member_count), 0) as total_members
            FROM corporations
            WHERE alliance_id = %s
        """, (alliance_id,))

        stats = cur.fetchone()

        return {
            "alliance_id": alliance_id,
            "name": row['alliance_name'],
            "ticker": row['ticker'] or '',
            "corporation_count": stats['corp_count'],
            "total_members": stats['total_members']
        }
