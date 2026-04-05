"""Pydantic models for fitting stats."""

from typing import List, Optional, Dict
from pydantic import BaseModel

from app.services.fitting_service import FittingItem


class TargetProfile(BaseModel):
    name: str = "none"
    sig_radius: float = 0       # meters
    velocity: float = 0         # m/s
    distance: float = 0         # meters


class SpoolStats(BaseModel):
    """Triglavian weapon spool-up stats."""
    min_dps: float = 0.0
    max_dps: float = 0.0
    avg_dps: float = 0.0
    cycles_to_max: int = 0
    time_to_max_s: float = 0.0


class AppliedDPS(BaseModel):
    target_profile: str = "none"
    turret_applied_dps: float = 0
    missile_applied_dps: float = 0
    drone_applied_dps: float = 0
    total_applied_dps: float = 0
    turret_hit_chance: float = 0
    missile_damage_factor: float = 0
    spool_applied: Optional[SpoolStats] = None  # Applied DPS spool variants


class FighterInput(BaseModel):
    """Fighter squadron input."""
    type_id: int
    quantity: int = 1  # number of squadrons


class FighterDPSStats(BaseModel):
    """DPS stats for a single fighter type."""
    type_name: str = ""
    type_id: int = 0
    squadron_size: int = 0
    squadrons: int = 0
    dps_per_squadron: float = 0.0
    total_dps: float = 0.0
    damage_type: str = "unknown"  # primary damage type


class FleetBoostInput(BaseModel):
    """A single fleet boost (command burst buff).
    buff_id: warfareBuffID from SDE
    value: Percentage (e.g., 25.88 for +25.88%)
    """
    buff_id: int
    value: float


class ProjectedEffectInput(BaseModel):
    """A projected effect from another ship."""
    effect_type: str  # "web" | "paint" | "neut" | "remote_shield" | "remote_armor"
    strength: float   # Base module strength (percentage for web/paint, GJ or HP for neut/rep)
    count: int = 1    # Number of this effect applied


class BoosterInput(BaseModel):
    type_id: int
    side_effects_enabled: List[int] = []  # indices of enabled side effects (0-4)


class FittingStatsRequest(BaseModel):
    ship_type_id: int
    items: List[FittingItem]
    ammo_type_id: Optional[int] = None  # legacy, keep for backward compat
    charges: Optional[Dict[int, int]] = None  # flag → charge_type_id
    character_id: Optional[int] = None  # use actual character skills instead of All V
    target_profile: Optional[str] = None  # "frigate", "cruiser", "battleship", etc.
    simulation_mode: bool = False  # False=fitting mode (passive only), True=all effects active
    include_implants: bool = True  # include character implants in calculation
    module_states: Optional[Dict[int, str]] = None  # flag → "offline"|"online"|"active"|"overheated"
    boosters: Optional[List[BoosterInput]] = None  # combat boosters with optional side effects
    fighters: Optional[List[FighterInput]] = None  # fighter squadrons
    mode_type_id: Optional[int] = None  # T3D mode (group 1306): Defense/Propulsion/Sharpshooter
    fleet_boosts: Optional[List[FleetBoostInput]] = None  # fleet command burst buffs
    projected_effects: Optional[List[ProjectedEffectInput]] = None  # projected effects ON this ship
    target_projected: Optional[List[ProjectedEffectInput]] = None  # effects on TARGET (for applied DPS)


class SlotUsage(BaseModel):
    hi_total: int = 0
    hi_used: int = 0
    med_total: int = 0
    med_used: int = 0
    low_total: int = 0
    low_used: int = 0
    rig_total: int = 0
    rig_used: int = 0


class ResourceUsage(BaseModel):
    pg_total: float = 0
    pg_used: float = 0
    cpu_total: float = 0
    cpu_used: float = 0
    calibration_total: float = 0
    calibration_used: float = 0
    turret_hardpoints_total: int = 0
    turret_hardpoints_used: int = 0
    launcher_hardpoints_total: int = 0
    launcher_hardpoints_used: int = 0
    drone_bay_total: float = 0
    drone_bay_used: float = 0
    drone_bandwidth_total: float = 0
    drone_bandwidth_used: float = 0


class DamageBreakdown(BaseModel):
    em: float = 0
    thermal: float = 0
    kinetic: float = 0
    explosive: float = 0


class ResistProfile(BaseModel):
    em: float = 0
    thermal: float = 0
    kinetic: float = 0
    explosive: float = 0


class OffenseStats(BaseModel):
    weapon_dps: float = 0
    drone_dps: float = 0
    fighter_dps: float = 0.0
    fighter_details: Optional[List[FighterDPSStats]] = None
    total_dps: float = 0
    volley_damage: float = 0
    damage_breakdown: DamageBreakdown = DamageBreakdown()
    overheated_weapon_dps: Optional[float] = None
    overheated_total_dps: Optional[float] = None
    spool: Optional[SpoolStats] = None


class DefenseStats(BaseModel):
    total_ehp: float = 0
    shield_ehp: float = 0
    armor_ehp: float = 0
    hull_ehp: float = 0
    shield_hp: float = 0       # raw HP (as shown in EVE fitting window)
    armor_hp: float = 0
    hull_hp: float = 0
    shield_resists: ResistProfile = ResistProfile()
    armor_resists: ResistProfile = ResistProfile()
    hull_resists: ResistProfile = ResistProfile()
    tank_type: str = "unknown"


class CapacitorStats(BaseModel):
    capacity: float = 0
    recharge_time: float = 0
    peak_recharge_rate: float = 0
    usage_rate: float = 0
    stable: bool = True
    stable_percent: float = 100.0
    lasts_seconds: float = 0


class NavigationStats(BaseModel):
    max_velocity: float = 0
    align_time: float = 0
    warp_speed: float = 0
    warp_time_5au: float = 0    # time for 5 AU warp (common reference)
    warp_time_20au: float = 0   # time for 20 AU warp
    agility: float = 0
    signature_radius: float = 0
    mass: float = 0
    cargo_capacity: float = 0


class TargetingStats(BaseModel):
    max_range: float = 0
    scan_resolution: float = 0
    max_locked_targets: int = 0
    sensor_strength: float = 0
    sensor_type: str = ""
    lock_time: float = 0  # seconds to lock a target (sig_radius-dependent)
    drone_control_range: float = 0
    scanability: float = 0  # sig_radius / sensor_strength — higher = easier to probe


class RepairStats(BaseModel):
    shield_rep: float = 0    # HP/s (shield boost rate)
    armor_rep: float = 0     # HP/s
    hull_rep: float = 0      # HP/s
    shield_passive_regen: float = 0  # peak passive regen HP/s at 25% shield
    shield_rep_ehp: float = 0     # effective HP/s (accounts for resists)
    armor_rep_ehp: float = 0
    sustained_tank_ehp: float = 0  # total incoming DPS the ship can sustain
    sustained_shield_rep: Optional[float] = None  # cap-limited shield rep HP/s
    sustained_armor_rep: Optional[float] = None    # cap-limited armor rep HP/s
    overheated_shield_rep: Optional[float] = None
    overheated_armor_rep: Optional[float] = None


class ModuleDetailItem(BaseModel):
    type_id: int
    type_name: str
    slot_type: str  # "high", "mid", "low", "rig", "drone"
    flag: int
    quantity: int = 1
    cpu: float = 0
    pg: float = 0
    cap_need: float = 0       # GJ per cycle
    cycle_time_ms: float = 0  # ms (duration or rof)
    cap_per_sec: float = 0    # GJ/s
    charge_type_id: Optional[int] = None
    charge_name: Optional[str] = None
    hardpoint_type: Optional[str] = None  # "turret", "launcher", or None


class FittingSkillRequirement(BaseModel):
    skill_id: int
    skill_name: str
    required_level: int       # max level needed across all items
    trained_level: Optional[int] = None  # character's level (None = unknown)
    rank: float = 1.0
    sp_required: int = 0
    required_by: List[str] = []  # item names requiring this skill


class ActiveImplant(BaseModel):
    type_id: int
    type_name: str = "Unknown"
    slot: int = 0


class FittingStatsResponse(BaseModel):
    ship: dict
    slots: SlotUsage
    resources: ResourceUsage
    offense: OffenseStats
    defense: DefenseStats
    capacitor: CapacitorStats
    navigation: NavigationStats
    targeting: TargetingStats
    repairs: RepairStats = RepairStats()
    applied_dps: Optional[AppliedDPS] = None
    violations: List[dict] = []
    module_details: List[ModuleDetailItem] = []
    required_skills: List[FittingSkillRequirement] = []
    skill_source: str = "all_v"  # "all_v" or character name
    character_id: Optional[int] = None
    active_implants: List[ActiveImplant] = []
    mode: Optional[str] = None  # Active T3D mode name if applicable
    active_boosts: Optional[List[dict]] = None  # Applied fleet boost buffs
    projected_effects_summary: Optional[List[dict]] = None  # Applied projected effects
    activatable_flags: List[int] = []  # Flags of modules with activation cycle (not passive)
