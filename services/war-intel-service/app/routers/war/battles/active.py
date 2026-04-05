"""Active battles and single battle detail endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors

from ..models import BattleSummary, ActiveBattlesResponse, BattleAllianceInfo
from ..utils import calculate_intensity
from .helpers import fetch_and_cache_alliance_names

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/battles/active", response_model=ActiveBattlesResponse)
@handle_endpoint_errors()
def get_active_battles(
    background_tasks: BackgroundTasks,
    limit: int = Query(100, ge=1, le=1000, description="Maximum battles to return"),
    min_kills: int = Query(1, ge=1, description="Minimum kills for battle"),
    minutes: int = Query(None, ge=1, le=1440, description="Filter by activity in last N minutes")
):
    """Get battles. Without minutes: only active. With minutes: all battles with recent activity."""
    with db_cursor() as cur:
        # Build WHERE clause
        where_conditions = ["b.total_kills >= %s"]
        params = [min_kills]

        # Always filter for active battles only (ended battles should not appear on live map)
        where_conditions.append("b.status = 'active'")

        if minutes:
            # With time filter: show active battles with activity in that window
            where_conditions.append("b.last_kill_at >= NOW() - INTERVAL '%s minutes'")
            params.append(minutes)

        params.append(limit)

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
                EXTRACT(EPOCH FROM (b.last_kill_at - b.started_at)) / 60 as duration_minutes
            FROM battles b
            LEFT JOIN "mapSolarSystems" s ON b.solar_system_id = s."solarSystemID"
            LEFT JOIN "mapRegions" r ON b.region_id = r."regionID"
            WHERE {" AND ".join(where_conditions)}
            ORDER BY b.last_kill_at DESC
            LIMIT %s
        """, params)
        rows = cur.fetchall()

        # Get top alliances for all battles in one query
        battle_ids = [row["battle_id"] for row in rows]
        top_alliances_map = {}

        if battle_ids:
            cur.execute("""
                SELECT
                    k.battle_id,
                    k.final_blow_alliance_id as alliance_id,
                    a.alliance_name,
                    COUNT(*) as kill_count
                FROM killmails k
                LEFT JOIN alliance_name_cache a ON k.final_blow_alliance_id = a.alliance_id
                WHERE k.battle_id = ANY(%s)
                AND k.final_blow_alliance_id IS NOT NULL
                GROUP BY k.battle_id, k.final_blow_alliance_id, a.alliance_name
                ORDER BY k.battle_id, kill_count DESC
            """, (battle_ids,))
            alliance_rows = cur.fetchall()

            # Collect missing alliance IDs for background fetching
            missing_alliance_ids = []

            for arow in alliance_rows:
                bid = arow["battle_id"]
                if bid not in top_alliances_map:
                    top_alliances_map[bid] = []
                # Only keep top 3 alliances per battle
                if len(top_alliances_map[bid]) < 3:
                    top_alliances_map[bid].append(BattleAllianceInfo(
                        alliance_id=arow["alliance_id"],
                        alliance_name=arow.get("alliance_name"),
                        kill_count=arow["kill_count"]
                    ))
                    # Track missing names
                    if not arow.get("alliance_name"):
                        missing_alliance_ids.append(arow["alliance_id"])

            # Trigger background fetch for missing alliance names
            if missing_alliance_ids:
                unique_missing = list(set(missing_alliance_ids))
                background_tasks.add_task(fetch_and_cache_alliance_names, unique_missing)

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
        # Ectmap compatibility fields
        system_id=row["solar_system_id"],
        system_name=row.get("solar_system_name"),
        security=row.get("security"),
        duration_minutes=int(row.get("duration_minutes") or 0),
        telegram_sent=row.get("telegram_message_id") is not None,
        intensity=calculate_intensity(row["total_kills"]),
        x=row.get("x"),
        z=row.get("z"),
        top_alliances=top_alliances_map.get(row["battle_id"])
    ) for row in rows]

    return ActiveBattlesResponse(battles=battles, total_active=len(battles))


@router.get("/battle/{battle_id}")
@handle_endpoint_errors()
def get_battle(battle_id: int, background_tasks: BackgroundTasks):
    """Get a single battle by ID (regardless of status)."""
    with db_cursor() as cur:
        cur.execute("""
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
                EXTRACT(EPOCH FROM (COALESCE(b.ended_at, b.last_kill_at) - b.started_at)) / 60 as duration_minutes
            FROM battles b
            LEFT JOIN "mapSolarSystems" s ON b.solar_system_id = s."solarSystemID"
            LEFT JOIN "mapRegions" r ON b.region_id = r."regionID"
            WHERE b.battle_id = %s
        """, (battle_id,))
        row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail=f"Battle {battle_id} not found")

        # Get top alliances for this battle
        cur.execute("""
            SELECT
                k.final_blow_alliance_id as alliance_id,
                a.alliance_name,
                COUNT(*) as kill_count
            FROM killmails k
            LEFT JOIN alliance_name_cache a ON k.final_blow_alliance_id = a.alliance_id
            WHERE k.battle_id = %s
            AND k.final_blow_alliance_id IS NOT NULL
            GROUP BY k.final_blow_alliance_id, a.alliance_name
            ORDER BY kill_count DESC
            LIMIT 3
        """, (battle_id,))
        alliance_rows = cur.fetchall()

        # Collect missing alliance IDs for background fetching
        missing_alliance_ids = [
            arow["alliance_id"]
            for arow in alliance_rows
            if not arow.get("alliance_name")
        ]
        if missing_alliance_ids:
            background_tasks.add_task(fetch_and_cache_alliance_names, missing_alliance_ids)

        top_alliances = [
            BattleAllianceInfo(
                alliance_id=arow["alliance_id"],
                alliance_name=arow.get("alliance_name"),
                kill_count=arow["kill_count"]
            )
            for arow in alliance_rows
        ]

        return BattleSummary(
            battle_id=row["battle_id"],
            solar_system_id=row["solar_system_id"],
            solar_system_name=row["solar_system_name"],
            region_id=row["region_id"],
            region_name=row["region_name"],
            started_at=row["started_at"],
            last_kill_at=row["last_kill_at"],
            ended_at=row["ended_at"],
            total_kills=row["total_kills"],
            total_isk_destroyed=float(row["total_isk_destroyed"] or 0),
            status=row["status"],
            status_level=row.get("status_level") or "gank",
            last_milestone=row["last_milestone_notified"],
            system_id=row["solar_system_id"],
            system_name=row["solar_system_name"],
            security=float(row["security"]) if row["security"] else 0.0,
            duration_minutes=int(row["duration_minutes"] or 0),
            telegram_sent=row["telegram_message_id"] is not None,
            intensity=calculate_intensity(row["total_kills"]),
            x=float(row["x"]) if row["x"] else None,
            z=float(row["z"]) if row["z"] else None,
            top_alliances=top_alliances
        )
