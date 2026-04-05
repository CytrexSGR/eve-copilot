# app/routers/powerbloc/victim_tank.py
"""Power Bloc victim tank profile endpoint - Dogma-based analysis."""

import logging
from typing import Dict, Any, List
from collections import defaultdict
from fastapi import APIRouter, Query

from app.database import db_cursor
from ._shared import _get_coalition_members
from eve_shared.utils.error_handling import handle_endpoint_errors
from app.utils.cache import get_cached, set_cached
from app.services.dogma import DogmaRepository, TankCalculatorService

logger = logging.getLogger(__name__)
router = APIRouter()

VICTIM_TANK_CACHE_TTL = 600  # 10 minutes (CPU intensive)
MAX_KILLMAILS_TO_ANALYZE = 100  # Limit for performance


@router.get("/{leader_id}/victim-tank-profile")
@handle_endpoint_errors()
def get_victim_tank_profile(
    leader_id: int,
    days: int = Query(7, ge=1, le=30)
) -> Dict[str, Any]:
    """Analyze victim tank profiles for PowerBloc kills.

    Returns aggregated tank data:
    - Tank type distribution (shield/armor/hull)
    - Resist weaknesses by damage type
    - Fleet effectiveness metrics (avg EHP, estimated DPS, TTK)

    Results are cached for 10 minutes due to CPU-intensive Dogma calculations.
    """
    cache_key = f"pb-victim-tank:{leader_id}:{days}"
    cached = get_cached(cache_key, VICTIM_TANK_CACHE_TTL)
    if cached:
        logger.debug(f"Victim tank cache hit for PowerBloc {leader_id}")
        return cached

    # Initialize Dogma services
    dogma_repo = DogmaRepository()
    tank_calc = TankCalculatorService(dogma_repo)

    with db_cursor() as cur:
        # Get coalition member alliances
        member_ids, coalition_name, name_map, ticker_map = _get_coalition_members(leader_id, cur)

        # Get recent killmails where coalition members got kills
        cur.execute("""
            SELECT killmail_id, ship_type_id, ship_name, ship_value, killmail_time
            FROM (
                SELECT DISTINCT ON (k.killmail_id)
                    k.killmail_id,
                    k.ship_type_id,
                    t."typeName" as ship_name,
                    k.ship_value,
                    k.killmail_time
                FROM killmails k
                JOIN killmail_attackers ka ON k.killmail_id = ka.killmail_id
                JOIN "invTypes" t ON k.ship_type_id = t."typeID"
                WHERE ka.alliance_id = ANY(%(member_ids)s)
                  AND k.killmail_time >= NOW() - %(days)s * INTERVAL '1 day'
                  AND k.ship_type_id IS NOT NULL
                ORDER BY k.killmail_id, k.killmail_time DESC
            ) sub
            ORDER BY killmail_time DESC
            LIMIT %(limit)s
        """, {
            'member_ids': member_ids,
            'days': days,
            'limit': MAX_KILLMAILS_TO_ANALYZE
        })

        killmails = cur.fetchall()

        if not killmails:
            return _empty_response(coalition_name)

        # Analyze each killmail
        tank_types = defaultdict(int)
        resist_totals = {'em': [], 'thermal': [], 'kinetic': [], 'explosive': []}
        ehp_values = []
        ship_class_tanks = defaultdict(lambda: {'shield': 0, 'armor': 0, 'hull': 0})

        analyzed_count = 0

        for km in killmails:
            killmail_id = km['killmail_id']
            ship_type_id = km['ship_type_id']
            ship_name = km['ship_name']

            # Get fitted modules from killmail
            fitted_modules = dogma_repo.get_killmail_victim_items(killmail_id)

            # Calculate tank
            tank_result = tank_calc.calculate_tank(
                ship_type_id=ship_type_id,
                fitted_modules=fitted_modules,
                skill_level=4
            )

            if not tank_result:
                continue

            analyzed_count += 1

            # Classify tank type
            primary = tank_result.primary_tank_layer
            tank_types[primary] += 1

            # Collect resist values (as percentages)
            # Use the primary tank layer's resists
            if primary == 'shield':
                resists = tank_result.shield_resists
            else:
                resists = tank_result.armor_resists

            resist_totals['em'].append(resists.em_percent)
            resist_totals['thermal'].append(resists.thermal_percent)
            resist_totals['kinetic'].append(resists.kinetic_percent)
            resist_totals['explosive'].append(resists.explosive_percent)

            # Collect EHP
            ehp_values.append(tank_result.total_ehp)

            # Track by ship class (simplified)
            ship_class = _classify_ship_simple(ship_name)
            ship_class_tanks[ship_class][primary] += 1

        if analyzed_count == 0:
            return _empty_response(coalition_name)

        # Calculate averages and distributions
        total = sum(tank_types.values())
        tank_distribution = {
            'shield': round(100 * tank_types.get('shield', 0) / total, 1),
            'armor': round(100 * tank_types.get('armor', 0) / total, 1),
            'hull': round(100 * tank_types.get('hull', 0) / total, 1),
        }

        # Calculate average resists and identify weaknesses
        resist_weaknesses = []
        for dmg_type in ['em', 'thermal', 'kinetic', 'explosive']:
            values = resist_totals[dmg_type]
            if values:
                avg = sum(values) / len(values)
                # Lower resist = more damage taken = weakness
                weakness_level = 'EXPLOIT' if avg < 35 else 'SOFT' if avg < 50 else 'NORMAL'
                resist_weaknesses.append({
                    'damage_type': dmg_type.upper(),
                    'avg_resist': round(avg, 1),
                    'weakness_level': weakness_level,
                })

        # Sort by weakness (lowest resist first)
        resist_weaknesses.sort(key=lambda x: x['avg_resist'])

        # Calculate fleet effectiveness
        avg_ehp = sum(ehp_values) / len(ehp_values) if ehp_values else 0

        # Estimate fleet DPS from recent battles (simplified)
        cur.execute("""
            SELECT
                COUNT(DISTINCT ka.character_id) as unique_attackers,
                AVG(ka.damage_done) as avg_damage_per_attacker
            FROM killmail_attackers ka
            JOIN killmails k ON ka.killmail_id = k.killmail_id
            WHERE ka.alliance_id = ANY(%(member_ids)s)
              AND k.killmail_time >= NOW() - %(days)s * INTERVAL '1 day'
        """, {'member_ids': member_ids, 'days': days})

        fleet_row = cur.fetchone()
        unique_attackers = fleet_row['unique_attackers'] or 0

        # Rough DPS estimate: assume average engagement has 10 pilots, each doing ~500 DPS
        estimated_fleet_dps = min(unique_attackers, 50) * 400  # Cap at 50 pilots average

        # Calculate average time-to-kill
        avg_ttk = avg_ehp / estimated_fleet_dps if estimated_fleet_dps > 0 else 0

        result = {
            'coalition_name': coalition_name,
            'period_days': days,
            'killmails_analyzed': analyzed_count,
            'tank_distribution': tank_distribution,
            'resist_weaknesses': resist_weaknesses,
            'fleet_effectiveness': {
                'avg_victim_ehp': round(avg_ehp, 0),
                'estimated_fleet_dps': round(estimated_fleet_dps, 0),
                'avg_time_to_kill_seconds': round(avg_ttk, 1),
                'overkill_ratio': round(estimated_fleet_dps / avg_ehp, 2) if avg_ehp > 0 else 0,
            },
            'top_ship_classes': _get_top_ship_classes(ship_class_tanks),
        }

        set_cached(cache_key, result, VICTIM_TANK_CACHE_TTL)
        return result


def _empty_response(coalition_name: str) -> Dict[str, Any]:
    """Return empty response when no data available."""
    return {
        'coalition_name': coalition_name,
        'period_days': 0,
        'killmails_analyzed': 0,
        'tank_distribution': {'shield': 0, 'armor': 0, 'hull': 0},
        'resist_weaknesses': [],
        'fleet_effectiveness': {
            'avg_victim_ehp': 0,
            'estimated_fleet_dps': 0,
            'avg_time_to_kill_seconds': 0,
            'overkill_ratio': 0,
        },
        'top_ship_classes': [],
    }


def _classify_ship_simple(ship_name: str) -> str:
    """Simplified ship classification based on name."""
    name_lower = ship_name.lower()

    if any(x in name_lower for x in ['titan', 'avatar', 'erebus', 'leviathan', 'ragnarok']):
        return 'Titan'
    if any(x in name_lower for x in ['supercarrier', 'nyx', 'hel', 'aeon', 'wyvern']):
        return 'Supercarrier'
    if any(x in name_lower for x in ['dreadnought', 'moros', 'naglfar', 'revelation', 'phoenix']):
        return 'Dreadnought'
    if any(x in name_lower for x in ['carrier', 'thanatos', 'nidhoggur', 'archon', 'chimera']):
        return 'Carrier'
    if 'battleship' in name_lower or any(x in name_lower for x in ['apocalypse', 'megathron', 'raven', 'typhoon', 'maelstrom']):
        return 'Battleship'
    if 'battlecruiser' in name_lower or any(x in name_lower for x in ['drake', 'hurricane', 'harbinger', 'brutix']):
        return 'Battlecruiser'
    if 'cruiser' in name_lower or any(x in name_lower for x in ['caracal', 'thorax', 'omen', 'rupture']):
        return 'Cruiser'
    if 'destroyer' in name_lower or any(x in name_lower for x in ['thrasher', 'catalyst', 'coercer', 'cormorant']):
        return 'Destroyer'
    if 'frigate' in name_lower or any(x in name_lower for x in ['rifter', 'merlin', 'punisher', 'incursus']):
        return 'Frigate'
    if any(x in name_lower for x in ['venture', 'retriever', 'covetor', 'hulk', 'mackinaw', 'skiff']):
        return 'Mining'
    if any(x in name_lower for x in ['industrial', 'hauler', 'badger', 'tayra', 'nereus', 'epithal']):
        return 'Industrial'

    return 'Other'


def _get_top_ship_classes(ship_class_tanks: Dict) -> List[Dict]:
    """Get top ship classes by kill count with their tank distribution."""
    result = []
    for ship_class, tanks in ship_class_tanks.items():
        total = sum(tanks.values())
        if total > 0:
            result.append({
                'ship_class': ship_class,
                'count': total,
                'shield_pct': round(100 * tanks['shield'] / total, 1),
                'armor_pct': round(100 * tanks['armor'] / total, 1),
            })

    # Sort by count descending
    result.sort(key=lambda x: x['count'], reverse=True)
    return result[:10]  # Top 10
