# app/services/dps/repository.py
"""Database repository for DPS calculation data.

Uses eve_shared pattern for database access.
"""

import logging
from typing import Optional, List, Dict, Any
from psycopg2.extras import RealDictCursor

from app.database import db_cursor
from .models import WeaponAttributes, AmmoAttributes, ShipBonus, DamageProfile

logger = logging.getLogger(__name__)

# SDE Attribute IDs
ATTR_EM_DAMAGE = 114
ATTR_THERMAL_DAMAGE = 118
ATTR_KINETIC_DAMAGE = 117
ATTR_EXPLOSIVE_DAMAGE = 116
ATTR_RATE_OF_FIRE = 51
ATTR_DAMAGE_MODIFIER = 64
ATTR_OPTIMAL_RANGE = 54
ATTR_FALLOFF = 158
ATTR_TRACKING = 160


class DPSRepository:
    """Repository for weapon, ammo, and ship bonus data from SDE."""

    def get_weapon_attributes(self, type_id: int) -> Optional[WeaponAttributes]:
        """Get weapon module attributes.

        Args:
            type_id: Weapon type ID

        Returns:
            WeaponAttributes or None if not found
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    t."typeID",
                    t."typeName",
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as rate_of_fire,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as damage_modifier,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as optimal,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as falloff,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as tracking
                FROM "invTypes" t
                LEFT JOIN "dgmTypeAttributes" ta ON t."typeID" = ta."typeID"
                WHERE t."typeID" = %s
                GROUP BY t."typeID", t."typeName"
            """, (
                ATTR_RATE_OF_FIRE, ATTR_DAMAGE_MODIFIER, ATTR_OPTIMAL_RANGE,
                ATTR_FALLOFF, ATTR_TRACKING, type_id
            ))

            row = cur.fetchone()
            if not row or not row['rate_of_fire']:
                return None

            return WeaponAttributes(
                type_id=row['typeID'],
                type_name=row['typeName'],
                rate_of_fire_ms=row['rate_of_fire'],
                damage_modifier=row['damage_modifier'] or 1.0,
                optimal_range=row['optimal'],
                falloff=row['falloff'],
                tracking=row['tracking']
            )

    def get_ammo_attributes(self, type_id: int) -> Optional[AmmoAttributes]:
        """Get ammunition damage attributes.

        Args:
            type_id: Ammo type ID

        Returns:
            AmmoAttributes or None if not found
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    t."typeID",
                    t."typeName",
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as em_damage,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as thermal_damage,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as kinetic_damage,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as explosive_damage,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as damage_modifier
                FROM "invTypes" t
                LEFT JOIN "dgmTypeAttributes" ta ON t."typeID" = ta."typeID"
                WHERE t."typeID" = %s
                GROUP BY t."typeID", t."typeName"
            """, (
                ATTR_EM_DAMAGE, ATTR_THERMAL_DAMAGE, ATTR_KINETIC_DAMAGE,
                ATTR_EXPLOSIVE_DAMAGE, ATTR_DAMAGE_MODIFIER, type_id
            ))

            row = cur.fetchone()
            if not row:
                return None

            return AmmoAttributes(
                type_id=row['typeID'],
                type_name=row['typeName'],
                damage=DamageProfile(
                    em=row['em_damage'] or 0,
                    thermal=row['thermal_damage'] or 0,
                    kinetic=row['kinetic_damage'] or 0,
                    explosive=row['explosive_damage'] or 0
                ),
                damage_modifier=row['damage_modifier'] or 1.0
            )

    def get_ship_damage_bonuses(self, ship_type_id: int) -> List[ShipBonus]:
        """Get ship damage-related bonuses from invTraits.

        Args:
            ship_type_id: Ship type ID

        Returns:
            List of ShipBonus objects
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    tr."typeID",
                    t."typeName",
                    tr."skillID",
                    s."typeName" as skill_name,
                    tr."bonus",
                    tr."bonusText"
                FROM "invTraits" tr
                JOIN "invTypes" t ON tr."typeID" = t."typeID"
                LEFT JOIN "invTypes" s ON tr."skillID" = s."typeID"
                WHERE tr."typeID" = %s
                AND (
                    tr."bonusText" ILIKE '%%damage%%'
                    OR tr."bonusText" ILIKE '%%rate of fire%%'
                )
            """, (ship_type_id,))

            bonuses = []
            for row in cur.fetchall():
                bonus_type = 'damage' if 'damage' in row['bonusText'].lower() else 'rate_of_fire'
                bonuses.append(ShipBonus(
                    ship_type_id=row['typeID'],
                    ship_name=row['typeName'],
                    skill_id=row['skillID'],
                    skill_name=row['skill_name'],
                    bonus_value=row['bonus'],
                    bonus_type=bonus_type,
                    is_role_bonus=(row['skillID'] == -1)
                ))

            return bonuses

    def get_skill_damage_bonuses(self, skill_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Get damage-related bonuses for skills.

        Args:
            skill_ids: List of skill type IDs

        Returns:
            Dict mapping skill_id to bonus attributes
        """
        if not skill_ids:
            return {}

        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    t."typeID",
                    t."typeName",
                    a."attributeName",
                    COALESCE(ta."valueFloat", ta."valueInt"::float) as value
                FROM "invTypes" t
                JOIN "dgmTypeAttributes" ta ON t."typeID" = ta."typeID"
                JOIN "dgmAttributeTypes" a ON ta."attributeID" = a."attributeID"
                WHERE t."typeID" = ANY(%s)
                AND (
                    a."attributeName" ILIKE '%%damage%%bonus%%'
                    OR a."attributeName" ILIKE '%%rate%%fire%%bonus%%'
                )
            """, (skill_ids,))

            result = {}
            for row in cur.fetchall():
                skill_id = row['typeID']
                if skill_id not in result:
                    result[skill_id] = {
                        'skill_name': row['typeName'],
                        'bonuses': {}
                    }
                result[skill_id]['bonuses'][row['attributeName']] = row['value']

            return result

    def search_weapons(self, name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search weapons by name.

        Args:
            name: Search term
            limit: Max results

        Returns:
            List of matching weapons with type_id and name
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT t."typeID", t."typeName", g."groupName"
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE t."typeName" ILIKE %s
                AND t."published" = 1
                AND g."categoryID" = 7
                AND (
                    g."groupName" ILIKE '%%turret%%'
                    OR g."groupName" ILIKE '%%launcher%%'
                    OR g."groupName" ILIKE '%%weapon%%'
                )
                AND g."groupName" NOT ILIKE '%%blueprint%%'
                ORDER BY t."typeName"
                LIMIT %s
            """, (f'%{name}%', limit))

            return [dict(row) for row in cur.fetchall()]

    def search_ammo(self, name: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search ammunition by name.

        Args:
            name: Search term
            limit: Max results

        Returns:
            List of matching ammo with type_id and name
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT t."typeID", t."typeName", g."groupName"
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                WHERE t."typeName" ILIKE %s
                AND t."published" = 1
                AND g."categoryID" = 8
                ORDER BY t."typeName"
                LIMIT %s
            """, (f'%{name}%', limit))

            return [dict(row) for row in cur.fetchall()]
