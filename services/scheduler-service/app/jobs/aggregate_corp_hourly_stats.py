#!/usr/bin/env python3
"""
Corporation Hourly Stats Aggregator

Aggregates killmail data into corporation_hourly_stats table for fast queries.
Designed to run every 30 minutes to keep data fresh.

Features:
- Aggregates all fields (kills, deaths, ISK, ships, systems, enemies)
- Phase 2 + Phase 3 fields: damage_types, ship_effectiveness, ewar_threats, expensive_losses
  solo_kills, solo_deaths, active_pilots, engagement_distribution, solo_ratio, damage_dealt, ewar_used
- Incremental updates (only processes new killmails)
- Supports backfill mode for historical data
- Uses UPSERT (INSERT ON CONFLICT UPDATE) for idempotent operation

Usage:
    # Normal mode: Process last 2 hours (run every 30 min)
    python3 -m app.jobs.aggregate_corp_hourly_stats

    # Backfill mode: Process specific date range
    python3 -m app.jobs.aggregate_corp_hourly_stats --backfill --start-date 2026-01-01 --end-date 2026-02-02

    # Verbose mode
    python3 -m app.jobs.aggregate_corp_hourly_stats --verbose
"""

import sys
import os
import json
import argparse
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from concurrent.futures import ProcessPoolExecutor
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

# Database connection
def get_db_connection():
    """Get PostgreSQL connection."""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", os.getenv("DB_HOST", "eve_db")),
        port=int(os.getenv("POSTGRES_PORT", os.getenv("DB_PORT", "5432"))),
        database=os.getenv("POSTGRES_DB", os.getenv("DB_NAME", "eve_sde")),
        user=os.getenv("POSTGRES_USER", os.getenv("DB_USER", "eve")),
        password=os.getenv("POSTGRES_PASSWORD", os.getenv("DB_PASSWORD", "eve"))
    )


# SDE Cache (loaded once per worker process)
_SDE_CACHE = {}

def load_sde_cache():
    """Load all SDE data needed for aggregation into memory (once per worker)."""
    global _SDE_CACHE

    if _SDE_CACHE:
        return _SDE_CACHE

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Load ship types with race and group info
            cur.execute('''
                SELECT t."typeID", t."raceID", g."groupName"
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE t."typeID" IS NOT NULL
            ''')

            ship_data = {}
            for row in cur.fetchall():
                ship_data[row[0]] = {
                    'race_id': row[1],
                    'group_name': row[2]
                }

            _SDE_CACHE['ships'] = ship_data

    return _SDE_CACHE


# RACE_DAMAGE mapping for damage_types inference
RACE_DAMAGE = {
    1: {"kinetic": 0.55, "thermal": 0.45},   # Caldari
    2: {"explosive": 0.55, "kinetic": 0.45}, # Minmatar
    4: {"em": 0.55, "thermal": 0.45},        # Amarr
    8: {"thermal": 0.55, "kinetic": 0.45},   # Gallente
}

# EWAR ship groups
EWAR_GROUPS = {
    "Electronic Attack Ship": "ecm",
    "Force Recon Ship": "dampener",
    "Interdictor": "bubble",
    "Heavy Interdictor": "bubble",
}

# Capital ship groups (from eve_shared)
from eve_shared.constants import CAPITAL_GROUP_NAMES as CAPITAL_GROUPS

# Weapon/Tank classification by race (lightweight equipment inference)
RACE_EQUIPMENT_PROFILE = {
    1: {  # Caldari
        "primary_weapon": "missile",
        "secondary_weapon": "hybrid",
        "tank_type": "shield"
    },
    2: {  # Minmatar
        "primary_weapon": "projectile",
        "secondary_weapon": "missile",
        "tank_type": "shield"
    },
    4: {  # Amarr
        "primary_weapon": "laser",
        "secondary_weapon": "drone",
        "tank_type": "armor"
    },
    8: {  # Gallente
        "primary_weapon": "hybrid",
        "secondary_weapon": "drone",
        "tank_type": "armor"
    }
}

# Engagement size thresholds
ENGAGEMENT_SOLO = 3      # <=3 attackers
ENGAGEMENT_SMALL = 10    # 4-10 attackers
ENGAGEMENT_MEDIUM = 30   # 11-30 attackers
ENGAGEMENT_LARGE = 100   # 31-100 attackers
# ENGAGEMENT_BLOB = >100 attackers


def calculate_damage_types(attackers: List[Dict], sde_cache: Dict) -> Dict[str, int]:
    """Calculate damage type distribution from attacker ship races (cached)."""
    damage_counts = {"em": 0, "thermal": 0, "kinetic": 0, "explosive": 0}

    for attacker in attackers:
        ship_type = attacker.get('ship_type_id')
        if not ship_type:
            continue

        ship_info = sde_cache['ships'].get(ship_type)
        if ship_info and ship_info['race_id'] in RACE_DAMAGE:
            for dt, ratio in RACE_DAMAGE[ship_info['race_id']].items():
                damage_counts[dt] += ratio

    return {k: int(v) for k, v in damage_counts.items()}


def classify_victim_ship(ship_type_id: int, sde_cache: Dict) -> str:
    """Get ship class for effectiveness tracking (cached)."""
    ship_info = sde_cache['ships'].get(ship_type_id)
    return ship_info['group_name'] if ship_info else "Unknown"


def detect_ewar_attackers(attackers: List[Dict], sde_cache: Dict) -> Dict[str, Dict]:
    """Detect EWAR ships in attacker list (cached)."""
    ewar_counts = {}

    for attacker in attackers:
        ship_type = attacker.get('ship_type_id')
        if not ship_type:
            continue

        ship_info = sde_cache['ships'].get(ship_type)
        if ship_info and ship_info['group_name'] in EWAR_GROUPS:
            group_name = ship_info['group_name']
            if group_name not in ewar_counts:
                ewar_counts[group_name] = {"count": 0, "ewar_type": EWAR_GROUPS[group_name]}
            ewar_counts[group_name]["count"] += 1

    return ewar_counts


def infer_equipment_profile(ship_type_id: int, ship_value: int, sde_cache: Dict) -> Dict[str, any]:
    """
    Lightweight equipment inference based on ship type (cached).
    Returns weapon class and tank type based on ship race.
    """
    ship_info = sde_cache['ships'].get(ship_type_id)

    if ship_info and ship_info['race_id'] in RACE_EQUIPMENT_PROFILE:
        profile = RACE_EQUIPMENT_PROFILE[ship_info['race_id']]
        return {
            "weapon_class": profile["primary_weapon"],
            "tank_type": profile["tank_type"],
            "ship_value": ship_value
        }

    return {"weapon_class": "mixed", "tank_type": "mixed", "ship_value": ship_value}


def calculate_engagement_size(attacker_count: int) -> str:
    """Classify engagement by attacker count."""
    if attacker_count <= ENGAGEMENT_SOLO:
        return 'solo'
    elif attacker_count <= ENGAGEMENT_SMALL:
        return 'small'
    elif attacker_count <= ENGAGEMENT_MEDIUM:
        return 'medium'
    elif attacker_count <= ENGAGEMENT_LARGE:
        return 'large'
    else:
        return 'blob'


def aggregate_hour(hour_start: datetime, hour_end: datetime, verbose: bool = False) -> Dict:
    """
    Aggregate killmail data for one hour bucket.

    Returns dict with:
        - rows_processed: number of killmails processed
        - corporations_updated: number of corporation rows inserted/updated
    """
    stats = {"rows_processed": 0, "corporations_updated": 0}

    # Load SDE cache once per worker process
    sde_cache = load_sde_cache()

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Fetch all killmails in this hour
            cur.execute("""
                SELECT
                    k.killmail_id,
                    k.killmail_time,
                    k.solar_system_id,
                    k.ship_type_id,
                    k.ship_value,
                    k.victim_corporation_id,
                    k.victim_character_id,
                    k.attacker_count,
                    (SELECT json_agg(json_build_object(
                        'corporation_id', ka.corporation_id,
                        'character_id', ka.character_id,
                        'ship_type_id', ka.ship_type_id
                    ))
                    FROM killmail_attackers ka
                    WHERE ka.killmail_id = k.killmail_id) as attackers
                FROM killmails k
                WHERE k.killmail_time >= %s
                  AND k.killmail_time < %s
                ORDER BY k.killmail_time
            """, (hour_start, hour_end))

            killmails = cur.fetchall()
            stats["rows_processed"] = len(killmails)

            if verbose:
                logger.info(f"Processing {len(killmails)} killmails for hour {hour_start}")

            if not killmails:
                return stats

            # Group by corporation_id
            corp_data = {}

            for km in killmails:
                attackers = km['attackers'] if km['attackers'] else []
                attacker_count = km['attacker_count']
                engagement_size = calculate_engagement_size(attacker_count)

                # Process each corporation involved (victim + attackers)
                corps_involved = set()

                # Add victim corporation
                if km['victim_corporation_id']:
                    corps_involved.add(km['victim_corporation_id'])

                # Add attacker corporations
                for attacker in attackers:
                    if attacker.get('corporation_id'):
                        corps_involved.add(attacker['corporation_id'])

                # Update stats for each corporation
                for corp_id in corps_involved:
                    if corp_id not in corp_data:
                        corp_data[corp_id] = {
                            'kills': 0,
                            'deaths': 0,
                            'isk_destroyed': 0,
                            'isk_lost': 0,
                            'ships_killed': {},
                            'ships_lost': {},
                            'systems_kills': {},
                            'systems_deaths': {},
                            'enemies_killed': {},
                            'killed_by': {},
                            'damage_types': {"em": 0, "thermal": 0, "kinetic": 0, "explosive": 0},
                            'ship_effectiveness': {},
                            'ewar_threats': {},
                            'expensive_losses': [],
                            'equipment_summary': {
                                "weapon_laser": 0,
                                "weapon_projectile": 0,
                                "weapon_hybrid": 0,
                                "weapon_missile": 0,
                                "weapon_mixed": 0,
                                "tank_shield": 0,
                                "tank_armor": 0,
                                "tank_mixed": 0
                            },
                            # Phase 3 fields
                            'solo_kills': 0,
                            'solo_deaths': 0,
                            'active_pilots': set(),  # Will convert to count later
                            'engagement_distribution': {
                                'solo': 0,
                                'small': 0,
                                'medium': 0,
                                'large': 0,
                                'blob': 0
                            },
                            'damage_dealt': {"em": 0, "thermal": 0, "kinetic": 0, "explosive": 0},
                            'ewar_used': {},
                            # Phase B2: kill value tracking
                            'kill_values': [],
                        }

                    data = corp_data[corp_id]

                    # Is this corporation the victim?
                    is_victim = (km['victim_corporation_id'] == corp_id)

                    if is_victim:
                        # Corporation lost this ship
                        data['deaths'] += 1
                        data['isk_lost'] += km['ship_value'] or 0

                        # Solo death tracking
                        if attacker_count <= ENGAGEMENT_SOLO:
                            data['solo_deaths'] += 1

                        # Victims are not counted as "active pilots"
                        # (active_pilots = PvP participants only, tracked via attackers below)

                        # Track ship losses
                        ship_id = str(km['ship_type_id'])
                        data['ships_lost'][ship_id] = data['ships_lost'].get(ship_id, 0) + 1

                        # Track system deaths
                        system_id = str(km['solar_system_id'])
                        data['systems_deaths'][system_id] = data['systems_deaths'].get(system_id, 0) + 1

                        # Ship effectiveness (victim ship classification)
                        ship_class = classify_victim_ship(km['ship_type_id'], sde_cache)
                        if ship_class not in data['ship_effectiveness']:
                            data['ship_effectiveness'][ship_class] = {"deaths": 0, "isk_lost": 0}
                        data['ship_effectiveness'][ship_class]["deaths"] += 1
                        data['ship_effectiveness'][ship_class]["isk_lost"] += km['ship_value'] or 0

                        # Expensive losses (>100M ISK)
                        if km['ship_value'] and km['ship_value'] > 100_000_000:
                            data['expensive_losses'].append({
                                'killmail_id': km['killmail_id'],
                                'ship_type_id': km['ship_type_id'],
                                'ship_value': km['ship_value'],
                                'system_id': km['solar_system_id']
                            })

                        # Equipment profile (lightweight inference from ship race)
                        equip = infer_equipment_profile(km['ship_type_id'], km['ship_value'] or 0, sde_cache)
                        weapon_key = f"weapon_{equip['weapon_class']}"
                        tank_key = f"tank_{equip['tank_type']}"
                        data['equipment_summary'][weapon_key] = data['equipment_summary'].get(weapon_key, 0) + 1
                        data['equipment_summary'][tank_key] = data['equipment_summary'].get(tank_key, 0) + 1

                        # Damage types (from attackers)
                        damage = calculate_damage_types(attackers, sde_cache)
                        for dt, count in damage.items():
                            data['damage_types'][dt] += count

                        # EWAR threats
                        ewar = detect_ewar_attackers(attackers, sde_cache)
                        for ship_class, ewar_data in ewar.items():
                            if ship_class not in data['ewar_threats']:
                                data['ewar_threats'][ship_class] = {"count": 0, "ewar_type": ewar_data["ewar_type"]}
                            data['ewar_threats'][ship_class]["count"] += ewar_data["count"]

                        # Killed by (attacker corporations)
                        for attacker in attackers:
                            enemy_id = attacker.get('corporation_id')
                            if enemy_id and enemy_id != corp_id:
                                enemy_key = str(enemy_id)
                                if enemy_key not in data['killed_by']:
                                    data['killed_by'][enemy_key] = {"kills": 0, "isk": 0}
                                data['killed_by'][enemy_key]["kills"] += 1
                                data['killed_by'][enemy_key]["isk"] += km['ship_value'] or 0

                    else:
                        # Corporation participated in killing this ship
                        # Note: Count each attacker's participation once per kill
                        # Find this corp's attacker in the list
                        corp_attacker = next((a for a in attackers if a.get('corporation_id') == corp_id), None)
                        if corp_attacker:
                            data['kills'] += 1
                            data['isk_destroyed'] += km['ship_value'] or 0
                            if km['ship_value']:
                                data['kill_values'].append(km['ship_value'])

                            # Solo kill tracking
                            if attacker_count <= ENGAGEMENT_SOLO:
                                data['solo_kills'] += 1

                            # Engagement distribution (count once per kill, not per attacker)
                            data['engagement_distribution'][engagement_size] += 1

                            # Track attacker pilot
                            if corp_attacker.get('character_id'):
                                data['active_pilots'].add(corp_attacker['character_id'])

                            # Track ship kills
                            ship_id = str(km['ship_type_id'])
                            data['ships_killed'][ship_id] = data['ships_killed'].get(ship_id, 0) + 1

                            # Track system kills
                            system_id = str(km['solar_system_id'])
                            data['systems_kills'][system_id] = data['systems_kills'].get(system_id, 0) + 1

                            # Enemies killed
                            if km['victim_corporation_id']:
                                enemy_key = str(km['victim_corporation_id'])
                                if enemy_key not in data['enemies_killed']:
                                    data['enemies_killed'][enemy_key] = {"kills": 0, "isk": 0}
                                data['enemies_killed'][enemy_key]["kills"] += 1
                                data['enemies_killed'][enemy_key]["isk"] += km['ship_value'] or 0

                            # Damage dealt (inverse of damage_types)
                            damage_dist = calculate_damage_types([corp_attacker], sde_cache)
                            for dmg_type, count in damage_dist.items():
                                data['damage_dealt'][dmg_type] += count

                            # EWAR used (attacker perspective)
                            ewar_ships = detect_ewar_attackers([corp_attacker], sde_cache)
                            for group_name, ewar_info in ewar_ships.items():
                                if group_name not in data['ewar_used']:
                                    data['ewar_used'][group_name] = {
                                        'count': 0,
                                        'ewar_type': ewar_info['ewar_type']
                                    }
                                data['ewar_used'][group_name]['count'] += 1

            # Post-processing for all corporations
            for corp_id in corp_data:
                data = corp_data[corp_id]

                # Keep only top 5 expensive losses
                losses = data['expensive_losses']
                data['expensive_losses'] = sorted(
                    losses, key=lambda x: x['ship_value'], reverse=True
                )[:5]

                # Convert active_pilots set to count
                data['active_pilots'] = len(data['active_pilots'])

                # Calculate solo_ratio
                total_kills = data['kills']
                data['solo_ratio'] = data['solo_kills'] / total_kills if total_kills > 0 else 0.0

                # Calculate avg/max kill value
                kv = data['kill_values']
                data['avg_kill_value'] = int(sum(kv) / len(kv)) if kv else 0
                data['max_kill_value'] = max(kv) if kv else 0

            # UPSERT into corporation_hourly_stats
            for corp_id, data in corp_data.items():
                cur.execute("""
                    INSERT INTO corporation_hourly_stats (
                        corporation_id, hour_bucket,
                        kills, deaths, isk_destroyed, isk_lost,
                        ships_killed, ships_lost,
                        systems_kills, systems_deaths,
                        enemies_killed, killed_by,
                        damage_types, ship_effectiveness, ewar_threats, expensive_losses,
                        equipment_summary,
                        solo_kills, solo_deaths, active_pilots, engagement_distribution, solo_ratio,
                        damage_dealt, ewar_used,
                        avg_kill_value, max_kill_value
                    ) VALUES (
                        %s, %s,
                        %s, %s, %s, %s,
                        %s::jsonb, %s::jsonb,
                        %s::jsonb, %s::jsonb,
                        %s::jsonb, %s::jsonb,
                        %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb,
                        %s::jsonb,
                        %s, %s, %s, %s::jsonb, %s,
                        %s::jsonb, %s::jsonb,
                        %s, %s
                    )
                    ON CONFLICT (corporation_id, hour_bucket) DO UPDATE SET
                        kills = EXCLUDED.kills,
                        deaths = EXCLUDED.deaths,
                        isk_destroyed = EXCLUDED.isk_destroyed,
                        isk_lost = EXCLUDED.isk_lost,
                        ships_killed = EXCLUDED.ships_killed,
                        ships_lost = EXCLUDED.ships_lost,
                        systems_kills = EXCLUDED.systems_kills,
                        systems_deaths = EXCLUDED.systems_deaths,
                        enemies_killed = EXCLUDED.enemies_killed,
                        killed_by = EXCLUDED.killed_by,
                        damage_types = EXCLUDED.damage_types,
                        ship_effectiveness = EXCLUDED.ship_effectiveness,
                        ewar_threats = EXCLUDED.ewar_threats,
                        expensive_losses = EXCLUDED.expensive_losses,
                        equipment_summary = EXCLUDED.equipment_summary,
                        solo_kills = EXCLUDED.solo_kills,
                        solo_deaths = EXCLUDED.solo_deaths,
                        active_pilots = EXCLUDED.active_pilots,
                        engagement_distribution = EXCLUDED.engagement_distribution,
                        solo_ratio = EXCLUDED.solo_ratio,
                        damage_dealt = EXCLUDED.damage_dealt,
                        ewar_used = EXCLUDED.ewar_used,
                        avg_kill_value = EXCLUDED.avg_kill_value,
                        max_kill_value = EXCLUDED.max_kill_value,
                        updated_at = NOW()
                """, (
                    corp_id, hour_start,
                    data['kills'], data['deaths'], data['isk_destroyed'], data['isk_lost'],
                    json.dumps(data['ships_killed']), json.dumps(data['ships_lost']),
                    json.dumps(data['systems_kills']), json.dumps(data['systems_deaths']),
                    json.dumps(data['enemies_killed']), json.dumps(data['killed_by']),
                    json.dumps(data['damage_types']), json.dumps(data['ship_effectiveness']),
                    json.dumps(data['ewar_threats']), json.dumps(data['expensive_losses']),
                    json.dumps(data['equipment_summary']),
                    data['solo_kills'], data['solo_deaths'], data['active_pilots'],
                    json.dumps(data['engagement_distribution']), data['solo_ratio'],
                    json.dumps(data['damage_dealt']), json.dumps(data['ewar_used']),
                    data['avg_kill_value'], data['max_kill_value']
                ))
                stats["corporations_updated"] += 1

            conn.commit()

            if verbose:
                logger.info(f"Updated {stats['corporations_updated']} corporation rows")

    return stats


def run_aggregator(start_time: datetime = None, end_time: datetime = None, verbose: bool = False, workers: int = 1):
    """
    Run the hourly stats aggregator.

    Args:
        start_time: Start of time range (default: 2 hours ago)
        end_time: End of time range (default: now)
        verbose: Print progress
        workers: Number of parallel workers (default: 1 for sequential, 4-8 recommended for backfill)
    """
    if not start_time:
        start_time = datetime.now() - timedelta(hours=2)
    if not end_time:
        end_time = datetime.now()

    # Truncate to hour buckets
    start_hour = start_time.replace(minute=0, second=0, microsecond=0)
    end_hour = end_time.replace(minute=0, second=0, microsecond=0)

    # Generate list of hour buckets to process
    hours = []
    current_hour = start_hour
    while current_hour < end_hour:
        next_hour = current_hour + timedelta(hours=1)
        hours.append((current_hour, next_hour, verbose))
        current_hour = next_hour

    total_hours = len(hours)

    if verbose:
        logger.info(f"Aggregating corporation_hourly_stats from {start_hour} to {end_hour}")
        logger.info(f"Processing {total_hours} hours with {workers} worker(s)")

    # Process hours (parallel or sequential)
    if workers > 1:
        # Parallel processing with ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(_aggregate_hour_wrapper, hours))
    else:
        # Sequential processing (backwards compatible)
        results = [aggregate_hour(h[0], h[1], h[2]) for h in hours]

    # Aggregate results
    total_rows = sum(r["rows_processed"] for r in results)
    total_corps = sum(r["corporations_updated"] for r in results)

    if verbose:
        logger.info("Aggregation complete:")
        logger.info(f"  Processed {total_rows} killmails")
        logger.info(f"  Updated {total_corps} corporation-hour buckets")

    return {
        "success": True,
        "rows_processed": total_rows,
        "corporations_updated": total_corps,
        "start_time": start_hour.isoformat(),
        "end_time": end_hour.isoformat()
    }


def _aggregate_hour_wrapper(args):
    """Wrapper for ProcessPoolExecutor.map() to unpack tuple arguments."""
    return aggregate_hour(args[0], args[1], args[2])


def main():
    parser = argparse.ArgumentParser(description='Corporation Hourly Stats Aggregator')
    parser.add_argument('--backfill', action='store_true', help='Backfill mode')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--workers', '-w', type=int, default=1,
                        help='Number of parallel workers (default: 1, recommended: 4-8 for backfill)')

    args = parser.parse_args()

    if args.backfill:
        if not args.start_date or not args.end_date:
            logger.error("--start-date and --end-date required for backfill mode")
            sys.exit(1)

        start_time = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_time = datetime.strptime(args.end_date, '%Y-%m-%d')
    else:
        # Normal mode: last 2 hours
        start_time = None
        end_time = None

    result = run_aggregator(start_time, end_time, verbose=args.verbose, workers=args.workers)

    if result["success"]:
        logger.info(f"Success: {result['rows_processed']} killmails → {result['corporations_updated']} updates")
        sys.exit(0)
    else:
        logger.error(f"Failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
