# app/services/dogma/models.py
"""Data models for Dogma Engine - tank and fitting analysis."""

from typing import Optional, List, Dict
from pydantic import BaseModel, Field, computed_field
from enum import Enum


class TankType(str, Enum):
    """Tank archetype classification."""
    SHIELD_BUFFER = "shield_buffer"
    SHIELD_ACTIVE = "shield_active"
    ARMOR_BUFFER = "armor_buffer"
    ARMOR_ACTIVE = "armor_active"
    HULL_TANK = "hull_tank"
    UNKNOWN = "unknown"


class ModuleSlot(str, Enum):
    """Ship fitting slot types."""
    HIGH = "high"
    MID = "mid"
    LOW = "low"
    RIG = "rig"
    SUBSYSTEM = "subsystem"
    CARGO = "cargo"


class ResistProfile(BaseModel):
    """Resistance values for a single layer (0.0-1.0 where 1.0 = no resist)."""
    em: float = Field(default=1.0, ge=0.0, le=1.0)
    thermal: float = Field(default=1.0, ge=0.0, le=1.0)
    kinetic: float = Field(default=1.0, ge=0.0, le=1.0)
    explosive: float = Field(default=1.0, ge=0.0, le=1.0)

    @computed_field
    @property
    def em_percent(self) -> float:
        """EM resistance as percentage (0-100)."""
        return (1.0 - self.em) * 100

    @computed_field
    @property
    def thermal_percent(self) -> float:
        """Thermal resistance as percentage (0-100)."""
        return (1.0 - self.thermal) * 100

    @computed_field
    @property
    def kinetic_percent(self) -> float:
        """Kinetic resistance as percentage (0-100)."""
        return (1.0 - self.kinetic) * 100

    @computed_field
    @property
    def explosive_percent(self) -> float:
        """Explosive resistance as percentage (0-100)."""
        return (1.0 - self.explosive) * 100

    @computed_field
    @property
    def average(self) -> float:
        """Average resistance multiplier."""
        return (self.em + self.thermal + self.kinetic + self.explosive) / 4

    @computed_field
    @property
    def lowest(self) -> float:
        """Lowest (best) resistance multiplier - resist hole."""
        return min(self.em, self.thermal, self.kinetic, self.explosive)


class ShipBaseStats(BaseModel):
    """Base ship stats from SDE without any modules."""
    ship_type_id: int
    ship_name: str

    # Hit Points
    shield_hp: float = 0
    armor_hp: float = 0
    hull_hp: float = 0

    # Base Resistances
    shield_resists: ResistProfile = Field(default_factory=ResistProfile)
    armor_resists: ResistProfile = Field(default_factory=ResistProfile)
    hull_resists: ResistProfile = Field(default_factory=ResistProfile)

    # Other stats
    shield_recharge_ms: float = 0  # Shield recharge time in ms
    signature_radius: float = 0
    max_velocity: float = 0

    @computed_field
    @property
    def total_raw_hp(self) -> float:
        """Total HP without resists."""
        return self.shield_hp + self.armor_hp + self.hull_hp


class TankModuleEffect(BaseModel):
    """Effect of a tank module on ship stats."""
    type_id: int
    type_name: str
    slot: ModuleSlot

    # HP bonuses (flat additions)
    shield_hp_bonus: float = 0
    armor_hp_bonus: float = 0
    hull_hp_bonus: float = 0

    # Resist bonuses (multipliers, e.g., 0.75 = 25% resist increase)
    shield_em_resist_mult: float = 1.0
    shield_thermal_resist_mult: float = 1.0
    shield_kinetic_resist_mult: float = 1.0
    shield_explosive_resist_mult: float = 1.0

    armor_em_resist_mult: float = 1.0
    armor_thermal_resist_mult: float = 1.0
    armor_kinetic_resist_mult: float = 1.0
    armor_explosive_resist_mult: float = 1.0

    # Signature radius penalty (for shield extenders)
    signature_radius_add: float = 0

    # Module classification
    is_shield_module: bool = False
    is_armor_module: bool = False
    is_hull_module: bool = False
    is_resist_module: bool = False
    is_hp_module: bool = False
    is_active_module: bool = False  # Requires cap (boosters, repairers)


class FittedModule(BaseModel):
    """A module fitted to a ship (from killmail or fitting)."""
    type_id: int
    flag: int  # Slot position from killmail
    quantity: int = 1
    was_destroyed: bool = True  # From killmail

    @computed_field
    @property
    def slot(self) -> ModuleSlot:
        """Determine slot type from flag."""
        if 11 <= self.flag <= 18:
            return ModuleSlot.LOW
        elif 19 <= self.flag <= 26:
            return ModuleSlot.MID
        elif 27 <= self.flag <= 34:
            return ModuleSlot.HIGH
        elif 92 <= self.flag <= 99:
            return ModuleSlot.RIG
        elif 125 <= self.flag <= 132:
            return ModuleSlot.SUBSYSTEM
        else:
            return ModuleSlot.CARGO


class TankResult(BaseModel):
    """Complete tank analysis result."""
    ship_type_id: int
    ship_name: str

    # Raw HP (after modules)
    shield_hp: float
    armor_hp: float
    hull_hp: float

    # Final Resists (after modules + stacking penalty)
    shield_resists: ResistProfile
    armor_resists: ResistProfile
    hull_resists: ResistProfile

    # EHP per layer (against omni damage)
    shield_ehp: float
    armor_ehp: float
    hull_ehp: float

    @computed_field
    @property
    def total_ehp(self) -> float:
        """Total EHP across all layers."""
        return self.shield_ehp + self.armor_ehp + self.hull_ehp

    # Tank classification
    tank_type: TankType = TankType.UNKNOWN
    primary_tank_layer: str = "unknown"  # "shield", "armor", "hull"

    # Meta information
    skill_assumption: str = "Level IV"
    modules_counted: int = 0
    signature_radius: float = 0

    # Module breakdown
    tank_modules: List[str] = Field(default_factory=list)  # Module names


class AttackerWeaponStats(BaseModel):
    """DPS stats for a single attacker."""
    character_id: Optional[int] = None
    ship_type_id: int
    ship_name: str
    weapon_type_id: Optional[int] = None
    weapon_name: Optional[str] = None
    damage_done: int = 0
    estimated_dps: float = 0
    is_final_blow: bool = False


class AttackerDPSResult(BaseModel):
    """Aggregated attacker DPS analysis."""
    total_attackers: int
    estimated_fleet_dps: float

    # DPS by weapon category
    dps_by_weapon_type: Dict[str, float] = Field(default_factory=dict)

    # Damage type distribution
    damage_profile: Dict[str, float] = Field(default_factory=dict)  # em, thermal, kinetic, explosive

    # Top attackers
    top_attackers: List[AttackerWeaponStats] = Field(default_factory=list)

    # Ship composition
    ships_by_class: Dict[str, int] = Field(default_factory=dict)


class KillmailAnalysis(BaseModel):
    """Complete killmail analysis combining victim tank and attacker DPS."""
    killmail_id: int
    killmail_time: Optional[str] = None
    solar_system_id: Optional[int] = None
    solar_system_name: Optional[str] = None

    # Victim analysis
    victim_ship_type_id: int
    victim_ship_name: str
    victim_tank: TankResult

    # Attacker analysis
    attacker_analysis: AttackerDPSResult

    # Derived metrics
    @computed_field
    @property
    def time_to_kill_seconds(self) -> float:
        """Estimated time to kill based on DPS vs EHP."""
        if self.attacker_analysis.estimated_fleet_dps <= 0:
            return 0
        return self.victim_tank.total_ehp / self.attacker_analysis.estimated_fleet_dps

    @computed_field
    @property
    def overkill_ratio(self) -> float:
        """Fleet DPS / Tank EHP ratio (higher = more overkill)."""
        if self.victim_tank.total_ehp <= 0:
            return 0
        return self.attacker_analysis.estimated_fleet_dps / self.victim_tank.total_ehp


class FittingRequest(BaseModel):
    """Request model for EHP calculation endpoint."""
    ship_type_id: int
    module_type_ids: List[int] = Field(default_factory=list)
    skill_level: int = Field(default=4, ge=0, le=5)
