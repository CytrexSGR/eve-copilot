# app/services/dps/models.py
"""Data models for DPS calculations."""

from typing import Optional, List
from pydantic import BaseModel, Field, computed_field


class DamageProfile(BaseModel):
    """Damage distribution across damage types."""
    em: float = 0
    thermal: float = 0
    kinetic: float = 0
    explosive: float = 0

    @computed_field
    @property
    def total(self) -> float:
        """Total damage across all types."""
        return self.em + self.thermal + self.kinetic + self.explosive


class WeaponAttributes(BaseModel):
    """Weapon module attributes from SDE."""
    type_id: int
    type_name: str
    rate_of_fire_ms: float = Field(description="Rate of fire in milliseconds")
    damage_modifier: float = Field(default=1.0, description="Weapon damage multiplier")
    optimal_range: Optional[float] = None
    falloff: Optional[float] = None
    tracking: Optional[float] = None

    @computed_field
    @property
    def rate_of_fire_seconds(self) -> float:
        """Rate of fire converted to seconds."""
        return self.rate_of_fire_ms / 1000


class AmmoAttributes(BaseModel):
    """Ammunition/charge attributes from SDE."""
    type_id: int
    type_name: str
    damage: DamageProfile
    damage_modifier: float = Field(default=1.0, description="Ammo damage multiplier")


class ShipBonus(BaseModel):
    """Ship bonus from invTraits."""
    ship_type_id: int
    ship_name: str
    skill_id: int = Field(description="-1 for role bonus")
    skill_name: Optional[str] = None
    bonus_value: float
    bonus_type: str = Field(description="e.g., 'damage', 'rate_of_fire', 'range'")
    is_role_bonus: bool = False


class SkillBonus(BaseModel):
    """Skill bonus affecting DPS."""
    skill_id: int
    skill_name: str
    level: int = Field(ge=0, le=5)
    bonus_per_level: float
    bonus_type: str = Field(description="e.g., 'damage_multiplier', 'rate_of_fire'")

    @computed_field
    @property
    def total_bonus(self) -> float:
        """Total bonus at current level."""
        return self.bonus_per_level * self.level


class DPSResult(BaseModel):
    """Complete DPS calculation result."""
    weapon_name: str
    ammo_name: str
    raw_dps: float = Field(description="DPS before skill/ship bonuses")
    skill_multiplier: float = Field(default=1.0)
    ship_multiplier: float = Field(default=1.0)
    total_dps: float
    damage_profile: DamageProfile

    # Breakdown
    skill_bonuses_applied: List[SkillBonus] = Field(default_factory=list)
    ship_bonuses_applied: List[ShipBonus] = Field(default_factory=list)
