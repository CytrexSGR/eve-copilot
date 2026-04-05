"""Combat Analysis Endpoints."""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from app.services.intelligence.esi_utils import batch_resolve_alliance_names
from .summary import get_alliance_summary
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/fast/{alliance_id}/ship-effectiveness")
@handle_endpoint_errors()
def get_ship_effectiveness(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30)
) -> List[Dict[str, Any]]:
    """
    Get ship class effectiveness (OPTIMIZED - uses intelligence_hourly_stats).

    Phase 3: Migrated from killmails + 2 JOINs to pre-aggregated hourly_stats.
    Reduces query time from ~600ms to <50ms by using ship_effectiveness JSONB field.
    """
    with db_cursor() as cur:
        # Query pre-aggregated ship_effectiveness from hourly_stats
        cur.execute("""
            WITH ship_agg AS (
                SELECT
                    key as ship_class,
                    SUM((value->>'deaths')::INT) as deaths,
                    SUM((value->>'isk_lost')::BIGINT) as isk_lost
                FROM intelligence_hourly_stats,
                LATERAL jsonb_each(ship_effectiveness)
                WHERE alliance_id = %s
                  AND hour_bucket >= NOW() - make_interval(days => %s::INT)
                  AND ship_effectiveness != '{}'::jsonb
                GROUP BY key
                HAVING SUM((value->>'deaths')::INT) >= 3
            )
            SELECT ship_class, deaths, isk_lost
            FROM ship_agg
            ORDER BY deaths DESC
            LIMIT 10
        """, (alliance_id, days))

        results = []
        for row in cur.fetchall():
            deaths = row["deaths"] or 0

            # Determine verdict based on death rate
            if deaths > 50:
                verdict = "bleeding"
            elif deaths > 20:
                verdict = "moderate"
            else:
                verdict = "acceptable"

            results.append({
                "ship_class": row["ship_class"],
                "deaths": deaths,
                "isk_lost": float(row["isk_lost"] or 0),
                "verdict": verdict
            })

        return results

@router.get("/fast/{alliance_id}/damage-taken")
@handle_endpoint_errors()
def get_damage_taken(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30)
) -> List[Dict[str, Any]]:
    """
    Analyze damage types taken (OPTIMIZED - uses intelligence_hourly_stats).

    Phase 3: Migrated from killmails table scans to pre-aggregated hourly_stats.
    Reduces query time from ~500ms to <50ms by using damage_types JSONB field.

    Returns damage type distribution with percentages.
    """
    with db_cursor() as cur:
        # Query pre-aggregated damage_types from hourly_stats
        cur.execute("""
            WITH damage_agg AS (
                SELECT
                    key as damage_type,
                    SUM(value::INT) as total_count
                FROM intelligence_hourly_stats,
                LATERAL jsonb_each_text(damage_types)
                WHERE alliance_id = %s
                  AND hour_bucket >= NOW() - make_interval(days => %s::INT)
                  AND damage_types != '{}'::jsonb
                GROUP BY key
            )
            SELECT
                damage_type,
                total_count,
                ROUND((total_count::NUMERIC / NULLIF(SUM(total_count) OVER (), 0)) * 100, 1) as percentage
            FROM damage_agg
            ORDER BY total_count DESC
        """, (alliance_id, days))

        return [
            {
                "damage_type": row["damage_type"],
                "percentage": float(row["percentage"] or 0)
            }
            for row in cur.fetchall()
        ]

@router.get("/fast/{alliance_id}/ewar-threats")
@handle_endpoint_errors()
def get_ewar_threats(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30)
) -> List[Dict[str, Any]]:
    """
    Detect EWAR threats (OPTIMIZED - uses intelligence_hourly_stats).

    Phase 3: Migrated from killmails + 2 JOINs to pre-aggregated hourly_stats.
    Reduces query time from ~500ms to <50ms by using ewar_threats JSONB field.
    """
    with db_cursor() as cur:
        # Query pre-aggregated ewar_threats from hourly_stats
        cur.execute("""
            WITH ewar_agg AS (
                SELECT
                    key as ship_class,
                    SUM((value->>'count')::INT) as kills_affected,
                    (value->>'ewar_type')::TEXT as ewar_type
                FROM intelligence_hourly_stats,
                LATERAL jsonb_each(ewar_threats)
                WHERE alliance_id = %s
                  AND hour_bucket >= NOW() - make_interval(days => %s::INT)
                  AND ewar_threats != '{}'::jsonb
                GROUP BY key, (value->>'ewar_type')::TEXT
            )
            SELECT ship_class, kills_affected, ewar_type
            FROM ewar_agg
            ORDER BY kills_affected DESC
        """, (alliance_id, days))

        ewar_results = cur.fetchall()

        # Get total deaths for percentage calculation
        cur.execute("""
            SELECT COALESCE(SUM(deaths), 0) as total
            FROM intelligence_hourly_stats
            WHERE alliance_id = %s
              AND hour_bucket >= NOW() - make_interval(days => %s::INT)
        """, (alliance_id, days))
        total_deaths = cur.fetchone()["total"] or 1

        return [
            {
                "ewar_type": row["ewar_type"],
                "ship_class": row["ship_class"],
                "kills_affected": row["kills_affected"],
                "percentage": round((row["kills_affected"] / total_deaths) * 100, 1)
            }
            for row in ewar_results
        ]

@router.get("/fast/{alliance_id}/enemy-vulnerabilities")
@handle_endpoint_errors()
def get_enemy_vulnerabilities(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(5, ge=1, le=20)
) -> List[Dict[str, Any]]:
    """Find enemy vulnerabilities: when and where WE kill THEM."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                k.victim_alliance_id as enemy_id,
                COUNT(*) as kills,
                array_agg(DISTINCT s."solarSystemName") as systems,
                array_agg(EXTRACT(HOUR FROM k.killmail_time)::INT) as hours
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            LEFT JOIN "mapSolarSystems" s ON k.solar_system_id = s."solarSystemID"
            WHERE ka.alliance_id = %s
              AND ka.is_final_blow = true
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
              AND k.victim_alliance_id IS NOT NULL
              AND k.victim_alliance_id != %s
            GROUP BY k.victim_alliance_id
            ORDER BY COUNT(*) DESC
            LIMIT %s
        """, (alliance_id, days, alliance_id, limit))

        rows = cur.fetchall()

        # Batch resolve alliance names
        enemy_ids = [row["enemy_id"] for row in rows if row["enemy_id"]]
        names = batch_resolve_alliance_names(enemy_ids) if enemy_ids else {}

        results = []
        for row in rows:
            hours = row["hours"] or []
            systems = [s for s in (row["systems"] or []) if s][:3]

            # Find peak vulnerability hours
            if hours:
                hour_counts = {}
                for h in hours:
                    hour_counts[h] = hour_counts.get(h, 0) + 1
                sorted_hours = sorted(hour_counts.items(), key=lambda x: -x[1])
                weak_hour_start = sorted_hours[0][0] if sorted_hours else 18
                weak_hour_end = (weak_hour_start + 2) % 24
            else:
                weak_hour_start, weak_hour_end = 18, 20

            results.append({
                "alliance_id": row["enemy_id"],
                "alliance_name": names.get(row["enemy_id"], f"Alliance {row['enemy_id']}"),
                "losses_to_us": row["kills"],
                "weak_systems": systems,
                "weak_hours": [weak_hour_start, weak_hour_end]
            })

        return results
