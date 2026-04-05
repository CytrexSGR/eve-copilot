"""
Top killers and expensive kills endpoints for news reporting.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/top-killers")
@handle_endpoint_errors()
def get_top_killers(
    minutes: int = Query(1440, ge=10, le=10080),
    limit: int = Query(20, ge=1, le=100),
    region_id: Optional[int] = Query(None),
):
    """Get top killers universe-wide by kill count and ISK destroyed."""
    with db_cursor() as cur:
        region_filter = "AND k.region_id = %s" if region_id else ""
        params = [minutes]
        if region_id:
            params.append(region_id)

        cur.execute(f"""
            WITH attacker_stats AS (
                SELECT
                    a.character_id,
                    a.character_name,
                    a.corporation_id,
                    a.alliance_id,
                    COUNT(DISTINCT a.killmail_id) as kills,
                    COALESCE(SUM(k.ship_value), 0) as isk_destroyed,
                    COUNT(DISTINCT a.killmail_id) FILTER (
                        WHERE a.is_final_blow = true
                    ) as final_blows,
                    COUNT(DISTINCT a.killmail_id) FILTER (
                        WHERE k.is_capital = true
                    ) as capital_kills,
                    MAX(k.killmail_time) as last_kill_at
                FROM killmail_attackers a
                JOIN killmails k ON a.killmail_id = k.killmail_id
                WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
                AND a.character_id IS NOT NULL
                AND a.character_id > 0
                {region_filter}
                GROUP BY a.character_id, a.character_name,
                         a.corporation_id, a.alliance_id
                ORDER BY kills DESC, isk_destroyed DESC
                LIMIT 200
            )
            SELECT
                s.character_id,
                s.character_name,
                s.corporation_id,
                s.alliance_id,
                anc.alliance_name,
                anc.ticker as alliance_ticker,
                s.kills,
                s.final_blows,
                s.capital_kills,
                s.isk_destroyed,
                s.last_kill_at
            FROM attacker_stats s
            LEFT JOIN alliance_name_cache anc ON s.alliance_id = anc.alliance_id
            ORDER BY s.kills DESC, s.isk_destroyed DESC
            LIMIT %s
        """, params + [limit])
        rows = cur.fetchall()

    result_killers = []
    for row in rows:
        result_killers.append({
            "character_id": row["character_id"],
            "character_name": row.get("character_name"),
            "corporation_id": row.get("corporation_id"),
            "alliance_id": row.get("alliance_id"),
            "alliance_name": row.get("alliance_name"),
            "alliance_ticker": row.get("alliance_ticker"),
            "kills": row["kills"],
            "final_blows": row["final_blows"],
            "capital_kills": row["capital_kills"],
            "isk_destroyed": float(row["isk_destroyed"]),
            "last_kill_at": row["last_kill_at"].isoformat() if row.get("last_kill_at") else None,
        })

    return {
        "minutes": minutes,
        "region_id": region_id,
        "killers": result_killers,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/expensive-kills")
@handle_endpoint_errors()
def get_expensive_kills(
    minutes: int = Query(1440, ge=10, le=10080),
    limit: int = Query(10, ge=1, le=50),
    min_value: Optional[float] = Query(None, description="Minimum ISK value filter"),
):
    """Get most expensive kills in the given time window."""
    with db_cursor() as cur:
        value_filter = "AND k.ship_value >= %s" if min_value else ""
        params = [minutes]
        if min_value:
            params.append(min_value)
        params.append(limit)

        cur.execute(f"""
            SELECT
                k.killmail_id,
                k.killmail_time,
                k.solar_system_id,
                ss."solarSystemName" as system_name,
                r."regionName" as region_name,
                ss.security as security_status,
                k.ship_type_id,
                t."typeName" as ship_name,
                g."groupName" as ship_class,
                k.ship_value as total_value,
                k.victim_character_id,
                k.victim_character_name,
                k.victim_corporation_id,
                k.victim_alliance_id,
                vanc.alliance_name as victim_alliance_name,
                vanc.ticker as victim_alliance_ticker,
                k.is_capital,
                k.attacker_count,
                k.final_blow_character_name,
                fanc.alliance_name as final_blow_alliance_name
            FROM killmails k
            JOIN "mapSolarSystems" ss ON k.solar_system_id = ss."solarSystemID"
            JOIN "mapRegions" r ON ss."regionID" = r."regionID"
            LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            LEFT JOIN "invGroups" g ON t."groupID" = g."groupID"
            LEFT JOIN alliance_name_cache vanc ON k.victim_alliance_id = vanc.alliance_id
            LEFT JOIN alliance_name_cache fanc ON k.final_blow_alliance_id = fanc.alliance_id
            WHERE k.killmail_time >= NOW() - INTERVAL '%s minutes'
            AND k.ship_value > 0
            {value_filter}
            ORDER BY k.ship_value DESC
            LIMIT %s
        """, params)
        rows = cur.fetchall()

    result_kills = []
    for row in rows:
        result_kills.append({
            "killmail_id": row["killmail_id"],
            "killmail_time": row["killmail_time"].isoformat() if row.get("killmail_time") else None,
            "system_name": row.get("system_name"),
            "region_name": row.get("region_name"),
            "security_status": round(float(row["security_status"]), 2) if row.get("security_status") else 0.0,
            "ship_name": row.get("ship_name"),
            "ship_class": row.get("ship_class"),
            "total_value": float(row["total_value"]),
            "is_capital": row.get("is_capital", False),
            "victim_name": row.get("victim_character_name"),
            "victim_alliance": row.get("victim_alliance_name"),
            "victim_alliance_ticker": row.get("victim_alliance_ticker"),
            "final_blow_name": row.get("final_blow_character_name"),
            "final_blow_alliance": row.get("final_blow_alliance_name"),
            "attacker_count": row.get("attacker_count"),
        })

    return {
        "minutes": minutes,
        "kills": result_kills,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
