"""Economics & Production Endpoints."""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/fast/{alliance_id}/economics")
@handle_endpoint_errors()
def get_economics(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30)
) -> Dict[str, Any]:
    """Get economic analysis: ISK balance, cost per kill, efficiency trends."""
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

        isk_balance = isk_destroyed - isk_lost
        cost_per_kill = round(isk_lost / kills, 0) if kills > 0 else 0
        cost_per_death = round(isk_lost / deaths, 0) if deaths > 0 else 0

        return {
            "isk_destroyed": isk_destroyed,
            "isk_lost": isk_lost,
            "isk_balance": isk_balance,
            "cost_per_kill": cost_per_kill,
            "cost_per_death": cost_per_death,
            "profitable": isk_balance > 0
        }

@router.get("/fast/{alliance_id}/expensive-losses")
@handle_endpoint_errors()
def get_expensive_losses(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(5, ge=1, le=20)
) -> List[Dict[str, Any]]:
    """
    Get most expensive individual ship losses (OPTIMIZED - uses intelligence_hourly_stats).

    Phase 4: Migrated from killmails ORDER BY to pre-aggregated expensive_losses JSONB.
    Reduces query time from ~200ms to <50ms.
    """
    with db_cursor() as cur:
        # Aggregate expensive_losses from hourly_stats
        cur.execute("""
            WITH all_losses AS (
                SELECT
                    (loss->>'killmail_id')::BIGINT as killmail_id,
                    (loss->>'ship_type_id')::INT as ship_type_id,
                    (loss->>'ship_value')::BIGINT as ship_value,
                    (loss->>'system_id')::INT as system_id
                FROM intelligence_hourly_stats,
                LATERAL jsonb_array_elements(expensive_losses) AS loss
                WHERE alliance_id = %s
                  AND hour_bucket >= NOW() - make_interval(days => %s::INT)
                  AND expensive_losses != '[]'::jsonb
            )
            SELECT DISTINCT ON (al.killmail_id)
                al.killmail_id,
                al.ship_type_id,
                t."typeName" as ship_name,
                g."groupName" as ship_class,
                al.ship_value,
                k.killmail_time,
                s."solarSystemName" as system_name
            FROM all_losses al
            LEFT JOIN killmails k ON al.killmail_id = k.killmail_id
            LEFT JOIN "invTypes" t ON al.ship_type_id = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            LEFT JOIN "mapSolarSystems" s ON al.system_id = s."solarSystemID"
            ORDER BY al.killmail_id, al.ship_value DESC
            LIMIT %s
        """, (alliance_id, days, limit))

        # Sort by ship_value DESC in Python (DISTINCT ON prevents ORDER BY ship_value)
        results = [
            {
                "killmail_id": row["killmail_id"],
                "type_id": row["ship_type_id"],
                "ship_name": row.get("ship_name") or f"Unknown ({row['ship_type_id']})",
                "ship_class": row.get("ship_class") or "Unknown",
                "isk_lost": float(row["ship_value"] or 0),
                "time": row["killmail_time"].isoformat() + "Z" if row.get("killmail_time") else None,
                "system_name": row.get("system_name") or "Unknown"
            }
            for row in cur.fetchall()
        ]

        # Sort by ISK lost descending and limit
        results.sort(key=lambda x: x["isk_lost"], reverse=True)
        return results[:limit]

@router.get("/fast/{alliance_id}/production-needs")
@handle_endpoint_errors()
def get_production_needs(
    alliance_id: int,
    days: int = Query(7, ge=1, le=30),
    limit: int = Query(10, ge=1, le=20)
) -> List[Dict[str, Any]]:
    """Calculate production/replacement needs based on ship losses."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT
                k.ship_type_id,
                t."typeName" as ship_name,
                g."groupName" as ship_class,
                COUNT(*) as losses_period,
                COALESCE(SUM(k.ship_value), 0) as total_isk_lost,
                COALESCE(AVG(k.ship_value), 0) as avg_ship_value
            FROM killmails k
            LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            WHERE k.victim_alliance_id = %s
              AND k.killmail_time >= NOW() - INTERVAL '%s days'
              AND k.ship_type_id NOT IN (670, 33328)
            GROUP BY k.ship_type_id, t."typeName", g."groupName"
            HAVING COUNT(*) >= 3
            ORDER BY COUNT(*) DESC
            LIMIT %s
        """, (alliance_id, days, limit))

        results = []
        for row in cur.fetchall():
            losses = row["losses_period"] or 0
            losses_per_day = losses / days
            weekly_replacement = int(losses_per_day * 7)
            avg_value = float(row["avg_ship_value"] or 0)

            # Determine priority
            if losses_per_day >= 10:
                priority = "critical"
            elif losses_per_day >= 5:
                priority = "high"
            elif losses_per_day >= 2:
                priority = "medium"
            elif avg_value > 100_000_000:
                priority = "high"
            else:
                priority = "low"

            results.append({
                "ship_type_id": row["ship_type_id"],
                "ship_name": row.get("ship_name") or f"Unknown ({row['ship_type_id']})",
                "ship_class": row.get("ship_class") or "Unknown",
                "losses_period": losses,
                "losses_per_day": round(losses_per_day, 1),
                "weekly_replacement": weekly_replacement,
                "estimated_cost": int(weekly_replacement * avg_value),
                "priority": priority
            })

        return results
