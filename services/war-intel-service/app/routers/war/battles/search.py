"""Battle search endpoint — queries the full battle archive (200k+ battles)."""

import logging
from datetime import datetime
from typing import Dict, Any, List, Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Query

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

from ..models import BattleSummary, BattleAllianceInfo
from ..utils import calculate_intensity
from .helpers import fetch_and_cache_alliance_names

logger = logging.getLogger(__name__)

router = APIRouter()

# Minimum fight-together ratio to count as same powerbloc
POWERBLOC_MIN_FIGHTS = 10


def _resolve_powerbloc_alliances(leader_id: int) -> List[int]:
    """Resolve a powerbloc leader alliance ID to all member alliance IDs."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT alliance_b as ally_id FROM alliance_fight_together
            WHERE alliance_a = %s AND fights_together >= %s
            UNION
            SELECT alliance_a as ally_id FROM alliance_fight_together
            WHERE alliance_b = %s AND fights_together >= %s
        """, (leader_id, POWERBLOC_MIN_FIGHTS, leader_id, POWERBLOC_MIN_FIGHTS))
        rows = cur.fetchall()
    allies = [row["ally_id"] for row in rows]
    allies.append(leader_id)
    return allies


@router.get("/battles/search")
@handle_endpoint_errors()
def search_battles(
    background_tasks: BackgroundTasks,
    status: Literal["active", "ended", "all"] = Query("all", description="Battle status filter"),
    date_from: Optional[datetime] = Query(None, description="Start date (UTC)"),
    date_to: Optional[datetime] = Query(None, description="End date (UTC)"),
    system_name: Optional[str] = Query(None, description="Solar system name (case-insensitive, supports % wildcard)"),
    region_id: Optional[int] = Query(None, description="Region ID filter"),
    alliance_id: Optional[int] = Query(None, description="Alliance participation filter"),
    corporation_id: Optional[int] = Query(None, description="Corporation participation filter"),
    character_id: Optional[int] = Query(None, description="Character/player participation filter"),
    character_name: Optional[str] = Query(None, description="Character name (case-insensitive partial match)"),
    powerbloc_id: Optional[int] = Query(
        None, description="Powerbloc leader alliance ID — resolves to all member alliances"
    ),
    min_kills: int = Query(1, ge=1, description="Minimum kill count"),
    min_isk: Optional[int] = Query(None, description="Minimum ISK destroyed"),
    status_level: Optional[Literal["gank", "brawl", "battle", "hellcamp"]] = Query(
        None, description="Battle size classification"
    ),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> Dict[str, Any]:
    """Search the full battle archive with flexible filters."""
    where_conditions = ["b.total_kills >= %s"]
    params: List[Any] = [min_kills]

    if status != "all":
        where_conditions.append("b.status = %s")
        params.append(status)

    if date_from:
        where_conditions.append("b.started_at >= %s")
        params.append(date_from)

    if date_to:
        where_conditions.append("b.started_at <= %s")
        params.append(date_to)

    if system_name:
        pattern = system_name if "%" in system_name else f"%{system_name}%"
        where_conditions.append('s."solarSystemName" ILIKE %s')
        params.append(pattern)

    if region_id:
        where_conditions.append("b.region_id = %s")
        params.append(region_id)

    if min_isk:
        where_conditions.append("b.total_isk_destroyed >= %s")
        params.append(min_isk)

    if status_level:
        where_conditions.append("b.status_level = %s")
        params.append(status_level)

    # Powerbloc: resolve to alliance list, then filter like alliance
    effective_alliance_ids = None
    if powerbloc_id:
        effective_alliance_ids = _resolve_powerbloc_alliances(powerbloc_id)
        where_conditions.append("""
            EXISTS (
                SELECT 1 FROM killmails k
                WHERE k.battle_id = b.battle_id
                AND (k.final_blow_alliance_id = ANY(%s) OR k.victim_alliance_id = ANY(%s))
            )
        """)
        params.append(effective_alliance_ids)
        params.append(effective_alliance_ids)
    elif alliance_id:
        where_conditions.append("""
            EXISTS (
                SELECT 1 FROM killmails k
                WHERE k.battle_id = b.battle_id
                AND (k.final_blow_alliance_id = %s OR k.victim_alliance_id = %s)
            )
        """)
        params.append(alliance_id)
        params.append(alliance_id)

    if corporation_id:
        where_conditions.append("""
            EXISTS (
                SELECT 1 FROM killmails k
                WHERE k.battle_id = b.battle_id
                AND (k.final_blow_corporation_id = %s OR k.victim_corporation_id = %s)
            )
        """)
        params.append(corporation_id)
        params.append(corporation_id)

    if character_id:
        where_conditions.append("""
            EXISTS (
                SELECT 1 FROM killmails k
                WHERE k.battle_id = b.battle_id
                AND (k.final_blow_character_id = %s OR k.victim_character_id = %s)
            )
        """)
        params.append(character_id)
        params.append(character_id)

    if character_name:
        name_pattern = character_name if "%" in character_name else f"%{character_name}%"
        where_conditions.append("""
            EXISTS (
                SELECT 1 FROM killmails k
                WHERE k.battle_id = b.battle_id
                AND (k.victim_character_name ILIKE %s OR k.final_blow_character_name ILIKE %s)
            )
        """)
        params.append(name_pattern)
        params.append(name_pattern)

    where_sql = " AND ".join(where_conditions)

    with db_cursor() as cur:
        # Count total matches
        cur.execute(f"""
            SELECT COUNT(*) as total
            FROM battles b
            LEFT JOIN "mapSolarSystems" s ON b.solar_system_id = s."solarSystemID"
            WHERE {where_sql}
        """, params)
        total_count = cur.fetchone()["total"]

        # Fetch battles
        query_params = params + [limit, offset]
        cur.execute(f"""
            SELECT
                b.battle_id, b.solar_system_id, b.region_id,
                b.started_at, b.last_kill_at, b.ended_at,
                b.total_kills, b.total_isk_destroyed, b.status,
                b.status_level,
                b.last_milestone_notified, b.telegram_message_id,
                s."solarSystemName" as solar_system_name,
                s.security as security,
                s.x as x, s.z as z,
                r."regionName" as region_name,
                EXTRACT(EPOCH FROM (
                    COALESCE(b.ended_at, b.last_kill_at) - b.started_at
                )) / 60 as duration_minutes
            FROM battles b
            LEFT JOIN "mapSolarSystems" s ON b.solar_system_id = s."solarSystemID"
            LEFT JOIN "mapRegions" r ON b.region_id = r."regionID"
            WHERE {where_sql}
            ORDER BY b.started_at DESC
            LIMIT %s OFFSET %s
        """, query_params)
        rows = cur.fetchall()

        # Top alliances per battle
        battle_ids = [row["battle_id"] for row in rows]
        top_alliances_map: Dict[int, List[BattleAllianceInfo]] = {}

        if battle_ids:
            cur.execute("""
                SELECT
                    k.battle_id,
                    k.final_blow_alliance_id as alliance_id,
                    a.alliance_name,
                    COUNT(*) as kill_count
                FROM killmails k
                LEFT JOIN alliance_name_cache a
                    ON k.final_blow_alliance_id = a.alliance_id
                WHERE k.battle_id = ANY(%s)
                AND k.final_blow_alliance_id IS NOT NULL
                GROUP BY k.battle_id, k.final_blow_alliance_id, a.alliance_name
                ORDER BY k.battle_id, kill_count DESC
            """, (battle_ids,))
            alliance_rows = cur.fetchall()

            missing_alliance_ids = []
            for arow in alliance_rows:
                bid = arow["battle_id"]
                if bid not in top_alliances_map:
                    top_alliances_map[bid] = []
                if len(top_alliances_map[bid]) < 3:
                    top_alliances_map[bid].append(BattleAllianceInfo(
                        alliance_id=arow["alliance_id"],
                        alliance_name=arow.get("alliance_name"),
                        kill_count=arow["kill_count"]
                    ))
                    if not arow.get("alliance_name"):
                        missing_alliance_ids.append(arow["alliance_id"])

            if missing_alliance_ids:
                background_tasks.add_task(
                    fetch_and_cache_alliance_names, list(set(missing_alliance_ids))
                )

    battles = [BattleSummary(
        battle_id=row["battle_id"],
        solar_system_id=row["solar_system_id"],
        solar_system_name=row.get("solar_system_name"),
        region_id=row.get("region_id"),
        region_name=row.get("region_name"),
        started_at=row["started_at"],
        last_kill_at=row["last_kill_at"],
        ended_at=row.get("ended_at"),
        total_kills=row["total_kills"],
        total_isk_destroyed=float(row["total_isk_destroyed"] or 0),
        status=row["status"],
        status_level=row.get("status_level") or "gank",
        last_milestone=row.get("last_milestone_notified") or 0,
        system_id=row["solar_system_id"],
        system_name=row.get("solar_system_name"),
        security=float(row["security"]) if row.get("security") else 0.0,
        duration_minutes=int(row.get("duration_minutes") or 0),
        telegram_sent=row.get("telegram_message_id") is not None,
        intensity=calculate_intensity(row["total_kills"]),
        x=float(row["x"]) if row.get("x") else None,
        z=float(row["z"]) if row.get("z") else None,
        top_alliances=top_alliances_map.get(row["battle_id"])
    ) for row in rows]

    return {
        "battles": [b.model_dump(by_alias=True) for b in battles],
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
    }
