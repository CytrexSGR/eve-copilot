"""Battle strategic context endpoint - Sovereignty and campaign data."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.utils.cache import get_cached, set_cached

logger = logging.getLogger(__name__)
router = APIRouter()

CONTEXT_CACHE_TTL = 300  # 5 minutes


@router.get("/battle/{battle_id}/strategic-context")
@handle_endpoint_errors()
def get_strategic_context(battle_id: int) -> Dict[str, Any]:
    """Get strategic sovereignty context for a battle.

    Returns sov holder, active campaigns in system and constellation,
    and ADM data if available.
    """
    cache_key = f"battle-ctx:{battle_id}"
    cached = get_cached(cache_key, CONTEXT_CACHE_TTL)
    if cached:
        return cached

    with db_cursor() as cur:
        # Get battle system
        cur.execute("""
            SELECT b.solar_system_id, s."constellationID"
            FROM battles b
            JOIN "mapSolarSystems" s ON b.solar_system_id = s."solarSystemID"
            WHERE b.battle_id = %s
        """, (battle_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail=f"Battle {battle_id} not found")

        system_id = row["solar_system_id"]
        constellation_id = row["constellationID"]

        # Get sov holder
        cur.execute("""
            SELECT sov.alliance_id, anc.alliance_name
            FROM sovereignty_map_cache sov
            LEFT JOIN alliance_name_cache anc ON sov.alliance_id = anc.alliance_id
            WHERE sov.solar_system_id = %s
        """, (system_id,))
        sov_row = cur.fetchone()

        system_sov = None
        if sov_row and sov_row["alliance_id"]:
            system_sov = {
                "alliance_id": sov_row["alliance_id"],
                "alliance_name": sov_row["alliance_name"],
            }

        # Get active campaigns in this system
        cur.execute("""
            SELECT
                dc.solar_system_id,
                s."solarSystemName" as system_name,
                dc.structure_type,
                dc.defender_name,
                dc.score
            FROM dotlan_sov_campaigns dc
            JOIN "mapSolarSystems" s ON dc.solar_system_id = s."solarSystemID"
            WHERE dc.solar_system_id = %s
            ORDER BY dc.structure_type
        """, (system_id,))
        campaign_rows = cur.fetchall()

        # Get latest ADM for system
        cur.execute("""
            SELECT adm_level FROM dotlan_adm_history
            WHERE solar_system_id = %s
            ORDER BY timestamp DESC LIMIT 1
        """, (system_id,))
        adm_row = cur.fetchone()
        adm_value = float(adm_row["adm_level"]) if adm_row else None

        system_campaigns = [
            {
                "system_name": r["system_name"],
                "structure_type": r["structure_type"],
                "defender": r["defender_name"],
                "score": float(r["score"]) if r["score"] is not None else None,
                "adm": adm_value,
            }
            for r in campaign_rows
        ]

        # Count campaigns in same constellation (for broader context)
        cur.execute("""
            SELECT COUNT(*) as cnt
            FROM dotlan_sov_campaigns dc
            JOIN "mapSolarSystems" s ON dc.solar_system_id = s."solarSystemID"
            WHERE s."constellationID" = %s
            AND dc.solar_system_id != %s
        """, (constellation_id, system_id))
        constellation_extra = cur.fetchone()["cnt"]

    # Determine strategic note
    strategic_note = None
    if system_campaigns:
        types = [c["structure_type"] for c in system_campaigns]
        if "IHUB" in types:
            strategic_note = "Infrastructure Hub under attack"
        elif "TCU" in types:
            strategic_note = "Territorial Claim Unit contested"
        else:
            strategic_note = "Sovereignty structure contested"
    elif constellation_extra > 0:
        strategic_note = f"{constellation_extra} sovereignty campaigns in constellation"

    result = {
        "battle_id": battle_id,
        "system_sov": system_sov,
        "active_campaigns": system_campaigns,
        "constellation_campaigns": constellation_extra,
        "strategic_note": strategic_note,
    }

    set_cached(cache_key, result, CONTEXT_CACHE_TTL)
    return result
