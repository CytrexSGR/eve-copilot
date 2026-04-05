"""Threat Intelligence — who attacks us, with what, and how to counter."""

import logging
from typing import Dict, Any, List, Tuple

from fastapi import APIRouter, HTTPException, Query
from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.utils.cache import get_cached, set_cached

logger = logging.getLogger(__name__)
router = APIRouter()

CACHE_TTL = 300  # 5 minutes


def _build_threat_query(entity_type: str, entity_id: int, days: int) -> Tuple[str, tuple]:
    """Build SQL for threat composition based on entity type."""
    if entity_type == "alliance":
        victim_filter = "k.victim_alliance_id = %s"
        attacker_exclude = "ka.alliance_id != %s"
        params = (entity_id, entity_id, days)
    else:
        victim_filter = "k.victim_corporation_id = %s"
        attacker_exclude = "ka.corporation_id != %s"
        params = (entity_id, entity_id, days)

    sql = f"""
        WITH threat_attackers AS (
            SELECT
                ka.alliance_id AS attacker_alliance_id,
                ka.corporation_id AS attacker_corp_id,
                ka.ship_type_id,
                ka.weapon_type_id,
                ka.damage_done,
                k.killmail_id,
                k.ship_value AS victim_value
            FROM killmail_attackers ka
            JOIN killmails k ON k.killmail_id = ka.killmail_id
            WHERE {victim_filter}
              AND {attacker_exclude}
              AND ka.alliance_id IS NOT NULL
              AND k.killmail_time >= NOW() - INTERVAL '1 day' * %s
        )
        SELECT
            ta.attacker_alliance_id,
            COALESCE(a.alliance_name, 'Unknown') AS alliance_name,
            COUNT(DISTINCT ta.killmail_id) AS kills_on_us,
            SUM(ta.victim_value) AS isk_destroyed,
            COUNT(DISTINCT ta.ship_type_id) AS ship_diversity,
            json_agg(DISTINCT ta.ship_type_id) FILTER (WHERE ta.ship_type_id IS NOT NULL) AS ship_types_used
        FROM threat_attackers ta
        LEFT JOIN alliance_name_cache a ON a.alliance_id = ta.attacker_alliance_id
        GROUP BY ta.attacker_alliance_id, a.alliance_name
        ORDER BY kills_on_us DESC
        LIMIT 20
    """
    return sql, params


def _aggregate_damage_profile(weapons: List[Dict[str, Any]]) -> Dict[str, float]:
    """Weighted average of damage profiles from weapon data."""
    if not weapons:
        return {"em": 0, "thermal": 0, "kinetic": 0, "explosive": 0}

    total_weight = sum(w.get("count", 1) for w in weapons)
    if total_weight == 0:
        return {"em": 0, "thermal": 0, "kinetic": 0, "explosive": 0}

    em = sum(w.get("em_pct", 0) * w.get("count", 1) for w in weapons) / total_weight
    th = sum(w.get("thermal_pct", 0) * w.get("count", 1) for w in weapons) / total_weight
    kin = sum(w.get("kinetic_pct", 0) * w.get("count", 1) for w in weapons) / total_weight
    exp = sum(w.get("explosive_pct", 0) * w.get("count", 1) for w in weapons) / total_weight

    return {"em": em, "thermal": th, "kinetic": kin, "explosive": exp}


@router.get("/threats/{entity_type}/{entity_id}")
@handle_endpoint_errors()
def get_threat_composition(
    entity_type: str,
    entity_id: int,
    days: int = Query(30, ge=1, le=180),
):
    """Get threat composition — who attacks this entity and with what."""
    if entity_type not in ("alliance", "corporation"):
        raise HTTPException(status_code=400, detail="entity_type must be 'alliance' or 'corporation'")

    cache_key = f"threats:{entity_type}:{entity_id}:{days}"
    cached = get_cached(cache_key, CACHE_TTL)
    if cached:
        return cached

    sql, params = _build_threat_query(entity_type, entity_id, days)

    with db_cursor() as cur:
        cur.execute(sql, params)
        threats = cur.fetchall()

        # Fetch weapon damage profiles for top threats
        if threats:
            top_alliance_ids = [t["attacker_alliance_id"] for t in threats[:10]]
            placeholders = ",".join(["%s"] * len(top_alliance_ids))

            cur.execute(f"""
                SELECT
                    ka.alliance_id,
                    wdp.em_pct, wdp.thermal_pct, wdp.kinetic_pct, wdp.explosive_pct,
                    COUNT(*) AS count
                FROM killmail_attackers ka
                JOIN weapon_damage_profiles wdp ON wdp.type_id = ka.weapon_type_id
                JOIN killmails k ON k.killmail_id = ka.killmail_id
                WHERE ka.alliance_id IN ({placeholders})
                  AND k.killmail_time >= NOW() - INTERVAL '1 day' * %s
                GROUP BY ka.alliance_id, wdp.em_pct, wdp.thermal_pct, wdp.kinetic_pct, wdp.explosive_pct
            """, (*top_alliance_ids, days))
            weapon_rows = cur.fetchall()

            # Group weapons by alliance
            weapons_by_alliance = {}
            for row in weapon_rows:
                aid = row["alliance_id"]
                if aid not in weapons_by_alliance:
                    weapons_by_alliance[aid] = []
                weapons_by_alliance[aid].append(row)

            for threat in threats:
                aid = threat["attacker_alliance_id"]
                threat["damage_profile"] = _aggregate_damage_profile(
                    weapons_by_alliance.get(aid, [])
                )

        # Capital presence detection
        cur.execute("""
            SELECT DISTINCT ka.alliance_id, ka.ship_type_id, ig."groupName"
            FROM killmail_attackers ka
            JOIN killmails k ON k.killmail_id = ka.killmail_id
            JOIN "invTypes" it ON it."typeID" = ka.ship_type_id
            JOIN "invGroups" ig ON ig."groupID" = it."groupID"
            WHERE k.victim_alliance_id = %s
              AND ig."groupID" IN (30, 485, 547, 659, 883, 902, 1538)
              AND k.killmail_time >= NOW() - INTERVAL '1 day' * %s
        """, (entity_id, days))
        capital_sightings = cur.fetchall()

    result = {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "days": days,
        "threats": [dict(t) for t in threats],
        "capital_sightings": [dict(c) for c in capital_sightings],
        "total_threats": len(threats),
    }

    set_cached(cache_key, result, CACHE_TTL)
    return result
