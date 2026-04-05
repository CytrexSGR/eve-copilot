"""
Pilot Skill Estimates Job

Calculates minimum skillpoints required for each pilot based on
ships and modules they've used in combat.

Data Sources:
- Ships flown (from kills as attacker)
- Ships lost (from kills as victim)
- Weapons used (from kills as attacker)
- Fitted modules from losses (killmail_items)

Uses:
- Ship Masteries (certMasteries + certSkills) for categorized ship skills
- Equipment Requirements (dgmTypeAttributes) for module skills

Runs daily for pilots in active alliances.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple, Set
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from psycopg2.extras import Json

logger = logging.getLogger(__name__)

# Database connection settings
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "eve_sde",
    "user": "eve",
    "password": os.environ.get("DB_PASSWORD", "")
}

# SP formula: 250 × Multiplier × (√32)^(Level-1)
# Pre-calculated SP per level for multiplier = 1
SP_PER_LEVEL = {
    1: 250,
    2: 1414,
    3: 8000,
    4: 45255,
    5: 256000
}

# Ship category ID in SDE (to filter ships from weapons)
SHIP_CATEGORY_ID = 6


@contextmanager
def db_cursor():
    """Database cursor context manager."""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        yield cur
    finally:
        conn.close()


def get_skill_info(cur, skill_ids: Set[int]) -> Dict[int, Dict[str, Any]]:
    """Get skill names and multipliers."""
    if not skill_ids:
        return {}

    cur.execute("""
        SELECT t."typeID" as skill_id,
               t."typeName" as skill_name,
               COALESCE(a."valueFloat", a."valueInt"::float, 1) as multiplier
        FROM "invTypes" t
        LEFT JOIN "dgmTypeAttributes" a ON t."typeID" = a."typeID" AND a."attributeID" = 275
        WHERE t."typeID" = ANY(%s)
    """, (list(skill_ids),))

    return {
        r['skill_id']: {
            'name': r['skill_name'],
            'multiplier': r['multiplier'] or 1
        }
        for r in cur.fetchall()
    }


def get_ship_mastery_skills(cur, ship_ids: List[int]) -> Dict[str, Dict[int, int]]:
    """
    Get skills from ship masteries (level 0 = basic mastery).

    Returns: {category_name: {skill_id: level}}
    """
    if not ship_ids:
        return {}

    # Get mastery skills for all ships at basic level (masteryLevel = 0)
    cur.execute("""
        SELECT DISTINCT
            c.name as category,
            cs."skillID" as skill_id,
            cs."skillLevel" as skill_level
        FROM "certMasteries" cm
        JOIN "certCerts" c ON c."certID" = cm."certID"
        JOIN "certSkills" cs ON cs."certID" = cm."certID"
            AND cs."certLevelInt" = cm."masteryLevel"
        WHERE cm."typeID" = ANY(%s)
          AND cm."masteryLevel" = 0
          AND cs."skillLevel" > 0
    """, (ship_ids,))

    categories: Dict[str, Dict[int, int]] = {}
    for r in cur.fetchall():
        cat = r['category']
        skill_id = r['skill_id']
        level = r['skill_level']

        if cat not in categories:
            categories[cat] = {}

        # Keep highest level if skill appears multiple times
        if skill_id not in categories[cat] or level > categories[cat][skill_id]:
            categories[cat][skill_id] = level

    return categories


def get_ship_skill_requirements(cur, ship_ids: List[int]) -> Dict[int, int]:
    """
    Get direct ship skill requirements (the actual ship skill needed).

    Returns: {skill_id: level}
    """
    if not ship_ids:
        return {}

    # Get primary skill requirements for ships
    cur.execute("""
        SELECT DISTINCT
            COALESCE(skill."valueFloat", skill."valueInt")::int as skill_id,
            COALESCE(level."valueFloat", level."valueInt")::int as skill_level
        FROM "dgmTypeAttributes" skill
        JOIN "dgmTypeAttributes" level ON level."typeID" = skill."typeID"
        WHERE skill."typeID" = ANY(%s)
          AND skill."attributeID" = 182
          AND level."attributeID" = 277
          AND COALESCE(skill."valueFloat", skill."valueInt") > 0
    """, (ship_ids,))

    result: Dict[int, int] = {}
    for r in cur.fetchall():
        skill_id = r['skill_id']
        level = r['skill_level']
        if skill_id not in result or level > result[skill_id]:
            result[skill_id] = level

    return result


def get_equipment_skill_requirements(cur, type_ids: List[int]) -> Dict[int, List[Tuple[int, int]]]:
    """
    Get skill requirements for equipment (modules, weapons).
    Filters out ships (categoryID = 6).

    Returns: {type_id: [(skill_id, level), ...]}
    """
    if not type_ids:
        return {}

    # Get skill requirements, excluding ships
    cur.execute("""
        SELECT
            a."typeID" as type_id,
            a."attributeID" as attr_id,
            COALESCE(a."valueFloat", a."valueInt"::float) as value
        FROM "dgmTypeAttributes" a
        JOIN "invTypes" t ON t."typeID" = a."typeID"
        JOIN "invGroups" g ON g."groupID" = t."groupID"
        WHERE a."typeID" = ANY(%s)
          AND a."attributeID" IN (182, 183, 184, 277, 278, 279, 1285, 1286, 1287, 1288, 1289, 1290)
          AND g."categoryID" != %s
    """, (type_ids, SHIP_CATEGORY_ID))

    # Group by typeID
    raw_data: Dict[int, Dict[int, float]] = {}
    for r in cur.fetchall():
        type_id = r['type_id']
        attr_id = r['attr_id']
        if type_id not in raw_data:
            raw_data[type_id] = {}
        raw_data[type_id][attr_id] = r['value']

    # Process into skill requirements
    result: Dict[int, List[Tuple[int, int]]] = {}

    # Skill/Level attribute pairs
    skill_level_pairs = [
        (182, 277), (183, 278), (184, 279),
        (1285, 1286), (1289, 1287), (1290, 1288)
    ]

    for type_id, attrs in raw_data.items():
        skills = []
        for skill_attr, level_attr in skill_level_pairs:
            if skill_attr in attrs and level_attr in attrs:
                skill_id = int(attrs[skill_attr])
                level = int(attrs[level_attr])
                if skill_id > 0 and level > 0:
                    skills.append((skill_id, level))

        if skills:
            result[type_id] = skills

    return result


def calculate_sp_for_level(multiplier: float, level: int) -> int:
    """Calculate SP needed to train a skill to a specific level."""
    if level < 1 or level > 5:
        return 0
    return int(SP_PER_LEVEL[level] * multiplier)


def calculate_pilot_skills(
    cur,
    character_id: int,
    alliance_id: int,
    days: int = 90
) -> Dict[str, Any]:
    """
    Calculate minimum skillpoints for a pilot based on items used.

    Data sources:
    - Ships flown (from kills as attacker)
    - Ships lost (from kills as victim)
    - Weapons used (from kills as attacker)
    - Fitted modules from losses (killmail_items)

    Returns categorized skill breakdown:
    {
        'min_sp': total_sp,
        'categories': {
            'Ships': {'skills': [...], 'sp': ...},
            'Equipment': {'skills': [...], 'sp': ...},
            'Fitted Modules': {'skills': [...], 'sp': ...}
        },
        'ships_analyzed': n,
        'modules_analyzed': n,
        'fitted_modules_analyzed': n
    }
    """
    # Get unique ships flown by this pilot (as attacker)
    cur.execute("""
        SELECT DISTINCT ka.ship_type_id
        FROM killmail_attackers ka
        JOIN killmails k ON ka.killmail_id = k.killmail_id
        WHERE ka.character_id = %s
          AND ka.alliance_id = %s
          AND k.killmail_time > NOW() - INTERVAL '%s days'
          AND ka.ship_type_id IS NOT NULL
          AND ka.ship_type_id > 0
    """, (character_id, alliance_id, days))
    ships_flown = [r['ship_type_id'] for r in cur.fetchall()]

    # Get unique ships lost by this pilot (as victim)
    cur.execute("""
        SELECT DISTINCT k.ship_type_id
        FROM killmails k
        WHERE k.victim_character_id = %s
          AND k.killmail_time > NOW() - INTERVAL '%s days'
          AND k.ship_type_id IS NOT NULL
          AND k.ship_type_id > 0
    """, (character_id, days))
    ships_lost = [r['ship_type_id'] for r in cur.fetchall()]

    # Combine ships flown and lost (unique)
    ship_ids = list(set(ships_flown + ships_lost))

    # Get unique weapons/modules used (as attacker)
    cur.execute("""
        SELECT DISTINCT ka.weapon_type_id
        FROM killmail_attackers ka
        JOIN killmails k ON ka.killmail_id = k.killmail_id
        WHERE ka.character_id = %s
          AND ka.alliance_id = %s
          AND k.killmail_time > NOW() - INTERVAL '%s days'
          AND ka.weapon_type_id IS NOT NULL
          AND ka.weapon_type_id > 0
    """, (character_id, alliance_id, days))
    weapon_ids = [r['weapon_type_id'] for r in cur.fetchall()]

    # Get fitted modules from losses (killmail_items)
    # Flags: 11-18 Low, 19-26 Mid, 27-34 High, 87-93 Drone, 125-132 Rig
    cur.execute("""
        SELECT DISTINCT ki.item_type_id
        FROM killmail_items ki
        JOIN killmails k ON ki.killmail_id = k.killmail_id
        JOIN "invTypes" t ON t."typeID" = ki.item_type_id
        JOIN "invGroups" g ON g."groupID" = t."groupID"
        JOIN "invCategories" c ON c."categoryID" = g."categoryID"
        WHERE k.victim_character_id = %s
          AND k.killmail_time > NOW() - INTERVAL '%s days'
          AND ki.flag BETWEEN 11 AND 132
          AND ki.flag <> 5
          AND c."categoryName" IN ('Module', 'Drone')
    """, (character_id, days))
    fitted_module_ids = [r['item_type_id'] for r in cur.fetchall()]

    if not ship_ids and not weapon_ids and not fitted_module_ids:
        return {
            'min_sp': 0,
            'categories': {},
            'ships_analyzed': 0,
            'modules_analyzed': 0,
            'fitted_modules_analyzed': 0
        }

    # Get DIRECT ship skill requirements (Caldari Battleship, etc.)
    ship_skills = get_ship_skill_requirements(cur, ship_ids)

    # Get mastery skills from ships (categorized support skills)
    mastery_skills = get_ship_mastery_skills(cur, ship_ids)

    # Get equipment requirements (weapons used)
    equipment_skills = get_equipment_skill_requirements(cur, weapon_ids)

    # Get fitted module requirements (from losses)
    fitted_skills = get_equipment_skill_requirements(cur, fitted_module_ids)

    # Count actual modules (excluding ships that appear as weapons)
    cur.execute("""
        SELECT COUNT(DISTINCT ka.weapon_type_id)
        FROM killmail_attackers ka
        JOIN killmails k ON ka.killmail_id = k.killmail_id
        JOIN "invTypes" t ON t."typeID" = ka.weapon_type_id
        JOIN "invGroups" g ON g."groupID" = t."groupID"
        WHERE ka.character_id = %s
          AND ka.alliance_id = %s
          AND k.killmail_time > NOW() - INTERVAL '%s days'
          AND ka.weapon_type_id IS NOT NULL
          AND g."categoryID" != %s
    """, (character_id, alliance_id, days, SHIP_CATEGORY_ID))
    actual_modules = cur.fetchone()['count']

    # Aggregate equipment skills into "Equipment" category
    equipment_aggregated: Dict[int, int] = {}
    for type_id, skills in equipment_skills.items():
        for skill_id, level in skills:
            if skill_id not in equipment_aggregated or level > equipment_aggregated[skill_id]:
                equipment_aggregated[skill_id] = level

    # Aggregate fitted module skills into "Fitted Modules" category
    fitted_aggregated: Dict[int, int] = {}
    for type_id, skills in fitted_skills.items():
        for skill_id, level in skills:
            if skill_id not in fitted_aggregated or level > fitted_aggregated[skill_id]:
                fitted_aggregated[skill_id] = level

    # Build final categories dict - Ships first!
    all_categories: Dict[str, Dict[int, int]] = {}

    # 1. Ships category (direct ship requirements)
    if ship_skills:
        all_categories['Ships'] = ship_skills

    # 2. Add mastery categories (support skills)
    for cat, skills in mastery_skills.items():
        all_categories[cat] = skills

    # 3. Equipment category (weapons used)
    if equipment_aggregated:
        all_categories['Equipment'] = equipment_aggregated

    # 4. Fitted Modules category (from losses)
    if fitted_aggregated:
        all_categories['Fitted Modules'] = fitted_aggregated

    mastery_skills = all_categories

    # Collect all skill IDs for info lookup
    all_skill_ids: Set[int] = set()
    for cat_skills in mastery_skills.values():
        all_skill_ids.update(cat_skills.keys())

    if not all_skill_ids:
        return {
            'min_sp': 0,
            'categories': {},
            'ships_analyzed': len(ship_ids),
            'modules_analyzed': actual_modules,
            'fitted_modules_analyzed': len(fitted_module_ids)
        }

    # Get skill info (names, multipliers)
    skill_info = get_skill_info(cur, all_skill_ids)

    # Build categorized output
    categories: Dict[str, Dict[str, Any]] = {}
    total_sp = 0

    # Track skills we've already counted (avoid double-counting across categories)
    counted_skills: Dict[int, int] = {}  # skill_id -> max_level

    for category, cat_skills in mastery_skills.items():
        cat_data = {
            'skills': [],
            'sp': 0
        }

        for skill_id, level in cat_skills.items():
            info = skill_info.get(skill_id, {'name': f'Skill {skill_id}', 'multiplier': 1})
            sp = calculate_sp_for_level(info['multiplier'], level)

            cat_data['skills'].append({
                'skill_id': skill_id,
                'name': info['name'],
                'level': level,
                'sp': sp,
                'multiplier': info['multiplier']
            })
            cat_data['sp'] += sp

            # Track for total (avoid double counting)
            if skill_id not in counted_skills or level > counted_skills[skill_id]:
                # Subtract old SP if we're upgrading
                if skill_id in counted_skills:
                    old_level = counted_skills[skill_id]
                    old_sp = calculate_sp_for_level(info['multiplier'], old_level)
                    total_sp -= old_sp

                counted_skills[skill_id] = level
                total_sp += sp

        # Sort skills by SP (highest first)
        cat_data['skills'].sort(key=lambda x: -x['sp'])
        categories[category] = cat_data

    return {
        'min_sp': total_sp,
        'categories': categories,
        'ships_analyzed': len(ship_ids),
        'modules_analyzed': actual_modules,
        'fitted_modules_analyzed': len(fitted_module_ids)
    }


def refresh_pilot_skill_estimates(days: int = 90, limit: int = 5000) -> Dict[str, Any]:
    """
    Refresh skill estimates for active pilots.

    Args:
        days: Number of days to analyze
        limit: Max pilots to process per run

    Returns:
        Dict with stats about the refresh operation
    """
    logger.info(f"Starting pilot skill estimates refresh for last {days} days")
    start_time = datetime.now()

    stats = {
        "pilots_processed": 0,
        "pilots_with_skills": 0,
        "total_sp_calculated": 0,
        "errors": 0
    }

    try:
        with db_cursor() as cur:
            # Get active pilots (those with kills in the period)
            # Prioritize pilots not yet analyzed or stale
            cur.execute("""
                SELECT DISTINCT ka.character_id, ka.alliance_id
                FROM killmail_attackers ka
                JOIN killmails k ON ka.killmail_id = k.killmail_id
                LEFT JOIN pilot_skill_estimates pse ON ka.character_id = pse.character_id
                WHERE k.killmail_time > NOW() - INTERVAL '%s days'
                  AND ka.character_id IS NOT NULL
                  AND ka.alliance_id IS NOT NULL
                  AND (pse.character_id IS NULL OR pse.updated_at < NOW() - INTERVAL '7 days')
                ORDER BY ka.character_id
                LIMIT %s
            """, (days, limit))

            pilots = cur.fetchall()
            logger.info(f"Found {len(pilots)} pilots to analyze")

            for pilot in pilots:
                character_id = pilot['character_id']
                alliance_id = pilot['alliance_id']

                try:
                    result = calculate_pilot_skills(cur, character_id, alliance_id, days)

                    # Upsert into cache table
                    cur.execute("""
                        INSERT INTO pilot_skill_estimates
                            (character_id, alliance_id, min_sp, skill_breakdown,
                             ships_analyzed, modules_analyzed, fitted_modules_analyzed, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (character_id) DO UPDATE SET
                            alliance_id = EXCLUDED.alliance_id,
                            min_sp = EXCLUDED.min_sp,
                            skill_breakdown = EXCLUDED.skill_breakdown,
                            ships_analyzed = EXCLUDED.ships_analyzed,
                            modules_analyzed = EXCLUDED.modules_analyzed,
                            fitted_modules_analyzed = EXCLUDED.fitted_modules_analyzed,
                            updated_at = NOW()
                    """, (
                        character_id,
                        alliance_id,
                        result['min_sp'],
                        Json(result['categories']),
                        result['ships_analyzed'],
                        result['modules_analyzed'],
                        result['fitted_modules_analyzed']
                    ))

                    stats["pilots_processed"] += 1
                    if result['min_sp'] > 0:
                        stats["pilots_with_skills"] += 1
                        stats["total_sp_calculated"] += result['min_sp']

                    if stats["pilots_processed"] % 500 == 0:
                        logger.info(f"Processed {stats['pilots_processed']} pilots...")

                except Exception as e:
                    logger.warning(f"Error processing pilot {character_id}: {e}")
                    stats["errors"] += 1

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(
                f"Pilot skill estimates refresh complete: "
                f"{stats['pilots_processed']} pilots, "
                f"{stats['pilots_with_skills']} with skills, "
                f"{stats['total_sp_calculated']:,} total SP, "
                f"in {duration:.1f}s"
            )

            return {
                "success": True,
                "stats": stats,
                "duration_seconds": duration
            }

    except Exception as e:
        logger.exception("Failed to refresh pilot skill estimates")
        return {
            "success": False,
            "error": str(e),
            "stats": stats
        }


if __name__ == "__main__":
    # Test run
    logging.basicConfig(level=logging.INFO)
    result = refresh_pilot_skill_estimates(days=30, limit=100)
    print(result)
