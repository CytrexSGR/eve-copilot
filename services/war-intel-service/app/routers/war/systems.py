"""
System intelligence endpoints for War Intel API.

Provides endpoints for solar system danger assessment and activity analysis.
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, Query

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from .models import SystemDanger, ActiveBattleInfo, KillmailSummary
from .utils import get_coalition_memberships

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/system/{system_id}/danger", response_model=SystemDanger)
@handle_endpoint_errors()
def get_system_danger(
    system_id: int,
    minutes: int = Query(1440, ge=10, le=10080, description="Timeframe in minutes (default 24h)")
):
    """Get danger assessment for a solar system with configurable timeframe."""
    with db_cursor() as cur:
        # Get system info (region, constellation, sov)
        cur.execute("""
            SELECT
                s."solarSystemName" as solar_system_name,
                s.security,
                c."constellationName" as constellation_name,
                r."regionName" as region_name,
                sov.alliance_id as sov_alliance_id,
                anc.alliance_name as sov_alliance_name
            FROM "mapSolarSystems" s
            JOIN "mapConstellations" c ON s."constellationID" = c."constellationID"
            JOIN "mapRegions" r ON s."regionID" = r."regionID"
            LEFT JOIN sovereignty_map_cache sov ON s."solarSystemID" = sov.solar_system_id
            LEFT JOIN alliance_name_cache anc ON sov.alliance_id = anc.alliance_id
            WHERE s."solarSystemID" = %s
        """, (system_id,))
        sys_info = cur.fetchone()

        # Get kills within timeframe
        cur.execute("""
            SELECT
                COUNT(*) as kills_total,
                COUNT(*) FILTER (WHERE killmail_time >= NOW() - INTERVAL '1 hour') as kills_1h,
                COUNT(*) FILTER (WHERE is_capital = true) as capital_kills,
                COALESCE(SUM(ship_value), 0) as isk_destroyed
            FROM killmails k
            WHERE k.solar_system_id = %s
            AND k.killmail_time >= NOW() - INTERVAL '%s minutes'
        """, (system_id, minutes))
        row = cur.fetchone()

        # Get active battles
        cur.execute("""
            SELECT battle_id, total_kills, total_isk_destroyed, started_at
            FROM battles
            WHERE solar_system_id = %s
            AND last_kill_at >= NOW() - INTERVAL '2 hours'
            ORDER BY total_kills DESC
            LIMIT 5
        """, (system_id,))
        battles_rows = cur.fetchall()

    active_battles = [
        ActiveBattleInfo(
            battle_id=b["battle_id"],
            total_kills=b["total_kills"],
            total_isk_destroyed=float(b["total_isk_destroyed"] or 0),
            started_at=str(b["started_at"]),
        )
        for b in battles_rows
    ]

    sys_name = sys_info.get("solar_system_name") if sys_info else None
    security = round((sys_info.get("security", 0) or 0), 1) if sys_info else None
    region_name = sys_info.get("region_name") if sys_info else None
    constellation_name = sys_info.get("constellation_name") if sys_info else None
    sov_alliance_id = sys_info.get("sov_alliance_id") if sys_info else None
    sov_alliance_name = sys_info.get("sov_alliance_name") if sys_info else None

    if not row or row["kills_total"] == 0:
        return SystemDanger(
            solar_system_id=system_id,
            solar_system_name=sys_name,
            region_name=region_name,
            constellation_name=constellation_name,
            security=security,
            sov_alliance_id=sov_alliance_id,
            sov_alliance_name=sov_alliance_name,
            danger_score=0.0,
            kills_1h=0,
            kills_24h=0,
            capital_kills=0,
            isk_destroyed_24h=0.0,
            gate_camp_risk=0.0,
            active_battles=active_battles,
        )

    kills_total = row["kills_total"]
    kills_1h = row["kills_1h"]
    capital_kills = row["capital_kills"]
    isk_destroyed = float(row["isk_destroyed"] or 0)

    # Simple danger scoring (scale based on timeframe)
    time_factor = 1440 / minutes  # normalize to 24h
    danger_score = min(100.0, (kills_total * time_factor * 2) + capital_kills * 10)
    gate_camp_risk = min(100.0, kills_1h * 20) if kills_1h > 2 else 0.0

    return SystemDanger(
        solar_system_id=system_id,
        solar_system_name=sys_name,
        region_name=region_name,
        constellation_name=constellation_name,
        security=security,
        sov_alliance_id=sov_alliance_id,
        sov_alliance_name=sov_alliance_name,
        danger_score=danger_score,
        kills_1h=kills_1h,
        kills_24h=kills_total,
        capital_kills=capital_kills,
        isk_destroyed_24h=isk_destroyed,
        gate_camp_risk=gate_camp_risk,
        active_battles=active_battles,
    )


@router.get("/system/{system_id}/kills", response_model=List[KillmailSummary])
@handle_endpoint_errors()
def get_system_kills(
    system_id: int,
    minutes: int = Query(1440, ge=10, le=10080, description="Timeframe in minutes"),
    limit: int = Query(100, ge=1, le=500)
):
    """Get recent kills in a solar system with pilot, corp, alliance and coalition info."""
    # Get coalition memberships for enrichment
    coalition_memberships = get_coalition_memberships()

    with db_cursor() as cur:
        cur.execute("""
            SELECT
                k.killmail_id, k.killmail_time, k.solar_system_id,
                k.ship_type_id, k.ship_value, k.attacker_count,
                k.victim_character_id, k.victim_corporation_id, k.victim_alliance_id,
                t."typeName" as ship_name,
                cn.character_name as victim_name,
                corp.corporation_name as victim_corporation_name,
                ally.alliance_name as victim_alliance_name
            FROM killmails k
            LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            LEFT JOIN character_name_cache cn ON k.victim_character_id = cn.character_id
            LEFT JOIN corp_name_cache corp ON k.victim_corporation_id = corp.corporation_id
            LEFT JOIN alliance_name_cache ally ON k.victim_alliance_id = ally.alliance_id
            WHERE k.solar_system_id = %s
            AND k.killmail_time >= NOW() - INTERVAL '%s minutes'
            ORDER BY k.killmail_time DESC
            LIMIT %s
        """, (system_id, minutes, limit))
        rows = cur.fetchall()

        # Get coalition leader names
        coalition_leader_ids = set(coalition_memberships.values())
        coalition_names = {}
        if coalition_leader_ids:
            cur.execute("""
                SELECT alliance_id, alliance_name
                FROM alliance_name_cache
                WHERE alliance_id = ANY(%s)
            """, (list(coalition_leader_ids),))
            for r in cur.fetchall():
                coalition_names[r["alliance_id"]] = r["alliance_name"]

    results = []
    for row in rows:
        alliance_id = row.get("victim_alliance_id")
        coalition_id = coalition_memberships.get(alliance_id) if alliance_id else None
        coalition_name = coalition_names.get(coalition_id) if coalition_id else None

        results.append(KillmailSummary(
            killmail_id=row["killmail_id"],
            killmail_time=row["killmail_time"],
            solar_system_id=row["solar_system_id"],
            ship_type_id=row["ship_type_id"],
            ship_name=row.get("ship_name"),
            victim_name=row.get("victim_name"),
            victim_corporation_id=row.get("victim_corporation_id"),
            victim_corporation_name=row.get("victim_corporation_name"),
            victim_alliance_id=alliance_id,
            victim_alliance_name=row.get("victim_alliance_name"),
            coalition_id=coalition_id,
            coalition_name=coalition_name,
            ship_value=float(row["ship_value"] or 0),
            attacker_count=row["attacker_count"]
        ))

    return results


@router.get("/system/{system_id}/ship-classes")
@handle_endpoint_errors()
def get_system_ship_classes(
    system_id: int,
    hours: int = Query(24, ge=1, le=168),
    group_by: str = Query("category", pattern="^(category|role|both)$")
):
    """Get ship class breakdown for kills in a system."""
    with db_cursor() as cur:
        if group_by == "category":
            cur.execute("""
                SELECT ship_category as key, COUNT(*) as count
                FROM killmails
                WHERE solar_system_id = %s
                AND killmail_time >= NOW() - INTERVAL '%s hours'
                AND ship_category IS NOT NULL
                GROUP BY ship_category
                ORDER BY count DESC
            """, (system_id, hours))
        elif group_by == "role":
            cur.execute("""
                SELECT ship_role as key, COUNT(*) as count
                FROM killmails
                WHERE solar_system_id = %s
                AND killmail_time >= NOW() - INTERVAL '%s hours'
                AND ship_role IS NOT NULL
                GROUP BY ship_role
                ORDER BY count DESC
            """, (system_id, hours))
        else:  # both
            cur.execute("""
                SELECT ship_category || ':' || ship_role as key, COUNT(*) as count
                FROM killmails
                WHERE solar_system_id = %s
                AND killmail_time >= NOW() - INTERVAL '%s hours'
                AND ship_category IS NOT NULL AND ship_role IS NOT NULL
                GROUP BY ship_category, ship_role
                ORDER BY count DESC
            """, (system_id, hours))

        rows = cur.fetchall()
        breakdown = {row["key"]: row["count"] for row in rows}
        total = sum(breakdown.values())

    return {
        "system_id": system_id,
        "hours": hours,
        "total_kills": total,
        "group_by": group_by,
        "breakdown": breakdown
    }
