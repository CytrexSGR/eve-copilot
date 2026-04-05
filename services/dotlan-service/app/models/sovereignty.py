"""Pydantic models for sovereignty data."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SovCampaign(BaseModel):
    """Active sovereignty campaign."""
    model_config = ConfigDict(from_attributes=True)

    campaign_id: int
    solar_system_id: int
    solar_system_name: Optional[str] = None
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    structure_type: str
    defender_name: Optional[str] = None
    defender_id: Optional[int] = None
    score: Optional[float] = None
    status: str = "active"
    first_seen: Optional[datetime] = None
    last_updated: Optional[datetime] = None


class SovChange(BaseModel):
    """Historical sovereignty change."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    solar_system_id: int
    solar_system_name: Optional[str] = None
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    change_type: str
    old_alliance_name: Optional[str] = None
    new_alliance_name: Optional[str] = None
    old_alliance_id: Optional[int] = None
    new_alliance_id: Optional[int] = None
    changed_at: datetime


class ADMHistoryEntry(BaseModel):
    """ADM history data point."""
    timestamp: datetime
    adm_level: float
