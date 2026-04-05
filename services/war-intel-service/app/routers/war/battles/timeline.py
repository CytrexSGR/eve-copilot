import logging
from fastapi import APIRouter, HTTPException, Query
from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.services.intelligence.esi_utils import (
    batch_resolve_alliance_names,
    batch_resolve_character_names,
    batch_resolve_corporation_names,
)
from ..utils import detect_tactical_shifts

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/battle/{battle_id}/timeline")
@handle_endpoint_errors()
def get_battle_timeline(
    battle_id: int,
    bucket_size_seconds: int = Query(60, ge=10, le=300, description="Bucket size in seconds")
):
    """Get minute-by-minute battle timeline with tactical shift detection."""
    with db_cursor() as cur:
        cur.execute("""
            SELECT solar_system_id, started_at,
                   COALESCE(ended_at, last_kill_at) as end_time,
                   total_kills
            FROM battles WHERE battle_id = %s
        """, (battle_id,))
        battle = cur.fetchone()
        if not battle:
            raise HTTPException(status_code=404, detail="Battle not found")

        system_id = battle["solar_system_id"]
        started_at = battle["started_at"]
        end_time = battle["end_time"]
        total_kills = battle["total_kills"]

        if not started_at or not end_time:
            return {
                "battle_id": battle_id,
                "buckets": [],
                "tactical_shifts": [],
                "total_minutes": 0,
                "total_kills": total_kills
            }

        duration_seconds = (end_time - started_at).total_seconds()
        total_minutes = int(duration_seconds / 60) + 1

        cur.execute("""
            WITH battle_kills AS (
                SELECT
                    k.killmail_id,
                    k.killmail_time,
                    k.ship_type_id,
                    k.ship_value,
                    k.is_capital,
                    COALESCE(c."categoryName", 'Unknown') as ship_category,
                    EXTRACT(EPOCH FROM (k.killmail_time - %s)) / %s as bucket_idx
                FROM killmails k
                LEFT JOIN "invTypes" t ON t."typeID" = k.ship_type_id
                LEFT JOIN "invGroups" g ON g."groupID" = t."groupID"
                LEFT JOIN "invCategories" c ON c."categoryID" = g."categoryID"
                WHERE k.battle_id = %s
                ORDER BY k.killmail_time ASC
            )
            SELECT
                FLOOR(bucket_idx)::int as bucket,
                COUNT(*) as kills,
                SUM(ship_value) as isk_destroyed,
                COUNT(*) FILTER (WHERE is_capital) as capital_kills,
                ARRAY_AGG(DISTINCT ship_category) as categories,
                MAX(ship_value) as max_kill_value,
                BOOL_OR(is_capital) as has_capital
            FROM battle_kills
            GROUP BY FLOOR(bucket_idx)::int
            ORDER BY bucket
        """, (started_at, bucket_size_seconds, battle_id))

        raw_buckets = cur.fetchall()

    buckets = []
    capital_first_seen = None
    kill_rate_history = []

    for row in raw_buckets:
        bucket_idx = row["bucket"]
        kills = row["kills"]
        isk = row["isk_destroyed"]
        capital_kills = row["capital_kills"]
        categories = row["categories"]
        max_value = row["max_kill_value"]
        has_capital = row["has_capital"]

        bucket_minute = bucket_idx * (bucket_size_seconds // 60)
        ship_categories = list(set(c for c in categories if c)) if categories else []

        buckets.append({
            "minute": bucket_minute,
            "bucket_index": bucket_idx,
            "kills": kills,
            "isk_destroyed": int(isk) if isk else 0,
            "capital_kills": capital_kills,
            "ship_categories": ship_categories,
            "max_kill_value": int(max_value) if max_value else 0,
            "has_capital": has_capital
        })

        kill_rate_history.append(kills)
        if has_capital and capital_first_seen is None:
            capital_first_seen = bucket_minute

    tactical_shifts = detect_tactical_shifts(buckets, kill_rate_history)

    if capital_first_seen is not None:
        tactical_shifts.append({
            "minute": capital_first_seen,
            "type": "capital_entry",
            "description": "Capital ships entered the fight",
            "severity": "high"
        })

    tactical_shifts.sort(key=lambda x: x["minute"])

    return {
        "battle_id": battle_id,
        "system_id": system_id,
        "started_at": started_at.isoformat() + "Z",
        "ended_at": end_time.isoformat() + "Z",
        "buckets": buckets,
        "tactical_shifts": tactical_shifts,
        "total_minutes": total_minutes,
        "total_kills": total_kills,
        "bucket_size_seconds": bucket_size_seconds
    }


@router.get("/battle/{battle_id}/reshipments")
@handle_endpoint_errors()
def get_battle_reshipments(battle_id: int):
    """Get reshipment analysis for a battle - identifies pilots who died multiple times."""
    with db_cursor() as cur:
        cur.execute("SELECT battle_id FROM battles WHERE battle_id = %s", (battle_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Battle {battle_id} not found")

        cur.execute("""
            SELECT
                k.victim_character_id,
                k.victim_alliance_id,
                COUNT(*) as deaths,
                SUM(k.ship_value) as total_isk_lost,
                array_agg(t."typeName" ORDER BY k.killmail_time) as ships_lost
            FROM killmails k
            LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            WHERE k.battle_id = %s
              AND k.victim_character_id IS NOT NULL
            GROUP BY k.victim_character_id, k.victim_alliance_id
            HAVING COUNT(*) >= 2
            ORDER BY COUNT(*) DESC
            LIMIT 100
        """, (battle_id,))

        reshippers = [{
            "character_id": row["victim_character_id"],
            "character_name": None,
            "alliance_id": row["victim_alliance_id"],
            "alliance_name": None,
            "deaths": row["deaths"],
            "ships_lost": row["ships_lost"] or [],
            "total_isk_lost": float(row["total_isk_lost"]) if row["total_isk_lost"] else 0
        } for row in cur.fetchall()]

        cur.execute("""
            WITH pilot_deaths AS (
                SELECT victim_character_id, victim_alliance_id, victim_corporation_id, COUNT(*) as deaths
                FROM killmails
                WHERE battle_id = %s AND victim_character_id IS NOT NULL
                GROUP BY victim_character_id, victim_alliance_id, victim_corporation_id
            )
            SELECT
                victim_alliance_id,
                COUNT(*) FILTER (WHERE deaths >= 2) as reshippers,
                COUNT(*) FILTER (WHERE deaths = 1) as one_death,
                SUM(deaths) FILTER (WHERE deaths >= 2) as total_reship_deaths,
                AVG(deaths) FILTER (WHERE deaths >= 2) as avg_deaths,
                MAX(deaths) as max_deaths
            FROM pilot_deaths
            WHERE victim_alliance_id IS NOT NULL
            GROUP BY victim_alliance_id
            ORDER BY reshippers DESC
        """, (battle_id,))

        by_alliance = []
        alliance_ids = set()
        for row in cur.fetchall():
            reshippers_count = row["reshippers"] or 0
            one_death = row["one_death"] or 0
            total_pilots = reshippers_count + one_death
            ratio = (reshippers_count / total_pilots) if total_pilots > 0 else 0
            if row["victim_alliance_id"]:
                alliance_ids.add(row["victim_alliance_id"])
            by_alliance.append({
                "alliance_id": row["victim_alliance_id"],
                "alliance_name": None,
                "total_reshippers": reshippers_count,
                "total_deaths": int(row["total_reship_deaths"]) if row["total_reship_deaths"] else 0,
                "avg_deaths_per_resshipper": round(float(row["avg_deaths"]), 1) if row["avg_deaths"] else 0,
                "max_deaths": row["max_deaths"] or 0,
                "reship_ratio": round(ratio, 2),
                "corps": []
            })

        cur.execute("""
            WITH pilot_deaths AS (
                SELECT victim_character_id, victim_alliance_id, victim_corporation_id, COUNT(*) as deaths
                FROM killmails
                WHERE battle_id = %s AND victim_character_id IS NOT NULL
                GROUP BY victim_character_id, victim_alliance_id, victim_corporation_id
            )
            SELECT
                victim_alliance_id,
                victim_corporation_id,
                COUNT(*) FILTER (WHERE deaths >= 2) as reshippers,
                COUNT(*) FILTER (WHERE deaths = 1) as one_death,
                SUM(deaths) FILTER (WHERE deaths >= 2) as total_reship_deaths
            FROM pilot_deaths
            WHERE victim_alliance_id IS NOT NULL AND victim_corporation_id IS NOT NULL
            GROUP BY victim_alliance_id, victim_corporation_id
            HAVING COUNT(*) FILTER (WHERE deaths >= 2) > 0
            ORDER BY victim_alliance_id, reshippers DESC
        """, (battle_id,))

        corp_ids = set()
        corp_data_by_alliance = {}
        for row in cur.fetchall():
            alliance_id = row["victim_alliance_id"]
            corp_id = row["victim_corporation_id"]
            if corp_id:
                corp_ids.add(corp_id)
            if alliance_id not in corp_data_by_alliance:
                corp_data_by_alliance[alliance_id] = []
            reshippers_count = row["reshippers"] or 0
            one_death = row["one_death"] or 0
            total_pilots = reshippers_count + one_death
            ratio = (reshippers_count / total_pilots) if total_pilots > 0 else 0
            corp_data_by_alliance[alliance_id].append({
                "corp_id": corp_id,
                "corp_name": None,
                "reshippers": reshippers_count,
                "total_deaths": int(row["total_reship_deaths"]) if row["total_reship_deaths"] else 0,
                "reship_ratio": round(ratio, 2)
            })

        for alliance in by_alliance:
            alliance["corps"] = corp_data_by_alliance.get(alliance["alliance_id"], [])

        total_reshippers = len(reshippers)
        cur.execute("""
            SELECT COUNT(DISTINCT victim_character_id) as cnt
            FROM killmails WHERE battle_id = %s AND victim_character_id IS NOT NULL
        """, (battle_id,))
        total_pilots = cur.fetchone()["cnt"] or 0
        one_death_pilots = total_pilots - total_reshippers

        max_deaths = max((r["deaths"] for r in reshippers), default=0)
        avg_deaths = sum(r["deaths"] for r in reshippers) / total_reshippers if total_reshippers > 0 else 0

    alliance_names = batch_resolve_alliance_names(list(alliance_ids)) if alliance_ids else {}
    corp_names = batch_resolve_corporation_names(list(corp_ids)) if corp_ids else {}

    char_ids = [r["character_id"] for r in reshippers if r.get("character_id")]
    char_names = batch_resolve_character_names(char_ids) if char_ids else {}

    for r in reshippers:
        r["character_name"] = char_names.get(r["character_id"], f"Pilot {r['character_id']}")
        r["alliance_name"] = alliance_names.get(r["alliance_id"]) if r.get("alliance_id") else None

    for alliance in by_alliance:
        alliance["alliance_name"] = alliance_names.get(alliance["alliance_id"], f"Alliance {alliance['alliance_id']}")
        for corp in alliance.get("corps", []):
            corp["corp_name"] = corp_names.get(corp["corp_id"], f"Corp {corp['corp_id']}")

    return {
        "reshippers": reshippers,
        "by_alliance": by_alliance,
        "summary": {
            "total_reshippers": total_reshippers,
            "total_one_death_pilots": one_death_pilots,
            "overall_reship_ratio": round(total_reshippers / total_pilots, 2) if total_pilots > 0 else 0,
            "avg_deaths_per_resshipper": round(avg_deaths, 1),
            "max_deaths": max_deaths
        }
    }
