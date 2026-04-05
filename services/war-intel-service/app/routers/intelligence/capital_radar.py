"""Capital Escalation Radar — detect invisible capital presence from weapon signatures."""

import logging
from fastapi import APIRouter, Query
from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.utils.cache import get_cached, set_cached

logger = logging.getLogger(__name__)
router = APIRouter()

CACHE_TTL = 300


@router.get("/capital-radar/{entity_type}/{entity_id}")
@handle_endpoint_errors()
def get_capital_radar(
    entity_type: str,
    entity_id: int,
    days: int = Query(30, ge=1, le=180),
):
    """Detect capital ship presence from killmail attacker data."""
    cache_key = f"cap-radar:{entity_type}:{entity_id}:{days}"
    cached = get_cached(cache_key, CACHE_TTL)
    if cached:
        return cached

    victim_filter = (
        "k.victim_alliance_id = %s" if entity_type == "alliance"
        else "k.victim_corporation_id = %s"
    )

    with db_cursor() as cur:
        # Systems where capitals appeared attacking us
        cur.execute(f"""
            SELECT
                k.solar_system_id,
                COALESCE(ss."solarSystemName", k.solar_system_id::text) AS system_name,
                ka.alliance_id AS capital_alliance_id,
                COALESCE(a.alliance_name, 'Unknown') AS alliance_name,
                ig."groupName" AS capital_class,
                COUNT(DISTINCT k.killmail_id) AS appearances,
                MIN(k.killmail_time) AS first_seen,
                MAX(k.killmail_time) AS last_seen
            FROM killmail_attackers ka
            JOIN killmails k ON k.killmail_id = ka.killmail_id
            JOIN "invTypes" it ON it."typeID" = ka.ship_type_id
            JOIN "invGroups" ig ON ig."groupID" = it."groupID"
            LEFT JOIN "mapSolarSystems" ss ON ss."solarSystemID" = k.solar_system_id
            LEFT JOIN alliance_name_cache a ON a.alliance_id = ka.alliance_id
            WHERE {victim_filter}
              AND ig."groupID" IN (30, 485, 547, 659, 883, 902, 1538)
              AND k.killmail_time >= NOW() - INTERVAL '1 day' * %s
            GROUP BY k.solar_system_id, ss."solarSystemName",
                     ka.alliance_id, a.alliance_name, ig."groupName"
            ORDER BY appearances DESC
        """, (entity_id, days))
        capital_systems = cur.fetchall()

        # Escalation timeline — time from first subcap kill to capital arrival in same battle
        cur.execute(f"""
            WITH battle_caps AS (
                SELECT
                    k.battle_id,
                    MIN(k.killmail_time) FILTER (
                        WHERE ig."groupID" NOT IN (30, 485, 547, 659, 883, 902, 1538)
                    ) AS first_subcap_kill,
                    MIN(k.killmail_time) FILTER (
                        WHERE ig."groupID" IN (30, 485, 547, 659, 883, 902, 1538)
                    ) AS first_capital_kill
                FROM killmail_attackers ka
                JOIN killmails k ON k.killmail_id = ka.killmail_id
                JOIN "invTypes" it ON it."typeID" = ka.ship_type_id
                JOIN "invGroups" ig ON ig."groupID" = it."groupID"
                WHERE {victim_filter}
                  AND k.battle_id IS NOT NULL
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %s
                GROUP BY k.battle_id
                HAVING MIN(k.killmail_time) FILTER (
                    WHERE ig."groupID" IN (30, 485, 547, 659, 883, 902, 1538)
                ) IS NOT NULL
            )
            SELECT
                AVG(EXTRACT(EPOCH FROM (first_capital_kill - first_subcap_kill))) AS avg_escalation_seconds,
                MIN(EXTRACT(EPOCH FROM (first_capital_kill - first_subcap_kill))) AS min_escalation_seconds,
                COUNT(*) AS escalation_count
            FROM battle_caps
            WHERE first_subcap_kill IS NOT NULL
              AND first_capital_kill > first_subcap_kill
        """, (entity_id, days))
        escalation = cur.fetchone()

    result = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "days": days,
        "capital_systems": [dict(r) for r in capital_systems],
        "escalation_stats": dict(escalation) if escalation else {},
        "total_capital_systems": len(set(r["solar_system_id"] for r in capital_systems)),
    }

    set_cached(cache_key, result, CACHE_TTL)
    return result
