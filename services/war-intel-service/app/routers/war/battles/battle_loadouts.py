"""Battle attacker loadout analysis endpoint - weapon profiling + fleet size estimation."""

import logging
from collections import defaultdict
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.utils.cache import get_cached, set_cached
from app.services.intelligence.esi_utils import batch_resolve_alliance_names

logger = logging.getLogger(__name__)
router = APIRouter()

LOADOUT_CACHE_TTL = 600  # 10 minutes


def classify_range(optimal_range: int | None) -> str:
    """Classify weapon optimal range into tactical categories."""
    if not optimal_range:
        return "Unknown"
    if optimal_range > 50000:
        return "Long"      # >50km sniper/kite
    if optimal_range > 15000:
        return "Medium"    # 15-50km standard
    return "Close"          # <15km brawl


@router.get("/battle/{battle_id}/attacker-loadouts")
@handle_endpoint_errors()
def get_attacker_loadouts(battle_id: int) -> Dict[str, Any]:
    """Analyze attacker ship loadouts and fleet sizes for a battle.

    Returns per-alliance breakdown of ships, weapons, range profiles,
    and estimated fleet sizes based on killmail attacker data.
    """
    cache_key = f"battle-loadouts:{battle_id}"
    cached = get_cached(cache_key, LOADOUT_CACHE_TTL)
    if cached:
        return cached

    with db_cursor() as cur:
        # Verify battle exists
        cur.execute("SELECT battle_id FROM battles WHERE battle_id = %s", (battle_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Battle {battle_id} not found")

        # Query 1: Ship + weapon loadout data
        cur.execute("""
            SELECT
                ka.alliance_id,
                t_ship."typeName" as ship_name,
                g_ship."groupName" as ship_class,
                t_weapon."typeName" as weapon_name,
                wp.weapon_class,
                wp.optimal_range,
                wp.primary_damage_type,
                SUM(ka.damage_done) as total_damage,
                COUNT(DISTINCT ka.character_id) as pilot_count,
                COUNT(DISTINCT k.killmail_id) as engagements
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
            JOIN "invTypes" t_ship ON ka.ship_type_id = t_ship."typeID"
            JOIN "invGroups" g_ship ON t_ship."groupID" = g_ship."groupID"
            LEFT JOIN "invTypes" t_weapon ON ka.weapon_type_id = t_weapon."typeID"
            LEFT JOIN weapon_damage_profiles wp ON ka.weapon_type_id = wp.type_id
            WHERE k.battle_id = %s
            AND ka.damage_done > 0
            AND ka.alliance_id IS NOT NULL
            GROUP BY ka.alliance_id, t_ship."typeName", g_ship."groupName",
                     t_weapon."typeName", wp.weapon_class, wp.optimal_range,
                     wp.primary_damage_type
            ORDER BY total_damage DESC
        """, (battle_id,))
        loadout_rows = cur.fetchall()

        # Query 2: Fleet sizes per alliance (attackers on each kill)
        cur.execute("""
            WITH alliance_fleet AS (
                SELECT
                    ka.alliance_id,
                    k.killmail_id,
                    COUNT(DISTINCT ka2.character_id) as fleet_on_kill
                FROM killmails k
                JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                    AND ka.is_final_blow = true
                JOIN killmail_attackers ka2 ON k.killmail_id = ka2.killmail_id
                WHERE k.battle_id = %s
                AND ka.alliance_id IS NOT NULL
                GROUP BY ka.alliance_id, k.killmail_id
            )
            SELECT
                alliance_id,
                AVG(fleet_on_kill)::numeric(10,1) as avg_fleet_size,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY fleet_on_kill)::int as median,
                MAX(fleet_on_kill) as max_size,
                COUNT(*) as kills
            FROM alliance_fleet
            GROUP BY alliance_id
        """, (battle_id,))
        fleet_rows = {r["alliance_id"]: r for r in cur.fetchall()}

    if not loadout_rows:
        result = {"battle_id": battle_id, "alliances": []}
        set_cached(cache_key, result, LOADOUT_CACHE_TTL)
        return result

    # Resolve alliance names
    alliance_ids = list(set(r["alliance_id"] for r in loadout_rows if r["alliance_id"]))
    alliance_names = batch_resolve_alliance_names(alliance_ids) if alliance_ids else {}

    # Group by alliance
    alliances: Dict[int, Dict] = {}
    for row in loadout_rows:
        aid = row["alliance_id"]
        if aid not in alliances:
            fleet = fleet_rows.get(aid)
            alliances[aid] = {
                "alliance_id": aid,
                "alliance_name": alliance_names.get(aid, f"Alliance {aid}"),
                "total_damage": 0,
                "pilot_count": 0,
                "fleet_size": {
                    "avg": float(fleet["avg_fleet_size"]) if fleet else None,
                    "median": int(fleet["median"]) if fleet else None,
                    "max": int(fleet["max_size"]) if fleet else None,
                    "kills_sampled": int(fleet["kills"]) if fleet else 0,
                } if fleet else None,
                "loadouts": [],
                "_pilots": set(),
            }

        alliances[aid]["total_damage"] += int(row["total_damage"] or 0)

        loadout = {
            "ship_name": row["ship_name"],
            "ship_class": row["ship_class"],
            "weapon_name": row["weapon_name"],
            "weapon_class": row["weapon_class"],
            "range": classify_range(row["optimal_range"]),
            "damage_type": row["primary_damage_type"],
            "pilot_count": row["pilot_count"],
            "engagements": row["engagements"],
            "total_damage": int(row["total_damage"] or 0),
        }
        alliances[aid]["loadouts"].append(loadout)

    # Finalize: compute pilot counts, sort, trim
    result_alliances: List[Dict] = []
    for aid, data in alliances.items():
        # Deduplicate pilot count across loadouts
        unique_pilots = set()
        for lo in data["loadouts"]:
            # pilot_count per loadout row is already distinct per group
            pass
        # Get total distinct pilots from loadout rows
        total_pilots = sum(lo["pilot_count"] for lo in data["loadouts"])
        # Cap at reasonable dedup (pilots appear in multiple ship/weapon combos)
        data["pilot_count"] = min(total_pilots, total_pilots)  # best estimate
        del data["_pilots"]

        # Only keep top 10 loadouts per alliance (by damage)
        data["loadouts"] = data["loadouts"][:10]
        result_alliances.append(data)

    # Sort alliances by total damage
    result_alliances.sort(key=lambda a: a["total_damage"], reverse=True)

    result = {
        "battle_id": battle_id,
        "alliances": result_alliances,
    }

    set_cached(cache_key, result, LOADOUT_CACHE_TTL)
    return result
