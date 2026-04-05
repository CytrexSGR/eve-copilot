"""HR Service Pydantic schemas."""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# --- Red List ---

class RedListEntity(BaseModel):
    """Red list entry."""
    id: Optional[int] = None
    entity_id: int
    entity_name: Optional[str] = None
    category: str = Field(..., pattern="^(character|corporation|alliance)$")
    severity: int = Field(default=1, ge=1, le=5)
    reason: Optional[str] = None
    added_by: Optional[str] = None
    added_at: Optional[datetime] = None
    active: bool = True


class RedListCreateRequest(BaseModel):
    """Create a red list entry."""
    entity_id: int
    entity_name: Optional[str] = None
    category: str = Field(..., pattern="^(character|corporation|alliance)$")
    severity: int = Field(default=1, ge=1, le=5)
    reason: Optional[str] = None
    added_by: Optional[str] = None


class RedListBulkRequest(BaseModel):
    """Bulk import red list entries."""
    entities: List[RedListCreateRequest]


# --- Vetting ---

class VettingCheckRequest(BaseModel):
    """Request to vet a character."""
    character_id: int
    check_contacts: bool = True
    check_wallet: bool = True
    check_skills: bool = True


class VettingReport(BaseModel):
    """Vetting report result."""
    id: Optional[int] = None
    character_id: int
    character_name: Optional[str] = None
    risk_score: int = Field(default=0, ge=0, le=100)
    flags: Dict[str, Any] = Field(default_factory=dict)
    red_list_hits: List[Dict[str, Any]] = Field(default_factory=list)
    wallet_flags: List[Dict[str, Any]] = Field(default_factory=list)
    skill_flags: List[Dict[str, Any]] = Field(default_factory=list)
    checked_at: Optional[datetime] = None


class SkillSnapshot(BaseModel):
    """Skill history snapshot for injection detection."""
    character_id: int
    total_sp: int
    unallocated_sp: int = 0
    snapshot_at: Optional[datetime] = None


# --- Role Sync ---

class RoleMapping(BaseModel):
    """ESI role to web permission mapping."""
    id: Optional[int] = None
    esi_role: str
    web_permission: str
    priority: int = 0
    active: bool = True


class RoleMappingCreate(BaseModel):
    """Create a role mapping."""
    esi_role: str
    web_permission: str
    priority: int = 0


class RoleSyncResult(BaseModel):
    """Result of a role sync operation."""
    character_id: int
    character_name: Optional[str] = None
    current_roles: List[str] = Field(default_factory=list)
    added_roles: List[str] = Field(default_factory=list)
    removed_roles: List[str] = Field(default_factory=list)
    escalation_alerts: List[str] = Field(default_factory=list)
    synced_at: Optional[datetime] = None


# --- Activity Tracking ---

class FleetSession(BaseModel):
    """Fleet participation record."""
    id: Optional[int] = None
    fleet_id: Optional[int] = None
    fleet_name: Optional[str] = None
    character_id: int
    character_name: Optional[str] = None
    ship_type_id: Optional[int] = None
    ship_name: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    solar_system_id: Optional[int] = None


class FleetSessionCreate(BaseModel):
    """Create a fleet session entry."""
    fleet_id: Optional[int] = None
    fleet_name: Optional[str] = None
    character_id: int
    ship_type_id: Optional[int] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    solar_system_id: Optional[int] = None


class ActivitySummary(BaseModel):
    """Activity summary for a character."""
    character_id: int
    character_name: Optional[str] = None
    fleet_count_30d: int = 0
    kill_count_30d: int = 0
    last_kill_at: Optional[datetime] = None
    last_fleet_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    total_sp: Optional[int] = None
    risk_score: Optional[int] = None
