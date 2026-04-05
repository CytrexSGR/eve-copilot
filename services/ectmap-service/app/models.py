"""Pydantic models for ectmap-service."""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MapInfo(BaseModel):
    name: str
    url: str
    port: int
    params: List[str]
    status: str = "unknown"


class SnapshotRequest(BaseModel):
    map_type: str = Field(..., description="ectmap, sovmap, or capitalmap")
    region: Optional[str] = None
    width: int = Field(1920, ge=800, le=3840)
    height: int = Field(1080, ge=600, le=2160)
    wait_ms: int = Field(3000, ge=1000, le=10000)
    params: Dict[str, Any] = Field(default_factory=dict)


class SnapshotResponse(BaseModel):
    snapshot_id: str
    filename: str
    url: str
    map_type: str
    created_at: str
    params: dict


class AtomicSnapshotRequest(BaseModel):
    map_type: str = Field("ectmap", description="ectmap, sovmap, or capitalmap")
    minutes: int = Field(1440, ge=10, le=10080, description="Time window in minutes")
    region: Optional[str] = Field(None, description="Region to zoom into")
    color_mode: str = Field("security", description="alliance, security, faction, etc.")
    width: int = Field(1920, ge=800, le=3840)
    height: int = Field(1080, ge=600, le=2160)
    wait_ms: int = Field(5000, ge=1000, le=15000)
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="Additional map params")


class AtomicSnapshotData(BaseModel):
    war_summary: dict
    conflicts: list
    hot_systems: list


class AtomicSnapshotResponse(BaseModel):
    snapshot_id: str
    image_url: str
    data_url: str
    map_type: str
    minutes: int
    region: Optional[str]
    created_at: str
    params: dict
    data: AtomicSnapshotData


class ViewCreate(BaseModel):
    name: str
    description: Optional[str] = None
    map_type: str
    region: Optional[str] = None
    width: int = 1920
    height: int = 1080
    params: Dict[str, Any] = Field(default_factory=dict)
    auto_snapshot: bool = False
    snapshot_schedule: Optional[str] = None


class ViewResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    map_type: str
    region: Optional[str]
    width: int
    height: int
    params: dict
    auto_snapshot: bool
    snapshot_schedule: Optional[str]
    last_snapshot_at: Optional[str]
    last_snapshot_id: Optional[str]
    created_at: str
