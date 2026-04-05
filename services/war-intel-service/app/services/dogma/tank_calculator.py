# app/services/dogma/tank_calculator.py
"""Tank calculator service - EHP and resistance calculations."""

import math
import logging
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from .models import (
    ShipBaseStats,
    TankModuleEffect,
    FittedModule,
    TankResult,
    ResistProfile,
    TankType,
    ModuleSlot,
)
from .repository import DogmaRepository

logger = logging.getLogger(__name__)


class TankCalculatorService:
    """Service for calculating ship tank (EHP, resistances)."""

    def __init__(self, repository: Optional[DogmaRepository] = None):
        """Initialize with repository.

        Args:
            repository: DogmaRepository instance (creates one if not provided)
        """
        self.repository = repository or DogmaRepository()

    def calculate_tank(
        self,
        ship_type_id: int,
        fitted_modules: List[FittedModule],
        skill_level: int = 4
    ) -> Optional[TankResult]:
        """Calculate complete tank for a ship with fitted modules.

        Args:
            ship_type_id: Ship type ID
            fitted_modules: List of fitted modules
            skill_level: Assumed skill level (0-5), default 4

        Returns:
            TankResult with EHP calculations or None if ship not found
        """
        # Get base ship stats
        ship_stats = self.repository.get_ship_base_stats(ship_type_id)
        if not ship_stats:
            logger.warning(f"Ship type {ship_type_id} not found in SDE")
            return None

        # Filter to tank-relevant slots only
        tank_modules = [
            m for m in fitted_modules
            if m.slot in (ModuleSlot.LOW, ModuleSlot.MID, ModuleSlot.RIG)
        ]

        # Get module effects
        module_type_ids = [m.type_id for m in tank_modules]
        module_effects = self.repository.get_module_tank_effects(module_type_ids)

        # Calculate HP with modules
        shield_hp = ship_stats.shield_hp
        armor_hp = ship_stats.armor_hp
        hull_hp = ship_stats.hull_hp
        signature_radius = ship_stats.signature_radius

        # Collect resist bonuses for stacking penalty
        shield_resist_bonuses: Dict[str, List[float]] = defaultdict(list)
        armor_resist_bonuses: Dict[str, List[float]] = defaultdict(list)

        tank_module_names = []

        for module in tank_modules:
            effect = module_effects.get(module.type_id)
            if not effect:
                continue

            tank_module_names.append(effect.type_name)

            # Apply HP bonuses (no stacking penalty for HP modules)
            shield_hp += effect.shield_hp_bonus
            armor_hp += effect.armor_hp_bonus
            hull_hp += effect.hull_hp_bonus
            signature_radius += effect.signature_radius_add

            # Collect resist bonuses for stacking
            if effect.shield_em_resist_mult != 1.0:
                shield_resist_bonuses['em'].append(effect.shield_em_resist_mult)
            if effect.shield_thermal_resist_mult != 1.0:
                shield_resist_bonuses['thermal'].append(effect.shield_thermal_resist_mult)
            if effect.shield_kinetic_resist_mult != 1.0:
                shield_resist_bonuses['kinetic'].append(effect.shield_kinetic_resist_mult)
            if effect.shield_explosive_resist_mult != 1.0:
                shield_resist_bonuses['explosive'].append(effect.shield_explosive_resist_mult)

            if effect.armor_em_resist_mult != 1.0:
                armor_resist_bonuses['em'].append(effect.armor_em_resist_mult)
            if effect.armor_thermal_resist_mult != 1.0:
                armor_resist_bonuses['thermal'].append(effect.armor_thermal_resist_mult)
            if effect.armor_kinetic_resist_mult != 1.0:
                armor_resist_bonuses['kinetic'].append(effect.armor_kinetic_resist_mult)
            if effect.armor_explosive_resist_mult != 1.0:
                armor_resist_bonuses['explosive'].append(effect.armor_explosive_resist_mult)

        # Apply stacking penalty and calculate final resists
        shield_resists = self._apply_stacked_resists(
            ship_stats.shield_resists,
            shield_resist_bonuses
        )
        armor_resists = self._apply_stacked_resists(
            ship_stats.armor_resists,
            armor_resist_bonuses
        )
        hull_resists = ship_stats.hull_resists  # Hull usually no resist modules

        # Apply skill bonuses to HP
        skill_hp_bonus = 1 + (0.05 * skill_level)  # 5% per level
        shield_hp *= skill_hp_bonus
        armor_hp *= skill_hp_bonus
        hull_hp *= skill_hp_bonus

        # Calculate EHP per layer
        shield_ehp = self._calculate_layer_ehp(shield_hp, shield_resists)
        armor_ehp = self._calculate_layer_ehp(armor_hp, armor_resists)
        hull_ehp = self._calculate_layer_ehp(hull_hp, hull_resists)

        # Determine tank type
        tank_type, primary_layer = self._classify_tank(
            shield_hp, armor_hp, shield_ehp, armor_ehp
        )

        return TankResult(
            ship_type_id=ship_type_id,
            ship_name=ship_stats.ship_name,
            shield_hp=shield_hp,
            armor_hp=armor_hp,
            hull_hp=hull_hp,
            shield_resists=shield_resists,
            armor_resists=armor_resists,
            hull_resists=hull_resists,
            shield_ehp=shield_ehp,
            armor_ehp=armor_ehp,
            hull_ehp=hull_ehp,
            tank_type=tank_type,
            primary_tank_layer=primary_layer,
            skill_assumption=f"Level {skill_level}",
            modules_counted=len(tank_modules),
            signature_radius=signature_radius,
            tank_modules=tank_module_names,
        )

    def calculate_base_tank(self, ship_type_id: int) -> Optional[TankResult]:
        """Calculate tank for a ship with NO modules.

        Args:
            ship_type_id: Ship type ID

        Returns:
            TankResult with base EHP (no modules)
        """
        return self.calculate_tank(ship_type_id, [], skill_level=0)

    def _apply_stacked_resists(
        self,
        base_resists: ResistProfile,
        bonuses: Dict[str, List[float]]
    ) -> ResistProfile:
        """Apply stacked resist bonuses with stacking penalty.

        Args:
            base_resists: Base resistance profile
            bonuses: Dict of resist type -> list of multipliers

        Returns:
            New ResistProfile with bonuses applied
        """
        def apply_stacked(base: float, mults: List[float]) -> float:
            """Apply multipliers with stacking penalty."""
            if not mults:
                return base

            # Sort by effectiveness (smallest multiplier = best)
            sorted_mults = sorted(mults)

            # Apply each with stacking penalty
            result = base
            for i, mult in enumerate(sorted_mults):
                penalty = self._stacking_penalty(i)
                # Interpolate between 1.0 and mult based on penalty
                effective_mult = 1.0 + (mult - 1.0) * penalty
                result *= effective_mult

            return max(0.0, min(1.0, result))

        return ResistProfile(
            em=apply_stacked(base_resists.em, bonuses.get('em', [])),
            thermal=apply_stacked(base_resists.thermal, bonuses.get('thermal', [])),
            kinetic=apply_stacked(base_resists.kinetic, bonuses.get('kinetic', [])),
            explosive=apply_stacked(base_resists.explosive, bonuses.get('explosive', [])),
        )

    def _stacking_penalty(self, index: int) -> float:
        """Calculate stacking penalty for module at given index.

        EVE Online formula: exp(-((index / 2.67)^2))

        Args:
            index: 0-based module index (0 = first module, full effect)

        Returns:
            Penalty multiplier (0.0 to 1.0)
        """
        return math.exp(-((index / 2.67) ** 2))

    def _calculate_layer_ehp(self, hp: float, resists: ResistProfile) -> float:
        """Calculate EHP for a single layer.

        EHP = HP / (1 - average_resist_percent)
        Or equivalently: HP / average_resist_multiplier

        For true omni-damage EHP, we use the average of resist multipliers.

        Args:
            hp: Raw hitpoints
            resists: Resistance profile

        Returns:
            Effective hitpoints
        """
        if hp <= 0:
            return 0

        # Average resist multiplier (lower = better)
        avg_resist = resists.average

        # EHP = HP / resist_mult
        # e.g., 1000 HP with 0.5 avg resist = 2000 EHP
        if avg_resist <= 0:
            return hp * 100  # Cap at 100x for near-immunity

        return hp / avg_resist

    def _classify_tank(
        self,
        shield_hp: float,
        armor_hp: float,
        shield_ehp: float,
        armor_ehp: float
    ) -> Tuple[TankType, str]:
        """Classify tank type based on HP distribution.

        Args:
            shield_hp: Shield HP after modules
            armor_hp: Armor HP after modules
            shield_ehp: Shield EHP
            armor_ehp: Armor EHP

        Returns:
            Tuple of (TankType, primary_layer_name)
        """
        # Determine primary tank layer by EHP
        if shield_ehp > armor_ehp * 1.5:
            primary = "shield"
            # Check if buffer or active (we can't tell without more info)
            tank_type = TankType.SHIELD_BUFFER
        elif armor_ehp > shield_ehp * 1.5:
            primary = "armor"
            tank_type = TankType.ARMOR_BUFFER
        else:
            # Balanced or hull tank
            primary = "shield" if shield_ehp >= armor_ehp else "armor"
            tank_type = TankType.UNKNOWN

        return tank_type, primary


# Singleton instance
_tank_calculator: Optional[TankCalculatorService] = None


def get_tank_calculator() -> TankCalculatorService:
    """Get singleton tank calculator instance."""
    global _tank_calculator
    if _tank_calculator is None:
        _tank_calculator = TankCalculatorService()
    return _tank_calculator
