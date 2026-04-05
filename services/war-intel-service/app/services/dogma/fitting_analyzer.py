# app/services/dogma/fitting_analyzer.py
"""Fitting analyzer service - analyzes killmail fittings for tank and DPS."""

import logging
from typing import Optional, Dict, List
from collections import defaultdict

from .models import (
    TankResult,
    AttackerDPSResult,
    AttackerWeaponStats,
    KillmailAnalysis,
    FittedModule,
)
from .repository import DogmaRepository
from .tank_calculator import TankCalculatorService, get_tank_calculator

logger = logging.getLogger(__name__)


# Weapon categories for classification
WEAPON_CATEGORIES = {
    # Turrets
    'Energy Turrets': ['Beam Laser', 'Pulse Laser', 'Tachyon', 'Mega Beam', 'Heavy Beam'],
    'Hybrid Turrets': ['Blaster', 'Railgun', 'Neutron Blaster', 'Ion Blaster', 'Electron Blaster'],
    'Projectile Turrets': ['Autocannon', 'Artillery', 'Howitzer', '1400mm', '1200mm', '800mm', '720mm', '650mm', '425mm', '280mm', '250mm', '220mm', '200mm', '180mm', '150mm', '125mm'],
    # Missiles
    'Missiles': ['Torpedo', 'Cruise Missile', 'Heavy Missile', 'Heavy Assault Missile', 'Light Missile', 'Rocket', 'XL Torpedo', 'XL Cruise'],
    # Drones
    'Drones': ['Drone', 'Fighter', 'Sentry'],
    # Other
    'Smartbombs': ['Smartbomb', 'Smart Bomb'],
    'Bombs': ['Bomb'],
}

# Ship class estimates for DPS (rough averages with T2 weapons)
SHIP_CLASS_DPS_ESTIMATES = {
    'frigate': 150,
    'destroyer': 250,
    'cruiser': 400,
    'battlecruiser': 600,
    'battleship': 900,
    'dreadnought': 10000,
    'carrier': 3000,
    'supercarrier': 15000,
    'titan': 25000,
    # T2/Faction variants
    'assault_frigate': 200,
    'interceptor': 100,
    'covert_ops': 50,
    'stealth_bomber': 800,
    'electronic_attack': 100,
    'logistics_frigate': 50,
    'command_destroyer': 300,
    'interdictor': 200,
    'heavy_assault_cruiser': 550,
    'heavy_interdictor': 350,
    'recon': 200,
    'logistics': 50,
    'strategic_cruiser': 600,
    'command_ship': 700,
    'marauder': 1500,
    'black_ops': 800,
}



def get_ship_dps(type_id: int, ship_class: str, dps_overrides: dict = None) -> float:
    """Get DPS for a ship, checking overrides first then class estimates.

    Args:
        type_id: Ship type ID
        ship_class: Ship class name (e.g., 'cruiser', 'heavy_assault_cruiser')
        dps_overrides: Optional dict of {type_id: dps} from Doctrine Engine

    Returns: Estimated DPS value
    """
    if dps_overrides and type_id in dps_overrides:
        return dps_overrides[type_id]
    return SHIP_CLASS_DPS_ESTIMATES.get(ship_class, 200)

class FittingAnalyzer:
    """Analyzer for killmail fittings - extracts tank and DPS info."""

    def __init__(
        self,
        repository: Optional[DogmaRepository] = None,
        tank_calculator: Optional[TankCalculatorService] = None
    ):
        """Initialize with dependencies.

        Args:
            repository: DogmaRepository instance
            tank_calculator: TankCalculatorService instance
        """
        self.repository = repository or DogmaRepository()
        self.tank_calculator = tank_calculator or get_tank_calculator()

    async def analyze_killmail(self, killmail_id: int) -> Optional[KillmailAnalysis]:
        """Perform complete killmail analysis.

        Args:
            killmail_id: Killmail ID

        Returns:
            KillmailAnalysis with tank and DPS data, or None if not found
        """
        # Get basic killmail info
        killmail_info = self.repository.get_killmail_info(killmail_id)
        if not killmail_info:
            logger.warning(f"Killmail {killmail_id} not found")
            return None

        # Analyze victim tank
        victim_tank = await self.analyze_victim_tank(killmail_id)
        if not victim_tank:
            # Create minimal tank result for unknown ships
            victim_tank = TankResult(
                ship_type_id=killmail_info['ship_type_id'] or 0,
                ship_name=killmail_info['ship_name'] or 'Unknown',
                shield_hp=0,
                armor_hp=0,
                hull_hp=0,
                shield_resists=ResistProfile(),
                armor_resists=ResistProfile(),
                hull_resists=ResistProfile(),
                shield_ehp=0,
                armor_ehp=0,
                hull_ehp=0,
            )

        # Analyze attacker DPS
        attacker_analysis = await self.analyze_attacker_dps(killmail_id)

        return KillmailAnalysis(
            killmail_id=killmail_id,
            killmail_time=str(killmail_info.get('killmail_time', '')),
            solar_system_id=killmail_info.get('solar_system_id'),
            solar_system_name=killmail_info.get('solar_system_name'),
            victim_ship_type_id=killmail_info['ship_type_id'] or 0,
            victim_ship_name=killmail_info['ship_name'] or 'Unknown',
            victim_tank=victim_tank,
            attacker_analysis=attacker_analysis,
        )

    async def analyze_victim_tank(self, killmail_id: int) -> Optional[TankResult]:
        """Analyze victim's tank from killmail items.

        Args:
            killmail_id: Killmail ID

        Returns:
            TankResult or None
        """
        # Get killmail info for ship type
        killmail_info = self.repository.get_killmail_info(killmail_id)
        if not killmail_info or not killmail_info.get('ship_type_id'):
            return None

        ship_type_id = killmail_info['ship_type_id']

        # Get fitted modules from killmail
        fitted_modules = self.repository.get_killmail_victim_items(killmail_id)

        # Calculate tank
        return self.tank_calculator.calculate_tank(
            ship_type_id=ship_type_id,
            fitted_modules=fitted_modules,
            skill_level=4  # Assume Skill IV
        )

    async def analyze_attacker_dps(self, killmail_id: int) -> AttackerDPSResult:
        """Analyze attacker DPS from killmail.

        Args:
            killmail_id: Killmail ID

        Returns:
            AttackerDPSResult with fleet DPS estimate
        """
        # Get attacker data
        attackers = self.repository.get_killmail_attackers(killmail_id)

        if not attackers:
            return AttackerDPSResult(
                total_attackers=0,
                estimated_fleet_dps=0,
            )

        # Process each attacker
        total_dps = 0.0
        dps_by_weapon_type: Dict[str, float] = defaultdict(float)
        damage_profile: Dict[str, float] = defaultdict(float)
        ships_by_class: Dict[str, int] = defaultdict(int)
        top_attackers: List[AttackerWeaponStats] = []

        total_damage = sum(a.get('damage_done', 0) for a in attackers)

        for attacker in attackers:
            ship_name = attacker.get('ship_name') or 'Unknown'
            weapon_name = attacker.get('weapon_name') or ship_name
            damage_done = attacker.get('damage_done', 0)

            # Estimate DPS for this attacker
            estimated_dps = self._estimate_attacker_dps(
                ship_name=ship_name,
                weapon_name=weapon_name,
                damage_done=damage_done,
                total_damage=total_damage,
            )
            total_dps += estimated_dps

            # Classify weapon type
            weapon_category = self._classify_weapon(weapon_name)
            dps_by_weapon_type[weapon_category] += estimated_dps

            # Ship class
            ship_class = self._classify_ship(ship_name)
            ships_by_class[ship_class] += 1

            # Track top attackers (by damage done)
            top_attackers.append(AttackerWeaponStats(
                character_id=attacker.get('character_id'),
                ship_type_id=attacker.get('ship_type_id') or 0,
                ship_name=ship_name,
                weapon_type_id=attacker.get('weapon_type_id'),
                weapon_name=weapon_name,
                damage_done=damage_done,
                estimated_dps=estimated_dps,
                is_final_blow=attacker.get('is_final_blow', False),
            ))

        # Sort top attackers by damage and limit
        top_attackers.sort(key=lambda x: x.damage_done, reverse=True)
        top_attackers = top_attackers[:10]

        # Estimate damage profile from weapon types
        damage_profile = self._estimate_damage_profile(dps_by_weapon_type)

        return AttackerDPSResult(
            total_attackers=len(attackers),
            estimated_fleet_dps=total_dps,
            dps_by_weapon_type=dict(dps_by_weapon_type),
            damage_profile=damage_profile,
            top_attackers=top_attackers,
            ships_by_class=dict(ships_by_class),
        )

    def _estimate_attacker_dps(
        self,
        ship_name: str,
        weapon_name: str,
        damage_done: int,
        total_damage: int
    ) -> float:
        """Estimate DPS for a single attacker.

        Args:
            ship_name: Attacker ship name
            weapon_name: Weapon used
            damage_done: Damage dealt
            total_damage: Total damage across all attackers

        Returns:
            Estimated DPS
        """
        # Try to match ship class
        ship_class = self._classify_ship(ship_name)
        base_dps = SHIP_CLASS_DPS_ESTIMATES.get(ship_class, 300)

        # Adjust if we have damage proportion
        if total_damage > 0 and damage_done > 0:
            # Weight by damage contribution
            damage_ratio = damage_done / total_damage
            # But cap the adjustment to prevent outliers
            base_dps = base_dps * min(2.0, max(0.5, damage_ratio * len(SHIP_CLASS_DPS_ESTIMATES)))

        return base_dps

    def _classify_weapon(self, weapon_name: str) -> str:
        """Classify weapon into category.

        Args:
            weapon_name: Weapon name

        Returns:
            Weapon category name
        """
        if not weapon_name:
            return 'Unknown'

        weapon_lower = weapon_name.lower()

        for category, keywords in WEAPON_CATEGORIES.items():
            for keyword in keywords:
                if keyword.lower() in weapon_lower:
                    return category

        # Default classification by common patterns
        if 'turret' in weapon_lower or 'cannon' in weapon_lower:
            return 'Projectile Turrets'
        elif 'laser' in weapon_lower:
            return 'Energy Turrets'
        elif 'blaster' in weapon_lower or 'rail' in weapon_lower:
            return 'Hybrid Turrets'
        elif 'missile' in weapon_lower or 'torpedo' in weapon_lower or 'rocket' in weapon_lower:
            return 'Missiles'
        elif 'drone' in weapon_lower or 'fighter' in weapon_lower:
            return 'Drones'

        return 'Other'

    def _classify_ship(self, ship_name: str) -> str:
        """Classify ship into class category.

        Args:
            ship_name: Ship name

        Returns:
            Ship class name
        """
        if not ship_name:
            return 'unknown'

        ship_lower = ship_name.lower()

        # Capital ships
        if any(x in ship_lower for x in ['titan', 'avatar', 'erebus', 'leviathan', 'ragnarok']):
            return 'titan'
        if any(x in ship_lower for x in ['supercarrier', 'nyx', 'hel', 'aeon', 'wyvern', 'vendetta', 'revenant']):
            return 'supercarrier'
        if any(x in ship_lower for x in ['dreadnought', 'moros', 'naglfar', 'revelation', 'phoenix', 'zirnitra']):
            return 'dreadnought'
        if any(x in ship_lower for x in ['carrier', 'thanatos', 'nidhoggur', 'archon', 'chimera']):
            return 'carrier'

        # Subcaps by hull size keywords
        if 'battleship' in ship_lower or any(x in ship_lower for x in ['apocalypse', 'armageddon', 'megathron', 'dominix', 'raven', 'scorpion', 'typhoon', 'tempest', 'maelstrom', 'rokh', 'hyperion', 'abaddon']):
            return 'battleship'
        if 'marauder' in ship_lower or any(x in ship_lower for x in ['golem', 'paladin', 'kronos', 'vargur']):
            return 'marauder'
        if 'black ops' in ship_lower or any(x in ship_lower for x in ['widow', 'redeemer', 'sin', 'panther', 'marshal']):
            return 'black_ops'
        if 'battlecruiser' in ship_lower or any(x in ship_lower for x in ['drake', 'ferox', 'brutix', 'myrmidon', 'hurricane', 'cyclone', 'harbinger', 'prophecy']):
            return 'battlecruiser'
        if any(x in ship_lower for x in ['strategic cruiser', 'loki', 'tengu', 'legion', 'proteus']):
            return 'strategic_cruiser'
        if 'cruiser' in ship_lower or any(x in ship_lower for x in ['caracal', 'moa', 'thorax', 'vexor', 'rupture', 'stabber', 'omen', 'maller', 'arbitrator']):
            return 'cruiser'
        if 'destroyer' in ship_lower or any(x in ship_lower for x in ['cormorant', 'catalyst', 'thrasher', 'coercer', 'algos', 'dragoon', 'talwar', 'corax']):
            return 'destroyer'
        if 'frigate' in ship_lower or any(x in ship_lower for x in ['condor', 'merlin', 'kestrel', 'heron', 'incursus', 'tristan', 'atron', 'rifter', 'slasher', 'probe', 'executioner', 'punisher', 'tormentor']):
            return 'frigate'
        if 'interceptor' in ship_lower or any(x in ship_lower for x in ['crow', 'raptor', 'taranis', 'ares', 'stiletto', 'claw', 'crusader', 'malediction']):
            return 'interceptor'
        if 'stealth bomber' in ship_lower or any(x in ship_lower for x in ['manticore', 'nemesis', 'hound', 'purifier']):
            return 'stealth_bomber'

        # Default to cruiser
        return 'cruiser'

    def _estimate_damage_profile(self, dps_by_weapon: Dict[str, float]) -> Dict[str, float]:
        """Estimate damage type distribution from weapon types.

        Args:
            dps_by_weapon: DPS by weapon category

        Returns:
            Damage profile (em, thermal, kinetic, explosive percentages)
        """
        # Default damage profiles by weapon type
        WEAPON_DAMAGE_PROFILES = {
            'Energy Turrets': {'em': 0.5, 'thermal': 0.5, 'kinetic': 0, 'explosive': 0},
            'Hybrid Turrets': {'em': 0, 'thermal': 0.5, 'kinetic': 0.5, 'explosive': 0},
            'Projectile Turrets': {'em': 0, 'thermal': 0, 'kinetic': 0.5, 'explosive': 0.5},
            'Missiles': {'em': 0.25, 'thermal': 0.25, 'kinetic': 0.25, 'explosive': 0.25},
            'Drones': {'em': 0.25, 'thermal': 0.25, 'kinetic': 0.25, 'explosive': 0.25},
            'Smartbombs': {'em': 0.25, 'thermal': 0.25, 'kinetic': 0.25, 'explosive': 0.25},
            'Bombs': {'em': 0, 'thermal': 0, 'kinetic': 0, 'explosive': 1.0},
            'Other': {'em': 0.25, 'thermal': 0.25, 'kinetic': 0.25, 'explosive': 0.25},
        }

        total_dps = sum(dps_by_weapon.values())
        if total_dps <= 0:
            return {'em': 25, 'thermal': 25, 'kinetic': 25, 'explosive': 25}

        profile = {'em': 0.0, 'thermal': 0.0, 'kinetic': 0.0, 'explosive': 0.0}

        for weapon_type, dps in dps_by_weapon.items():
            weapon_profile = WEAPON_DAMAGE_PROFILES.get(weapon_type, WEAPON_DAMAGE_PROFILES['Other'])
            weight = dps / total_dps

            for damage_type, ratio in weapon_profile.items():
                profile[damage_type] += ratio * weight * 100  # Convert to percentage

        return profile


# Import at module level to avoid circular imports
from .models import ResistProfile


# Singleton instance
_fitting_analyzer: Optional[FittingAnalyzer] = None


def get_fitting_analyzer() -> FittingAnalyzer:
    """Get singleton fitting analyzer instance."""
    global _fitting_analyzer
    if _fitting_analyzer is None:
        _fitting_analyzer = FittingAnalyzer()
    return _fitting_analyzer
