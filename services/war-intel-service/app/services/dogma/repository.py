# app/services/dogma/repository.py
"""Database repository for Dogma Engine - ship and module stats from SDE."""

import logging
from typing import Optional, List, Dict, Any
from psycopg2.extras import RealDictCursor

from app.database import db_cursor
from .models import (
    ShipBaseStats,
    TankModuleEffect,
    ResistProfile,
    ModuleSlot,
    FittedModule,
)

logger = logging.getLogger(__name__)

# =============================================================================
# SDE Attribute IDs
# =============================================================================

# Hit Points
ATTR_SHIELD_HP = 263  # shieldCapacity
ATTR_ARMOR_HP = 265   # armorHP
ATTR_HULL_HP = 9      # hp (structure)

# Shield Resistances (1.0 = 0% resist, 0.5 = 50% resist)
ATTR_SHIELD_EM = 271       # shieldEmDamageResonance
ATTR_SHIELD_THERMAL = 274  # shieldThermalDamageResonance
ATTR_SHIELD_KINETIC = 273  # shieldKineticDamageResonance
ATTR_SHIELD_EXPLOSIVE = 272  # shieldExplosiveDamageResonance

# Armor Resistances
ATTR_ARMOR_EM = 267       # armorEmDamageResonance
ATTR_ARMOR_THERMAL = 270  # armorThermalDamageResonance
ATTR_ARMOR_KINETIC = 269  # armorKineticDamageResonance
ATTR_ARMOR_EXPLOSIVE = 268  # armorExplosiveDamageResonance

# Hull Resistances
ATTR_HULL_EM = 113       # emDamageResonance
ATTR_HULL_THERMAL = 110  # thermalDamageResonance
ATTR_HULL_KINETIC = 109  # kineticDamageResonance
ATTR_HULL_EXPLOSIVE = 111  # explosiveDamageResonance

# Other Ship Stats
ATTR_SHIELD_RECHARGE = 479  # shieldRechargeRate (ms)
ATTR_SIGNATURE_RADIUS = 552  # signatureRadius
ATTR_MAX_VELOCITY = 37  # maxVelocity

# Module Effect Attributes
ATTR_SHIELD_BONUS = 72      # shieldBonus (flat HP add)
ATTR_ARMOR_BONUS = 1159     # armorHPBonusAdd (flat HP add)
ATTR_HULL_BONUS = 150       # hpBonusAdd (flat HP add)

# Resist multipliers (for hardeners/membranes)
ATTR_SHIELD_EM_RESIST_BONUS = 271      # Uses same as ship for active modules
ATTR_SHIELD_THERMAL_RESIST_BONUS = 274
ATTR_SHIELD_KINETIC_RESIST_BONUS = 273
ATTR_SHIELD_EXPLOSIVE_RESIST_BONUS = 272

# Signature radius modifier
ATTR_SIG_RADIUS_ADD = 983  # signatureRadiusAdd

# Module Group IDs for classification
GROUP_SHIELD_EXTENDER = 38
GROUP_SHIELD_RECHARGER = 39
GROUP_SHIELD_BOOSTER = 40
GROUP_SHIELD_HARDENER = 77  # Adaptive Invulnerability Field
GROUP_SHIELD_AMPLIFIER = 295  # Resistance Amplifiers
GROUP_ARMOR_PLATE = 329
GROUP_ARMOR_HARDENER = 328  # Energized Adaptive Nano Membrane
GROUP_ARMOR_MEMBRANE = 326  # Armor Coating (passive)
GROUP_ARMOR_REPAIRER = 62
GROUP_HULL_REPAIRER = 63
GROUP_DAMAGE_CONTROL = 60


class DogmaRepository:
    """Repository for ship and module stats from EVE SDE."""

    def get_ship_base_stats(self, ship_type_id: int) -> Optional[ShipBaseStats]:
        """Get base ship stats without any modules.

        Args:
            ship_type_id: Ship type ID

        Returns:
            ShipBaseStats or None if not found
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    t."typeID",
                    t."typeName",
                    -- Hit Points
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as shield_hp,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as armor_hp,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as hull_hp,
                    -- Shield Resists
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as shield_em,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as shield_thermal,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as shield_kinetic,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as shield_explosive,
                    -- Armor Resists
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as armor_em,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as armor_thermal,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as armor_kinetic,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as armor_explosive,
                    -- Hull Resists
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as hull_em,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as hull_thermal,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as hull_kinetic,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as hull_explosive,
                    -- Other
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as shield_recharge,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as signature_radius,
                    MAX(CASE WHEN ta."attributeID" = %s THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as max_velocity
                FROM "invTypes" t
                LEFT JOIN "dgmTypeAttributes" ta ON t."typeID" = ta."typeID"
                WHERE t."typeID" = %s
                GROUP BY t."typeID", t."typeName"
            """, (
                # HP
                ATTR_SHIELD_HP, ATTR_ARMOR_HP, ATTR_HULL_HP,
                # Shield resists
                ATTR_SHIELD_EM, ATTR_SHIELD_THERMAL, ATTR_SHIELD_KINETIC, ATTR_SHIELD_EXPLOSIVE,
                # Armor resists
                ATTR_ARMOR_EM, ATTR_ARMOR_THERMAL, ATTR_ARMOR_KINETIC, ATTR_ARMOR_EXPLOSIVE,
                # Hull resists
                ATTR_HULL_EM, ATTR_HULL_THERMAL, ATTR_HULL_KINETIC, ATTR_HULL_EXPLOSIVE,
                # Other
                ATTR_SHIELD_RECHARGE, ATTR_SIGNATURE_RADIUS, ATTR_MAX_VELOCITY,
                # WHERE
                ship_type_id
            ))

            row = cur.fetchone()
            if not row:
                return None

            return ShipBaseStats(
                ship_type_id=row['typeID'],
                ship_name=row['typeName'],
                shield_hp=row['shield_hp'] or 0,
                armor_hp=row['armor_hp'] or 0,
                hull_hp=row['hull_hp'] or 0,
                shield_resists=ResistProfile(
                    em=row['shield_em'] or 1.0,
                    thermal=row['shield_thermal'] or 1.0,
                    kinetic=row['shield_kinetic'] or 1.0,
                    explosive=row['shield_explosive'] or 1.0,
                ),
                armor_resists=ResistProfile(
                    em=row['armor_em'] or 1.0,
                    thermal=row['armor_thermal'] or 1.0,
                    kinetic=row['armor_kinetic'] or 1.0,
                    explosive=row['armor_explosive'] or 1.0,
                ),
                hull_resists=ResistProfile(
                    em=row['hull_em'] or 1.0,
                    thermal=row['hull_thermal'] or 1.0,
                    kinetic=row['hull_kinetic'] or 1.0,
                    explosive=row['hull_explosive'] or 1.0,
                ),
                shield_recharge_ms=row['shield_recharge'] or 0,
                signature_radius=row['signature_radius'] or 0,
                max_velocity=row['max_velocity'] or 0,
            )

    def get_module_tank_effects(self, type_ids: List[int]) -> Dict[int, TankModuleEffect]:
        """Get tank-related effects for modules.

        Args:
            type_ids: List of module type IDs

        Returns:
            Dict mapping type_id to TankModuleEffect
        """
        if not type_ids:
            return {}

        with db_cursor() as cur:
            # Get module attributes and group info
            # Resist attributes 984-987 are shared across all module types
            # The values are negative percentages (e.g., -32.5 = 32.5% resist bonus)
            cur.execute("""
                SELECT
                    t."typeID",
                    t."typeName",
                    g."groupID",
                    g."groupName",
                    -- HP bonuses
                    MAX(CASE WHEN ta."attributeID" = 72 THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as shield_bonus,
                    MAX(CASE WHEN ta."attributeID" = 1159 THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as armor_bonus,
                    MAX(CASE WHEN ta."attributeID" = 150 THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as hull_bonus,
                    -- Resist bonuses (984-987 are shared, we assign based on group later)
                    MAX(CASE WHEN ta."attributeID" = 984 THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as em_resist_bonus,
                    MAX(CASE WHEN ta."attributeID" = 985 THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as explosive_resist_bonus,
                    MAX(CASE WHEN ta."attributeID" = 986 THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as kinetic_resist_bonus,
                    MAX(CASE WHEN ta."attributeID" = 987 THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as thermal_resist_bonus,
                    -- Signature radius add
                    MAX(CASE WHEN ta."attributeID" = 983 THEN COALESCE(ta."valueFloat", ta."valueInt"::float) END) as sig_radius_add
                FROM "invTypes" t
                JOIN "invGroups" g ON t."groupID" = g."groupID"
                LEFT JOIN "dgmTypeAttributes" ta ON t."typeID" = ta."typeID"
                WHERE t."typeID" = ANY(%s)
                GROUP BY t."typeID", t."typeName", g."groupID", g."groupName"
            """, (type_ids,))

            results = {}
            for row in cur.fetchall():
                group_id = row['groupID']

                # Determine slot and module type based on group
                is_shield = group_id in (
                    GROUP_SHIELD_EXTENDER, GROUP_SHIELD_RECHARGER,
                    GROUP_SHIELD_BOOSTER, GROUP_SHIELD_HARDENER,
                    GROUP_SHIELD_AMPLIFIER
                )
                is_armor = group_id in (
                    GROUP_ARMOR_PLATE, GROUP_ARMOR_HARDENER,
                    GROUP_ARMOR_MEMBRANE, GROUP_ARMOR_REPAIRER
                )
                is_hull = group_id in (GROUP_HULL_REPAIRER,)
                is_damage_control = group_id == GROUP_DAMAGE_CONTROL

                # Determine slot (shield mods are mid, armor mods are low)
                if is_shield:
                    slot = ModuleSlot.MID
                elif is_armor or is_damage_control:
                    slot = ModuleSlot.LOW
                else:
                    slot = ModuleSlot.LOW  # Default

                # Check if active module (boosters, repairers)
                is_active = group_id in (
                    GROUP_SHIELD_BOOSTER, GROUP_ARMOR_REPAIRER,
                    GROUP_HULL_REPAIRER
                )

                # Check if resist module
                is_resist = group_id in (
                    GROUP_SHIELD_HARDENER, GROUP_SHIELD_AMPLIFIER,
                    GROUP_ARMOR_HARDENER, GROUP_ARMOR_MEMBRANE,
                    GROUP_DAMAGE_CONTROL
                )

                # Check if HP module
                is_hp = group_id in (
                    GROUP_SHIELD_EXTENDER, GROUP_ARMOR_PLATE
                )

                # Convert resist bonus percentages to multipliers
                # SDE stores as negative percentages (e.g., -32.5 = 32.5% resist bonus)
                # We need multipliers: -32.5% -> 0.675 (damage taken is 67.5%)
                def resist_to_mult(value):
                    if value is None:
                        return 1.0
                    # Convert percentage to multiplier: -32.5 -> 1 + (-32.5/100) = 0.675
                    return 1.0 + (value / 100.0)

                em_mult = resist_to_mult(row['em_resist_bonus'])
                thermal_mult = resist_to_mult(row['thermal_resist_bonus'])
                kinetic_mult = resist_to_mult(row['kinetic_resist_bonus'])
                explosive_mult = resist_to_mult(row['explosive_resist_bonus'])

                # Assign resist multipliers based on module type
                # Shield modules affect shield, armor modules affect armor
                # Damage Control affects both (special case)
                if is_shield:
                    shield_em = em_mult
                    shield_thermal = thermal_mult
                    shield_kinetic = kinetic_mult
                    shield_explosive = explosive_mult
                    armor_em = armor_thermal = armor_kinetic = armor_explosive = 1.0
                elif is_armor:
                    armor_em = em_mult
                    armor_thermal = thermal_mult
                    armor_kinetic = kinetic_mult
                    armor_explosive = explosive_mult
                    shield_em = shield_thermal = shield_kinetic = shield_explosive = 1.0
                elif is_damage_control:
                    # Damage Control affects both shield and armor
                    shield_em = armor_em = em_mult
                    shield_thermal = armor_thermal = thermal_mult
                    shield_kinetic = armor_kinetic = kinetic_mult
                    shield_explosive = armor_explosive = explosive_mult
                else:
                    shield_em = shield_thermal = shield_kinetic = shield_explosive = 1.0
                    armor_em = armor_thermal = armor_kinetic = armor_explosive = 1.0

                results[row['typeID']] = TankModuleEffect(
                    type_id=row['typeID'],
                    type_name=row['typeName'],
                    slot=slot,
                    shield_hp_bonus=row['shield_bonus'] or 0,
                    armor_hp_bonus=row['armor_bonus'] or 0,
                    hull_hp_bonus=row['hull_bonus'] or 0,
                    shield_em_resist_mult=shield_em,
                    shield_thermal_resist_mult=shield_thermal,
                    shield_kinetic_resist_mult=shield_kinetic,
                    shield_explosive_resist_mult=shield_explosive,
                    armor_em_resist_mult=armor_em,
                    armor_thermal_resist_mult=armor_thermal,
                    armor_kinetic_resist_mult=armor_kinetic,
                    armor_explosive_resist_mult=armor_explosive,
                    signature_radius_add=row['sig_radius_add'] or 0,
                    is_shield_module=is_shield,
                    is_armor_module=is_armor,
                    is_hull_module=is_hull,
                    is_resist_module=is_resist,
                    is_hp_module=is_hp,
                    is_active_module=is_active,
                )

            return results

    def get_killmail_victim_items(self, killmail_id: int) -> List[FittedModule]:
        """Get fitted modules from a killmail's victim.

        Args:
            killmail_id: Killmail ID

        Returns:
            List of FittedModule objects (low/mid/high/rig slots only)
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    ki.item_type_id,
                    ki.flag,
                    ki.quantity,
                    ki.was_destroyed
                FROM killmail_items ki
                WHERE ki.killmail_id = %s
                AND ki.flag BETWEEN 11 AND 99
                ORDER BY ki.flag
            """, (killmail_id,))

            return [
                FittedModule(
                    type_id=row['item_type_id'],
                    flag=row['flag'],
                    quantity=row['quantity'] or 1,
                    was_destroyed=row['was_destroyed']
                )
                for row in cur.fetchall()
            ]

    def get_killmail_attackers(self, killmail_id: int) -> List[Dict[str, Any]]:
        """Get attacker data from a killmail.

        Args:
            killmail_id: Killmail ID

        Returns:
            List of attacker dicts with ship/weapon info
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    ka.character_id,
                    ka.corporation_id,
                    ka.alliance_id,
                    ka.ship_type_id,
                    s."typeName" as ship_name,
                    ka.weapon_type_id,
                    w."typeName" as weapon_name,
                    ka.damage_done,
                    ka.is_final_blow
                FROM killmail_attackers ka
                LEFT JOIN "invTypes" s ON ka.ship_type_id = s."typeID"
                LEFT JOIN "invTypes" w ON ka.weapon_type_id = w."typeID"
                WHERE ka.killmail_id = %s
                ORDER BY ka.damage_done DESC
            """, (killmail_id,))

            return [dict(row) for row in cur.fetchall()]

    def get_killmail_info(self, killmail_id: int) -> Optional[Dict[str, Any]]:
        """Get basic killmail info including victim ship.

        Args:
            killmail_id: Killmail ID

        Returns:
            Dict with killmail info or None
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT
                    k.killmail_id,
                    k.killmail_time,
                    k.solar_system_id,
                    ss."solarSystemName" as solar_system_name,
                    k.ship_type_id,
                    t."typeName" as ship_name
                FROM killmails k
                LEFT JOIN "mapSolarSystems" ss ON k.solar_system_id = ss."solarSystemID"
                LEFT JOIN "invTypes" t ON k.ship_type_id = t."typeID"
                WHERE k.killmail_id = %s
            """, (killmail_id,))

            row = cur.fetchone()
            return dict(row) if row else None

    def get_type_name(self, type_id: int) -> Optional[str]:
        """Get type name from SDE.

        Args:
            type_id: Type ID

        Returns:
            Type name or None
        """
        with db_cursor() as cur:
            cur.execute("""
                SELECT "typeName" FROM "invTypes" WHERE "typeID" = %s
            """, (type_id,))
            row = cur.fetchone()
            return row['typeName'] if row else None

    def get_type_names_bulk(self, type_ids: List[int]) -> Dict[int, str]:
        """Get type names for multiple IDs.

        Args:
            type_ids: List of type IDs

        Returns:
            Dict mapping type_id to name
        """
        if not type_ids:
            return {}

        with db_cursor() as cur:
            cur.execute("""
                SELECT "typeID", "typeName"
                FROM "invTypes"
                WHERE "typeID" = ANY(%s)
            """, (type_ids,))

            return {row['typeID']: row['typeName'] for row in cur.fetchall()}
