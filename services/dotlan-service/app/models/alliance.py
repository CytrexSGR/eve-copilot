"""Pydantic models for alliance statistics."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AllianceStats(BaseModel):
    """Alliance ranking entry."""
    model_config = ConfigDict(from_attributes=True)

    alliance_name: str
    alliance_slug: str
    alliance_id: Optional[int] = None
    systems_count: int = 0
    member_count: int = 0
    corp_count: int = 0
    rank_by_systems: Optional[int] = None
    snapshot_date: date


class AllianceStatsHistory(BaseModel):
    """Alliance stats over time."""
    alliance_name: str
    alliance_id: Optional[int] = None
    snapshots: list[AllianceStats] = []
