"""Alliance Summary Endpoints."""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from app.services.intelligence.esi_utils import batch_resolve_alliance_info
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/alliances")
@handle_endpoint_errors()
async def get_alliances_list(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(50, ge=1, le=100)
) -> List[Dict[str, Any]]:
    """Get list of alliances for selection (alias for /fast/alliances)."""
    return await get_all_alliances_summary(days, limit)

@router.get("/fast/alliances")
@handle_endpoint_errors()
def get_all_alliances_summary(
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(50, ge=1, le=100)
) -> List[Dict[str, Any]]:
    """Get summary for all tracked alliances, sorted by activity.

    Returns format compatible with frontend AllianceSelector:
    - id: alliance ID
    - name: alliance name (from ESI)
    - ticker: alliance ticker (from ESI)
    - has_reports: always True for active alliances
    - kills, deaths, efficiency: combat stats
    """
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                alliance_id,
                SUM(kills) as kills,
                SUM(deaths) as deaths,
                SUM(isk_destroyed) as isk_destroyed,
                SUM(isk_lost) as isk_lost
            FROM intelligence_hourly_stats
            WHERE hour_bucket >= NOW() - INTERVAL '%s days'
            GROUP BY alliance_id
            HAVING SUM(kills) + SUM(deaths) >= 10
            ORDER BY SUM(kills) + SUM(deaths) DESC
            LIMIT %s
        """, (days, limit))

        rows = cur.fetchall()

    # Resolve alliance names and tickers via ESI
    alliance_ids = [row["alliance_id"] for row in rows]
    alliance_info = batch_resolve_alliance_info(alliance_ids)

    return [
        {
            "id": row["alliance_id"],
            "alliance_id": row["alliance_id"],
            "name": alliance_info.get(row["alliance_id"], {}).get("name", f"Alliance {row['alliance_id']}"),
            "alliance_name": alliance_info.get(row["alliance_id"], {}).get("name", f"Alliance {row['alliance_id']}"),
            "ticker": alliance_info.get(row["alliance_id"], {}).get("ticker", "???"),
            "has_reports": True,
            "kills": row["kills"] or 0,
            "deaths": row["deaths"] or 0,
            "isk_destroyed": float(row["isk_destroyed"] or 0),
            "isk_lost": float(row["isk_lost"] or 0),
            "efficiency": round(
                (float(row["isk_destroyed"] or 0) /
                 (float(row["isk_destroyed"] or 0) + float(row["isk_lost"] or 0))) * 100, 1
            ) if (row["isk_destroyed"] or 0) + (row["isk_lost"] or 0) > 0 else 0
        }
        for row in rows
    ]

@router.get("/fast/{alliance_id}/summary")
@handle_endpoint_errors()
def get_alliance_summary(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30)
) -> Dict[str, Any]:
    """Get combat summary for an alliance (FAST)."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                COALESCE(SUM(kills), 0) as kills,
                COALESCE(SUM(deaths), 0) as deaths,
                COALESCE(SUM(isk_destroyed), 0) as isk_destroyed,
                COALESCE(SUM(isk_lost), 0) as isk_lost
            FROM intelligence_hourly_stats
            WHERE alliance_id = %s
              AND hour_bucket >= NOW() - INTERVAL '%s days'
        """, (alliance_id, days))
        row = cur.fetchone()

        kills = row["kills"] or 0
        deaths = row["deaths"] or 0
        isk_destroyed = float(row["isk_destroyed"] or 0)
        isk_lost = float(row["isk_lost"] or 0)

        total_isk = isk_destroyed + isk_lost
        isk_efficiency = round((isk_destroyed / total_isk) * 100, 1) if total_isk > 0 else 0
        kill_efficiency = round(100.0 * kills / (kills + deaths), 1) if (kills + deaths) > 0 else 0

        # Active pilots = attackers + victims (all PvP participants)
        cur.execute("""
            SELECT COUNT(DISTINCT character_id) as active_pilots
            FROM (
                SELECT ka.character_id
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                WHERE ka.alliance_id = %(aid)s
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                  AND ka.character_id IS NOT NULL
                UNION
                SELECT k.victim_character_id
                FROM killmails k
                WHERE k.victim_alliance_id = %(aid)s
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %(days)s
                  AND k.victim_character_id IS NOT NULL
            ) all_pilots
        """, {"aid": alliance_id, "days": days})
        active_pilots = cur.fetchone()["active_pilots"] or 0

        # Trend: current period vs previous period (kills delta)
        cur.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN hour_bucket >= NOW() - INTERVAL '1 day' * %(days)s THEN kills END), 0) as cur_kills,
                COALESCE(SUM(CASE WHEN hour_bucket >= NOW() - INTERVAL '1 day' * %(days)s THEN deaths END), 0) as cur_deaths,
                COALESCE(SUM(CASE WHEN hour_bucket < NOW() - INTERVAL '1 day' * %(days)s THEN kills END), 0) as prev_kills,
                COALESCE(SUM(CASE WHEN hour_bucket < NOW() - INTERVAL '1 day' * %(days)s THEN deaths END), 0) as prev_deaths
            FROM intelligence_hourly_stats
            WHERE alliance_id = %(aid)s
              AND hour_bucket >= NOW() - INTERVAL '1 day' * %(days2x)s
        """, {"aid": alliance_id, "days": days, "days2x": days * 2})
        trend_row = cur.fetchone()
        cur_kills = trend_row["cur_kills"] or 0
        prev_kills = trend_row["prev_kills"] or 0
        kills_trend = cur_kills - prev_kills
        deaths_trend = (trend_row["cur_deaths"] or 0) - (trend_row["prev_deaths"] or 0)

        return {
            "alliance_id": alliance_id,
            "period_days": days,
            "kills": kills,
            "deaths": deaths,
            "isk_destroyed": isk_destroyed,
            "isk_lost": isk_lost,
            "efficiency": isk_efficiency,
            "isk_efficiency": isk_efficiency,
            "kill_efficiency": kill_efficiency,
            "kd_ratio": round(kills / deaths, 2) if deaths > 0 else float(kills),
            "active_pilots": active_pilots,
            "kills_trend": kills_trend,
            "deaths_trend": deaths_trend,
            "prev_kills": prev_kills,
        }
