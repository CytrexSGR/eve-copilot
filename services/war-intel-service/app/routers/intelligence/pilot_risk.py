"""Pilot Risk Intelligence — AWOX detection, performance assessment, fleet contribution."""

import logging
from fastapi import APIRouter, Query
from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.utils.cache import get_cached, set_cached

logger = logging.getLogger(__name__)
router = APIRouter()

CACHE_TTL = 600


@router.get("/pilot-risk/{corp_id}")
@handle_endpoint_errors()
def get_pilot_risk(
    corp_id: int,
    days: int = Query(90, ge=7, le=180),
):
    """Get pilot risk scores, performance categories, and fleet roles for a corporation."""
    cache_key = f"pilot-risk:{corp_id}:{days}"
    cached = get_cached(cache_key, CACHE_TTL)
    if cached:
        return cached

    with db_cursor() as cur:
        # AWOX flagged kills
        cur.execute("""
            SELECT
                ka.character_id,
                COUNT(*) AS awox_count
            FROM killmail_attackers ka
            JOIN killmails k ON k.killmail_id = ka.killmail_id
            WHERE ka.corporation_id = %s
              AND k.zkb_awox = true
              AND k.killmail_time >= NOW() - INTERVAL '1 day' * %s
            GROUP BY ka.character_id
        """, (corp_id, days))
        awox_pilots = {row["character_id"]: row["awox_count"] for row in cur.fetchall()}

        # Pilot performance (ISK efficiency + loss patterns)
        cur.execute("""
            WITH pilot_kills AS (
                SELECT
                    ka.character_id,
                    COUNT(DISTINCT ka.killmail_id) AS kills,
                    SUM(k.ship_value) AS isk_killed
                FROM killmail_attackers ka
                JOIN killmails k ON k.killmail_id = ka.killmail_id
                WHERE ka.corporation_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %s
                GROUP BY ka.character_id
            ),
            pilot_deaths AS (
                SELECT
                    k.victim_character_id AS character_id,
                    COUNT(*) AS deaths,
                    SUM(k.ship_value) AS isk_lost,
                    COUNT(*) FILTER (WHERE k.attacker_count <= 1) AS solo_deaths,
                    AVG(k.ship_value) AS avg_loss_value
                FROM killmails k
                WHERE k.victim_corporation_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %s
                  AND k.victim_character_id IS NOT NULL
                GROUP BY k.victim_character_id
            )
            SELECT
                COALESCE(pk.character_id, pd.character_id) AS character_id,
                COALESCE(pk.kills, 0) AS kills,
                COALESCE(pd.deaths, 0) AS deaths,
                COALESCE(pk.isk_killed, 0) AS isk_killed,
                COALESCE(pd.isk_lost, 0) AS isk_lost,
                COALESCE(pd.solo_deaths, 0) AS solo_deaths,
                COALESCE(pd.avg_loss_value, 0) AS avg_loss_value
            FROM pilot_kills pk
            FULL OUTER JOIN pilot_deaths pd ON pk.character_id = pd.character_id
            ORDER BY COALESCE(pd.isk_lost, 0) DESC
            LIMIT 200
        """, (corp_id, days, corp_id, days))
        pilot_stats = cur.fetchall()

    # Compute categories
    pilots = []
    at_risk = 0
    for pilot in pilot_stats:
        char_id = pilot["character_id"]
        isk_killed = float(pilot["isk_killed"] or 0)
        isk_lost = float(pilot["isk_lost"] or 0)
        total_isk = isk_killed + isk_lost
        efficiency = (isk_killed / total_isk * 100) if total_isk > 0 else 0

        # Performance category
        if efficiency < 20 and pilot["deaths"] > 10:
            category = "LIABILITY"
        elif efficiency < 40:
            category = "TRAINABLE"
        else:
            category = "NORMAL"

        awox_count = awox_pilots.get(char_id, 0)
        if awox_count > 0:
            at_risk += 1

        pilots.append({
            "character_id": char_id,
            "kills": pilot["kills"],
            "deaths": pilot["deaths"],
            "isk_killed": isk_killed,
            "isk_lost": isk_lost,
            "efficiency": round(efficiency, 1),
            "solo_deaths": pilot["solo_deaths"],
            "avg_loss_value": float(pilot["avg_loss_value"] or 0),
            "performance_category": category,
            "awox_count": awox_count,
        })

    result = {
        "corporation_id": corp_id,
        "days": days,
        "pilots": pilots,
        "summary": {
            "total_analyzed": len(pilots),
            "normal": sum(1 for p in pilots if p["performance_category"] == "NORMAL"),
            "trainable": sum(1 for p in pilots if p["performance_category"] == "TRAINABLE"),
            "liability": sum(1 for p in pilots if p["performance_category"] == "LIABILITY"),
            "at_risk_awox": at_risk,
        },
    }

    set_cached(cache_key, result, CACHE_TTL)
    return result


@router.get("/corp-health/{corp_id}")
@handle_endpoint_errors()
def get_corp_health(
    corp_id: int,
    days: int = Query(30, ge=7, le=90),
):
    """CEO dashboard — aggregate corporation health metrics."""
    cache_key = f"corp-health:{corp_id}:{days}"
    cached = get_cached(cache_key, CACHE_TTL)
    if cached:
        return cached

    with db_cursor() as cur:
        # Member count + activity
        cur.execute("""
            SELECT member_count, alliance_id
            FROM corporations
            WHERE corporation_id = %s
        """, (corp_id,))
        corp = cur.fetchone()
        member_count = corp["member_count"] if corp else 0

        # Active pilots
        cur.execute("""
            SELECT COUNT(DISTINCT character_id) AS active_pilots
            FROM (
                SELECT ka.character_id
                FROM killmail_attackers ka
                JOIN killmails k ON k.killmail_id = ka.killmail_id
                WHERE ka.corporation_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %s
                UNION
                SELECT k.victim_character_id
                FROM killmails k
                WHERE k.victim_corporation_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %s
                  AND k.victim_character_id IS NOT NULL
            ) active
        """, (corp_id, days, corp_id, days))
        active = cur.fetchone()

        # ISK efficiency
        cur.execute("""
            WITH kills AS (
                SELECT COALESCE(SUM(DISTINCT k.ship_value), 0) AS isk_killed
                FROM killmail_attackers ka
                JOIN killmails k ON k.killmail_id = ka.killmail_id
                WHERE ka.corporation_id = %s
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %s
            ),
            losses AS (
                SELECT COALESCE(SUM(ship_value), 0) AS isk_lost
                FROM killmails
                WHERE victim_corporation_id = %s
                  AND killmail_time >= NOW() - INTERVAL '1 day' * %s
            )
            SELECT kills.isk_killed, losses.isk_lost
            FROM kills, losses
        """, (corp_id, days, corp_id, days))
        isk = cur.fetchone()

        # Member count trend
        cur.execute("""
            SELECT snapshot_date, member_count
            FROM corporation_member_count_history
            WHERE corporation_id = %s
              AND snapshot_date >= CURRENT_DATE - INTERVAL '1 day' * %s
            ORDER BY snapshot_date
        """, (corp_id, days))
        member_trend = cur.fetchall()

    isk_killed = float(isk["isk_killed"] or 0)
    isk_lost = float(isk["isk_lost"] or 0)
    total_isk = isk_killed + isk_lost

    result = {
        "corporation_id": corp_id,
        "days": days,
        "member_count": member_count,
        "active_pilots": active["active_pilots"] if active else 0,
        "activity_rate": round(active["active_pilots"] / member_count * 100, 1) if member_count > 0 else 0,
        "isk_killed": isk_killed,
        "isk_lost": isk_lost,
        "isk_efficiency": round(isk_killed / total_isk * 100, 1) if total_isk > 0 else 0,
        "member_trend": [{"date": str(r["snapshot_date"]), "count": r["member_count"]} for r in member_trend],
    }

    set_cached(cache_key, result, CACHE_TTL)
    return result
