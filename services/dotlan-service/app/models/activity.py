"""Pydantic models for system activity data."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class SystemActivity(BaseModel):
    """Current activity for a single system."""
    model_config = ConfigDict(from_attributes=True)

    solar_system_id: int
    solar_system_name: Optional[str] = None
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    security_status: Optional[float] = None
    npc_kills: int = 0
    ship_kills: int = 0
    pod_kills: int = 0
    jumps: int = 0
    timestamp: Optional[datetime] = None


class SystemActivityHistory(BaseModel):
    """Hourly activity data point."""
    timestamp: datetime
    npc_kills: int = 0
    ship_kills: int = 0
    pod_kills: int = 0
    jumps: int = 0


class SystemActivityResponse(BaseModel):
    """Full activity response for a system."""
    solar_system_id: int
    solar_system_name: Optional[str] = None
    latest: Optional[SystemActivity] = None
    history: list[SystemActivityHistory] = []


class HeatmapEntry(BaseModel):
    """Single entry in a heatmap response."""
    solar_system_id: int
    solar_system_name: Optional[str] = None
    value: int = 0
    normalized: float = Field(0.0, ge=0.0, le=1.0, description="0-1 normalized value")


class TopSystemEntry(BaseModel):
    """Entry in a top-systems ranking."""
    solar_system_id: int
    solar_system_name: Optional[str] = None
    region_name: Optional[str] = None
    security_status: Optional[float] = None
    npc_kills: int = 0
    ship_kills: int = 0
    pod_kills: int = 0
    jumps: int = 0
