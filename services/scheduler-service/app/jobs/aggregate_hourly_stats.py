#!/usr/bin/env python3
"""
Intelligence Hourly Stats Aggregator

Aggregates killmail data into intelligence_hourly_stats table for fast queries.
Designed to run every 30 minutes to keep data fresh.

Features:
- Aggregates all fields (kills, deaths, ISK, ships, systems, enemies)
- Phase 2 fields: damage_types, ship_effectiveness, ewar_threats, expensive_losses
- SDE cache: single bulk-load of ship data, no per-killmail DB lookups
- Error handling: failed hours are skipped, backfill continues
- Progress logging with ETA

Usage:
    # Normal mode: Process last 2 hours (run every 30 min)
    python3 -m app.jobs.aggregate_hourly_stats

    # Backfill mode: Process specific date range
    python3 -m app.jobs.aggregate_hourly_stats --backfill --start-date 2026-01-10 --end-date 2026-02-05

    # Verbose mode
    python3 -m app.jobs.aggregate_hourly_stats --verbose
"""

import sys
import os
import json
import argparse
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List
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


# ---------------------------------------------------------------------------
# SDE Cache (loaded once, used for all lookups)
# ---------------------------------------------------------------------------
_SDE_CACHE = {}


def load_sde_cache():
    """Load all SDE data needed for aggregation into memory (once)."""
    global _SDE_CACHE

    if _SDE_CACHE:
        return _SDE_CACHE

    with get_db_connection() as conn:
        with conn.cursor() as cur:
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

    logger.info(f"SDE cache loaded: {len(_SDE_CACHE['ships'])} types")
    return _SDE_CACHE


def _get_ship_info(ship_type_id: int) -> dict | None:
    """Lookup ship info from SDE cache. Returns None if not found."""
    cache = load_sde_cache()
    return cache['ships'].get(ship_type_id)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RACE_DAMAGE = {
    1: {"kinetic": 0.55, "thermal": 0.45},   # Caldari
    2: {"explosive": 0.55, "kinetic": 0.45},  # Minmatar
    4: {"em": 0.55, "thermal": 0.45},         # Amarr
    8: {"thermal": 0.55, "kinetic": 0.45},    # Gallente
}

EWAR_GROUPS = {
    "Electronic Attack Ship": "ecm",
    "Force Recon Ship": "dampener",
    "Interdictor": "bubble",
    "Heavy Interdictor": "bubble",
}

RACE_EQUIPMENT_PROFILE = {
    1: {"primary_weapon": "missile", "tank_type": "shield"},    # Caldari
    2: {"primary_weapon": "projectile", "tank_type": "shield"}, # Minmatar
    4: {"primary_weapon": "laser", "tank_type": "armor"},       # Amarr
    8: {"primary_weapon": "hybrid", "tank_type": "armor"},      # Gallente
}


# ---------------------------------------------------------------------------
# SDE-cached helper functions (zero DB calls)
# ---------------------------------------------------------------------------

def calculate_damage_types(attackers: List[Dict]) -> Dict[str, int]:
    """Calculate damage type distribution from attacker ship races (from cache)."""
    damage_counts = {"em": 0, "thermal": 0, "kinetic": 0, "explosive": 0}

    for attacker in attackers:
        ship_type = attacker.get('ship_type_id')
        if not ship_type:
            continue

        info = _get_ship_info(ship_type)
        if info and info['race_id'] in RACE_DAMAGE:
            for dt, ratio in RACE_DAMAGE[info['race_id']].items():
                damage_counts[dt] += ratio

    return {k: int(v) for k, v in damage_counts.items()}


def classify_victim_ship(ship_type_id: int) -> str:
    """Get ship group name from cache."""
    info = _get_ship_info(ship_type_id)
    return info['group_name'] if info else "Unknown"


def detect_ewar_attackers(attackers: List[Dict]) -> Dict[str, Dict]:
    """Detect EWAR ships in attacker list (from cache)."""
    ewar_counts = {}

    for attacker in attackers:
        ship_type = attacker.get('ship_type_id')
        if not ship_type:
            continue

        info = _get_ship_info(ship_type)
        if info and info['group_name'] in EWAR_GROUPS:
            group_name = info['group_name']
            if group_name not in ewar_counts:
                ewar_counts[group_name] = {"count": 0, "ewar_type": EWAR_GROUPS[group_name]}
            ewar_counts[group_name]["count"] += 1

    return ewar_counts


def infer_equipment_profile(ship_type_id: int) -> Dict[str, str]:
    """Infer weapon class and tank type from ship race (from cache)."""
    info = _get_ship_info(ship_type_id)
    if info and info['race_id'] in RACE_EQUIPMENT_PROFILE:
        profile = RACE_EQUIPMENT_PROFILE[info['race_id']]
        return {
            "weapon_class": profile["primary_weapon"],
            "tank_type": profile["tank_type"],
        }
    return {"weapon_class": "mixed", "tank_type": "mixed"}


def detect_coalition_allies(attackers: List[Dict], own_alliance_id: int) -> List[int]:
    """Detect co-attacker alliances (coalition members)."""
    ally_ids = []
    for attacker in attackers:
        ally_id = attacker.get('alliance_id')
        if ally_id and ally_id != own_alliance_id:
            ally_ids.append(ally_id)
    return ally_ids


# ---------------------------------------------------------------------------
# Core aggregation
# ---------------------------------------------------------------------------

def aggregate_hour(hour_start: datetime, hour_end: datetime, verbose: bool = False) -> Dict:
    """
    Aggregate killmail data for one hour bucket.
    Uses a single DB connection for the query + upsert.
    All SDE lookups come from in-memory cache.
    """
    stats = {"rows_processed": 0, "alliances_updated": 0}

    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    k.killmail_id,
                    k.killmail_time,
                    k.solar_system_id,
                    k.ship_type_id,
                    k.ship_value,
                    k.victim_alliance_id,
                    k.attacker_count,
                    (SELECT json_agg(json_build_object(
                        'alliance_id', ka.alliance_id,
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

            if not killmails:
                return stats

            # Group by alliance_id
            alliance_data = {}

            for km in killmails:
                attackers = km['attackers'] if km['attackers'] else []

                alliances_involved = set()

                if km['victim_alliance_id']:
                    alliances_involved.add(km['victim_alliance_id'])

                for attacker in attackers:
                    if attacker.get('alliance_id'):
                        alliances_involved.add(attacker['alliance_id'])

                for alliance_id in alliances_involved:
                    if alliance_id not in alliance_data:
                        alliance_data[alliance_id] = {
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
                            'coalition_allies': {},
                            # Phase B1: solo tracking
                            'solo_kills': 0,
                        }

                    data = alliance_data[alliance_id]

                    is_victim = (km['victim_alliance_id'] == alliance_id)

                    if is_victim:
                        data['deaths'] += 1
                        data['isk_lost'] += km['ship_value'] or 0

                        ship_id = str(km['ship_type_id'])
                        data['ships_lost'][ship_id] = data['ships_lost'].get(ship_id, 0) + 1

                        system_id = str(km['solar_system_id'])
                        data['systems_deaths'][system_id] = data['systems_deaths'].get(system_id, 0) + 1

                        ship_class = classify_victim_ship(km['ship_type_id'])
                        if ship_class not in data['ship_effectiveness']:
                            data['ship_effectiveness'][ship_class] = {"deaths": 0, "isk_lost": 0}
                        data['ship_effectiveness'][ship_class]["deaths"] += 1
                        data['ship_effectiveness'][ship_class]["isk_lost"] += km['ship_value'] or 0

                        if km['ship_value'] and km['ship_value'] > 100_000_000:
                            data['expensive_losses'].append({
                                'killmail_id': km['killmail_id'],
                                'ship_type_id': km['ship_type_id'],
                                'ship_value': km['ship_value'],
                                'system_id': km['solar_system_id']
                            })

                        equip = infer_equipment_profile(km['ship_type_id'])
                        weapon_key = f"weapon_{equip['weapon_class']}"
                        tank_key = f"tank_{equip['tank_type']}"
                        data['equipment_summary'][weapon_key] = data['equipment_summary'].get(weapon_key, 0) + 1
                        data['equipment_summary'][tank_key] = data['equipment_summary'].get(tank_key, 0) + 1

                        damage = calculate_damage_types(attackers)
                        for dt, count in damage.items():
                            data['damage_types'][dt] += count

                        ewar = detect_ewar_attackers(attackers)
                        for ship_class, ewar_data in ewar.items():
                            if ship_class not in data['ewar_threats']:
                                data['ewar_threats'][ship_class] = {"count": 0, "ewar_type": ewar_data["ewar_type"]}
                            data['ewar_threats'][ship_class]["count"] += ewar_data["count"]

                        for attacker in attackers:
                            enemy_id = attacker.get('alliance_id')
                            if enemy_id and enemy_id != alliance_id:
                                enemy_key = str(enemy_id)
                                if enemy_key not in data['killed_by']:
                                    data['killed_by'][enemy_key] = {"kills": 0, "isk": 0}
                                data['killed_by'][enemy_key]["kills"] += 1
                                data['killed_by'][enemy_key]["isk"] += km['ship_value'] or 0

                    else:
                        data['kills'] += 1
                        data['isk_destroyed'] += km['ship_value'] or 0

                        ship_id = str(km['ship_type_id'])
                        data['ships_killed'][ship_id] = data['ships_killed'].get(ship_id, 0) + 1

                        system_id = str(km['solar_system_id'])
                        if system_id not in data['systems_kills']:
                            data['systems_kills'][system_id] = {"kills": 0, "solo_kills": 0, "total_value": 0}
                        data['systems_kills'][system_id]["kills"] += 1

                        attacker_count = len(attackers)
                        if attacker_count <= 3:
                            data['systems_kills'][system_id]["solo_kills"] += 1
                            data['solo_kills'] += 1

                        data['systems_kills'][system_id]["total_value"] += km['ship_value'] or 0

                        if km['victim_alliance_id']:
                            enemy_key = str(km['victim_alliance_id'])
                            if enemy_key not in data['enemies_killed']:
                                data['enemies_killed'][enemy_key] = {"kills": 0, "isk": 0}
                            data['enemies_killed'][enemy_key]["kills"] += 1
                            data['enemies_killed'][enemy_key]["isk"] += km['ship_value'] or 0

                        ally_ids = detect_coalition_allies(attackers, alliance_id)
                        for ally_id in ally_ids:
                            ally_key = str(ally_id)
                            if ally_key not in data['coalition_allies']:
                                data['coalition_allies'][ally_key] = 0
                            data['coalition_allies'][ally_key] += 1

            # Keep only top 5 expensive losses per alliance
            for alliance_id in alliance_data:
                losses = alliance_data[alliance_id]['expensive_losses']
                alliance_data[alliance_id]['expensive_losses'] = sorted(
                    losses, key=lambda x: x['ship_value'], reverse=True
                )[:5]

            # Keep only top 20 coalition allies per alliance (by joint kill count)
            for alliance_id in alliance_data:
                allies = alliance_data[alliance_id]['coalition_allies']
                ally_list = [{"alliance_id": int(k), "joint_kills": v} for k, v in allies.items() if v >= 10]
                sorted_allies = sorted(ally_list, key=lambda x: x['joint_kills'], reverse=True)[:20]
                alliance_data[alliance_id]['coalition_allies'] = sorted_allies

            # Calculate solo_ratio for each alliance
            for alliance_id in alliance_data:
                d = alliance_data[alliance_id]
                d['solo_ratio'] = d['solo_kills'] / d['kills'] if d['kills'] > 0 else 0.0

            # UPSERT into intelligence_hourly_stats
            for alliance_id, data in alliance_data.items():
                cur.execute("""
                    INSERT INTO intelligence_hourly_stats (
                        alliance_id, hour_bucket,
                        kills, deaths, isk_destroyed, isk_lost,
                        ships_killed, ships_lost,
                        systems_kills, systems_deaths,
                        enemies_killed, killed_by,
                        damage_types, ship_effectiveness, ewar_threats, expensive_losses,
                        equipment_summary, coalition_allies,
                        solo_kills, solo_ratio
                    ) VALUES (
                        %s, %s,
                        %s, %s, %s, %s,
                        %s::jsonb, %s::jsonb,
                        %s::jsonb, %s::jsonb,
                        %s::jsonb, %s::jsonb,
                        %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb,
                        %s::jsonb, %s::jsonb,
                        %s, %s
                    )
                    ON CONFLICT (alliance_id, hour_bucket) DO UPDATE SET
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
                        coalition_allies = EXCLUDED.coalition_allies,
                        solo_kills = EXCLUDED.solo_kills,
                        solo_ratio = EXCLUDED.solo_ratio,
                        updated_at = NOW()
                """, (
                    alliance_id, hour_start,
                    data['kills'], data['deaths'], data['isk_destroyed'], data['isk_lost'],
                    json.dumps(data['ships_killed']), json.dumps(data['ships_lost']),
                    json.dumps(data['systems_kills']), json.dumps(data['systems_deaths']),
                    json.dumps(data['enemies_killed']), json.dumps(data['killed_by']),
                    json.dumps(data['damage_types']), json.dumps(data['ship_effectiveness']),
                    json.dumps(data['ewar_threats']), json.dumps(data['expensive_losses']),
                    json.dumps(data['equipment_summary']), json.dumps(data['coalition_allies']),
                    data['solo_kills'], data['solo_ratio']
                ))
                stats["alliances_updated"] += 1

            conn.commit()

    return stats


# ---------------------------------------------------------------------------
# Runner with error handling + progress
# ---------------------------------------------------------------------------

def run_aggregator(start_time: datetime = None, end_time: datetime = None, verbose: bool = False):
    """Run the hourly stats aggregator with per-hour error handling and progress logging."""
    if not start_time:
        start_time = datetime.now() - timedelta(hours=2)
    if not end_time:
        end_time = datetime.now()

    start_hour = start_time.replace(minute=0, second=0, microsecond=0)
    end_hour = end_time.replace(minute=0, second=0, microsecond=0)

    # Pre-load SDE cache before processing
    load_sde_cache()

    total_hours = int((end_hour - start_hour).total_seconds() / 3600)
    logger.info(f"Aggregating intelligence_hourly_stats: {start_hour} → {end_hour} ({total_hours} hours)")

    total_rows = 0
    total_alliances = 0
    failed_hours = []
    processed = 0
    run_start = time.time()

    current_hour = start_hour
    while current_hour < end_hour:
        next_hour = current_hour + timedelta(hours=1)
        processed += 1

        try:
            hour_start_t = time.time()
            stats = aggregate_hour(current_hour, next_hour, verbose=verbose)
            elapsed = time.time() - hour_start_t

            total_rows += stats["rows_processed"]
            total_alliances += stats["alliances_updated"]

            # Progress logging
            if verbose or processed % 24 == 0:
                total_elapsed = time.time() - run_start
                avg_per_hour = total_elapsed / processed
                remaining = (total_hours - processed) * avg_per_hour
                eta_min = remaining / 60

                logger.info(
                    f"[{processed}/{total_hours}] {current_hour.strftime('%Y-%m-%d %H:%M')} "
                    f"— {stats['rows_processed']} km, {stats['alliances_updated']} alliances "
                    f"({elapsed:.1f}s) — ETA {eta_min:.0f}min"
                )

        except Exception as e:
            failed_hours.append(current_hour)
            logger.error(f"[{processed}/{total_hours}] {current_hour.strftime('%Y-%m-%d %H:%M')} — ERROR: {e}")

        current_hour = next_hour

    total_elapsed = time.time() - run_start
    logger.info(f"Aggregation complete in {total_elapsed / 60:.1f}min:")
    logger.info(f"  {total_rows} killmails → {total_alliances} alliance-hour updates")
    if failed_hours:
        logger.warning(f"  {len(failed_hours)} failed hours (will retry on next run):")
        for h in failed_hours[:10]:
            logger.warning(f"    {h}")

    return {
        "success": True,
        "rows_processed": total_rows,
        "alliances_updated": total_alliances,
        "failed_hours": len(failed_hours),
        "start_time": start_hour.isoformat(),
        "end_time": end_hour.isoformat()
    }


def main():
    parser = argparse.ArgumentParser(description='Intelligence Hourly Stats Aggregator')
    parser.add_argument('--backfill', action='store_true', help='Backfill mode')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')

    args = parser.parse_args()

    if args.backfill:
        if not args.start_date or not args.end_date:
            logger.error("--start-date and --end-date required for backfill mode")
            sys.exit(1)

        start_time = datetime.strptime(args.start_date, '%Y-%m-%d')
        end_time = datetime.strptime(args.end_date, '%Y-%m-%d')
    else:
        start_time = None
        end_time = None

    result = run_aggregator(start_time, end_time, verbose=args.verbose)

    if result["success"]:
        logger.info(f"Success: {result['rows_processed']} killmails → {result['alliances_updated']} updates")
        if result["failed_hours"] > 0:
            logger.warning(f"{result['failed_hours']} hours failed")
        sys.exit(0)
    else:
        logger.error(f"Failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
