# app/services/dps/service.py
"""DPS Calculator Service - Core calculation logic."""

import math
import logging
from typing import Optional, Dict, List

from .models import (
    WeaponAttributes, AmmoAttributes, DamageProfile,
    ShipBonus, SkillBonus, DPSResult
)
from .repository import DPSRepository

logger = logging.getLogger(__name__)

# Known skill IDs and their bonus types
DAMAGE_SKILLS = {
    3315: ('Surgical Strike', 'damage_multiplier', 0.03),  # +3% per level
    20315: ('Warhead Upgrades', 'damage_multiplier', 0.02),  # +2% per level
}

ROF_SKILLS = {
    3300: ('Gunnery', 'rate_of_fire', -0.02),  # -2% per level (faster)
    3310: ('Rapid Firing', 'rate_of_fire', -0.04),  # -4% per level
    21071: ('Rapid Launch', 'rate_of_fire', -0.03),  # -3% per level
}


class DPSCalculatorService:
    """Service for calculating weapon DPS with all modifiers."""

    def __init__(self, repository: Optional[DPSRepository] = None):
        """Initialize service.

        Args:
            repository: DPS repository for database queries
        """
        self.repository = repository or DPSRepository()

    def calculate_raw_dps(
        self,
        weapon: WeaponAttributes,
        ammo: AmmoAttributes
    ) -> float:
        """Calculate raw DPS without any skill or ship bonuses.

        Formula: (TotalDamage x WeaponDamageMultiplier x AmmoDamageMultiplier) / RoF

        Args:
            weapon: Weapon attributes
            ammo: Ammo attributes

        Returns:
            Raw DPS value
        """
        total_damage = ammo.damage.total
        damage_mod = weapon.damage_modifier * ammo.damage_modifier
        rof_seconds = weapon.rate_of_fire_seconds

        return (total_damage * damage_mod) / rof_seconds

    def calculate_dps(
        self,
        weapon_type_id: int,
        ammo_type_id: int,
        character_skills: Optional[Dict[int, int]] = None,
        ship_type_id: Optional[int] = None,
        ship_skill_levels: Optional[Dict[int, int]] = None
    ) -> Optional[DPSResult]:
        """Calculate complete DPS with all applicable modifiers.

        Args:
            weapon_type_id: Weapon module type ID
            ammo_type_id: Ammunition type ID
            character_skills: Dict of skill_id -> level
            ship_type_id: Ship type ID for ship bonuses
            ship_skill_levels: Dict of ship skill_id -> level

        Returns:
            DPSResult with complete calculation breakdown
        """
        # Fetch base data
        weapon = self.repository.get_weapon_attributes(weapon_type_id)
        ammo = self.repository.get_ammo_attributes(ammo_type_id)

        if not weapon or not ammo:
            logger.warning(f"Weapon {weapon_type_id} or ammo {ammo_type_id} not found")
            return None

        # Calculate raw DPS
        raw_dps = self.calculate_raw_dps(weapon, ammo)

        # Apply skill bonuses
        skill_multiplier = 1.0
        applied_skill_bonuses = []

        if character_skills:
            skill_multiplier, applied_skill_bonuses = self._apply_skill_bonuses(
                character_skills
            )

        # Apply ship bonuses
        ship_multiplier = 1.0
        applied_ship_bonuses = []

        if ship_type_id:
            ship_multiplier, applied_ship_bonuses = self._apply_ship_bonuses(
                ship_type_id,
                ship_skill_levels or {}
            )

        # Calculate final DPS
        total_dps = raw_dps * skill_multiplier * ship_multiplier

        # Scale damage profile
        damage_profile = DamageProfile(
            em=ammo.damage.em * weapon.damage_modifier / weapon.rate_of_fire_seconds * skill_multiplier * ship_multiplier,
            thermal=ammo.damage.thermal * weapon.damage_modifier / weapon.rate_of_fire_seconds * skill_multiplier * ship_multiplier,
            kinetic=ammo.damage.kinetic * weapon.damage_modifier / weapon.rate_of_fire_seconds * skill_multiplier * ship_multiplier,
            explosive=ammo.damage.explosive * weapon.damage_modifier / weapon.rate_of_fire_seconds * skill_multiplier * ship_multiplier
        )

        return DPSResult(
            weapon_name=weapon.type_name,
            ammo_name=ammo.type_name,
            raw_dps=raw_dps,
            skill_multiplier=skill_multiplier,
            ship_multiplier=ship_multiplier,
            total_dps=total_dps,
            damage_profile=damage_profile,
            skill_bonuses_applied=applied_skill_bonuses,
            ship_bonuses_applied=applied_ship_bonuses
        )

    def _apply_skill_bonuses(
        self,
        skills: Dict[int, int]
    ) -> tuple[float, List[SkillBonus]]:
        """Apply skill damage bonuses.

        Args:
            skills: Dict of skill_id -> level

        Returns:
            Tuple of (multiplier, list of applied bonuses)
        """
        damage_mult = 1.0
        rof_mult = 1.0
        applied = []

        # Damage skills (multiplicative)
        for skill_id, (name, bonus_type, bonus_per_level) in DAMAGE_SKILLS.items():
            level = skills.get(skill_id, 0)
            if level > 0:
                damage_mult *= (1 + bonus_per_level * level)
                applied.append(SkillBonus(
                    skill_id=skill_id,
                    skill_name=name,
                    level=level,
                    bonus_per_level=bonus_per_level * 100,  # Convert to percentage
                    bonus_type=bonus_type
                ))

        # RoF skills (faster = more DPS)
        for skill_id, (name, bonus_type, bonus_per_level) in ROF_SKILLS.items():
            level = skills.get(skill_id, 0)
            if level > 0:
                rof_mult *= 1 / (1 + bonus_per_level * level)
                applied.append(SkillBonus(
                    skill_id=skill_id,
                    skill_name=name,
                    level=level,
                    bonus_per_level=bonus_per_level * 100,
                    bonus_type=bonus_type
                ))

        return damage_mult * rof_mult, applied

    def _apply_ship_bonuses(
        self,
        ship_type_id: int,
        skill_levels: Dict[int, int]
    ) -> tuple[float, List[ShipBonus]]:
        """Apply ship damage bonuses.

        Args:
            ship_type_id: Ship type ID
            skill_levels: Dict of skill_id -> level for ship skills

        Returns:
            Tuple of (multiplier, list of applied bonuses)
        """
        bonuses = self.repository.get_ship_damage_bonuses(ship_type_id)
        multiplier = 1.0
        applied = []

        for bonus in bonuses:
            if bonus.is_role_bonus:
                multiplier *= (1 + bonus.bonus_value / 100)
                applied.append(bonus)
            else:
                level = skill_levels.get(bonus.skill_id, 0)
                if level > 0:
                    multiplier *= (1 + (bonus.bonus_value / 100) * level)
                    applied.append(bonus)

        return multiplier, applied

    def _stacking_penalty(self, index: int) -> float:
        """Calculate EVE Online stacking penalty.

        Formula: exp(-((index/2.67)^2))

        Args:
            index: 0-based index of module in stack

        Returns:
            Penalty multiplier (1.0 = no penalty)
        """
        return math.exp(-((index / 2.67) ** 2))

    def compare_ammo(
        self,
        weapon_type_id: int,
        ammo_type_ids: List[int],
        character_skills: Optional[Dict[int, int]] = None,
        ship_type_id: Optional[int] = None,
        ship_skill_levels: Optional[Dict[int, int]] = None
    ) -> List[DPSResult]:
        """Compare DPS across different ammo types.

        Args:
            weapon_type_id: Weapon to test
            ammo_type_ids: List of ammo types to compare
            character_skills: Character skill levels
            ship_type_id: Ship for bonuses
            ship_skill_levels: Ship skill levels

        Returns:
            List of DPSResult sorted by total_dps descending
        """
        results = []
        for ammo_id in ammo_type_ids:
            result = self.calculate_dps(
                weapon_type_id=weapon_type_id,
                ammo_type_id=ammo_id,
                character_skills=character_skills,
                ship_type_id=ship_type_id,
                ship_skill_levels=ship_skill_levels
            )
            if result:
                results.append(result)

        return sorted(results, key=lambda r: r.total_dps, reverse=True)
