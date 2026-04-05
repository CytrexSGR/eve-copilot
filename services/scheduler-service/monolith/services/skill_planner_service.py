"""
Skill Planner Service
Calculates training times and optimal attribute remaps.
"""

import math
from typing import List, Dict, Optional
from dataclasses import dataclass
from src.database import get_db_connection
from psycopg2.extras import RealDictCursor


ATTRIBUTES = ['perception', 'memory', 'willpower', 'intelligence', 'charisma']
TOTAL_POINTS = 99
MIN_ATTR = 17
MAX_ATTR = 27

# Attribute ID mapping for SDE
ATTR_IDS = {
    164: 'charisma',
    165: 'intelligence',
    166: 'memory',
    167: 'perception',
    168: 'willpower',
}


@dataclass
class SkillItem:
    item_id: int
    skill_type_id: int
    skill_name: str
    rank: int
    from_level: int
    to_level: int
    primary_attribute: str
    secondary_attribute: str
    sp_required: int = 0
    training_seconds: int = 0


@dataclass
class RemapSuggestion:
    after_item_id: Optional[int]
    after_skill_name: str
    new_attributes: Dict[str, int]
    time_saved_seconds: int


def sp_for_level(rank: int, level: int) -> int:
    """Calculate total SP required to reach a level."""
    if level <= 0:
        return 0
    return int(250 * rank * (math.sqrt(32) ** (level - 1)))


def sp_between_levels(rank: int, from_level: int, to_level: int) -> int:
    """Calculate SP required to train from one level to another."""
    return sp_for_level(rank, to_level) - sp_for_level(rank, from_level)


def sp_per_minute(primary: int, secondary: int) -> float:
    """Calculate SP gained per minute."""
    return primary + secondary / 2


def training_seconds(sp_needed: int, primary: int, secondary: int) -> int:
    """Calculate training time in seconds."""
    spm = sp_per_minute(primary, secondary)
    if spm <= 0:
        return 0
    return int((sp_needed / spm) * 60)


def format_duration(seconds: int) -> str:
    """Format seconds to human readable duration."""
    if seconds <= 0:
        return "0s"

    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60

    if days > 0:
        return f"{days}d {hours}h"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"


def calculate_optimal_attributes(skills: List[SkillItem]) -> Dict[str, int]:
    """
    Calculate optimal attribute distribution for a skill plan.
    Weights by SP needed (primary: 1.0, secondary: 0.5).
    """
    weighted = {attr: 0.0 for attr in ATTRIBUTES}

    for skill in skills:
        sp = sp_between_levels(skill.rank, skill.from_level, skill.to_level)
        weighted[skill.primary_attribute] += sp * 1.0
        weighted[skill.secondary_attribute] += sp * 0.5

    total_weight = sum(weighted.values())
    if total_weight == 0:
        return {'perception': 20, 'memory': 20, 'willpower': 20, 'intelligence': 20, 'charisma': 19}

    # Start with minimum
    result = {attr: MIN_ATTR for attr in ATTRIBUTES}
    remaining = TOTAL_POINTS - (MIN_ATTR * 5)  # 14 points

    # Distribute by weight
    sorted_attrs = sorted(ATTRIBUTES, key=lambda a: weighted[a], reverse=True)
    for attr in sorted_attrs:
        if remaining <= 0:
            break
        want = int((weighted[attr] / total_weight) * 14)
        add = min(MAX_ATTR - result[attr], want, remaining)
        result[attr] += add
        remaining -= add

    # Distribute remainder
    while remaining > 0:
        for attr in sorted_attrs:
            if result[attr] < MAX_ATTR:
                result[attr] += 1
                remaining -= 1
                break
        else:
            break

    return result


def find_remap_points(
    items: List[SkillItem],
    current_attrs: Dict[str, int],
    implant_bonuses: Dict[str, int]
) -> List[RemapSuggestion]:
    """
    Find points in plan where a remap saves significant time (>1 day).
    """
    suggestions = []
    attrs = current_attrs.copy()

    for i in range(1, len(items)):
        remaining = items[i:]
        if not remaining:
            continue

        optimal = calculate_optimal_attributes(remaining)

        # Calculate time with current vs optimal
        time_current = sum(
            training_seconds(
                sp_between_levels(s.rank, s.from_level, s.to_level),
                attrs[s.primary_attribute] + implant_bonuses.get(s.primary_attribute, 0),
                attrs[s.secondary_attribute] + implant_bonuses.get(s.secondary_attribute, 0)
            )
            for s in remaining
        )

        time_optimal = sum(
            training_seconds(
                sp_between_levels(s.rank, s.from_level, s.to_level),
                optimal[s.primary_attribute] + implant_bonuses.get(s.primary_attribute, 0),
                optimal[s.secondary_attribute] + implant_bonuses.get(s.secondary_attribute, 0)
            )
            for s in remaining
        )

        time_saved = time_current - time_optimal

        # Only suggest if saves > 1 day
        if time_saved > 86400:
            suggestions.append(RemapSuggestion(
                after_item_id=items[i-1].item_id,
                after_skill_name=items[i-1].skill_name,
                new_attributes=optimal,
                time_saved_seconds=time_saved
            ))
            attrs = optimal

    return suggestions


class SkillPlannerService:
    """Service for skill plan calculations."""

    def get_skill_info(self, skill_type_ids: List[int]) -> Dict[int, dict]:
        """Get skill info from SDE."""
        if not skill_type_ids:
            return {}

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        t."typeID" as type_id,
                        t."typeName" as type_name,
                        COALESCE(rank.value, 1) as rank,
                        COALESCE(primary_attr.value, 167) as primary_attr_id,
                        COALESCE(secondary_attr.value, 168) as secondary_attr_id
                    FROM "invTypes" t
                    LEFT JOIN (SELECT "typeID", COALESCE("valueInt","valueFloat")::int as value FROM "dgmTypeAttributes" WHERE "attributeID" = 275) rank ON rank."typeID" = t."typeID"
                    LEFT JOIN (SELECT "typeID", COALESCE("valueInt","valueFloat")::int as value FROM "dgmTypeAttributes" WHERE "attributeID" = 180) primary_attr ON primary_attr."typeID" = t."typeID"
                    LEFT JOIN (SELECT "typeID", COALESCE("valueInt","valueFloat")::int as value FROM "dgmTypeAttributes" WHERE "attributeID" = 181) secondary_attr ON secondary_attr."typeID" = t."typeID"
                    WHERE t."typeID" = ANY(%s)
                """, (skill_type_ids,))
                rows = cur.fetchall()

        result = {}
        for row in rows:
            result[row['type_id']] = {
                'type_name': row['type_name'],
                'rank': row['rank'],
                'primary_attribute': ATTR_IDS.get(row['primary_attr_id'], 'perception'),
                'secondary_attribute': ATTR_IDS.get(row['secondary_attr_id'], 'willpower'),
            }
        return result

    def get_character_skill_levels(self, character_id: int) -> Dict[int, int]:
        """Get character's current skill levels."""
        from src.character import character_api
        result = character_api.get_skills(character_id)
        skills = result.get('skills', [])
        return {s['skill_id']: s.get('trained_skill_level', s.get('level', 0)) for s in skills}

    def calculate_plan(
        self,
        plan_id: int,
        character_id: int,
        attributes: Dict[str, int],
        implant_bonuses: Dict[str, int]
    ) -> dict:
        """Calculate full plan with training times and remap suggestions."""

        # Get plan items
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, skill_type_id, target_level, sort_order, notes
                    FROM skill_plan_items
                    WHERE plan_id = %s
                    ORDER BY sort_order
                """, (plan_id,))
                items_raw = cur.fetchall()

        if not items_raw:
            return {
                'plan_id': plan_id,
                'character_id': character_id,
                'items': [],
                'total_training_time_seconds': 0,
                'total_training_time_formatted': '0s',
                'optimal_attributes': attributes,
                'remap_suggestions': []
            }

        # Get skill info
        skill_ids = [i['skill_type_id'] for i in items_raw]
        skill_info = self.get_skill_info(skill_ids)

        # Get character's current levels
        char_levels = self.get_character_skill_levels(character_id)

        # Build skill items
        items: List[SkillItem] = []
        for item in items_raw:
            info = skill_info.get(item['skill_type_id'], {})
            from_level = char_levels.get(item['skill_type_id'], 0)

            # Skip if already trained to target
            if from_level >= item['target_level']:
                continue

            skill = SkillItem(
                item_id=item['id'],
                skill_type_id=item['skill_type_id'],
                skill_name=info.get('type_name', 'Unknown'),
                rank=info.get('rank', 1),
                from_level=from_level,
                to_level=item['target_level'],
                primary_attribute=info.get('primary_attribute', 'perception'),
                secondary_attribute=info.get('secondary_attribute', 'willpower'),
            )

            # Calculate SP and time
            skill.sp_required = sp_between_levels(skill.rank, skill.from_level, skill.to_level)
            primary_total = attributes.get(skill.primary_attribute, 20) + implant_bonuses.get(skill.primary_attribute, 0)
            secondary_total = attributes.get(skill.secondary_attribute, 20) + implant_bonuses.get(skill.secondary_attribute, 0)
            skill.training_seconds = training_seconds(skill.sp_required, primary_total, secondary_total)

            items.append(skill)

        # Calculate totals
        total_seconds = sum(s.training_seconds for s in items)
        cumulative = 0
        items_output = []

        for skill in items:
            cumulative += skill.training_seconds
            items_output.append({
                'item_id': skill.item_id,
                'skill_type_id': skill.skill_type_id,
                'skill_name': skill.skill_name,
                'from_level': skill.from_level,
                'to_level': skill.to_level,
                'sp_required': skill.sp_required,
                'training_time_seconds': skill.training_seconds,
                'training_time_formatted': format_duration(skill.training_seconds),
                'cumulative_seconds': cumulative,
                'cumulative_formatted': format_duration(cumulative),
                'primary_attribute': skill.primary_attribute,
                'secondary_attribute': skill.secondary_attribute,
            })

        # Calculate optimal attributes and remap suggestions
        optimal = calculate_optimal_attributes(items)
        remaps = find_remap_points(items, attributes, implant_bonuses)

        return {
            'plan_id': plan_id,
            'character_id': character_id,
            'items': items_output,
            'total_training_time_seconds': total_seconds,
            'total_training_time_formatted': format_duration(total_seconds),
            'optimal_attributes': optimal,
            'remap_suggestions': [
                {
                    'after_item_id': r.after_item_id,
                    'after_skill_name': r.after_skill_name,
                    'new_attributes': r.new_attributes,
                    'time_saved_seconds': r.time_saved_seconds,
                    'time_saved_formatted': format_duration(r.time_saved_seconds),
                }
                for r in remaps
            ]
        }


skill_planner_service = SkillPlannerService()
