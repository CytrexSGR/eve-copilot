"""Battle victim tank analysis endpoint - Dogma Engine integration."""

import logging
from typing import Any, Dict, List
from collections import defaultdict

from fastapi import APIRouter, HTTPException

from app.database import db_cursor
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.utils.cache import get_cached, set_cached
from app.services.dogma import DogmaRepository, TankCalculatorService

logger = logging.getLogger(__name__)
router = APIRouter()

TANK_CACHE_TTL = 600  # 10 minutes (CPU intensive)
MAX_KILLMAILS = 20  # Analyze top 20 high-value losses


@router.get("/battle/{battle_id}/victim-tank-analysis")
@handle_endpoint_errors()
def get_victim_tank_analysis(battle_id: int) -> Dict[str, Any]:
    """Analyze victim tank profiles for a battle using the Dogma Engine.

    Analyzes the top 20 high-value losses (>10M ISK) to determine:
    - Tank type distribution (shield/armor/hull)
    - Average EHP and resist profiles
    - Per-side tank comparison
    - Top losses with EHP data
    """
    cache_key = f"battle-dogma:{battle_id}"
    cached = get_cached(cache_key, TANK_CACHE_TTL)
    if cached:
        return cached

    dogma_repo = DogmaRepository()
    tank_calc = TankCalculatorService(dogma_repo)

    with db_cursor() as cur:
        # Verify battle exists
        cur.execute("SELECT battle_id FROM battles WHERE battle_id = %s", (battle_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Battle {battle_id} not found")

        # Get side assignments for per-side analysis
        cur.execute("""
            SELECT
                ka.alliance_id as attacker_alliance,
                k.victim_alliance_id as victim_alliance
            FROM killmails k
            JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                AND ka.is_final_blow = true
            WHERE k.battle_id = %s
            AND ka.alliance_id IS NOT NULL
            AND k.victim_alliance_id IS NOT NULL
        """, (battle_id,))
        # Build rough side mapping: victim alliances are "losers" to their attackers
        victim_to_attacker = {}
        for row in cur.fetchall():
            victim_to_attacker[row["victim_alliance"]] = row["attacker_alliance"]

        # Get top high-value killmails
        cur.execute("""
            SELECT
                k.killmail_id,
                k.ship_type_id,
                t."typeName" as ship_name,
                k.ship_value,
                k.victim_alliance_id
            FROM killmails k
            JOIN "invTypes" t ON k.ship_type_id = t."typeID"
            WHERE k.battle_id = %s
            AND k.ship_value > 10000000
            ORDER BY k.ship_value DESC
            LIMIT %s
        """, (battle_id, MAX_KILLMAILS))
        killmails = cur.fetchall()

    if not killmails:
        result = _empty_response(battle_id)
        set_cached(cache_key, result, TANK_CACHE_TTL)
        return result

    # Analyze each killmail
    tank_types = defaultdict(int)
    resist_totals = {'em': [], 'thermal': [], 'kinetic': [], 'explosive': []}
    ehp_values = []
    top_losses: List[Dict] = []
    analyzed = 0

    for km in killmails:
        ship_type_id = km["ship_type_id"]
        fitted_modules = dogma_repo.get_killmail_victim_items(km["killmail_id"])
        tank_result = tank_calc.calculate_tank(
            ship_type_id=ship_type_id,
            fitted_modules=fitted_modules,
            skill_level=4,
        )
        if not tank_result:
            continue

        analyzed += 1
        primary = tank_result.primary_tank_layer
        tank_types[primary] += 1
        ehp_values.append(tank_result.total_ehp)

        # Collect resists from primary tank layer
        resists = tank_result.shield_resists if primary == 'shield' else tank_result.armor_resists
        resist_totals['em'].append(resists.em_percent)
        resist_totals['thermal'].append(resists.thermal_percent)
        resist_totals['kinetic'].append(resists.kinetic_percent)
        resist_totals['explosive'].append(resists.explosive_percent)

        # Build top loss entry
        weakness = min(
            [('EM', resists.em_percent), ('THERMAL', resists.thermal_percent),
             ('KINETIC', resists.kinetic_percent), ('EXPLOSIVE', resists.explosive_percent)],
            key=lambda x: x[1]
        )
        top_losses.append({
            "killmail_id": km["killmail_id"],
            "ship_name": km["ship_name"],
            "ship_value": float(km["ship_value"]),
            "ehp": round(tank_result.total_ehp),
            "tank_type": primary,
            "resist_weakness": weakness[0],
        })

    if analyzed == 0:
        result = _empty_response(battle_id)
        set_cached(cache_key, result, TANK_CACHE_TTL)
        return result

    # Calculate distributions
    total = sum(tank_types.values())
    tank_distribution = {
        'shield': round(100 * tank_types.get('shield', 0) / total, 1),
        'armor': round(100 * tank_types.get('armor', 0) / total, 1),
        'hull': round(100 * tank_types.get('hull', 0) / total, 1),
    }

    # Calculate resist profile with weakness classification
    resist_profile = {}
    for dmg_type in ['em', 'thermal', 'kinetic', 'explosive']:
        values = resist_totals[dmg_type]
        if values:
            avg = sum(values) / len(values)
            weakness = 'EXPLOIT' if avg < 35 else 'SOFT' if avg < 50 else 'NORMAL'
            resist_profile[dmg_type] = {'avg': round(avg, 1), 'weakness': weakness}
        else:
            resist_profile[dmg_type] = {'avg': 0, 'weakness': 'NORMAL'}

    avg_ehp = round(sum(ehp_values) / len(ehp_values)) if ehp_values else 0

    result = {
        "battle_id": battle_id,
        "killmails_analyzed": analyzed,
        "tank_distribution": tank_distribution,
        "avg_ehp": avg_ehp,
        "resist_profile": resist_profile,
        "top_losses": top_losses[:5],
    }

    set_cached(cache_key, result, TANK_CACHE_TTL)
    return result


def _empty_response(battle_id: int) -> Dict[str, Any]:
    return {
        "battle_id": battle_id,
        "killmails_analyzed": 0,
        "tank_distribution": {"shield": 0, "armor": 0, "hull": 0},
        "avg_ehp": 0,
        "resist_profile": {
            "em": {"avg": 0, "weakness": "NORMAL"},
            "thermal": {"avg": 0, "weakness": "NORMAL"},
            "kinetic": {"avg": 0, "weakness": "NORMAL"},
            "explosive": {"avg": 0, "weakness": "NORMAL"},
        },
        "top_losses": [],
    }
