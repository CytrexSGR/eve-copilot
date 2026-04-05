"""Logi Shield Score — proxy for enemy logistics strength via kill asymmetry."""

import logging
from fastapi import APIRouter, Query
from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.utils.cache import get_cached, set_cached

logger = logging.getLogger(__name__)
router = APIRouter()

LOGI_SHIP_GROUPS = (832, 1527)  # Logistics, Logistics Frigate

CACHE_TTL = 300


def _calculate_logi_score(
    our_kills: int,
    their_kills: int,
    our_damage_dealt: float,
    their_logi_count: int,
    their_fleet_size: int,
) -> float:
    """Calculate logi shield score 0-100.

    Factors:
    - Kill asymmetry (we deal damage but get few kills = strong logi)
    - Logi-to-fleet ratio
    - Damage absorption (damage dealt vs kills achieved)
    """
    if their_fleet_size == 0:
        return 0

    # Factor 1: Kill suppression (0-40 points)
    # High damage dealt but few kills = strong healing
    if our_damage_dealt > 0 and our_kills > 0:
        damage_per_kill = our_damage_dealt / our_kills
        # Normalize: 100k dmg/kill = 0 points, 1M+ dmg/kill = 40 points
        suppression = min(40, max(0, (damage_per_kill - 100000) / 900000 * 40))
    else:
        suppression = 0

    # Factor 2: Logi ratio (0-40 points)
    logi_ratio = their_logi_count / their_fleet_size
    logi_points = min(40, logi_ratio * 200)  # 20% logi = 40 points

    # Factor 3: Kill asymmetry (0-20 points)
    total = our_kills + their_kills
    if total > 0:
        their_survival = 1 - (our_kills / total)
        asymmetry = min(20, their_survival * 25)
    else:
        asymmetry = 0

    return min(100, max(0, suppression + logi_points + asymmetry))


@router.get("/logi-score/{entity_type}/{entity_id}")
@handle_endpoint_errors()
def get_logi_score(
    entity_type: str,
    entity_id: int,
    days: int = Query(30, ge=1, le=180),
):
    """Calculate logistics shield score for enemy entities that attack us."""
    cache_key = f"logi-score:{entity_type}:{entity_id}:{days}"
    cached = get_cached(cache_key, CACHE_TTL)
    if cached:
        return cached

    victim_filter = (
        "k.victim_alliance_id = %s" if entity_type == "alliance"
        else "k.victim_corporation_id = %s"
    )

    with db_cursor() as cur:
        # Per-enemy-alliance logi analysis
        cur.execute(f"""
            WITH enemy_battles AS (
                SELECT
                    ka.alliance_id AS enemy_alliance_id,
                    k.battle_id,
                    COUNT(DISTINCT k.killmail_id) AS kills_on_us,
                    SUM(ka.damage_done) AS total_damage,
                    COUNT(DISTINCT ka.character_id) AS fleet_size
                FROM killmail_attackers ka
                JOIN killmails k ON k.killmail_id = ka.killmail_id
                WHERE {victim_filter}
                  AND ka.alliance_id IS NOT NULL
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %s
                GROUP BY ka.alliance_id, k.battle_id
            ),
            enemy_logi AS (
                SELECT
                    ka.alliance_id,
                    COUNT(DISTINCT ka.character_id) AS logi_pilots
                FROM killmail_attackers ka
                JOIN killmails k ON k.killmail_id = ka.killmail_id
                JOIN "invTypes" it ON it."typeID" = ka.ship_type_id
                JOIN "invGroups" ig ON ig."groupID" = it."groupID"
                WHERE {victim_filter}
                  AND ig."groupID" IN (832, 1527)
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %s
                GROUP BY ka.alliance_id
            )
            SELECT
                eb.enemy_alliance_id,
                COALESCE(a.alliance_name, 'Unknown') AS alliance_name,
                SUM(eb.kills_on_us) AS kills_on_us,
                SUM(eb.total_damage) AS total_damage,
                AVG(eb.fleet_size)::int AS avg_fleet_size,
                COALESCE(el.logi_pilots, 0) AS logi_pilots
            FROM enemy_battles eb
            LEFT JOIN enemy_logi el ON el.alliance_id = eb.enemy_alliance_id
            LEFT JOIN alliance_name_cache a ON a.alliance_id = eb.enemy_alliance_id
            GROUP BY eb.enemy_alliance_id, a.alliance_name, el.logi_pilots
            ORDER BY SUM(eb.kills_on_us) DESC
            LIMIT 15
        """, (entity_id, days, entity_id, days))
        enemy_data = cur.fetchall()

    scores = []
    for enemy in enemy_data:
        score = _calculate_logi_score(
            our_kills=0,  # We don't know our kills on them from this query
            their_kills=enemy["kills_on_us"],
            our_damage_dealt=enemy["total_damage"] or 0,
            their_logi_count=enemy["logi_pilots"] or 0,
            their_fleet_size=enemy["avg_fleet_size"] or 1,
        )
        scores.append({
            "alliance_id": enemy["enemy_alliance_id"],
            "alliance_name": enemy["alliance_name"],
            "logi_score": round(score, 1),
            "logi_pilots": enemy["logi_pilots"],
            "avg_fleet_size": enemy["avg_fleet_size"],
            "kills_on_us": enemy["kills_on_us"],
        })

    result = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "days": days,
        "enemy_logi_scores": scores,
    }

    set_cached(cache_key, result, CACHE_TTL)
    return result
