"""
User Settings and Autonomy Configuration
Defines user preferences for AI agent behavior.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict

# Import enums from core module (prevents circular imports)
from ..core.enums import RiskLevel, AutonomyLevel

# Re-export for backward compatibility
__all__ = ["RiskLevel", "AutonomyLevel", "UserSettings", "get_default_settings"]


class UserSettings(BaseModel):
    """
    User preferences for AI behavior.

    Attributes:
        character_id: EVE character ID
        autonomy_level: Preferred autonomy level (default: RECOMMENDATIONS)
        require_confirmation: Ask before WRITE_HIGH_RISK tools (default: True)
        budget_limit_isk: Max ISK for automated actions (future trading)
        allowed_regions: Restrict operations to specific regions
        blocked_tools: User-blacklisted tools
    """

    model_config = ConfigDict(use_enum_values=False)

    character_id: int
    autonomy_level: AutonomyLevel = AutonomyLevel.RECOMMENDATIONS
    require_confirmation: bool = True
    budget_limit_isk: Optional[float] = None
    allowed_regions: Optional[List[int]] = None
    blocked_tools: List[str] = Field(default_factory=list)

    @field_validator('budget_limit_isk')
    @classmethod
    def validate_budget(cls, v):
        """Ensure budget is positive if set."""
        if v is not None and v <= 0:
            raise ValueError("Budget limit must be positive")
        return v


def get_default_settings(character_id: int) -> UserSettings:
    """
    Get default safe settings for new user.

    Args:
        character_id: EVE character ID

    Returns:
        UserSettings with safe defaults (L1, confirmations enabled)
    """
    return UserSettings(
        character_id=character_id,
        autonomy_level=AutonomyLevel.RECOMMENDATIONS,
        require_confirmation=True
    )
